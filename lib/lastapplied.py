"""The apiVersion each object was applied with, read from the saved snapshot.

kubectl stores the manifest it applied in the `kubectl.kubernetes.io/last-applied-configuration` annotation, so an object the API server converted long ago still
says which apiVersion its owner writes. That is what pluto judges. pluto's own in-cluster mode reads it by Listing every resource the server advertises, Secrets
included when the identity may (FairwindsOps/pluto pkg/discovery-api/discovery_api.go:83,115@v5.24.5; no flag excludes a resource, cmd/root.go:87-114), and the
Secret values then reach the pluto process. kubegap already saved every kind except Secrets in `objects/`, so the step hands pluto a List built here on stdin
(`pluto detect -`, cmd/root.go:403-411) and pluto never contacts the cluster.

Each entry holds what pluto reads and nothing else: `kind`, `apiVersion`, `metadata.name` and `metadata.namespace` (`Stub`, pkg/api/versions.go:46-57). apiVersion and
kind come from the annotation; name and namespace from the object itself, because a manifest applied with `kubectl apply -n` or with generateName need not carry them.
An object whose annotation names another kind is skipped as pluto skips it (discovery_api.go:148): a ControllerRevision carries the annotations of its StatefulSet or
DaemonSet (kubernetes/kubernetes pkg/controller/statefulset/stateful_set_utils.go:594-595@v1.37.2, pkg/controller/daemon/update.go:539@v1.37.2), so the manifest in it is not its own. ConfigMap annotations are scrubbed before the file is written
(lib/scrub.py), which loses nothing here: versions.yaml@v5.24.5 has no rule for ConfigMap or Secret.

A kind `objects.dump-all` excludes or cannot read is not in the snapshot. Against the 112 rows of versions.yaml that costs nothing pluto could judge: `bindings`, the access and token reviews and the
`metrics.eks.amazonaws.com` kinds refused the List anyway, `componentstatuses`, `pods.metrics.k8s.io` and `nodes.metrics.k8s.io` have no rule, and Events carry no last-applied annotation because nobody
applies them; an Event applied by hand with `events.k8s.io/v1beta1` would be missed.
"""

from __future__ import annotations

import json
from pathlib import Path

from .scrub import LAST_APPLIED
from .snapshot import load_json


def stubs(snap: Path) -> list[dict]:
    """One {apiVersion, kind, metadata{name, namespace?}} per saved object that carries a readable last-applied annotation of its own kind, in file then item order."""
    out: list[dict] = []
    for path in sorted((snap / "objects").glob("*.json")):
        for obj in (load_json(path) or {}).get("items") or []:
            meta = obj.get("metadata") or {}
            text = (meta.get("annotations") or {}).get(LAST_APPLIED)
            if not isinstance(text, str):  # absent, or replaced by {len, shape} on a ConfigMap (lib/scrub.py)
                continue
            try:
                manifest = json.loads(text)
            except ValueError:
                continue
            if not isinstance(manifest, dict) or manifest.get("kind") != obj.get("kind"):
                continue
            stub_meta = {"name": meta.get("name")}
            if meta.get("namespace"):
                stub_meta["namespace"] = meta["namespace"]
            out.append({"apiVersion": manifest.get("apiVersion"), "kind": manifest.get("kind"), "metadata": stub_meta})
    return out


def pluto_input(snap: Path) -> tuple[str, int]:
    """(the JSON List `pluto detect -` reads, number of entries). pluto expands a List into its items (pkg/api/versions.go:145,185@v5.24.5); an empty one is a valid input."""
    items = stubs(snap)
    return json.dumps({"apiVersion": "v1", "kind": "List", "items": items}), len(items)
