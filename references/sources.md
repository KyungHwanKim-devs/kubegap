# Source-verified facts

What kubegap relies on about other software, where kubegap relies on it, and the line in that software's source that makes it true. The rule behind this file is in `references/development.md`: a fact about another project comes from its source at the version kubegap pins or supports, cited as `file:line@version`. A fact that could not be found in source is written as **unverified** with the reason.

Versions read are the ones seen on the two clusters and the newest release at the time of reading. Real runs on the clusters are the second layer of evidence; each section says what was read in source and what was only observed.

Data files carry the citation next to the entry as a `source:` key. `tests/test_sources.py` fails when an entry of a covered file has none.

## Log signatures (#129)

`logs.signatures` matches the patterns in `collectors/*/signatures.yaml` and `signatures/catalog.yaml` against the component pod logs (`lib/logs.py` `scan`). A pattern the component never prints never matches and the signature stays silent.

Covered so far: CoreDNS. The other collectors and `signatures/catalog.yaml` are not yet read.

### CoreDNS

Versions read: v1.11.3 (EKS add-on `v1.11.3-eksbuild.1` on the EKS cluster), v1.12.3 (the image in `manifests/coredns.yaml@v1.33.5+k3s1`, the k3s cluster), v1.15.0 (newest release). Go strings were read at go1.21.0 (the `go` line of `go.mod@v1.11.3`) and go1.26.0 (`go.mod@v1.15.0`).

How a CoreDNS line looks. Text format is the default: the level as `[ERROR] `, `[WARNING] `, `[INFO] ` or `[FATAL] ` (`plugin/pkg/log/log.go:101@v1.11.3`), then `plugin/<name>: ` for a plugin logger (`plugin/pkg/log/plugin.go:15@v1.11.3`, `:15@v1.12.3`, `:16@v1.15.0`), then the message. v1.15.0 added `-log-format json` (`coremain/run.go:33@v1.15.0`); in JSON mode the plugin name goes into a `"plugin"` field (`plugin/pkg/log/json.go:105@v1.15.0`) and `plugin/<name>: ` is not in the line, so `coredns.loop` and the `plugin/errors` parts of the patterns below do not match JSON logs. Neither cluster's manifest passes the flag (`manifests/coredns.yaml:137@v1.33.5+k3s1` passes only `-conf`). The EKS add-on's arguments were observed on the cluster, not read in source: the add-on manifest is not published.

| Signature | What kubegap relies on | Source | Holds for |
|---|---|---|---|
| `coredns.servfail` | A SERVFAIL that CoreDNS itself returns is logged by the `errors` plugin as `plugin/errors: 2 <name> <type>: <error>`: the rcode is printed as a number, `%d` | `plugin/errors/errors.go:97@v1.11.3`, `:97@v1.12.3`, `:118@v1.15.0` | all three |
| | The `forward` plugin returns `dns.RcodeServerFailure` (2) with the upstream error, or with `no healthy proxies` when every upstream is down, so upstream failures reach the `errors` line above | `plugin/forward/forward.go:202,205@v1.11.3`, `:223,226@v1.12.3`, `:294,297@v1.15.0` | all three |
| | The word `SERVFAIL` appears only in the query log of the `log` plugin, whose `{rcode}` is the rcode name (`plugin/pkg/replacer/replacer.go:67`, `plugin/log/log.go:69@v1.11.3`, `:89@v1.15.0`). The `log` plugin is not in the k3s default Corefile (`manifests/coredns.yaml:55-77@v1.33.5+k3s1`). For EKS this is **unverified**: the add-on's default Corefile is not published in a source repository; a run records whether the cluster's Corefile has `log` in `coredns.summary` `config.log` (`lib/coredns.py:79`) | as listed | all three |
| `coredns.upstream-timeout` | The upstream error text reaches the `errors` line (rows above). A read deadline prints `i/o timeout` (`src/internal/poll/fd.go:60@go1.21.0`, `@go1.26.0`) inside `read udp <src>-><dst>: ` from `net.OpError` (`src/net/net.go:469@go1.21.0`, `:501@go1.26.0`); `unreachable` comes from errno 101 `network is unreachable` (`src/syscall/zerrors_linux_amd64.go:1458@go1.21.0`, `:1456@go1.26.0`) | as listed | all three |
| `coredns.loop` | The `loop` plugin logs `Loop (<src> -> <dst>) detected for zone "<zone>"` with `Fatalf`, so the process exits and the pod restarts; the line reads `[FATAL] plugin/loop: Loop (` | `plugin/loop/loop.go:53@v1.11.3`, `:53@v1.12.3`, `:52@v1.15.0` | all three, text format |
| `coredns.reload-failed` | The `reload` plugin logs `Corefile parse failed: <err>` (warning) when the new Corefile does not parse and `Corefile changed but reload failed: <err>` (error) when the restart fails; both lines start `plugin/reload: ` | `plugin/reload/reload.go:97,111@v1.11.3`, `:97,111@v1.12.3`, `:116,134@v1.15.0` | all three |
| | A directive error inside `<err>` reads `<file>:<line> - Error during parsing: <msg>`, from CoreDNS's fork of the Caddy parser | `coredns/caddy caddyfile/dispenser.go:229@v1.1.1` (`go.mod@v1.11.3`), `:238@8de985351a98` (`go.mod@v1.12.3`), `:238@v1.1.4` (`go.mod@v1.15.0`) | all three |

Notes that do not change a pattern:

- v1.15.0 can consolidate repeated errors (`errors { consolidate ... }`, `plugin/errors/errors.go:53-80@v1.15.0`), in which case the individual `plugin/errors: 2 ...` lines are replaced by a summary line. Neither default Corefile configures it.
- `Error during parsing` also appears when a pod starts with a broken Corefile; there the process exits instead of keeping the old configuration. `coredns.reload-failed` counts both.
- A timeout line also contains `plugin/errors: 2 `, so it counts under both `coredns.upstream-timeout` and `coredns.servfail`. Both describe the same event from two sides: the cause, and the answer the client got.

Corrections found in source:

- `coredns.servfail` matched only ` SERVFAIL `, which only the `log` plugin prints. With the k3s default Corefile, or any Corefile without `log`, it could never match, so the signature stayed silent through upstream outages. The pattern now also matches `plugin/errors: 2 `, the line CoreDNS writes when it answers SERVFAIL itself. `tests/test_sources.py` holds lines built from the format strings above.
