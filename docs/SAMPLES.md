# Making a sample report

The reports in `samples/` are real runs with names replaced. Numbers, findings and wording are left as they are. To add or refresh one:

1. Run `/kubegap` or `/kubegap full` and find the snapshot folder the last line of `report.md` names.
2. Copy `report.md` out of the snapshot, and for a full audit `report-details.md` too (a daily audit writes one file).
3. Mask tokens, account ids and private IPs in place:

   ```bash
   scripts/kubegap mask --ips report.md report-details.md
   ```

4. Replace names with placeholders. The map file is yours and is not committed; the format is in the header of `scripts/scrub-sample.py`. Every hostname in the `hosts` list gets a placeholder of its own, so two hosts never end up with the same name. Three things are replaced whatever your map holds: load balancer DNS names (`*.elb.<region>.amazonaws.com`), the names the AWS Load Balancer Controller gives its load balancers and target groups (`k8s-<namespace>-<name>-<hash>`), and the path of the snapshot folder.

   ```bash
   scripts/scrub-sample.py --map ~/.kubegap/scrub-map.yaml report.md         samples/<lang>/<cluster>/<mode>/report.md
   scripts/scrub-sample.py --map ~/.kubegap/scrub-map.yaml report-details.md samples/<lang>/<cluster>/<mode>/report-details.md
   ```

5. Look for what the map missed. Reading is not enough for a file of ten thousand lines: list the names the snapshot holds (namespaces, nodes, workloads, CronJobs, ConfigMaps, PVCs, Ingress hosts) and search the scrubbed files for each. Anything found goes into the map, not into a hand edit, so the next refresh gets it too. Node names that carry a private IP (`ip-10-0-1-23.<region>.compute.internal`) need a rule of their own; the script's header shows one.
6. Add the row to `samples/README.md`.
7. When a sample README shows changed (`samples/<lang>/eks/full`, `samples/<lang>/k3s/daily`), make the pictures again: `uvx --with playwright --with markdown python scripts/make-media.py`. The terminal recording is made with `vhs` from `docs/media/src/` (its `env.sh` says how).

Folder rule: `samples/<lang>/<cluster>/<mode>/` with `lang` in `en`, `ko`; `cluster` in `eks`, `k3s`; `mode` in `daily`, `full`.
