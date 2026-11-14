# Sourced by kubegap-run.tape. Run from an empty folder, with KUBEGAP_ROOT set to the repository:
#   mkdir -p snapshots/demo && cp -R "$KUBEGAP_ROOT/tests/fixtures/snapshot-k3s" snapshots/demo/2026-11-07T10-23-00
#   KUBEGAP_HOME=$PWD "$KUBEGAP_ROOT/scripts/kubegap" summarize --context demo
#   cp "$KUBEGAP_ROOT"/docs/media/src/{env.sh,kubegap-run.tape} . && vhs kubegap-run.tape
# The snapshot is the committed fixture, whose names are placeholders, so nothing of a real cluster is on screen.
export KUBEGAP_HOME=$PWD
PS1='$ '
kubegap() { "${KUBEGAP_ROOT:?set KUBEGAP_ROOT to the kubegap repository}/scripts/kubegap" "$@" 2>&1 | sed "s#$PWD#~/.kubegap#g" | cut -c1-148; }
clear
