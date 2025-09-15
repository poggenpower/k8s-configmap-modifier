#!/usr/bin/env python3

import yaml
import json
import logging
import os
from kubernetes import client, config
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('backup-config-modifier')

def get_namespace() -> str:
    """
    Reads the current Kubernetes namespace from the service account file,
    or falls back to the 'NAMESPACE' environment variable if the file does not exist.
    Raises an exception if neither is available.

    Returns:
        str: The namespace as a string.

    Raises:
        RuntimeError: If namespace cannot be determined.
    """
    namespace_file = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    try:
        with open(namespace_file) as f:
            return f.read().strip()
    except FileNotFoundError:
        env_namespace = os.environ.get("NAMESPACE")
        if env_namespace:
            return env_namespace
        raise RuntimeError("Namespace could not be determined from file or environment variable 'NAMESPACE'.")

def get_configmap(v1: client.CoreV1Api, name: str, namespace: str) -> client.V1ConfigMap:
    """
    Fetches a ConfigMap by name and namespace.

    Args:
        v1 (client.CoreV1Api): Kubernetes CoreV1Api client.
        name (str): Name of the ConfigMap.
        namespace (str): Namespace of the ConfigMap.

    Returns:
        client.V1ConfigMap: The requested ConfigMap object.
    """
    logger.info(f'Reading ConfigMap: {name}')
    return v1.read_namespaced_config_map(name=name, namespace=namespace)

def parse_config(configmap: client.V1ConfigMap, key: str = 'config.yaml') -> Dict[str, Any]:
    """
    Parses YAML configuration from the specified key in the ConfigMap data.

    Args:
        configmap (client.V1ConfigMap): The ConfigMap object.
        key (str): The key in the ConfigMap data containing YAML.

    Returns:
        Dict[str, Any]: Parsed configuration as a dictionary.
    """
    logger.info('Parsing YAML configuration from ConfigMap')
    config_data = yaml.safe_load(configmap.data.get(key, '{}'))
    logger.info(f'Parsed configuration keys: {list(config_data.keys())}')
    logger.debug(f'Full configuration: {config_data}')
    return config_data

def ensure_directory_key(config_data: Dict[str, Any], directory_key: str) -> None:
    """
    Ensures the configuration contains the directory key, creating it if missing.

    Args:
        config_data (Dict[str, Any]): The configuration dictionary.
        directory_key (str): The key for directories in the config.

    Returns:
        None
    """
    if directory_key not in config_data:
        config_data[directory_key] = []
        logger.warning(f'Created new {directory_key} list (was missing from config)')
    else:
        logger.info(f'Existing {directory_key}: {config_data[directory_key]}')

def list_local_storage_dirs_by_node(v1: client.CoreV1Api) -> Dict[str, List[str]]:
    """
    Lists all PersistentVolumes with StorageClass 'local-storage', extracts their paths,
    and groups them by node based on node affinity.

    Args:
        v1 (client.CoreV1Api): Kubernetes CoreV1Api client.

    Returns:
        Dict[str, List[str]]: Dictionary mapping node names to lists of directory paths.
    """
    logger.info("Listing all PersistentVolumes with StorageClass 'local-storage' and grouping by node")
    pv_list = v1.list_persistent_volume()
    node_dirs = {}
    for pv in pv_list.items:
        sc = pv.spec.storage_class_name
        if sc == "local-storage":
            path = None
            if pv.spec.local and pv.spec.local.path:
                path = pv.spec.local.path
            node_name = None
            # Discover node affinity from required terms
            if pv.spec.node_affinity and pv.spec.node_affinity.required:
                for term in pv.spec.node_affinity.required.node_selector_terms:
                    for expr in term.match_expressions:
                        if expr.key == "kubernetes.io/hostname" and expr.values:
                            node_name = expr.values[0]
            if path and node_name:
                node_dirs.setdefault(node_name, []).append(path)
    logger.info(f'Directories grouped by node: {node_dirs}')
    return node_dirs

def add_directories(config_data: Dict[str, Any], directory_key: str, new_dirs: List[str]) -> None:
    """
    Adds new directory paths to the configuration if they are not already present.

    Args:
        config_data (Dict[str, Any]): The configuration dictionary.
        directory_key (str): The key for directories in the config.
        new_dirs (List[str]): List of new directory paths to add.

    Returns:
        None
    """
    logger.info(f'Adding required directories: {new_dirs}')
    added_dirs = []
    for dir_name in new_dirs:
        if dir_name not in config_data[directory_key]:
            config_data[directory_key].append(dir_name)
            added_dirs.append(dir_name)
            logger.debug(f'Added directory: {dir_name}')
    if added_dirs:
        logger.info(f'Added directories: {added_dirs}')
    else:
        logger.info('All required directories already present')
    logger.info(f'Final {directory_key} list: {config_data[directory_key]}')

def update_or_create_configmap(
    v1: client.CoreV1Api,
    namespace: str,
    target_cm_name: str,
    new_config_yaml: str
) -> None:
    """
    Updates the target ConfigMap if it exists, otherwise creates a new one.

    Args:
        v1 (client.CoreV1Api): Kubernetes CoreV1Api client.
        namespace (str): Namespace for the ConfigMap.
        target_cm_name (str): Name of the target ConfigMap.
        new_config_yaml (str): YAML string of the modified configuration.

    Returns:
        None
    """
    logger.info(f'Checking if target ConfigMap {target_cm_name} exists')
    try:
        existing_cm = v1.read_namespaced_config_map(
            name=target_cm_name,
            namespace=namespace 
        )
        logger.info('Target ConfigMap exists - updating')
        existing_cm.data = {'config.yaml': new_config_yaml}
        v1.replace_namespaced_config_map(
            name=target_cm_name,
            namespace=namespace,
            body=existing_cm
        )
        logger.info(f'Successfully updated existing {target_cm_name} ConfigMap')
    except client.rest.ApiException as e:
        if e.status == 404:
            logger.info('Target ConfigMap does not exist - creating new one')
            new_cm = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=target_cm_name),
                data={'config.yaml': new_config_yaml}
            )
            v1.create_namespaced_config_map(
                namespace=namespace,
                body=new_cm
            )
            logger.info(f'Successfully created new {target_cm_name} ConfigMap')
        else:
            logger.error(f'API error while checking ConfigMap: {e}')
            raise

def main() -> None:
    """
    Main entry point for modifying the backup configuration ConfigMap.

    Returns:
        None
    """
    logger.info('Starting backup configuration modifier')
    source_cm_name = os.environ.get('SOURCE_CONFIGMAP_NAME', 'backup-template')
    target_cm_name = os.environ.get('TARGET_CONFIGMAP_NAME', 'backup-config')
    directory_key = os.environ.get('DIRECTORY_KEY', 'directories')

    logger.info('Loading Kubernetes in-cluster configuration')
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException as kccece:
        try:
            logger.warning(f"Can't load kubeconfig from cluster, try KUBECONFG file")
            config.load_kube_config()
        except config.config_exception.ConfigException as kccece:
            logger.error(f'Failed to initialize Kubernetes client: {e}')
            exit(1)
    v1 = client.CoreV1Api()
    logger.info('Kubernetes client initialized successfully')

    try:
        namespace = get_namespace()
        source_cm = get_configmap(v1, source_cm_name, namespace)
        node_dirs = list_local_storage_dirs_by_node(v1)
        for node in node_dirs.keys():
            config_data = parse_config(source_cm)
            ensure_directory_key(config_data, directory_key)
            add_directories(config_data, directory_key, node_dirs[node])
            new_config_yaml = yaml.dump(config_data, default_flow_style=False)
            update_or_create_configmap(v1, namespace, f"{target_cm_name}-{node}", new_config_yaml)
            logger.info(f'Configuration modification for {target_cm_name}-{node} completed successfully')
    except Exception as e:
        logger.error(f'Failed with exception: {e}', exc_info=True)
        exit(1)

if __name__ == '__main__':
    main()
#