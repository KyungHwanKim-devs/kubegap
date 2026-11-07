"""Component detection rules.

The rules live in this one file; each collector folder also has a `detect` file, and this list serves as the index
of those files. A rule is "installed if any of the following match" (`any`), and the evidence kinds are:
  daemonset / deployment / statefulset / cronjob: "namespace/name", each side an fnmatch glob (`*` anywhere, `?`, `[...]`): `*/*grafana*` is
                "name contains grafana in any namespace", `*/velero` is "name is exactly velero", `kube-system/coredns` is exact on both sides.
                A name pattern without a leading `*` is anchored at the first character, which is why most workload patterns start with `*`:
                a Helm chart names its workload `<release>` when the release name contains the chart name and `<release>-<chart>` otherwise
                (the `fullname` helper every chart in references/sources.md shares), so the chart name is a suffix, not a prefix, and a release name
                that merely contains it (`karpenter-aws`) keeps its own name, which is why the patterns end in `*` as well (#130)
  crd:          CRD name (plural.group)
  namespace:    namespace name
  storageclass_provisioner: the provisioner value of a StorageClass
  node_annotation: node annotation key prefix
  node_version_contains: substring of a node's kubeletVersion
  configmap_data_regex: regex (re.M) matched against ConfigMap data (all keys concatenated). For configuration only visible in config bodies
  image:        substring of a container image of a DaemonSet/Deployment/StatefulSet/CronJob
  aws_addons:   the `aws eks list-addons` result is non-empty
Every entry carries a `source`: the line of the project's install manifest, Helm chart or code that produces the name at the tag read, as
`owner/repo path:line@tag`, or `unverified` with the reason. tests/test_sources.py requires one on every entry and refuses an evidence key that
`lib/collection/discover._Facts.evidence` does not handle (a key it does not know never matches: `cronjob_ignored` sat on the descheduler rule from
2025 until #130, so the chart's default CronJob install was never detected). The full reading, 112 entries against 70 projects, is in
references/sources.md (#130).

`family` groups alternatives that play the same role. Absence is judged per family: "is there any CNI at all?".
`platform` marks components that only matter on that platform (missing is not an absence).

Declaring a new platform's components (e.g. GKE or AKS): add rules here with `"platform": "<name>"` using the same platform
name that `discover.detect_platform` returns ("gke", "aks", ...). The platform's managed add-ons go in the `platform` family,
its distribution marker (if any) in `distribution`, and cloud-specific CNI/CSI/ingress controllers in their usual families with
the `platform` marker so that their absence off that platform is not reported. Each such component still needs a
`collectors/<name>/` folder (detect + collect.yaml) to be collected; `collectors/<platform>-platform/` is enabled by the
platform name alone (see discover.py "Adding a platform").
"""

from __future__ import annotations

import fnmatch


def match_name(pattern: str, ns: str, name: str) -> bool:
    """`namespace/name` glob: each side is an fnmatch pattern (`*` anywhere, `?`, `[...]`, case-sensitive), applied to the namespace and the name separately.
    The one matcher for the detection rules below and for the pod-metrics `discover.name` patterns of collectors/*/collect.yaml (#136)."""
    pns, _, pname = pattern.partition("/")
    return fnmatch.fnmatchcase(ns, pns) and fnmatch.fnmatchcase(name, pname)


EVIDENCE_KEYS = ("daemonset", "deployment", "statefulset", "cronjob", "crd", "namespace", "storageclass_provisioner", "node_annotation", "node_version_contains", "configmap_data_regex", "image", "aws_addons")

COMPONENTS: list[dict] = [
    # networking
    {
        "name": "vpc-cni",
        "family": "cni",
        "platform": "eks",
        "any": [
            {
                "daemonset": "kube-system/aws-node",
                "source": "aws/amazon-vpc-cni-k8s config/master/aws-k8s-cni.yaml:161-165@v1.23.2 (DaemonSet aws-node in kube-system), charts/aws-vpc-cni/templates/daemonset.yaml:1-5@v1.23.2, charts/aws-vpc-cni/values.yaml:143@v1.23.2 (fullnameOverride aws-node, so the name is the same for any release name); the EKS managed add-on deploys this manifest",
            }
        ],
    },
    {
        "name": "cilium",
        "family": "cni",
        "any": [
            {
                "daemonset": "*/cilium",
                "source": "cilium/cilium install/kubernetes/cilium/templates/cilium-agent/daemonset.yaml:17-20@v1.20.4 (name .Values.name, namespace cilium.namespace), install/kubernetes/cilium/values.yaml:224@v1.20.4 (name: cilium), install/kubernetes/cilium/templates/_helpers.tpl:11-13@v1.20.4 (namespaceOverride or the release namespace; the README installs into kube-system, README.md:36)",
            },
            {"crd": "ciliumnetworkpolicies.cilium.io", "source": "cilium/cilium pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml:7@v1.20.4"},
        ],
    },
    {
        "name": "calico",
        "family": "cni",
        "any": [
            {
                "daemonset": "*/calico-node",
                "source": "projectcalico/calico manifests/calico.yaml:12795-12799@v3.33.0 (DaemonSet calico-node in kube-system); tigera/operator pkg/render/node.go:68,1350@v1.44.0 and pkg/common/common.go:18@v1.44.0 (the operator renders calico-node in calico-system: hence the * namespace)",
            },
            {"crd": "felixconfigurations.crd.projectcalico.org", "source": "projectcalico/calico manifests/calico.yaml:2102@v3.33.0, manifests/crds.yaml:2016@v3.33.0, manifests/operator-crds.yaml:37104@v3.33.0"},
        ],
    },
    {
        "name": "flannel",
        "family": "cni",
        "any": [
            {
                "node_annotation": "flannel.alpha.coreos.com/",
                "source": "flannel-io/flannel main.go:132@v0.28.10 (--kube-annotation-prefix default flannel.alpha.coreos.com), pkg/subnet/kube/annotations.go:36-46,63-72@v0.28.10 (the keys <prefix>/backend-data, /backend-type, /public-ip, /kube-subnet-manager); k3s-io/k3s pkg/agent/flannel/flannel.go:54,65-68@v1.37.1+k3s1 (the embedded flannel uses the same prefix)",
            },
            {
                "daemonset": "*/kube-flannel*",
                "source": "flannel-io/flannel Documentation/kube-flannel.yml:101-104@v0.28.10 (DaemonSet kube-flannel-ds in namespace kube-flannel), chart/kube-flannel/templates/daemonset.yaml:2-5@v0.28.10 (the literal name kube-flannel-ds in the release namespace)",
            },
        ],
    },
    {
        "name": "coredns",
        "family": "dns",
        "any": [
            {
                "deployment": "kube-system/coredns",
                "source": "coredns/deployment kubernetes/coredns.yaml.sed:69-72@coredns-1.14.0, kubernetes/kubernetes cluster/addons/dns/coredns/coredns.yaml.base:87-90@v1.37.2, k3s-io/k3s manifests/coredns.yaml:82-85@v1.37.1+k3s1; the EKS managed add-on's manifest is not public (observed on the EKS cluster)",
            },
            {
                "deployment": "kube-system/rke2-coredns*",
                "source": "rancher/rke2 charts/chart_versions.yaml:15-16@v1.37.1+rke2r1 and charts/build-chart.sh:39-42@v1.37.1+rke2r1 (HelmChart rke2-coredns in kube-system); rancher/rke2-charts charts/rke2-coredns/rke2-coredns/1.49.002/templates/_helpers.tpl:13-20@cf8a16b and templates/deployment.yaml:4-7@cf8a16b (the branch main read at that commit on 2026-11-05; the Deployment is rke2-coredns-rke2-coredns)",
            },
        ],
    },
    {"name": "node-local-dns", "family": "dns-cache", "any": [{"daemonset": "kube-system/node-local-dns", "source": "kubernetes/kubernetes cluster/addons/dns/nodelocaldns/nodelocaldns.yaml:105-108@v1.37.2"}]},
    {
        "name": "kube-proxy",
        "family": "kube-proxy",
        "any": [
            {
                "daemonset": "kube-system/kube-proxy",
                "source": "kubernetes/kubernetes cmd/kubeadm/app/phases/addons/proxy/manifests.go:56-61@v1.37.2, cmd/kubeadm/app/constants/constants.go:341@v1.37.2; the EKS managed add-on's manifest is not public (observed on the EKS cluster)",
            },
            {
                "node_version_contains": "+k3s",
                "source": "k3s-io/k3s scripts/version.sh:89-91@v1.37.1+k3s1 and scripts/build:32@v1.37.1+k3s1 (the kubelet reports the k3s tag as its version), pkg/daemons/agent/agent.go:48-62@v1.37.1+k3s1 (kube-proxy runs inside the k3s process, no DaemonSet; its metrics come mixed into the kubelet scrape)",
            },
            {
                "node_version_contains": "+rke2",
                "source": "rancher/rke2 pkg/executor/staticpod/staticpod.go:179-181@v1.37.1+rke2r1 (kube-proxy is a static pod, no DaemonSet), pkg/rke2/kp.go:10,17-18@v1.37.1+rke2r1 (the old rke2-kube-proxy HelmChart is disabled), scripts/version.sh:65@v1.37.1+rke2r1 (the version suffix); until #130 the rule looked for a DaemonSet rke2-kube-proxy* that no RKE2 release ever produced (rancher/rke2-charts charts/rke2-kube-proxy/rke2-kube-proxy/v1.21.1-build2021052004/templates/daemonset.yaml:2-7@cf8a16b named it kube-proxy), so kube-proxy was absent on every RKE2 cluster",
            },
        ],
    },
    {
        "name": "alb-controller",
        "family": "ingress",
        "platform": "eks",
        "any": [
            {
                "deployment": "*/*aws-load-balancer-controller*",
                "source": "kubernetes-sigs/aws-load-balancer-controller helm/aws-load-balancer-controller/templates/deployment.yaml:2-5@v3.6.2, helm/aws-load-balancer-controller/templates/_helpers.tpl:14-25@v3.6.2 (the release name, or <release>-aws-load-balancer-controller: hence the leading *; until #130 the pattern was anchored and matched only the release name aws-load-balancer-controller)",
            },
            {"crd": "targetgroupbindings.elbv2.k8s.aws", "source": "kubernetes-sigs/aws-load-balancer-controller helm/aws-load-balancer-controller/crds/crds.yaml:895@v3.6.2"},
        ],
    },
    {
        "name": "ingress-nginx",
        "family": "ingress",
        "any": [
            {
                "deployment": "*/*ingress-nginx-controller*",
                "source": "kubernetes/ingress-nginx charts/ingress-nginx/templates/controller-deployment.yaml:1-3,11-12@helm-chart-4.15.1 and templates/_helpers.tpl:20-28,100-102@helm-chart-4.15.1 (<fullname>-controller, fullname = release name or <release>-ingress-nginx), deploy/static/provider/cloud/deploy.yaml:392,400-401@controller-v1.15.1 (ingress-nginx-controller in ingress-nginx); rancher/rke2 charts/chart_versions.yaml:18-19@v1.37.1+rke2r1 (rke2-ingress-nginx-controller)",
            },
            {"daemonset": "*/*ingress-nginx-controller*", "source": "kubernetes/ingress-nginx charts/ingress-nginx/templates/controller-daemonset.yaml:1-3,11-12@helm-chart-4.15.1 (the same name when controller.kind is DaemonSet)"},
            {
                "image": "ingress-nginx/controller",
                "source": "kubernetes/ingress-nginx charts/ingress-nginx/values.yaml:8,29@helm-chart-4.15.1 (registry.k8s.io/ingress-nginx/controller), deploy/static/provider/cloud/deploy.yaml:446@controller-v1.15.1",
            },
            {
                "image": "nginx-ingress-controller",
                "source": "unverified: the Bitnami build of the same controller (docker.io/bitnami/nginx-ingress-controller); bitnami/containers removed the directory on 2026-04-20 (commit d2724e8d02, 'Deprecate nginx-ingress-controller'), so no current tag carries it. Kept for clusters still running that image; lib/summaries/traffic._nginx matches the same two",
            },
        ],
    },
    {
        "name": "traefik",
        "family": "ingress",
        "any": [
            {
                "deployment": "*/*traefik*",
                "source": "traefik/traefik-helm-chart traefik/templates/deployment.yaml:21-24@v42.3.0 and traefik/templates/_helpers.tpl:74-85@v42.3.0 (the release name or <release>-traefik), k3s-io/k3s manifests/traefik.yaml:13-16@v1.37.1+k3s1 (release traefik in kube-system), rancher/rke2 charts/chart_versions.yaml:21-22@v1.37.1+rke2r1 (rke2-traefik: the reason for the leading *)",
            },
            {"daemonset": "*/*traefik*", "source": "traefik/traefik-helm-chart traefik/templates/deployment.yaml:21-24@v42.3.0 (the same template emits a DaemonSet when deployment.kind says so)"},
            {"crd": "ingressroutes.traefik.io", "source": "traefik/traefik-helm-chart traefik/crds/traefik.io_ingressroutes.yaml:7@v42.3.0"},
            {
                "crd": "ingressroutes.traefik.containo.us",
                "source": "traefik/traefik-helm-chart traefik/crds/traefik.containo.us_ingressroutes.yaml:7@v27.0.2 (Traefik v2; chart v28.0.0, Traefik v3.0.0, ships traefik.io only: traefik/Chart.yaml:5-7@v28.0.0)",
            },
        ],
    },
    {
        "name": "metallb",
        "family": "loadbalancer",
        "any": [
            {"crd": "ipaddresspools.metallb.io", "source": "metallb/metallb config/crd/bases/metallb.io_ipaddresspools.yaml:7@v0.16.2, :9@v0.13.0 (the file does not exist at v0.12.1: the CRD begins at 0.13)"},
            {
                "daemonset": "*/*-speaker",
                "source": "metallb/metallb charts/metallb/templates/speaker.yaml:127-130@v0.16.2 and charts/metallb/templates/_helpers.tpl:14-20@v0.16.2 (<fullname>-speaker; fullname = release name or <release>-metallb), charts/metallb/templates/speaker.yaml:107-109@v0.13.0 and @metallb-chart-0.12.1 (the same template); until #130 the pattern was metallb-speaker*, which only release name metallb produced",
            },
            {"daemonset": "*/speaker", "source": "metallb/metallb config/manifests/metallb-native.yaml:2274-2280@v0.16.2 (DaemonSet speaker in metallb-system), manifests/metallb.yaml:314-320@v0.12.1"},
        ],
    },
    {
        "name": "external-dns",
        "family": "external-dns",
        "any": [
            {
                "deployment": "*/*external-dns*",
                "source": "kubernetes-sigs/external-dns charts/external-dns/templates/deployment.yaml:4-7@v0.24.0 and charts/external-dns/templates/_helpers.tpl:23-34@v0.24.0 (the release name or <release>-external-dns: hence the leading *, missing until #130)",
            }
        ],
    },
    {
        "name": "istio",
        "family": "service-mesh",
        "any": [
            {
                "deployment": "*/istiod*",
                "source": "istio/istio manifests/charts/istio-control/istio-discovery/templates/deployment.yaml:5-8@1.31.3 (istiod, or istiod-<revision> for a revisioned install, in the release namespace), manifests/charts/istio-control/istio-discovery/values.yaml:212,229-230@1.31.3 (istioNamespace istio-system is the documented default, not a hard-coded namespace)",
            },
            {"crd": "virtualservices.networking.istio.io", "source": "istio/istio manifests/charts/base/files/crd-all.gen.yaml:11913@1.31.3"},
        ],
    },
    {
        "name": "linkerd",
        "family": "service-mesh",
        "any": [
            {
                "deployment": "*/linkerd-destination",
                "source": "linkerd/linkerd2 charts/linkerd-control-plane/templates/destination.yaml:135,146-147@edge-26.11.1 (the literal name in the release namespace), cli/cmd/root.go:22@edge-26.11.1 (the CLI default namespace linkerd)",
            }
        ],
    },
    # node lifecycle / scaling
    {
        "name": "karpenter",
        "family": "node-autoscaler",
        "any": [
            {
                "crd": "nodepools.karpenter.sh",
                "source": "aws/karpenter-provider-aws pkg/apis/crds/karpenter.sh_nodepools.yaml:7@v1.15.1, :7@v0.32.0 (v0.31.4 ships provisioners.karpenter.sh only: pkg/apis/crds/karpenter.sh_provisioners.yaml:7@v0.31.4)",
            },
            {
                "deployment": "*/*karpenter*",
                "source": "aws/karpenter-provider-aws charts/karpenter/templates/deployment.yaml:3-6@v1.15.1 and charts/karpenter/templates/_helpers.tpl:13-24@v1.15.1 (the release name or <release>-karpenter; charts/karpenter/README.md:16 installs release karpenter), charts/karpenter/templates/deployment.yaml:2-5@v0.31.4 (the same at 0.31)",
            },
        ],
    },
    {
        "name": "cluster-autoscaler",
        "family": "node-autoscaler",
        "any": [
            {
                "deployment": "*/*cluster-autoscaler*",
                "source": "kubernetes/autoscaler cluster-autoscaler/charts/cluster-autoscaler/templates/deployment.yaml:4,10-11@cluster-autoscaler-chart-9.60.0 and cluster-autoscaler/charts/cluster-autoscaler/templates/_helpers.tpl:13-24@cluster-autoscaler-chart-9.60.0 (<release>-aws-cluster-autoscaler unless the release name is aws-cluster-autoscaler; cloudProvider aws is the default, values.yaml:144), cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml:124-127@cluster-autoscaler-chart-9.60.0 (Deployment cluster-autoscaler in kube-system); until #130 the pattern was anchored at cluster-autoscaler and missed every release name but one",
            }
        ],
    },
    {"name": "keda", "family": "pod-autoscaler-ext", "any": [{"crd": "scaledobjects.keda.sh", "source": "kedacore/keda config/crd/bases/keda.sh_scaledobjects.yaml:7@v2.21.0"}]},
    {"name": "vpa", "family": "vpa", "any": [{"crd": "verticalpodautoscalers.autoscaling.k8s.io", "source": "kubernetes/autoscaler vertical-pod-autoscaler/deploy/vpa-v1-crd-gen.yaml:229@cluster-autoscaler-chart-9.60.0"}]},
    {
        "name": "metrics-server",
        "family": "metrics-server",
        "any": [
            {
                "deployment": "*/*metrics-server*",
                "source": "kubernetes-sigs/metrics-server manifests/base/deployment.yaml:3-6@v0.9.1 (metrics-server in kube-system; the release asset components.yaml is built from it, manifests/base/kustomization.yaml:1-8), charts/metrics-server/templates/deployment.yaml:2-5@v0.9.1 and charts/metrics-server/templates/_helpers.tpl:13-24@v0.9.1 (the release name or <release>-metrics-server in the release namespace; charts/metrics-server/README.md:16 installs without a namespace flag), k3s-io/k3s manifests/metrics-server/metrics-server-deployment.yaml:9-12@v1.37.1+k3s1, rancher/rke2-charts charts/rke2-metrics-server/rke2-metrics-server/3.14.001/templates/_helpers.tpl:13-23@cf8a16b (the branch main read at that commit on 2026-11-05; rke2-metrics-server); until #130 the rule required kube-system/metrics-server exactly",
            }
        ],
    },
    {
        "name": "node-termination-handler",
        "family": "spot-handler",
        "platform": "eks",
        "any": [
            {
                "daemonset": "*/*aws-node-termination-handler*",
                "source": "aws/aws-node-termination-handler config/helm/aws-node-termination-handler/templates/daemonset.linux.yaml:1,3-6@v1.25.6 and config/helm/aws-node-termination-handler/templates/_helpers.tpl:15-26@v1.25.6 (the release name or <release>-aws-node-termination-handler; the DaemonSet is the IMDS mode, values.yaml:141 enableSqsTerminationDraining false)",
            },
            {
                "deployment": "*/*aws-node-termination-handler*",
                "source": "aws/aws-node-termination-handler config/helm/aws-node-termination-handler/templates/deployment.yaml:1,3-6@v1.25.6 (the queue-processor mode, enableSqsTerminationDraining true, is a Deployment of the same name; not detected until #130)",
            },
        ],
    },
    {
        "name": "descheduler",
        "family": "descheduler",
        "any": [
            {
                "cronjob": "*/*descheduler*",
                "source": "kubernetes-sigs/descheduler charts/descheduler/templates/cronjob.yaml:1,3-6@descheduler-helm-chart-0.37.0 and charts/descheduler/values.yaml:5-6@descheduler-helm-chart-0.37.0 (kind: CronJob is the chart default), charts/descheduler/templates/_helpers.tpl:14-25@descheduler-helm-chart-0.37.0, kubernetes/cronjob/cronjob.yaml:3-6@descheduler-helm-chart-0.37.0 (descheduler-cronjob in kube-system); until #130 this was the key cronjob_ignored, which the matcher did not know, so the default install was never detected",
            },
            {
                "deployment": "*/*descheduler*",
                "source": "kubernetes-sigs/descheduler charts/descheduler/templates/deployment.yaml:1,3-6@descheduler-helm-chart-0.37.0 (kind: Deployment), kubernetes/deployment/deployment.yaml:2-5@descheduler-helm-chart-0.37.0",
            },
        ],
    },
    {
        "name": "kured",
        "family": "node-reboot",
        "any": [
            {
                "daemonset": "*/*kured*",
                "source": "kubereboot/charts charts/kured/templates/daemonset.yaml:2-5@kured-6.1.0 and charts/kured/templates/_helpers.tpl:14-25@kured-6.1.0 (the release name or <release>-kured), kubereboot/kured kured-ds.yaml:9-12@1.23.0 (DaemonSet kured in kube-system); until #130 the pattern was the exact name kured",
            }
        ],
    },
    # storage
    {
        "name": "ebs-csi",
        "family": "csi",
        "platform": "eks",
        "any": [
            {
                "daemonset": "*/ebs-csi-node*",
                "source": "kubernetes-sigs/aws-ebs-csi-driver charts/aws-ebs-csi-driver/templates/node.yaml:2@v1.67.2 and charts/aws-ebs-csi-driver/templates/_node.tpl:7-8@v1.67.2 (the literal ebs-csi-node in the release namespace; additional DaemonSets are ebs-csi-node-<key>), deploy/kubernetes/base/node.yaml:6@v1.67.2 and deploy/kubernetes/base/kustomization.yaml:3@v1.67.2 (kube-system); the EKS managed add-on's manifest is not public (observed on the EKS cluster)",
            },
            {
                "storageclass_provisioner": "ebs.csi.aws.com",
                "source": "kubernetes-sigs/aws-ebs-csi-driver cmd/main.go:159@v1.67.2, deploy/kubernetes/base/csidriver.yaml:6@v1.67.2; the chart creates no StorageClass by default (charts/aws-ebs-csi-driver/values.yaml:505@v1.67.2 storageClasses: []), so this fires only where the user made one",
            },
            {"image": "aws-ebs-csi-driver", "source": "kubernetes-sigs/aws-ebs-csi-driver charts/aws-ebs-csi-driver/values.yaml:6@v1.67.2 (public.ecr.aws/ebs-csi-driver/aws-ebs-csi-driver), deploy/kubernetes/base/node.yaml:51@v1.67.2"},
        ],
    },
    {
        "name": "efs-csi",
        "family": "csi-shared",
        "platform": "eks",
        "any": [
            {
                "daemonset": "*/efs-csi-node*",
                "source": "kubernetes-sigs/aws-efs-csi-driver charts/aws-efs-csi-driver/templates/node-daemonset.yaml:5-6@v3.5.4 (the literal efs-csi-node in the release namespace), deploy/kubernetes/base/node-daemonset.yaml:7@v3.5.4 and deploy/kubernetes/base/kustomization.yaml:3@v3.5.4 (kube-system)",
            },
            {"image": "aws-efs-csi-driver", "source": "kubernetes-sigs/aws-efs-csi-driver charts/aws-efs-csi-driver/values.yaml:14@v3.5.4 (public.ecr.aws/efs-csi-driver/amazon/aws-efs-csi-driver)"},
        ],
    },
    {
        "name": "local-path-provisioner",
        "family": "csi",
        "any": [
            {
                "deployment": "*/*local-path-provisioner*",
                "source": "k3s-io/k3s manifests/local-storage.yaml:41-42@v1.37.1+k3s1 (local-path-provisioner in kube-system), rancher/local-path-provisioner deploy/local-path-storage.yaml:76-77@v0.0.37 (the same name in local-path-storage, README.md:30), deploy/chart/local-path-provisioner/templates/deployment.yaml:4-5@v0.0.37 and deploy/chart/local-path-provisioner/templates/_helpers.tpl:14-22@v0.0.37 (the release name or <release>-local-path-provisioner); until #130 the rule required kube-system/local-path-provisioner exactly",
            },
            {
                "storageclass_provisioner": "rancher.io/local-path",
                "source": "rancher/local-path-provisioner main.go:30@v0.0.37, deploy/local-path-storage.yaml:144@v0.0.37, k3s-io/k3s manifests/local-storage.yaml:96@v1.37.1+k3s1; a Helm release's default provisioner is cluster.local/<fullname> instead (deploy/chart/local-path-provisioner/templates/_helpers.tpl:72-77@v0.0.37), which the image entry covers",
            },
            {
                "image": "rancher/local-path-provisioner",
                "source": "rancher/local-path-provisioner deploy/chart/local-path-provisioner/values.yaml:8@v0.0.37, deploy/local-path-storage.yaml:91@v0.0.37, k3s-io/k3s manifests/local-storage.yaml:69@v1.37.1+k3s1",
            },
        ],
    },
    {"name": "longhorn", "family": "csi", "any": [{"crd": "volumes.longhorn.io", "source": "longhorn/longhorn chart/templates/crds.yaml:5080@v1.13.0, deploy/longhorn.yaml:5477@v1.13.0"}]},
    {"name": "rook-ceph", "family": "csi", "any": [{"crd": "cephclusters.ceph.rook.io", "source": "rook/rook deploy/examples/crds.yaml:1517@v1.21.1"}]},
    {
        "name": "nfs-provisioner",
        "family": "csi-shared",
        "any": [
            {
                "storageclass_provisioner": "nfs.csi.k8s.io",
                "source": "kubernetes-csi/csi-driver-nfs pkg/nfs/nfs.go:75@v4.13.6, deploy/v4.13.6/storageclass.yaml:6@v4.13.6; neither install path creates the StorageClass (deploy/install-driver.sh:37-40@v4.13.6, charts/latest/csi-driver-nfs/values.yaml:197-198@v4.13.6 storageClass.create false), so the driver's own workloads are matched below",
            },
            {"daemonset": "*/csi-nfs-node*", "source": "kubernetes-csi/csi-driver-nfs deploy/v4.13.6/csi-nfs-node.yaml:5-6@v4.13.6 (csi-nfs-node in kube-system), charts/latest/csi-driver-nfs/values.yaml:132@v4.13.6"},
            {"deployment": "*/csi-nfs-controller*", "source": "kubernetes-csi/csi-driver-nfs deploy/v4.13.6/csi-nfs-controller.yaml:5-6@v4.13.6, charts/latest/csi-driver-nfs/values.yaml:55@v4.13.6"},
            {
                "deployment": "*/*nfs-subdir-external-provisioner*",
                "source": "kubernetes-sigs/nfs-subdir-external-provisioner charts/nfs-subdir-external-provisioner/templates/deployment.yaml:4@nfs-subdir-external-provisioner-4.0.18 and charts/nfs-subdir-external-provisioner/templates/_helpers.tpl:14-22@nfs-subdir-external-provisioner-4.0.18 (the release name or <release>-nfs-subdir-external-provisioner; README.md:9,28)",
            },
            {"deployment": "*/nfs-client-provisioner*", "source": "kubernetes-sigs/nfs-subdir-external-provisioner deploy/deployment.yaml:4,8@nfs-subdir-external-provisioner-4.0.18 (the kustomize install's Deployment, in default)"},
            {
                "storageclass_provisioner": "k8s-sigs.io/nfs-subdir-external-provisioner",
                "source": "kubernetes-sigs/nfs-subdir-external-provisioner deploy/class.yaml:5@nfs-subdir-external-provisioner-4.0.18, deploy/deployment.yaml:30@nfs-subdir-external-provisioner-4.0.18",
            },
            {
                "image": "sig-storage/nfs-subdir-external-provisioner",
                "source": "kubernetes-sigs/nfs-subdir-external-provisioner charts/nfs-subdir-external-provisioner/values.yaml:5@nfs-subdir-external-provisioner-4.0.18, deploy/deployment.yaml:24@nfs-subdir-external-provisioner-4.0.18",
            },
        ],
    },
    {
        "name": "velero",
        "family": "backup",
        "any": [
            {"crd": "backups.velero.io", "source": "vmware-tanzu/velero config/crd/v1/bases/velero.io_backups.yaml:7@v1.18.4"},
            {
                "deployment": "*/velero",
                "source": "vmware-tanzu/velero pkg/install/deployment.go:359@v1.18.4 (velero install names it velero), pkg/install/resources.go:56@v1.18.4 (namespace velero); vmware-tanzu/helm-charts charts/velero/templates/deployment.yaml:6-7@velero-12.2.3 (the literal name velero in the release namespace)",
            },
        ],
    },
    {"name": "k8up", "family": "backup", "any": [{"crd": "backups.k8up.io", "source": "k8up-io/k8up charts/k8up/crds/k8up.io_backups.yaml:7@v2.16.1, config/crd/apiextensions.k8s.io/v1/k8up.io_backups.yaml:7@v2.16.1"}]},
    # certificates / secrets
    {"name": "cert-manager", "family": "certificates", "any": [{"crd": "certificates.cert-manager.io", "source": "cert-manager/cert-manager deploy/crds/cert-manager.io_certificates.yaml:7@v1.21.3"}]},
    {"name": "external-secrets", "family": "secrets-manager", "any": [{"crd": "externalsecrets.external-secrets.io", "source": "external-secrets/external-secrets deploy/crds/bundle.yaml:13956@v2.14.0"}]},
    {
        "name": "secrets-store-csi",
        "family": "secrets-manager",
        "any": [
            {
                "daemonset": "*/*secrets-store-csi-driver*",
                "source": "kubernetes-sigs/secrets-store-csi-driver charts/secrets-store-csi-driver/templates/secrets-store-csi-driver.yaml:5-6@v1.6.1 and charts/secrets-store-csi-driver/templates/_helpers.tpl:14-24@v1.6.1 (<release>-secrets-store-csi-driver; the README's release csi-secrets-store gives csi-secrets-store-secrets-store-csi-driver, charts/secrets-store-csi-driver/README.md:22); until #130 the pattern was anchored and matched neither documented name",
            },
            {"daemonset": "*/csi-secrets-store*", "source": "kubernetes-sigs/secrets-store-csi-driver deploy/secrets-store-csi-driver.yaml:4-5@v1.6.1 (the static manifest's DaemonSet csi-secrets-store in kube-system)"},
            {"crd": "secretproviderclasses.secrets-store.csi.x-k8s.io", "source": "kubernetes-sigs/secrets-store-csi-driver deploy/secrets-store.csi.x-k8s.io_secretproviderclasses.yaml:7@v1.6.1"},
            {"image": "csi-secrets-store/driver", "source": "kubernetes-sigs/secrets-store-csi-driver deploy/secrets-store-csi-driver.yaml:39@v1.6.1 (registry.k8s.io/csi-secrets-store/driver)"},
        ],
    },
    {"name": "sealed-secrets", "family": "secrets-manager", "any": [{"crd": "sealedsecrets.bitnami.com", "source": "bitnami-labs/sealed-secrets helm/sealed-secrets/crds/bitnami.com_sealedsecrets.yaml:6@v0.41.2"}]},
    {
        "name": "vault",
        "family": "secrets-manager",
        "any": [
            {
                "statefulset": "*/*vault",
                "source": "hashicorp/vault-helm templates/server-statefulset.yaml:15-16@v0.34.1 and templates/_helpers.tpl:12-23@v0.34.1 (the release name when it contains vault, else <release>-vault; README.md:37 installs release vault); a release such as vault-prod keeps its own name and is matched by the image entries",
            },
            {"deployment": "*/*vault-agent-injector*", "source": "hashicorp/vault-helm templates/injector-deployment.yaml:12-13@v0.34.1 (<fullname>-agent-injector)"},
            {"image": "hashicorp/vault", "source": "hashicorp/vault-helm values.yaml:78@v0.34.1 (server image hashicorp/vault; also matches hashicorp/vault-k8s, the injector image at values.yaml:70)"},
        ],
    },
    {
        "name": "eks-pod-identity-agent",
        "family": "pod-identity",
        "platform": "eks",
        "any": [
            {
                "daemonset": "kube-system/eks-pod-identity-agent*",
                "source": "aws/eks-pod-identity-agent charts/eks-pod-identity-agent/templates/daemonset.yaml:11-12@v0.2.6 and charts/eks-pod-identity-agent/values.yaml:5-7,138,159@v0.2.6 (the name is pinned to eks-pod-identity-agent, plus a suffix for the hybrid DaemonSets; charts/eks-pod-identity-agent/README.md:21 installs into kube-system); the managed add-on's manifest is not public, the EKS guide shows pods eks-pod-identity-agent-* in kube-system (awsdocs/amazon-eks-user-guide latest/ug/manage-access/aws-access/pod-id-agent-setup.adoc:78-79@8d43223, the branch mainline read at that commit on 2026-11-05)",
            }
        ],
    },
    # deployment / GitOps
    {
        "name": "ecr",
        "family": "registry",
        "any": [
            {
                "image": ".dkr.ecr.",
                "source": "awsdocs/amazon-eks-user-guide latest/ug/workloads/add-ons-images.adoc:8,19-28,64,67@8d43223 (the branch mainline, read at that commit on 2026-11-05: private registries are <account>.dkr.ecr.<region>.amazonaws.com and .amazonaws.com.cn; the ECR user guide repository is archived, so the hostname grammar itself is unverified and read from the EKS add-on registry table). Enabled when pods use ECR images (always with EKS managed add-ons). Images from ECR Public (public.ecr.aws, the EBS and EFS chart defaults) are not counted: they say nothing about the cluster's own registry. The aws step is skipped off EKS",
            }
        ],
    },
    {
        "name": "argocd",
        "family": "gitops",
        "any": [
            {
                "deployment": "*/*argocd-server",
                "source": "argoproj/argo-cd manifests/install.yaml:36064@v3.6.0 and manifests/base/server/argocd-server-deployment.yaml:8@v3.6.0 (argocd-server; docs/getting_started.md:15-16 applies it into argocd); argoproj/argo-helm charts/argo-cd/templates/argocd-server/deployment.yaml:11@argo-cd-10.12.0, charts/argo-cd/templates/_helpers.tpl:124-126@argo-cd-10.12.0 and charts/argo-cd/templates/_common.tpl:14-25@argo-cd-10.12.0 (<fullname>-server; a release named argo-cd gives argo-cd-argocd-server: hence the leading *)",
            },
            {"crd": "applications.argoproj.io", "source": "argoproj/argo-cd manifests/crds/application-crd.yaml:7@v3.6.0"},
        ],
    },
    {
        "name": "flux",
        "family": "gitops",
        "any": [
            {
                "crd": "kustomizations.kustomize.toolkit.fluxcd.io",
                "source": "fluxcd/kustomize-controller config/crd/bases/kustomize.toolkit.fluxcd.io_kustomizations.yaml:8@v1.10.1 (installed by fluxcd/flux2 manifests/bases/kustomize-controller/kustomization.yaml:4-5@v2.10.0)",
            }
        ],
    },
    {"name": "argo-rollouts", "family": "progressive-delivery", "any": [{"crd": "rollouts.argoproj.io", "source": "argoproj/argo-rollouts manifests/crds/rollout-crd.yaml:6@v1.10.1, manifests/install.yaml:30786@v1.10.1"}]},
    {
        "name": "reloader",
        "family": "config-reload",
        "any": [
            {
                "deployment": "*/*reloader*",
                "source": "stakater/Reloader deployments/kubernetes/chart/reloader/templates/_helpers.tpl:14-21@v1.4.23 (always <release>-reloader) and deployments/kubernetes/chart/reloader/templates/deployment.yaml:17-18@v1.4.23, deployments/kubernetes/reloader.yaml:113-114@v1.4.23 (reloader-reloader in default); until #130 the pattern was anchored at reloader and missed every release name but one, with no other evidence",
            },
            {"image": "stakater/reloader", "source": "stakater/Reloader deployments/kubernetes/chart/reloader/values.yaml:20-21@v1.4.23 (ghcr.io/stakater/reloader)"},
        ],
    },
    {
        "name": "actions-runner-controller",
        "family": "ci-runner",
        "any": [
            {"crd": "autoscalingrunnersets.actions.github.com", "source": "actions/actions-runner-controller charts/gha-runner-scale-set-controller/crds/actions.github.com_autoscalingrunnersets.yaml:7@gha-runner-scale-set-0.15.1"},
            {
                "crd": "runnerdeployments.actions.summerwind.dev",
                "source": "actions/actions-runner-controller charts/actions-runner-controller/crds/actions.summerwind.dev_runnerdeployments.yaml:7@gha-runner-scale-set-0.15.1 (the legacy chart)",
            },
        ],
    },
    # observability
    {
        "name": "prometheus-operator",
        "family": "metrics-operator",
        "any": [{"crd": "prometheuses.monitoring.coreos.com", "source": "prometheus-operator/prometheus-operator example/prometheus-operator-crd/monitoring.coreos.com_prometheuses.yaml:8@v0.94.2"}],
    },
    {
        "name": "prometheus",
        "family": "metrics-store",
        "any": [
            {
                "statefulset": "*/prometheus-*",
                "source": "prometheus-operator/prometheus-operator pkg/prometheus/common.go:201-214@v0.94.2 and pkg/prometheus/server/statefulset.go:87@v0.94.2 (prometheus-<cr name> for kind Prometheus; a PrometheusAgent is prom-agent-<name>, which only remote-writes and is not a store, so it is not matched on purpose); prometheus-community/helm-charts charts/kube-prometheus-stack/templates/prometheus/prometheus.yaml:4-10@kube-prometheus-stack-92.18.0 (the CR is <fullname>-prometheus). The prefix also matches the charts/prometheus subchart's prometheus-alertmanager, which never exists without the server",
            },
            {
                "deployment": "*/*prometheus-server*",
                "source": "prometheus-community/helm-charts charts/prometheus/templates/_helpers.tpl:110-118@prometheus-29.40.3 and charts/prometheus/templates/deploy.yaml:2-3@prometheus-29.40.3 (<release>-server when the release contains prometheus, else <release>-prometheus-server: hence the leading *, missing until #130)",
            },
            {"image": "prom/prometheus", "source": "prometheus/prometheus Makefile.common:86@v3.15.1 and Makefile:38@v3.15.1 (the Docker Hub image prom/prometheus)"},
            {
                "image": "prometheus/prometheus",
                "source": "prometheus/promci publish_main/action.yml:27-29@872d318d090d73df349cb6ed90aadd072ca478f7 (quay.io/prometheus/prometheus), prometheus-community/helm-charts charts/prometheus/values.yaml:194-195@prometheus-29.40.3, charts/kube-prometheus-stack/values.yaml:4636-4638@kube-prometheus-stack-92.18.0",
            },
        ],
    },
    {
        "name": "victoria-metrics",
        "family": "metrics-store",
        "any": [
            {
                "image": "victoriametrics/victoria-metrics",
                "source": "VictoriaMetrics/helm-charts charts/victoria-metrics-single/values.yaml:90-92@victoria-metrics-single-0.50.0, VictoriaMetrics/operator internal/config/config.go:400-402@v0.75.2 (the single-node image)",
            },
            {
                "deployment": "*/vmsingle-*",
                "source": "VictoriaMetrics/operator internal/controller/operator/factory/vmsingle/vmsingle.go:164-173@v0.75.2 and api/operator/v1beta1/vmsingle_types.go:344-348@v0.75.2 (a VMSingle is a Deployment vmsingle-<name>), VictoriaMetrics/helm-charts charts/victoria-metrics-single/templates/server.yaml:7-8@victoria-metrics-single-0.50.0 (the non-legacy chart mode); until #130 the rule looked for a StatefulSet vmsingle*, which nothing produces",
            },
            {
                "statefulset": "*/*victoria-metrics-single*",
                "source": "VictoriaMetrics/helm-charts charts/victoria-metrics-single/templates/server.yaml:14,17,19@victoria-metrics-single-0.50.0 and charts/victoria-metrics-common/templates/_helpers.tpl:168-181@victoria-metrics-common-0.4.5 (the chart default: StatefulSet <release>-victoria-metrics-single-server)",
            },
            {"image": "victoriametrics/vmstorage", "source": "VictoriaMetrics/operator internal/config/config.go:431@v0.75.2 (a VMCluster's storage image; vmselect :460 and vminsert :485 never run without it)"},
        ],
    },
    {
        "name": "thanos",
        "family": "metrics-longterm",
        "any": [
            {"image": "thanos/thanos", "source": "thanos-io/thanos Makefile:8@v0.42.5 (quay.io/thanos/thanos), prometheus-community/helm-charts charts/kube-prometheus-stack/values.yaml:3812-3815@kube-prometheus-stack-92.18.0"},
            {"image": "thanosio/thanos", "source": "thanos-io/thanos .circleci/config.yml:52-53,77-78@v0.42.5 (the Docker Hub image; not matched until #130)"},
            {"image": "bitnami/thanos", "source": "bitnami/charts bitnami/thanos/values.yaml:70-71@thanos/17.6.0"},
        ],
    },
    {
        "name": "alertmanager",
        "family": "alert-router",
        "any": [
            {
                "statefulset": "*/alertmanager-*",
                "source": "prometheus-operator/prometheus-operator pkg/alertmanager/statefulset.go:159,913-915@v0.94.2 (alertmanager-<cr name>), prometheus-community/helm-charts charts/kube-prometheus-stack/templates/alertmanager/alertmanager.yaml:3-5@kube-prometheus-stack-92.18.0",
            },
            {
                "statefulset": "*/*alertmanager",
                "source": "prometheus-community/helm-charts charts/alertmanager/templates/_helpers.tpl:14-22@alertmanager-2.1.4 and charts/alertmanager/templates/statefulset.yaml:3,5@alertmanager-2.1.4 (the standalone chart: alertmanager or <release>-alertmanager, which the operator pattern never matched until #130)",
            },
            {
                "image": "prometheus/alertmanager",
                "source": "prometheus-community/helm-charts charts/alertmanager/values.yaml:13@alertmanager-2.1.4 (quay.io/prometheus/alertmanager), charts/kube-prometheus-stack/values.yaml:1036-1038@kube-prometheus-stack-92.18.0",
            },
            {"image": "prom/alertmanager", "source": "prometheus/alertmanager Makefile.common:86@v0.34.2 and Makefile:21@v0.34.2 (the Docker Hub image; not matched until #130)"},
        ],
    },
    {
        "name": "grafana",
        "family": "dashboards",
        "any": [
            {
                "image": "grafana/grafana",
                "source": "grafana-community/helm-charts charts/grafana/values.yaml:119-123@grafana-14.3.1 (docker.io/grafana/grafana; the chart moved from grafana/helm-charts after grafana-10.5.15, grafana/helm-charts charts/grafana/README.md:5@80d6bc9, the branch main read at that commit on 2026-11-05; kube-prometheus-stack pulls it from ghcr.io/grafana-community, charts/kube-prometheus-stack/Chart.yaml:62-65@kube-prometheus-stack-92.18.0). The substring also matches the chart's own grafana/grafana-image-renderer (values.yaml:1747), the same install",
            },
            {
                "deployment": "*/*grafana*",
                "source": "grafana-community/helm-charts charts/grafana/templates/deployment.yaml:3,5-6@grafana-14.3.1 and charts/grafana/templates/_helpers.tpl:14-24,56-62@grafana-14.3.1 (the release name or <release>-grafana, in namespaceOverride or the release namespace); also matches a grafana-agent Deployment (grafana/agent operations/helm/charts/grafana-agent/templates/_helpers.tpl:18-21@helm-chart/0.44.2), a chart replaced by Alloy and archived, which is why the image entry comes first",
            },
            {"statefulset": "*/*grafana*", "source": "grafana-community/helm-charts charts/grafana/values.yaml:1993@grafana-14.3.1 (useStatefulSet: true renders a StatefulSet of the same name)"},
        ],
    },
    {
        "name": "loki",
        "family": "logs-store",
        "any": [
            {
                "image": "grafana/loki",
                "source": "grafana/loki production/helm/loki/values.yaml:89@helm-loki-7.5.0, grafana/helm-charts charts/loki/values.yaml:2@loki-2.16.0 (the legacy chart). The substring also matches grafana/loki-canary (production/helm/loki/values.yaml:837), the same install",
            },
            {
                "statefulset": "*/*loki*",
                "source": "grafana/loki production/helm/loki/templates/write/statefulset-write.yaml:5,7@helm-loki-7.5.0 and templates/backend/statefulset-backend.yaml:5,7@helm-loki-7.5.0 (loki-write, loki-backend from the chart name in SimpleScalable mode, values.yaml:59), templates/single-binary/statefulset.yaml:5,7@helm-loki-7.5.0 and templates/_helpers.tpl:34-46@helm-loki-7.5.0 (the release name or <release>-loki in SingleBinary mode: hence the leading *, missing until #130), grafana/helm-charts charts/loki/templates/statefulset.yaml:2,4@loki-2.16.0; the pattern also matches the memcached StatefulSets loki-chunks-cache and loki-results-cache of the same install",
            },
            {
                "deployment": "*/*loki*",
                "source": "grafana/loki production/helm/loki/templates/read/deployment-read.yaml:5,7@helm-loki-7.5.0 (loki-read); the pattern also matches loki-gateway, the install's nginx (templates/gateway/deployment-gateway-nginx.yaml:3,5@helm-loki-7.5.0)",
            },
        ],
    },
    {
        "name": "elasticsearch-opensearch",
        "family": "logs-store",
        "any": [
            {
                "statefulset": "*/*elasticsearch*",
                "source": "elastic/helm-charts elasticsearch/templates/statefulset.yaml:3,5@v8.5.1 and elasticsearch/values.yaml:2-3@v8.5.1 (<clusterName>-<nodeGroup>, elasticsearch-master; the chart is archived, last release 2022-11-16)",
            },
            {
                "image": "elasticsearch/elasticsearch",
                "source": "elastic/cloud-on-k8s pkg/controller/common/container/container.go:15,56@v3.5.0 (docker.elastic.co/elasticsearch/elasticsearch, the image of every ECK nodeSet StatefulSet <cluster>-es-<nodeset>, pkg/apis/elasticsearch/v1/name.go:61,124-125@v3.5.0; a name glob on -es- would also match unrelated StatefulSets, so the image is the evidence), elastic/helm-charts elasticsearch/values.yaml:78@v8.5.1",
            },
            {
                "statefulset": "*/*opensearch*",
                "source": "opensearch-project/helm-charts charts/opensearch/templates/_helpers.tpl:53-56@opensearch-2.39.0 and charts/opensearch/templates/statefulset.yaml:3,5@opensearch-2.39.0 (<clusterName>-<nodeGroup>, opensearch-cluster-master); the operator names StatefulSets <cr>-<component> (opensearch-project/opensearch-k8s-operator opensearch-operator/pkg/builders/cluster.go:718-721@v3.0.0), which the image entry covers",
            },
            {"image": "opensearchproject/opensearch", "source": "opensearch-project/helm-charts charts/opensearch/values.yaml:132@opensearch-2.39.0"},
        ],
    },
    {
        "name": "promtail",
        "family": "logs-agent",
        "any": [
            {
                "daemonset": "*/*promtail*",
                "source": "grafana/helm-charts charts/promtail/templates/daemonset.yaml:3,5@promtail-6.17.1 and charts/promtail/templates/_helpers.tpl:13-21@promtail-6.17.1 (the release name or <release>-promtail; loki-stack installs it as loki-promtail, charts/loki-stack/requirements.yaml:6-9@loki-stack-2.10.3)",
            }
        ],
    },
    {
        "name": "alloy",
        "family": "logs-agent",
        "any": [
            {
                "daemonset": "*/*alloy*",
                "source": "grafana/alloy operations/helm/charts/alloy/templates/controllers/daemonset.yaml:3,5@helm-chart/1.15.0 and operations/helm/charts/alloy/templates/_helpers.tpl:13-21@helm-chart/1.15.0 (the release name or <release>-alloy; controller.type daemonset is the default, values.yaml:294-297)",
            },
            {"image": "grafana/alloy", "source": "grafana/alloy operations/helm/charts/alloy/values.yaml:162@helm-chart/1.15.0 (covers the deployment and statefulset controller types too)"},
        ],
    },
    {
        "name": "fluent-bit",
        "family": "logs-agent",
        "any": [
            {
                "daemonset": "*/*fluent-bit*",
                "source": "fluent/helm-charts charts/fluent-bit/templates/daemonset.yaml:3,5@fluent-bit-0.58.3 and charts/fluent-bit/templates/_helpers.tpl:14-22@fluent-bit-0.58.3 (the release name or <release>-fluent-bit; kind DaemonSet is the default, values.yaml:4); aws-observability/helm-charts charts/amazon-cloudwatch-observability/templates/linux/fluent-bit-daemonset.yaml:1,7@amazon-cloudwatch-observability-7.0.0 (the CloudWatch chart's DaemonSet fluent-bit). Until #130 a second pattern *fluentbit* sat here without a source; no official chart produces that spelling",
            }
        ],
    },
    {
        "name": "fluentd",
        "family": "logs-agent",
        "any": [
            {
                "daemonset": "*/*fluentd*",
                "source": "fluent/helm-charts charts/fluentd/templates/daemonset.yaml:3,5@fluentd-0.6.0 and charts/fluentd/templates/_helpers.tpl:14-22@fluentd-0.6.0 (the release name or <release>-fluentd; kind DaemonSet is the default, values.yaml:5)",
            }
        ],
    },
    {
        "name": "vector",
        "family": "logs-agent",
        "any": [
            {
                "daemonset": "*/*vector*",
                "source": "vectordotdev/helm-charts charts/vector/templates/daemonset.yaml:1,3,5@vector-0.61.0 and charts/vector/templates/_helpers.tpl:82-90@vector-0.61.0 (role Agent; the chart default role Aggregator is a StatefulSet, values.yaml:14-18, which the image entry covers)",
            },
            {"image": "timberio/vector", "source": "vectordotdev/helm-charts charts/vector/values.yaml:48@vector-0.61.0 (docker.io/timberio/vector; not matched until #130, so a default Aggregator install was absent)"},
        ],
    },
    {
        "name": "cloudwatch-agent",
        "family": "logs-agent",
        "platform": "eks",
        "any": [
            {
                "daemonset": "*/cloudwatch-agent*",
                "source": "aws-observability/helm-charts charts/amazon-cloudwatch-observability/templates/linux/cloudwatch-agent-custom-resource.yaml:74,78,80-81@amazon-cloudwatch-observability-7.0.0 and charts/amazon-cloudwatch-observability/templates/_helpers.tpl:507-509@amazon-cloudwatch-observability-7.0.0 (the AmazonCloudWatchAgent CR is named cloudwatch-agent, mode daemonset), aws/amazon-cloudwatch-agent-operator internal/naming/main.go:61-63@v3.8.0 and internal/manifests/collector/daemonset.go:18,26@v3.8.0 (the operator creates a DaemonSet of the CR's name); until #130 the rule matched any DaemonSet in the namespace amazon-cloudwatch, which is only the README's example (README.md:17) and usually named the chart's fluent-bit instead",
            },
            {
                "image": "cloudwatch-agent/cloudwatch-agent",
                "source": "aws-observability/helm-charts charts/amazon-cloudwatch-observability/values.yaml:746-749@amazon-cloudwatch-observability-7.0.0 (public.ecr.aws/cloudwatch-agent/cloudwatch-agent)",
            },
        ],
    },
    {
        "name": "kube-state-metrics",
        "family": "kube-state-metrics",
        "any": [
            {
                "deployment": "*/*kube-state-metrics*",
                "source": "prometheus-community/helm-charts charts/kube-state-metrics/templates/deployment.yaml:2-5,8@kube-state-metrics-9.0.0 and charts/kube-state-metrics/templates/_helpers.tpl:14-22@kube-state-metrics-9.0.0 (the release name or <release>-kube-state-metrics), kubernetes/kube-state-metrics examples/standard/deployment.yaml:2,8-9@v2.20.0 (kube-state-metrics in kube-system)",
            },
            {
                "statefulset": "*/*kube-state-metrics*",
                "source": "prometheus-community/helm-charts charts/kube-state-metrics/templates/deployment.yaml:2-5@kube-state-metrics-9.0.0 and charts/kube-state-metrics/values.yaml:40-41@kube-state-metrics-9.0.0 (autosharding.enabled renders a StatefulSet of the same name; not matched until #130)",
            },
        ],
    },
    {
        "name": "node-exporter",
        "family": "node-exporter",
        "any": [
            {
                "daemonset": "*/*node-exporter*",
                "source": "prometheus-community/helm-charts charts/prometheus-node-exporter/templates/daemonset.yaml:2,4@prometheus-node-exporter-4.60.1 and charts/prometheus-node-exporter/templates/_helpers.tpl:14-22@prometheus-node-exporter-4.60.1 (the release name or <release>-prometheus-node-exporter)",
            }
        ],
    },
    {
        "name": "kubernetes-event-exporter",
        "family": "event-retention",
        "any": [
            {
                "deployment": "*/*event-exporter*",
                "source": "resmoio/kubernetes-event-exporter deploy/02-deployment.yaml:2,4-5@v1.7 (event-exporter in monitoring), bitnami/charts bitnami/kubernetes-event-exporter/templates/deployment.yaml:7,9-10@kubernetes-event-exporter/3.6.3 (the release name or <release>-kubernetes-event-exporter)",
            }
        ],
    },
    # fluent-bit's kubernetes_events input also ships events to a log store (seen on a k3s: a fluent-bit ConfigMap forwarding to an ES events index). Was a false absence finding before this rule.
    {
        "name": "fluent-bit-events",
        "family": "event-retention",
        "any": [
            {
                "configmap_data_regex": r"(?i)\[INPUT\]\s*\n\s*Name\s+kubernetes_events|^\s*-\s*name:\s*kubernetes_events\s*$",
                "source": "fluent/fluent-bit plugins/in_kubernetes_events/kubernetes_events.c:1190@v5.1.5 (the plugin name), fluent/helm-charts charts/fluent-bit/values.yaml:399-416@fluent-bit-0.58.3 (the chart writes the classic [INPUT] format into the ConfigMap), fluent/fluent-bit lib/cfl/src/cfl_kvlist.c:681-684@v5.1.5 via src/config_format/flb_config_format.c:446-460@v5.1.5 (property keys are case-insensitive: hence (?i)); the second alternative is the YAML config format (inputs: - name: kubernetes_events), neither of which the regex read until #130",
            }
        ],
    },
    {
        "name": "opentelemetry-collector",
        "family": "traces",
        "any": [
            {"crd": "opentelemetrycollectors.opentelemetry.io", "source": "open-telemetry/opentelemetry-operator config/crd/bases/opentelemetry.io_opentelemetrycollectors.yaml:7@v0.162.0"},
            {
                "daemonset": "*/*opentelemetry*collector*",
                "source": "open-telemetry/opentelemetry-helm-charts charts/opentelemetry-collector/templates/daemonset.yaml:1,3,5@opentelemetry-collector-0.178.2 and charts/opentelemetry-collector/templates/_helpers.tpl:32-42@opentelemetry-collector-0.178.2 (<release>-opentelemetry-collector-agent; until #130 the pattern was *otel*collector*, and otel is not a substring of opentelemetry)",
            },
            {"deployment": "*/*opentelemetry*collector*", "source": "open-telemetry/opentelemetry-helm-charts charts/opentelemetry-collector/templates/deployment.yaml:1,3,5@opentelemetry-collector-0.178.2 (mode deployment)"},
            {
                "daemonset": "*/*otel*collector*",
                "source": "open-telemetry/opentelemetry-operator internal/naming/main.go:61-63@v0.162.0 (an operator-managed collector is named <cr>-collector; this pattern catches the CRs and releases people name otel-…, the CRD entry the rest)",
            },
            {"deployment": "*/*otel*collector*", "source": "open-telemetry/opentelemetry-operator internal/naming/main.go:61-63@v0.162.0"},
        ],
    },
    {
        "name": "tempo-jaeger",
        "family": "traces",
        "any": [
            {
                "statefulset": "*/*tempo*",
                "source": "grafana/helm-charts charts/tempo/templates/statefulset.yaml:2,4@tempo-1.24.4 and charts/tempo/templates/_helpers.tpl:14-22@tempo-1.24.4 (the release name or <release>-tempo), charts/tempo-distributed/templates/ingester/statefulset-ingester.yaml:7,9@tempo-distributed-1.61.3 (<fullname>-ingester with tempo in the fullname)",
            },
            {"image": "grafana/tempo", "source": "grafana/helm-charts charts/tempo/values.yaml:25@tempo-1.24.4"},
            {
                "deployment": "*/*jaeger*",
                "source": "jaegertracing/helm-charts charts/jaeger/templates/jaeger/jaeger-deploy.yaml:1,3,5@jaeger-4.16.1 and charts/jaeger/templates/_helpers.tpl:14-22@jaeger-4.16.1 (the release name or <release>-jaeger); the operator names the all-in-one Deployment after the CR (jaegertracing/jaeger-operator pkg/deployment/all_in_one.go:220-222@v1.65.0), which the image entry covers",
            },
            {"image": "jaegertracing/jaeger", "source": "jaegertracing/helm-charts charts/jaeger/values.yaml:161@jaeger-4.16.1"},
        ],
    },
    {"name": "sloth", "family": "slo", "any": [{"crd": "prometheusservicelevels.sloth.slok.dev", "source": "slok/sloth pkg/kubernetes/gen/crd/sloth.slok.dev_prometheusservicelevels.yaml:7@v0.16.0"}]},
    {"name": "pyrra", "family": "slo", "any": [{"crd": "servicelevelobjectives.pyrra.dev", "source": "pyrra-dev/pyrra examples/kubernetes/manifests/setup/pyrra-slo-CustomResourceDefinition.yaml:6@v0.10.2"}]},
    {
        "name": "kubecost-opencost",
        "family": "cost",
        "any": [
            {
                "deployment": "*/*kubecost*",
                "source": "kubecost/cost-analyzer-helm-chart kubecost/templates/frontend/_helpers.tpl:21-27@v3.3.1 and kubecost/templates/frontend/frontend-deployment.yaml:3,5@v3.3.1 (<release>-frontend; the chart name is not in the workload names, kubecost/README.md:59,70 installs release kubecost), which is why the image entry follows",
            },
            {"image": "kubecost/cost-model", "source": "kubecost/cost-analyzer-helm-chart kubecost/values.yaml:37,553@v3.3.1 (icr.io/kubecost/cost-model, the cost-model container; kubecost/frontend at :453 is the same install)"},
            {
                "deployment": "*/*opencost*",
                "source": "opencost/opencost-helm-chart charts/opencost/templates/deployment.yaml:8,10@opencost-2.5.33 and charts/opencost/templates/_helpers.tpl:25-28@opencost-2.5.33 (the release name or <release>-opencost)",
            },
            {"image": "opencost/opencost", "source": "opencost/opencost-helm-chart charts/opencost/values.yaml:309@opencost-2.5.33"},
        ],
    },
    # policy / security
    {"name": "kyverno", "family": "policy", "any": [{"crd": "clusterpolicies.kyverno.io", "source": "kyverno/kyverno config/crds/kyverno/kyverno.io_clusterpolicies.yaml:7@v1.19.2"}]},
    {
        "name": "gatekeeper",
        "family": "policy",
        "any": [
            {
                "crd": "constrainttemplates.templates.gatekeeper.sh",
                "source": "open-policy-agent/gatekeeper config/crd/bases/constrainttemplate-customresourcedefinition.yaml:6@v3.23.1, charts/gatekeeper/crds/constrainttemplate-customresourcedefinition.yaml:9@v3.23.1",
            }
        ],
    },
    {"name": "trivy-operator", "family": "vuln-scan", "any": [{"crd": "vulnerabilityreports.aquasecurity.github.io", "source": "aquasecurity/trivy-operator deploy/helm/crds/aquasecurity.github.io_vulnerabilityreports.yaml:7@v0.36.1"}]},
    {
        "name": "falco",
        "family": "runtime-security",
        "any": [
            {
                "daemonset": "*/*falco*",
                "source": "falcosecurity/charts charts/falco/templates/daemonset.yaml:1,3,5@falco-9.2.2 and charts/falco/templates/_helpers.tpl:13-21@falco-9.2.2 (the release name or <release>-falco; controller.kind daemonset is the default, values.yaml:154-156)",
            },
            {"deployment": "*/*falco*", "source": "falcosecurity/charts charts/falco/values.yaml:154-156@falco-9.2.2 (controller.kind deployment renders a Deployment of the same name)"},
            {"image": "falcosecurity/falco", "source": "falcosecurity/charts charts/falco/values.yaml:13@falco-9.2.2"},
        ],
    },
    # platform
    {
        "name": "eks-managed-addons",
        "family": "platform",
        "platform": "eks",
        "any": [{"aws_addons": True, "source": "boto/botocore botocore/data/eks/2017-11-01/service-2.json:757-764,5618-5622@1.43.123 (ListAddons, GET /clusters/{name}/addons, response member addons)"}],
    },
    {
        "name": "k3s",
        "family": "distribution",
        "any": [{"node_version_contains": "+k3s", "source": "k3s-io/k3s scripts/version.sh:89-91@v1.37.1+k3s1 and scripts/build:32@v1.37.1+k3s1 (the git tag v1.37.1+k3s1 becomes component-base's gitVersion, which the kubelet reports)"}],
    },
    {
        "name": "rke2",
        "family": "distribution",
        "any": [
            {
                "node_version_contains": "+rke2",
                "source": "rancher/rke2 scripts/version.sh:60,65@v1.37.1+rke2r1, rancher/image-build-kubernetes Dockerfile:42,45@v1.37.1-rke2r1-build20260924 and scripts/semver-parse.sh:23,42-43@v1.37.1-rke2r1-build20260924 (the kubelet is built with v<k8s>+rke2rN as its version)",
            }
        ],
    },
]
