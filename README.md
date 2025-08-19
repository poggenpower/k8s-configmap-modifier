# Kubernetes ConfigMap Modifier

A containerized solution for dynamically modifying Kubernetes ConfigMaps by adding directory entries from one ConfigMap to another.

## Features

- 🐳 **Containerized**: Slim Docker image based on Python Alpine
- 🔄 **Dynamic Configuration**: Reads directories to add from a separate ConfigMap
- 📝 **Comprehensive Logging**: Uses Python's standard logging module
- 🔒 **RBAC Secured**: Proper Service Account with minimal required permissions
- 🚀 **CI/CD Ready**: GitHub Actions for automated Docker image builds
- 🏗️ **Multi-Architecture**: Supports both AMD64 and ARM64

## How It Works

1. Reads the source configuration from `backup-template` ConfigMap
2. Reads directories to add from `backup-directories` ConfigMap
3. Adds missing directories to the configuration
4. Creates or updates the `backup-config` ConfigMap with the modified configuration

## Quick Start

### 1. Deploy to Kubernetes

```bash
# Apply the Kubernetes manifests
kubectl apply -f k8s/configmap-modifier.yaml

# Check the job logs
kubectl logs job/backup-config-modifier-job

# Verify the result
kubectl get configmap backup-config -o yaml
```

### 2. Modify Directories to Add

```bash
kubectl patch configmap backup-directories --patch '
data:
  strings: |
    wurst
    backup
    bilder
    new-directory
'
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

## Configuration

### Source ConfigMap (`backup-template`)
Contains the base YAML configuration that will be modified.

### Directories ConfigMap (`backup-directories`)
Contains the list of directories to add, one per line.

### Target ConfigMap (`backup-config`)
The resulting ConfigMap with the modified configuration.

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the script (requires Kubernetes access)
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
