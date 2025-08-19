#!/usr/bin/env python3

import yaml
import json
import logging
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
        # Read the source configmap
        logger.info('Reading source ConfigMap: backup-template')
        source_cm = v1.read_namespaced_config_map(
            name='backup-template',
            namespace='default'
        )
        logger.info(f'Source ConfigMap found with keys: {list(source_cm.data.keys())}')
        
        # Parse the YAML config
        logger.info('Parsing YAML configuration from source ConfigMap')
        config_data = yaml.safe_load(source_cm.data.get('config.yaml', '{}'))
        logger.info(f'Parsed configuration keys: {list(config_data.keys())}')
        logger.debug(f'Full configuration: {config_data}')
        
        # Ensure directories list exists
        logger.info('Checking directories list in configuration')
        if 'directories' not in config_data:
            config_data['directories'] = []
            logger.warning('Created new directories list (was missing from config)')
        else:
            logger.info(f'Existing directories: {config_data["directories"]}')
        
        # Read the directories to add from ConfigMap
        logger.info('Reading directories to add from ConfigMap: backup-directories')
        dirs_cm = v1.read_namespaced_config_map(
            name='backup-directories',
            namespace='default'
        )
        
        # Parse the directories list
        dirs_string = dirs_cm.data.get('strings', '')
        new_dirs = [line.strip() for line in dirs_string.strip().split('\n') if line.strip()]
        logger.info(f'Directories to add from ConfigMap: {new_dirs}')
        
        # Add the required entries if they don't exist
        logger.info(f'Adding required directories: {new_dirs}')
        added_dirs = []
        for dir_name in new_dirs:
            if dir_name not in config_data['directories']:
                config_data['directories'].append(dir_name)
                added_dirs.append(dir_name)
                logger.debug(f'Added directory: {dir_name}')
        
        if added_dirs:
            logger.info(f'Added directories: {added_dirs}')
        else:
            logger.info('All required directories already present')
        
        logger.info(f'Final directories list: {config_data["directories"]}')
        
        # Create the new configmap
        logger.info('Converting modified configuration back to YAML')
        new_config_yaml = yaml.dump(config_data, default_flow_style=False)
        logger.info(f'Generated YAML config ({len(new_config_yaml)} characters)')
        logger.debug(f'Generated YAML content:\n{new_config_yaml}')
        
        # Check if target configmap exists
        logger.info('Checking if target ConfigMap backup-config exists')
        try:
            existing_cm = v1.read_namespaced_config_map(
                name='backup-config',
                namespace='default'
            )
            logger.info('Target ConfigMap exists - updating')
            # Update existing configmap
            existing_cm.data = {'config.yaml': new_config_yaml}
            v1.replace_namespaced_config_map(
                name='backup-config',
                namespace='default',
                body=existing_cm
            )
            logger.info('Successfully updated existing backup-config ConfigMap')
        except client.rest.ApiException as e:
            if e.status == 404:
                logger.info('Target ConfigMap does not exist - creating new one')
                # Create new configmap
                new_cm = client.V1ConfigMap(
                    metadata=client.V1ObjectMeta(name='backup-config'),
                    data={'config.yaml': new_config_yaml}
                )
                v1.create_namespaced_config_map(
                    namespace='default',
                    body=new_cm
                )
                logger.info('Successfully created new backup-config ConfigMap')
            else:
                logger.error(f'API error while checking ConfigMap: {e}')
                raise
                
        logger.info('Configuration modification completed successfully')
        
    except Exception as e:
        logger.error(f'Failed with exception: {e}', exc_info=True)
        exit(1)

if __name__ == '__main__':
    main()
