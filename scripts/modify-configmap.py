#!/usr/bin/env python3

import yaml
import json
import logging
import os
from kubernetes import client, config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('backup-config-modifier')

def main():
    logger.info('Starting backup configuration modifier')
    
    # Configurable names and key via ENV
    source_cm_name = os.environ.get('SOURCE_CONFIGMAP_NAME', 'backup-template')
    dirs_cm_name = os.environ.get('DIRECTORIES_CONFIGMAP_NAME', 'backup-directories')
    target_cm_name = os.environ.get('TARGET_CONFIGMAP_NAME', 'backup-config')
    directory_key = os.environ.get('DIRECTORY_KEY', 'directories')

    # Load in-cluster config
    logger.info('Loading Kubernetes in-cluster configuration')
    try:
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        logger.info('Kubernetes client initialized successfully')
    except Exception as e:
        logger.error(f'Failed to initialize Kubernetes client: {e}')
        exit(1)
    
    try:
        # get own namespace
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            namespace = f.read().strip()

        # Read the source configmap
        logger.info(f'Reading source ConfigMap: {source_cm_name}')
        source_cm = v1.read_namespaced_config_map(
            name=source_cm_name,
            namespace=namespace
        )
        logger.info(f'Source ConfigMap found with keys: {list(source_cm.data.keys())}')
        
        # Parse the YAML config
        logger.info('Parsing YAML configuration from source ConfigMap')
        config_data = yaml.safe_load(source_cm.data.get('config.yaml', '{}'))
        logger.info(f'Parsed configuration keys: {list(config_data.keys())}')
        logger.debug(f'Full configuration: {config_data}')
        
        # Ensure directories list exists
        logger.info(f'Checking {directory_key} list in configuration')
        if directory_key not in config_data:
            config_data[directory_key] = []
            logger.warning(f'Created new {directory_key} list (was missing from config)')
        else:
            logger.info(f'Existing {directory_key}: {config_data[directory_key]}')
        
        # Read the directories to add from ConfigMap
        logger.info(f'Reading directories to add from ConfigMap: {dirs_cm_name}')
        dirs_cm = v1.read_namespaced_config_map(
            name=dirs_cm_name,
            namespace=namespace
        )
        
        # Parse the directories list
        dirs_string = dirs_cm.data.get('strings', '')
        new_dirs = [line.strip() for line in dirs_string.strip().split('\n') if line.strip()]
        logger.info(f'Directories to add from ConfigMap: {new_dirs}')
        
        # Add the required entries if they don't exist
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
        
        # Create the new configmap
        logger.info('Converting modified configuration back to YAML')
        new_config_yaml = yaml.dump(config_data, default_flow_style=False)
        logger.info(f'Generated YAML config ({len(new_config_yaml)} characters)')
        logger.debug(f'Generated YAML content:\n{new_config_yaml}')
        
        # Check if target configmap exists
        logger.info(f'Checking if target ConfigMap {target_cm_name} exists')
        try:
            existing_cm = v1.read_namespaced_config_map(
                name=target_cm_name,
                namespace=namespace 
            )
            logger.info('Target ConfigMap exists - updating')
            # Update existing configmap
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
                # Create new configmap
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
                
        logger.info('Configuration modification completed successfully')
        
    except Exception as e:
        logger.error(f'Failed with exception: {e}', exc_info=True)
        exit(1)

if __name__ == '__main__':
    main()