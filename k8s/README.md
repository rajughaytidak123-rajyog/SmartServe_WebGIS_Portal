# SmartServe GIS – Kubernetes (K8s) Production Deployment Guide

This directory contains production-ready Kubernetes manifests for orchestrating the **SmartServe GIS Location-Based Multi-Service WebGIS Platform** on local clusters (Minikube / Kind / Docker Desktop K8s) or enterprise cloud Kubernetes (GKE / EKS / AKS).

---

## 1. Architectural Overview

```
                        [ Internet / Client Browser ]
                                     │
                                     ▼
                    [ Ingress Controller (Port 80/443) ]
                                     │
             ┌───────────────────────┴───────────────────────┐
             │                                               │
             ▼                                               ▼
  [ Service: smartserve-client ]              [ Service: smartserve-backend ]
       (Nginx Pods x 2)                            (FastAPI Pods x 2)
  ├── Leaflet Frontend (/)                                   │
  ├── MapLibre Vector (/maplibre)                            │
  └── Static PMTiles (/data)                                 ▼
                                              [ StatefulSet: smartserve-postgis ]
                                                ├── Pod: smartserve-postgis-0
                                                └── PVC: 10Gi (Persistent Volume)
```

---

## 2. Manifest Inventory

| File | Resource Kind | Purpose |
| :--- | :--- | :--- |
| `01-namespace.yaml` | `Namespace` | Creates isolated `smartserve-gis` namespace |
| `02-secret.yaml` | `Secret` | Stores encrypted DB credentials & connection strings |
| `03-postgis-pv-pvc.yaml` | `PersistentVolumeClaim` | 10Gi durable storage claim for PostGIS data |
| `04-postgis-statefulset.yaml` | `StatefulSet` | High-availability PostGIS instance with health probes |
| `05-postgis-service.yaml` | `Service` | Internal ClusterIP & Headless routing for PostGIS |
| `06-backend-deployment.yaml` | `Deployment` | Replicated FastAPI REST API instances (x2) |
| `07-backend-service.yaml` | `Service` | Internal routing to backend REST pods |
| `08-client-deployment.yaml` | `Deployment` | Replicated Nginx WebGIS client instances (x2) |
| `09-client-service.yaml` | `Service` | NodePort service exposing client on Port 30080 |
| `10-ingress.yaml` | `Ingress` | Unified HTTP reverse proxy & path-based routing |

---

## 3. Step-by-Step Deployment Instructions

### A. Pre-requisites
- A running Kubernetes cluster: Minikube (`minikube start`) or Kind (`kind create cluster`).
- `kubectl` CLI installed and configured.

### B. Build Local Docker Images (if running locally)
```bash
# Build Backend image
docker build -t smartserve-backend:2.0.0 -f backend/Dockerfile .

# Build Client image
docker build -t smartserve-client:2.0.0 -f docker/Dockerfile.client .

# If using Minikube, load images into Minikube VM:
minikube image load smartserve-backend:2.0.0
minikube image load smartserve-client:2.0.0
```

### C. Apply Kubernetes Manifests in Order
```bash
# 1. Create Namespace
kubectl apply -f k8s/01-namespace.yaml

# 2. Create DB Secrets
kubectl apply -f k8s/02-secret.yaml

# 3. Create Persistent Volume Claim
kubectl apply -f k8s/03-postgis-pv-pvc.yaml

# 4. Deploy PostGIS StatefulSet & Services
kubectl apply -f k8s/04-postgis-statefulset.yaml
kubectl apply -f k8s/05-postgis-service.yaml

# Wait for PostGIS to become ready
kubectl wait --for=condition=ready pod -l app=smartserve-postgis -n smartserve-gis --timeout=120s

# 5. Deploy Backend REST API & Services
kubectl apply -f k8s/06-backend-deployment.yaml
kubectl apply -f k8s/07-backend-service.yaml

# 6. Deploy WebGIS Client & Services
kubectl apply -f k8s/08-client-deployment.yaml
kubectl apply -f k8s/09-client-service.yaml

# 7. (Optional) Deploy Ingress
kubectl apply -f k8s/10-ingress.yaml
```

---

## 4. Verification & Testing

Check pod status:
```bash
kubectl get pods,svc,pvc -n smartserve-gis
```

Expected Output:
```text
NAME                                      READY   STATUS    RESTARTS   AGE
pod/smartserve-backend-674b89d89b-7t8k9   1/1     Running   0          45s
pod/smartserve-backend-674b89d89b-f2z1x   1/1     Running   0          45s
pod/smartserve-client-857c59db6b-4p2m9    1/1     Running   0          30s
pod/smartserve-client-857c59db6b-k8w1x    1/1     Running   0          30s
pod/smartserve-postgis-0                  1/1     Running   0          2m

NAME                                  TYPE        CLUSTER-IP       PORT(S)
service/smartserve-backend            ClusterIP   10.96.124.45     8000/TCP
service/smartserve-client             NodePort    10.96.210.88     80:30080/TCP
service/smartserve-postgis            ClusterIP   10.96.85.12      5432/TCP
service/smartserve-postgis-headless   ClusterIP   None             5432/TCP
```

### Accessing the WebGIS Client
```bash
# Access via Port Forwarding
kubectl port-forward svc/smartserve-client 8080:80 -n smartserve-gis

# Access Leaflet: http://localhost:8080/
# Access MapLibre: http://localhost:8080/maplibre/
# Access Backend Health: http://localhost:8080/health
```

---

## 5. Teardown / Cleanup

To delete all deployed resources and release storage:
```bash
kubectl delete namespace smartserve-gis
```
