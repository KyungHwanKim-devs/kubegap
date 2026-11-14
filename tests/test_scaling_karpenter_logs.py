"""The Karpenter log lines lib/summaries/scaling.py reads, built from the logging calls cited in references/sources.md ("lib/summaries/scaling.py Karpenter log facts", #129)."""

from __future__ import annotations

from lib.foundations.karpenterlog import disruption_line, launch_failure_key

# pkg/controllers/disruption/controller.go:188@v0.37.0 with Command.String() types.go:184-194@v0.37.0
L037 = '{"level":"INFO","time":"2026-11-04T00:30:10.620Z","logger":"controller","message":"disrupting via consolidation delete, terminating 1 nodes (3 pods) ip-10-0-1-5.ap-northeast-2.compute.internal/m6g.large/spot","commit":"490ef94","command-id":"b1"}'
# controller.go:188@v1.0.0 with types.go:141-151@v1.0.0 and the reason as a field
L10 = '{"level":"INFO","time":"2026-11-04T00:30:10.620Z","logger":"controller","message":"disrupting nodeclaim(s) via delete, terminating 2 nodes (5 pods) ip-a/m6g.large/spot, ip-b/m6g.large/spot","commit":"abc","command-id":"b2","reason":"underutilized"}'
# controller.go:205@v1.3.0 (queue.go:295@v1.6.0) with LogValues types.go:143-176@v1.3.0
L13 = '{"level":"INFO","time":"2026-11-04T00:30:10.620Z","logger":"controller","message":"disrupting node(s)","commit":"abc","command-id":"b3","reason":"drifted","decision":"replace","disrupted-node-count":1,"replacement-node-count":1,"pod-count":4,"disrupted-nodes":[{"Node":{"name":"ip-c"},"NodeClaim":{"name":"default-x1"},"instance-type":"m6g.large","capacity-type":"spot"}],"replacement-nodes":[{"capacity-type":"spot","instance-types":"m6g.large, m6g.xlarge"}]}'
# queue.go:388-390@v1.15.1: the reason is the first token of the command string (types.go:350-380@v1.15.1), capitalised (pkg/apis/v1/nodepool.go:184-189@v1.15.1), no reason field
L115 = '{"level":"INFO","time":"2026-11-04T00:30:10.620Z","logger":"controller","message":"disrupting node(s)","commit":"abc","command":"Underutilized/4f2a: delete: nodepools=[default]: [ip-d, ip-e] (savings: $0.12)","decision":"delete","disrupted-node-count":2,"replacement-node-count":0,"pod-count":6,"disrupted-nodes":[{"Node":{"name":"ip-d"},"NodeClaim":{"name":"default-y1"},"instance-type":"m6g.large","capacity-type":"spot"},{"Node":{"name":"ip-e"},"NodeClaim":{"name":"default-y2"},"instance-type":"m6g.large","capacity-type":"spot"}],"replacement-nodes":[]}'


def test_every_shape_of_the_disruption_line_is_read():
    assert disruption_line(L037) == ("consolidation", "delete", 1, 3, "ip-10-0-1-5.ap-northeast-2.compute.internal/m6g.large/spot")
    assert disruption_line(L10) == ("underutilized", "delete", 2, 5, "ip-a/m6g.large/spot, ip-b/m6g.large/spot")
    assert disruption_line(L13) == ("drifted", "replace", 1, 4, "ip-c")
    assert disruption_line(L115) == ("underutilized", "delete", 2, 6, "ip-d, ip-e")
    assert disruption_line('{"level":"INFO","logger":"controller","message":"deleted nodeclaim","NodeClaim":{"name":"default-fzhkl"}}') is None


def test_launch_failures_are_keyed_by_code_or_phrase():
    # pkg/controllers/nodeclaim/lifecycle/launch.go:103@v0.37.0 (ERROR, "launching nodeclaim") and the controller-runtime Reconciler error form (:132@v1.15.1)
    assert launch_failure_key('{"level":"ERROR","logger":"controller","message":"launching nodeclaim","error":"creating instance, with fleet error(s), UnauthorizedOperation: You are not authorized"}') == "launching nodeclaim"
    assert (
        launch_failure_key(
            '{"level":"ERROR","logger":"controller","message":"Reconciler error","error":"launching nodeclaim, creating instance, with fleet error(s), InsufficientInstanceCapacity: We currently do not have sufficient capacity"}'
        )
        == "InsufficientInstanceCapacity"
    )
    assert launch_failure_key('{"level":"INFO","logger":"controller","message":"launched nodeclaim","NodeClaim":{"name":"a"}}') is None
