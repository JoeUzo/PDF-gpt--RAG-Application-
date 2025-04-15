#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# A simple script to manage a Redis deployment in a Kubernetes cluster using the
# Bitnami Helm Chart. This script provides two options:
#   - "create": Install/upgrade Redis with persistence for master and replica,
#               using the 'efs-sc' StorageClass.
#   - "delete": Remove the Redis deployment and its namespace.
# ------------------------------------------------------------------------------
 
set -e  
set -u  

if [ "$#" -eq 0 ]; then
  echo "Usage: $(basename "$0") {create|delete}"
  exit 1
fi

ACTION="$1"

NAMESPACE="redis"
RELEASE_NAME="my-redis"
STORAGE_CLASS="efs-sc"
PV_SIZE="8Gi"

create() {
  echo "Creating namespace '$NAMESPACE' if it doesn't exist..."
  kubectl create namespace "$NAMESPACE" 2>/dev/null || true

  echo "Adding the Bitnami repo if not already added..."
  helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true
  helm repo update

  echo "Installing/Upgrading Redis in namespace '$NAMESPACE'..."
  helm upgrade --install "$RELEASE_NAME" bitnami/redis \
    --namespace "$NAMESPACE" \
    --set auth.enabled=false \
    --set master.persistence.enabled=true \
    --set master.persistence.size="$PV_SIZE" \
    --set master.persistence.storageClass="$STORAGE_CLASS" \
    --set replica.persistence.enabled=true \
    --set replica.persistence.size="$PV_SIZE" \
    --set replica.persistence.storageClass="$STORAGE_CLASS" \
    --set replica.replicaCount=1

  echo "-------------------------"
  echo "Redis installed/upgraded!"
  echo "Namespace:  $NAMESPACE"
  echo "Release:    $RELEASE_NAME"
  echo "Storage:    $PV_SIZE on $STORAGE_CLASS"
  echo "-------------------------"
  echo "You can connect to Redis from within your cluster at:"
  echo "  Service name: ${RELEASE_NAME}.${NAMESPACE}.svc.cluster.local"
  echo "  Port: 6379 (TCP)"
  echo "-------------------------"
}

delete() {
  echo "Deleting Redis release '$RELEASE_NAME' in namespace '$NAMESPACE'..."
  helm uninstall "$RELEASE_NAME" --namespace "$NAMESPACE" 2>/dev/null || true

  echo "Deleting namespace '$NAMESPACE'..."
  kubectl delete namespace "$NAMESPACE" --ignore-not-found
}

case "$ACTION" in
  create)
    create
    ;;
  delete)
    delete
    ;;
  *)
    echo "Invalid action specified. Use 'create' or 'delete'."
    exit 1
    ;;
esac
