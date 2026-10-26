"""Cost and efficiency summary.

EKS: per-node hourly price (on-demand from aws/pricing-<type>.json = Pricing API, spot from the latest per-AZ price in aws/ec2-spot-prices.json) gives a monthly estimate; 7-day CPU p95 gives idle cost, KRR saved cores give over-request cost,
plus EIP, NAT, LB and EKS cluster charges (including the extended support surcharge). If aws/ce-cost-30d.json (Cost Explorer) exists it is shown next to the actual bill. Chargeback is approximated by each namespace's share of requests.
Small k3s cluster: there is no bill, so only core efficiency (allocatable vs p95 actual vs requests) and "could one node be removed?" are produced.

Price constants (ap-northeast-2, public list prices as of 2026-10, for estimation): idle EIP 0.005 USD/h, NAT gateway 0.059 USD/h + data, ALB/NLB 0.0225 USD/h + LCU, EKS cluster 0.10 USD/h, extended support 0.60 USD/h.
Shape is described in SKILL.md.
"""

from __future__ import annotations

import contextlib
import csv
import json
from collections import Counter
from pathlib import Path

from .snapshot import load_json

HOURS = 730
RATE = {"eip_idle": 0.005, "nat": 0.059, "lb": 0.0225, "eks_cluster": 0.10, "eks_extended": 0.60}


def _metric(snap: Path, qid: str, key: str) -> dict[str, float]:
    out = {}
    for s in (load_json(snap / "metrics" / f"{qid}.json") or {}).get("result") or []:
        with contextlib.suppress(KeyError, ValueError, TypeError, IndexError):
            out[(s.get("metric") or {}).get(key)] = float(s["value"][1])
    return out


def _q(v) -> float:
    s = str(v or "0")
    for u, mul in (("Ki", 1024), ("Mi", 1024**2), ("Gi", 1024**3), ("m", 0.001)):
        if s.endswith(u):
            return float(s[: -len(u)]) * mul
    try:
        return float(s)
    except ValueError:
        return 0.0


def _ondemand_prices(snap: Path) -> dict[str, dict]:
    out = {}
    for f in sorted((snap / "aws").glob("pricing-*.json")) if (snap / "aws").is_dir() else []:
        itype = f.name[len("pricing-") : -len(".json")]
        d = load_json(f) or {}
        pl = d.get("PriceList") or []
        if not pl:
            continue
        try:
            prod = json.loads(pl[0]) if isinstance(pl[0], str) else pl[0]
            od = next(iter((prod.get("terms") or {}).get("OnDemand", {}).values()))
            pd = next(iter(od["priceDimensions"].values()))
            attrs = prod.get("product", {}).get("attributes", {})
            out[itype] = {"usd_h": float(pd["pricePerUnit"]["USD"]), "vcpu": attrs.get("vcpu"), "memory": attrs.get("memory")}
        except (IndexError, KeyError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return out


def _spot_prices(snap: Path) -> dict[tuple, float]:
    rows = load_json(snap / "aws" / "ec2-spot-prices.json") or []
    latest: dict[tuple, tuple] = {}
    for r in rows if isinstance(rows, list) else []:
        k = (r.get("type"), r.get("az"))
        ts = r.get("ts") or ""
        if k not in latest or ts > latest[k][0]:
            with contextlib.suppress(TypeError, ValueError):
                latest[k] = (ts, float(r.get("price")))
    return {k: v[1] for k, v in latest.items()}


def analyze(snap: Path, inv: dict | None, summary: dict | None) -> dict:
    inv = inv or {}
    summary = summary or {}
    platform = (inv.get("cluster") or {}).get("platform")
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    nodes = (inv.get("nodes") or {}).get("nodes") or []
    p95 = _metric(snap, "node_cpu_usage_ratio_p95_7d", "node")
    req = _metric(snap, "node_cpu_request_ratio", "node")
    mem_p95 = _metric(snap, "node_memory_usage_ratio_p95_7d", "node")
    # ---- node efficiency (common) ----
    node_rows = []
    for n in nodes:
        alloc = n.get("allocatable") or {}
        node_rows.append(
            {
                "node": n["name"],
                "instance_type": n.get("instance_type"),
                "capacity_type": (n.get("capacity_type") or "").lower().replace("_", "-") or None,
                "zone": n.get("zone"),
                "pool": n.get("nodepool") or (("nodegroup:" + n["nodegroup"]) if n.get("nodegroup") else None),
                "cpu": round(_q(alloc.get("cpu")), 2),
                "memory_gb": round(_q(alloc.get("memory")) / 1024**3, 1),
                "cpu_p95_ratio": p95.get(n["name"]),
                "cpu_request_ratio": req.get(n["name"]),
                "memory_p95_ratio": mem_p95.get(n["name"]),
            }
        )
    total_cpu = sum(r["cpu"] for r in node_rows)
    used_cpu = sum((r["cpu_p95_ratio"] or 0) * r["cpu"] for r in node_rows)
    req_cpu = sum((r["cpu_request_ratio"] or 0) * r["cpu"] for r in node_rows)
    efficiency = {
        "nodes": len(node_rows),
        "allocatable_cpu": round(total_cpu, 2),
        "p95_used_cpu": round(used_cpu, 2),
        "requested_cpu": round(req_cpu, 2),
        "p95_util_ratio": round(used_cpu / total_cpu, 3) if total_cpu else None,
        "request_ratio": round(req_cpu / total_cpu, 3) if total_cpu else None,
        "request_over_usage": round(req_cpu / used_cpu, 1) if used_cpu else None,
    }
    n1 = (summary.get("resilience") or {}).get("n_plus_one") or {}
    efficiency["can_drop_largest_node"] = bool(n1.get("ok")) if n1.get("available") else None
    # ---- trend ----
    trend = []
    hist = snap.parent / "history.csv"
    if hist.is_file():
        try:
            for r in csv.DictReader(hist.open(encoding="utf-8")):
                trend.append({"snapshot": r.get("snapshot"), "nodes": int(r.get("nodes") or 0)})
        except (OSError, ValueError):
            pass
    out = {"platform": platform, "efficiency": efficiency, "node_count_trend": trend[-12:], "nodes": node_rows}
    if platform != "eks":
        out["pricing"] = {"available": False, "note": "no bill (small k3s cluster). Core efficiency and N-1 only"}
        return out
    # ---- EKS pricing ----
    od = _ondemand_prices(snap)
    spot = _spot_prices(snap)
    pools = {p["metadata"]["name"]: p for p in ((load_json(snap / "objects" / "nodepools.karpenter.sh.json") or {}).get("items") or [])}

    def pool_allows_spot(pool):
        p = pools.get(pool)
        if not p:
            return None
        for r in (((p.get("spec") or {}).get("template") or {}).get("spec") or {}).get("requirements") or []:
            if r.get("key") == "karpenter.sh/capacity-type":
                return "spot" in (r.get("values") or [])
        return True

    compute = 0.0
    spot_m = 0.0
    od_m = 0.0
    idle = 0.0
    savings = 0.0
    for r in node_rows:
        t = r["instance_type"]
        odp = (od.get(t) or {}).get("usd_h")
        sp = spot.get((t, r["zone"]))
        is_spot = r["capacity_type"] == "spot"
        hourly = sp if (is_spot and sp is not None) else odp
        r["usd_h"] = round(hourly, 4) if hourly is not None else None
        r["ondemand_usd_h"] = odp
        r["spot_usd_h"] = sp
        r["monthly_usd"] = round(hourly * HOURS, 2) if hourly is not None else None
        r["idle_monthly_usd"] = round(hourly * HOURS * (1 - (r["cpu_p95_ratio"] or 0)), 2) if hourly is not None and r["cpu_p95_ratio"] is not None else None
        r["pool_allows_spot"] = pool_allows_spot(r["pool"]) if r["pool"] and not str(r["pool"]).startswith("nodegroup:") else False
        r["system"] = str(r["pool"] or "").startswith(("system", "nodegroup:")) or str(r["pool"] or "").find("system") >= 0
        if hourly is not None:
            compute += hourly * HOURS
            if is_spot:
                spot_m += hourly * HOURS
                if odp:
                    savings += (odp - hourly) * HOURS
            else:
                od_m += hourly * HOURS
            if r["idle_monthly_usd"] is not None:
                idle += r["idle_monthly_usd"]
    by_pool = Counter()
    for r in node_rows:
        if r.get("monthly_usd") is not None:
            by_pool[r["pool"] or "?"] += r["monthly_usd"]
    on_demand_in_spot_pool = [r["node"] for r in node_rows if r["capacity_type"] != "spot" and r["pool_allows_spot"]]
    idle_nodes = [
        {"node": r["node"], "instance_type": r["instance_type"], "pool": r["pool"], "cpu_p95_ratio": r["cpu_p95_ratio"], "memory_p95_ratio": r["memory_p95_ratio"], "monthly_usd": r["monthly_usd"]}
        for r in node_rows
        if r["cpu_p95_ratio"] is not None and r["cpu_p95_ratio"] < 0.05 and (r["memory_p95_ratio"] or 0) < 0.3 and not r["system"]
    ]
    # ---- over-request cost ----
    krr_tot = ((summary.get("resources") or {}).get("krr") or {}).get("totals") or {}
    usd_per_core_month = compute / total_cpu if total_cpu and compute else None
    saving_cores = krr_tot.get("cpu_request_saving_cores")
    request_waste = round(saving_cores * usd_per_core_month, 2) if (saving_cores and usd_per_core_month) else None
    # ---- EIP, NAT, LB, EKS charges ----
    eips = [e for e in (load_json(snap / "aws" / "ec2-addresses.json") or []) if isinstance(e, dict)]
    eip_unused = [e["ip"] for e in eips if not e.get("association")]
    nats = [n for n in (load_json(snap / "aws" / "ec2-nat-gateways.json") or []) if isinstance(n, dict)]
    lbs = ((summary.get("traffic") or {}).get("alb") or {}).get("lbs") or []
    idle_lbs = [ln["name"] for ln in lbs if (ln.get("type") == "application" and (ln.get("requests_24h") or 0) == 0) or (ln.get("type") == "network" and (ln.get("processed_bytes_24h") or 0) == 0)]
    support = ((inv.get("cluster") or {}).get("eks") or {}).get("support_type")
    eks_fee = RATE["eks_extended"] * HOURS if support == "EXTENDED" else RATE["eks_cluster"] * HOURS
    fixed = {
        "eip_unused": len(eip_unused),
        "eip_unused_monthly_usd": round(len(eip_unused) * RATE["eip_idle"] * HOURS, 2),
        "eips_total": len(eips),
        "nat_gateways": len(nats),
        "nat_monthly_usd_base": round(len(nats) * RATE["nat"] * HOURS, 2),
        "load_balancers": len(lbs),
        "lb_monthly_usd_base": round(len(lbs) * RATE["lb"] * HOURS, 2),
        "idle_load_balancers": idle_lbs,
        "eks_cluster_monthly_usd": round(eks_fee, 2),
        "eks_support_type": support,
        "eks_extended_surcharge_monthly_usd": round((RATE["eks_extended"] - RATE["eks_cluster"]) * HOURS, 2) if support == "EXTENDED" else 0.0,
    }
    # ---- chargeback ----
    ns_cpu: Counter = Counter()
    for p in (load_json(snap / "objects" / "pods.json") or {}).get("items") or []:
        if p.get("status", {}).get("phase") != "Running":
            continue
        for c in (p.get("spec") or {}).get("containers") or []:
            ns_cpu[p["metadata"]["namespace"]] += _q(((c.get("resources") or {}).get("requests") or {}).get("cpu"))
    tot_req = sum(ns_cpu.values())
    chargeback = [
        {"namespace": ns, "cpu_request": round(v, 2), "share": round(v / tot_req, 3) if tot_req else None, "monthly_usd_est": round(v / tot_req * compute, 2) if tot_req and compute else None, "prod": ns in prod}
        for ns, v in ns_cpu.most_common(15)
    ]
    # ---- Cost Explorer ----
    ce = load_json(snap / "aws" / "ce-cost-30d.json")
    bill = None
    if ce:
        groups = ((ce.get("ResultsByTime") or [{}])[0].get("Groups")) or []
        rows = sorted([(g["Keys"][0], float(g["Metrics"]["UnblendedCost"]["Amount"])) for g in groups if g.get("Keys")], key=lambda r: -r[1])
        bill = {
            "window": (ce.get("ResultsByTime") or [{}])[0].get("TimePeriod"),
            "total_usd": round(sum(v for _, v in rows), 2),
            "by_service": [{"service": k, "usd": round(v, 2)} for k, v in rows[:12]],
            "note": "Cost Explorer covers the whole account (including RDS, S3 etc. outside this cluster). 0.01 USD per request",
        }
    out.update(
        {
            "pricing": {"available": bool(od), "ondemand_types": od, "spot_latest": {f"{t}@{az}": p for (t, az), p in spot.items()}, "hours_per_month": HOURS, "rates": RATE},
            "compute": {
                "monthly_usd": round(compute, 2),
                "spot_monthly_usd": round(spot_m, 2),
                "ondemand_monthly_usd": round(od_m, 2),
                "spot_node_share": round(sum(1 for r in node_rows if r["capacity_type"] == "spot") / len(node_rows), 2) if node_rows else None,
                "spot_savings_monthly_usd": round(savings, 2),
                "by_pool": {k: round(v, 2) for k, v in by_pool.items()},
                "usd_per_core_month": round(usd_per_core_month, 2) if usd_per_core_month else None,
                "idle_monthly_usd": round(idle, 2),
                "idle_ratio": round(idle / compute, 2) if compute else None,
                "idle_nodes": idle_nodes,
                "on_demand_in_spot_pool": on_demand_in_spot_pool,
            },
            "request_waste": {"krr_saving_cores": saving_cores, "monthly_usd_est": request_waste, "requests_cpu_total": krr_tot.get("cpu_request_current"), "recommended_cpu_total": krr_tot.get("cpu_request_recommended")},
            "fixed": fixed,
            "chargeback": chargeback,
            "bill": bill,
            "monthly_total_est": round(compute + fixed["nat_monthly_usd_base"] + fixed["lb_monthly_usd_base"] + fixed["eks_cluster_monthly_usd"] + fixed["eip_unused_monthly_usd"], 2),
        }
    )
    return out
