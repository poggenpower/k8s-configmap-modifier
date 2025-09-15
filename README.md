# Kubernetes ConfigMap Modifier

A containerized solution for dynamically modifying Kubernetes ConfigMaps by adding directory entries from one ConfigMap to another.

## Features

- 🐳 **Containerized**: Slim Docker image based on Python Alpine
- 🔄 **Dynamic Configuration**: Reads directories to add from PersistentVolumes with `local-storage` StorageClass
- 📝 **Comprehensive Logging**: Uses Python's standard logging module
- 🔒 **RBAC Secured**: Proper Service Account with minimal required permissions
- 🚀 **CI/CD Ready**: GitHub Actions for automated Docker image builds
- 🏗️ **Multi-Architecture**: Supports both AMD64 and ARM64

## How It Works

1. Reads the source configuration from the `backup-template` ConfigMap
2. Lists directories from PersistentVolumes with StorageClass `local-storage`, grouped by node
3. Adds missing directories to the configuration under the specified key (default: `directories`)
4. Creates or updates a target ConfigMap for each node (e.g., `backup-config-NODENAME`) with the modified configuration

## Quick Start

### 1. Deploy to Kubernetes

```bash
kubectl apply -f k8s/configmap-modifier.yaml
kubectl logs job/backup-config-modifier-job
kubectl get configmap backup-config-NODENAME -o yaml
```

### 2. Example: Patch Source ConfigMap

```bash
kubectl patch configmap backup-template --patch '
data:
  config.yaml: |
    directories:
      - /mnt/old
'
```

### 3. Example: Add a Local Storage PV

```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: local-pv-example
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  storageClassName: local-storage
  local:
    path: /mnt/new
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: kubernetes.io/hostname
              operator: In
              values:
                - node-1
EOF
```

## Docker Image

The Docker image is automatically built and published to GitHub Container Registry:

- **Registry**: `ghcr.io/YOUR-USERNAME/k8s-configmap-modifier`
- **Tags**: `latest`, version tags, branch names
- **Architectures**: `linux/amd64`, `linux/arm64`

### Building Locally

```bash
docker build -t configmap-modifier .
docker run --rm configmap-modifier python --version
```

## Configuration via Environment Variables

You can customize the behavior of the modifier using the following environment variables:

| Environment Variable         | Default Value        | Description                                                      |
|------------------------------|----------------------|------------------------------------------------------------------|
| `SOURCE_CONFIGMAP_NAME`      | `backup-template`    | Name of the source ConfigMap containing the base YAML config     |
| `TARGET_CONFIGMAP_NAME`      | `backup-config`      | Name prefix of the target ConfigMap to create or update          |
| `DIRECTORY_KEY`              | `directories`        | Key in the YAML config where directories are listed              |
| `NAMESPACE`                  | *auto-detect*        | Namespace to operate in (auto-detected or set explicitly)        |
| `KUBECONFIG`                 | *optional*           | Path to kubeconfig file (for out-of-cluster use)                 |

Set these variables in your Kubernetes manifest or Docker run command to override defaults.

## Development

### Running Locally
if you want to run with a restricted user similar to the service account you should create formyour cronjob, follow `sample-yaml/user-for-local-testing.yaml`

```bash
export KUBECONFIG=/path/to/your/kubeconfig # if custom user
pip install -r requirements.txt
python scripts/modify-configmap.py
```

### GitHub Actions

The repository includes automated CI/CD:

- ✅ **Multi-architecture builds** (AMD64, ARM64)
- ✅ **Security scanning** with Trivy
- ✅ **Automated tagging** based on Git refs
- ✅ **GitHub Container Registry** publishing

## Security

- Uses non-root user in container
- Minimal RBAC permissions (only ConfigMap access)
- Regular security scanning with Trivy
- Pinned dependency versions

## License

MIT License - see LICENSE file for details.
