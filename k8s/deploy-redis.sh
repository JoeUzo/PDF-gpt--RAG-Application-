#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# A simple script to install Redis in a Kubernetes cluster using the Bitnami Helm Chart.
# This script sets up a single-replica Redis deployment with persistence for both
# master and replica components, using the 'efs-sc' StorageClass.
# ------------------------------------------------------------------------------

set -e  # Exit immediately if any command fails
set -u  # Treat unset variables as an error

NAMESPACE="redis"
RELEASE_NAME="my-redis"
STORAGE_CLASS="efs-sc"
PV_SIZE="8Gi"

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
  --set master.persistence.size=$PV_SIZE \
  --set master.persistence.storageClass=$STORAGE_CLASS \
  --set replica.persistence.enabled=true \
  --set replica.persistence.size=$PV_SIZE \
  --set replica.persistence.storageClass=$STORAGE_CLASS \
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
