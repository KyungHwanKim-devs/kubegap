"""Verdicts that a first run on a real cluster showed to be wrong (2026-11-14). A daily run cannot open the raw material to doubt a verdict,
so each of these has to be right in the check itself."""

from __future__ import annotations

import re

from lib.foundations import scrub
from lib.foundations.signatures import load as load_signatures
from lib.judgement.evaluate import evidence
from lib.summaries.resilience import backup


def test_jvm_option_names_are_not_an_out_of_memory_error():
    sig = next(s for s in load_signatures(["core"])[0] if s.id == "elasticsearch.oom")
    pat = re.compile(sig.pattern)
    startup = "[2026-11-14T01:13:20,101][INFO ][o.o.n.Node] JVM arguments [-Xms512m, -XX:+HeapDumpOnOutOfMemoryError, -XX:+ExitOnOutOfMemoryError, -XX:OnOutOfMemoryError=kill]"
    assert not pat.search(startup)
    assert pat.search("fatal error in thread [elasticsearch[n][search][T#3]], exiting java.lang.OutOfMemoryError: Java heap space")
    assert pat.search("Caused by: OutOfMemoryError: unable to create native thread")


def test_a_reference_to_another_variable_is_not_a_literal_password():
    assert scrub.env_secret_like("REDISCLI_AUTH", "$(REDIS_PASSWORD)") is False  # expanded by Kubernetes from a variable that may come from a Secret
    assert scrub.env_secret_like("REDISCLI_AUTH", "correct-horse-battery") is True


def test_a_field_that_names_where_a_secret_is_is_not_a_secret():
    template = "volumes:\n  - secret:\n      secretName: istio-ca-root-cert\n  tokenPath: /var/run/secrets/tokens\npassword: s3cr3t-value-here\n"
    assert scrub.secret_like_keys({"config": template}) == ["config:password"]


def test_a_copy_to_another_node_of_the_cluster_is_not_off_the_cluster():
    nodes = {"kkh", "192.168.0.101"}
    for text in ("rsync -a /snapshots/ root@kkh:/backup/", "scp dump.sql backup@192.168.0.101:/data"):
        assert not backup.OFFSITE_RE.search(backup._without_copies_to_nodes(text, nodes)), text
    assert backup.OFFSITE_RE.search(backup._without_copies_to_nodes("rsync -a /snapshots/ backup@vault.example.com:/k3s/", nodes))
    assert backup.OFFSITE_RE.search(backup._without_copies_to_nodes("restic backup /dumps", nodes))


def test_oom_evidence_tells_the_history_of_replaced_pods_from_the_pod_running_now():
    """`live_pod_restarts_max` counts the pods that were ended by OOM and still run (lib/summaries/resilience/oom.py), never the pod that replaced
    one. A daily run read "(the pods running now: 0 at most)" as the current pod's restart count and wrote 0 for a pod that had restarted once."""
    gone = {"kernel_any_node_read": False, "pods_oomkilled": 1, "pods_replaced": 1, "restarts_of_those_pods": 163, "live_pod_restarts_max": 0}
    assert "1 already replaced, 163 restarts in those pods (none of those pods is running now)" in evidence.oom_text(gone)
    some = {"kernel_any_node_read": False, "pods_oomkilled": 2, "pods_replaced": 1, "restarts_of_those_pods": 11, "live_pod_restarts_max": 9}
    assert "1 already replaced, 11 restarts in those pods (those of them still running: 9 at most)" in evidence.oom_text(some)


def test_a_line_of_code_that_reads_a_credential_is_not_one():
    """A script kept in a ConfigMap: the lines that read a token from the environment or from a function are not the token; a quoted literal is."""
    script = "\n".join(
        [
            'TOKEN = os.environ["DISCORD_BOT_TOKEN"]',
            'OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")',
            '    client_secret=env("x_api_key_secret"),',
            "token = load_token()",
            'API_KEY = "sk-live-0123456789abcdef"',
        ]
    )
    assert scrub.secret_like_keys({"bot.py": script}) == ["bot.py:API_KEY"]


def test_a_variable_that_names_a_secret_object_is_not_a_credential():
    assert not scrub.env_secret_like("TS_KUBE_SECRET", "tailscale-state-proxy")  # tailscale containerboot: the name of the Secret the state goes to
    assert scrub.env_secret_like("APP_SECRET", "tailscale-state-proxy")


def test_a_service_of_a_helm_release_is_declared_by_its_marks(tmp_path):
    import json

    from lib.output import outline

    (tmp_path / "objects").mkdir()
    svc = {"metadata": {"namespace": "middleware", "name": "kafka-external", "labels": {"app.kubernetes.io/managed-by": "Helm"}, "annotations": {"meta.helm.sh/release-name": "kafka", "meta.helm.sh/release-namespace": "middleware"}}}
    plain = {"metadata": {"namespace": "middleware", "name": "by-hand"}}
    (tmp_path / "objects" / "services.json").write_text(json.dumps({"items": [svc, plain]}))
    who = outline.declared_by_marks(tmp_path, "loadbalancer/middleware/kafka-external")
    assert who["helm_release"] == "middleware/kafka" and who["managed_by"] == "helm" and "services" in who["read_from"]
    assert outline.declared_by_marks(tmp_path, "loadbalancer/middleware/by-hand") is None
