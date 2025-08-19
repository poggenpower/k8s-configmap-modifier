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

## Configuration via Environment Variables

You can customize the behavior of the modifier using the following environment variables:

| Environment Variable         | Default Value        | Description                                                      |
|------------------------------|----------------------|------------------------------------------------------------------|
| `SOURCE_CONFIGMAP_NAME`      | `backup-template`    | Name of the source ConfigMap containing the base YAML config     |
| `DIRECTORIES_CONFIGMAP_NAME` | `backup-directories` | Name of the ConfigMap listing directories to add                 |
| `TARGET_CONFIGMAP_NAME`      | `backup-config`      | Name of the target ConfigMap to create or update                 |
| `DIRECTORY_KEY`              | `directories`        | Key in the YAML config where directories are listed              |

Set these variables in your Kubernetes manifest or Docker run command to override defaults.


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
