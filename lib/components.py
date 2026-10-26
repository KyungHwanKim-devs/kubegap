"""Component detection rules.

The rules live in this one file; each collector folder also has a `detect` file, and this list serves as the index
of those files. A rule is "installed if any of the following match" (`any`), and the evidence kinds are:
  daemonset / deployment / statefulset: "namespace/name". A trailing * on the name means prefix match. Namespace * means any
  crd:          CRD name (plural.group)
  namespace:    namespace name
  storageclass_provisioner: the provisioner value of a StorageClass
  node_annotation: node annotation key prefix
  configmap_data_regex: regex (re.M) matched against ConfigMap data (all keys concatenated). For configuration only visible in config bodies
  image:        substring of a DaemonSet/Deployment/StatefulSet container image
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

COMPONENTS: list[dict] = [
    # networking
    {"name": "vpc-cni", "family": "cni", "platform": "eks", "any": [{"daemonset": "kube-system/aws-node"}]},
    {"name": "cilium", "family": "cni", "any": [{"daemonset": "kube-system/cilium"}, {"crd": "ciliumnetworkpolicies.cilium.io"}]},
    {"name": "calico", "family": "cni", "any": [{"daemonset": "*/calico-node"}, {"crd": "felixconfigurations.crd.projectcalico.org"}]},
    {"name": "flannel", "family": "cni", "any": [{"node_annotation": "flannel.alpha.coreos.com/"}, {"daemonset": "*/kube-flannel*"}]},
    {"name": "coredns", "family": "dns", "any": [{"deployment": "kube-system/coredns"}, {"deployment": "kube-system/rke2-coredns*"}]},
    {"name": "node-local-dns", "family": "dns-cache", "any": [{"daemonset": "kube-system/node-local-dns"}]},
    {
        "name": "kube-proxy",
        "family": "kube-proxy",
        "any": [{"daemonset": "kube-system/kube-proxy"}, {"daemonset": "kube-system/rke2-kube-proxy*"}, {"node_version_contains": "+k3s"}],
    },  # k3s embeds kube-proxy in the k3s binary (no DaemonSet); its metrics come mixed into the kubelet scrape
    {"name": "alb-controller", "family": "ingress", "platform": "eks", "any": [{"deployment": "*/aws-load-balancer-controller"}, {"crd": "targetgroupbindings.elbv2.k8s.aws"}]},
    {
        "name": "ingress-nginx",
        "family": "ingress",
        "any": [{"deployment": "*/*ingress-nginx-controller*"}, {"daemonset": "*/*ingress-nginx-controller*"}, {"image": "ingress-nginx/controller"}],
    },  # the Helm release name is prefixed (e.g. nginx-ingress-ingress-nginx-controller)
    {"name": "traefik", "family": "ingress", "any": [{"deployment": "*/traefik*"}, {"daemonset": "*/traefik*"}, {"crd": "ingressroutes.traefik.io"}, {"crd": "ingressroutes.traefik.containo.us"}]},
    {"name": "metallb", "family": "loadbalancer", "any": [{"crd": "ipaddresspools.metallb.io"}, {"daemonset": "*/metallb-speaker*"}, {"daemonset": "*/speaker"}]},
    {"name": "external-dns", "family": "external-dns", "any": [{"deployment": "*/external-dns*"}]},
    {"name": "istio", "family": "service-mesh", "any": [{"deployment": "istio-system/istiod"}, {"crd": "virtualservices.networking.istio.io"}]},
    {"name": "linkerd", "family": "service-mesh", "any": [{"deployment": "linkerd/linkerd-destination"}]},
    # node lifecycle / scaling
    {"name": "karpenter", "family": "node-autoscaler", "any": [{"crd": "nodepools.karpenter.sh"}, {"deployment": "*/karpenter"}]},
    {"name": "cluster-autoscaler", "family": "node-autoscaler", "any": [{"deployment": "*/cluster-autoscaler*"}]},
    {"name": "keda", "family": "pod-autoscaler-ext", "any": [{"crd": "scaledobjects.keda.sh"}]},
    {"name": "vpa", "family": "vpa", "any": [{"crd": "verticalpodautoscalers.autoscaling.k8s.io"}]},
    {"name": "metrics-server", "family": "metrics-server", "any": [{"deployment": "kube-system/metrics-server"}]},
    {"name": "node-termination-handler", "family": "spot-handler", "platform": "eks", "any": [{"daemonset": "*/aws-node-termination-handler*"}]},
    {"name": "descheduler", "family": "descheduler", "any": [{"deployment": "*/descheduler*"}, {"cronjob_ignored": "*/descheduler*"}]},
    {"name": "kured", "family": "node-reboot", "any": [{"daemonset": "*/kured"}]},
    # storage
    {"name": "ebs-csi", "family": "csi", "platform": "eks", "any": [{"daemonset": "kube-system/ebs-csi-node"}, {"storageclass_provisioner": "ebs.csi.aws.com"}]},
    {"name": "efs-csi", "family": "csi-shared", "platform": "eks", "any": [{"daemonset": "kube-system/efs-csi-node"}]},
    {"name": "local-path-provisioner", "family": "csi", "any": [{"deployment": "kube-system/local-path-provisioner"}, {"storageclass_provisioner": "rancher.io/local-path"}]},
    {"name": "longhorn", "family": "csi", "any": [{"crd": "volumes.longhorn.io"}]},
    {"name": "rook-ceph", "family": "csi", "any": [{"crd": "cephclusters.ceph.rook.io"}]},
    {"name": "nfs-provisioner", "family": "csi-shared", "any": [{"storageclass_provisioner": "nfs.csi.k8s.io"}, {"deployment": "*/nfs-subdir-external-provisioner*"}]},
    {"name": "velero", "family": "backup", "any": [{"crd": "backups.velero.io"}, {"deployment": "*/velero"}]},
    {"name": "k8up", "family": "backup", "any": [{"crd": "backups.k8up.io"}]},
    # certificates / secrets
    {"name": "cert-manager", "family": "certificates", "any": [{"crd": "certificates.cert-manager.io"}]},
    {"name": "external-secrets", "family": "secrets-manager", "any": [{"crd": "externalsecrets.external-secrets.io"}]},
    {"name": "secrets-store-csi", "family": "secrets-manager", "any": [{"daemonset": "*/secrets-store-csi-driver*"}, {"crd": "secretproviderclasses.secrets-store.csi.x-k8s.io"}]},
    {"name": "sealed-secrets", "family": "secrets-manager", "any": [{"crd": "sealedsecrets.bitnami.com"}]},
    {"name": "vault", "family": "secrets-manager", "any": [{"statefulset": "*/vault"}, {"deployment": "*/vault-agent-injector*"}]},
    {"name": "eks-pod-identity-agent", "family": "pod-identity", "platform": "eks", "any": [{"daemonset": "kube-system/eks-pod-identity-agent"}]},
    # deployment / GitOps
    {"name": "ecr", "family": "registry", "any": [{"image": ".dkr.ecr."}]},  # enabled when pods use ECR images (always on EKS, since add-on images come from ECR). The aws step is skipped off EKS
    {"name": "argocd", "family": "gitops", "any": [{"deployment": "*/argocd-server"}, {"crd": "applications.argoproj.io"}]},
    {"name": "flux", "family": "gitops", "any": [{"crd": "kustomizations.kustomize.toolkit.fluxcd.io"}]},
    {"name": "argo-rollouts", "family": "progressive-delivery", "any": [{"crd": "rollouts.argoproj.io"}]},
    {"name": "reloader", "family": "config-reload", "any": [{"deployment": "*/reloader*"}]},
    {"name": "actions-runner-controller", "family": "ci-runner", "any": [{"crd": "autoscalingrunnersets.actions.github.com"}, {"crd": "runnerdeployments.actions.summerwind.dev"}]},
    # observability
    {"name": "prometheus-operator", "family": "metrics-operator", "any": [{"crd": "prometheuses.monitoring.coreos.com"}]},
    {"name": "prometheus", "family": "metrics-store", "any": [{"statefulset": "*/prometheus-*"}, {"deployment": "*/prometheus-server*"}, {"image": "prom/prometheus"}, {"image": "prometheus/prometheus"}]},
    {"name": "victoria-metrics", "family": "metrics-store", "any": [{"image": "victoriametrics/victoria-metrics"}, {"statefulset": "*/vmsingle*"}]},
    {"name": "thanos", "family": "metrics-longterm", "any": [{"image": "thanos/thanos"}]},
    {"name": "alertmanager", "family": "alert-router", "any": [{"statefulset": "*/alertmanager-*"}, {"image": "prometheus/alertmanager"}]},
    {"name": "grafana", "family": "dashboards", "any": [{"deployment": "*/*grafana*"}, {"image": "grafana/grafana"}]},
    {"name": "loki", "family": "logs-store", "any": [{"statefulset": "*/loki*"}, {"deployment": "*/loki*"}, {"image": "grafana/loki"}]},
    {"name": "elasticsearch-opensearch", "family": "logs-store", "any": [{"statefulset": "*/*elasticsearch*"}, {"statefulset": "*/*opensearch*"}]},
    {"name": "promtail", "family": "logs-agent", "any": [{"daemonset": "*/*promtail*"}]},
    {"name": "alloy", "family": "logs-agent", "any": [{"daemonset": "*/*alloy*"}]},
    {"name": "fluent-bit", "family": "logs-agent", "any": [{"daemonset": "*/*fluent-bit*"}, {"daemonset": "*/*fluentbit*"}]},
    {"name": "fluentd", "family": "logs-agent", "any": [{"daemonset": "*/*fluentd*"}]},
    {"name": "vector", "family": "logs-agent", "any": [{"daemonset": "*/*vector*"}]},
    {"name": "cloudwatch-agent", "family": "logs-agent", "platform": "eks", "any": [{"daemonset": "amazon-cloudwatch/*"}]},
    {"name": "kube-state-metrics", "family": "kube-state-metrics", "any": [{"deployment": "*/*kube-state-metrics*"}]},
    {"name": "node-exporter", "family": "node-exporter", "any": [{"daemonset": "*/*node-exporter*"}]},
    {"name": "kubernetes-event-exporter", "family": "event-retention", "any": [{"deployment": "*/*event-exporter*"}]},
    # fluent-bit's kubernetes_events input also ships events to a log store (seen on a k3s: a fluent-bit ConfigMap forwarding to an ES events index). Was a false absence finding before this rule.
    {"name": "fluent-bit-events", "family": "event-retention", "any": [{"configmap_data_regex": r"\[INPUT\]\s*\n\s*Name\s+kubernetes_events"}]},
    {"name": "opentelemetry-collector", "family": "traces", "any": [{"crd": "opentelemetrycollectors.opentelemetry.io"}, {"daemonset": "*/*otel*collector*"}, {"deployment": "*/*otel*collector*"}]},
    {"name": "tempo-jaeger", "family": "traces", "any": [{"statefulset": "*/*tempo*"}, {"deployment": "*/*jaeger*"}]},
    {"name": "sloth", "family": "slo", "any": [{"crd": "prometheusservicelevels.sloth.slok.dev"}]},
    {"name": "pyrra", "family": "slo", "any": [{"crd": "servicelevelobjectives.pyrra.dev"}]},
    {"name": "kubecost-opencost", "family": "cost", "any": [{"deployment": "*/*kubecost*"}, {"deployment": "*/*opencost*"}]},
    # policy / security
    {"name": "kyverno", "family": "policy", "any": [{"crd": "clusterpolicies.kyverno.io"}]},
    {"name": "gatekeeper", "family": "policy", "any": [{"crd": "constrainttemplates.templates.gatekeeper.sh"}]},
    {"name": "trivy-operator", "family": "vuln-scan", "any": [{"crd": "vulnerabilityreports.aquasecurity.github.io"}]},
    {"name": "falco", "family": "runtime-security", "any": [{"daemonset": "*/*falco*"}]},
    # platform
    {"name": "eks-managed-addons", "family": "platform", "platform": "eks", "any": [{"aws_addons": True}]},
    {"name": "k3s", "family": "distribution", "any": [{"node_version_contains": "+k3s"}]},
    {"name": "rke2", "family": "distribution", "any": [{"node_version_contains": "+rke2"}]},
]
