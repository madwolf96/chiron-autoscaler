#!/bin/bash

usage() { echo "Usage: $0 [-c cluster: <string>] [-z zone: <string>]" 1>&2; exit 1; }

while getopts ":c:z:" o; do
    case "${o}" in
        c)
            c=${OPTARG}
            ;;
        z)
            z=${OPTARG}
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ -z "${c}" ] || [ -z "${z}" ]; then
    usage
fi

if [ ! -d ./kubeconfig.yaml ]; then
    GET_CMD="gcloud container clusters describe $c --zone=$z"

    cat > kubeconfig.yaml <<EOF
apiVersion: v1
kind: Config
current-context: cluster-1
contexts: [{name: cluster-1, context: {cluster: cluster-1, user: user-1}}]
users: [{name: user-1, user: {auth-provider: {name: gcp}}}]
clusters:
- name: cluster-1
  cluster:
    server: "https://$(eval "$GET_CMD --format='value(endpoint)'")"
    certificate-authority-data: "$(eval "$GET_CMD --format='value(masterAuth.clusterCaCertificate)'")"
EOF
else
    echo "kubeconfig.yaml already exist!"
fi
