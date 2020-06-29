# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to build the parameters for cloudformation stacks based on
   param files in the params folder
"""

import json
import secrets
import string # pylint: disable=deprecated-module # https://www.logilab.org/ticket/2481
import os
import ast
import yaml
import boto3

from schema import Schema
from update_pipeline_schema_validation import UpdateSchemaValidation

SOURCE_EVENT = os.environ["UPDATE_PIPELINE_EVENT"]
CODEBUILD_SRC_DIR = os.environ["CODEBUILD_SRC_DIR"]
    
class UpdatePipelines:
    def __init__(self, source_event, source_file_name):
        self.source_event = source_event
        self.source_file_name = source_file_name

    def update_deployment_map(self):
        source_event = UpdateSchemaValidation(self.source_event).validated
        source_map = UpdatePipelines._parse(self.source_file_name)
        
        for update in source_event.get('updates'):
            update_name = update['pipeline']
            for p in source_map.get('pipelines'):
                # same pipeline
                if update_name == p.get('name'):
                    for update_target in update['targets']:
                        update_target_name = update_target['path']
                        for pipeline_target in p['targets']:
                            # same target
                            if update_target_name == pipeline_target.get('path'):
                                pipeline_target['cfns'] = update_target['cfns']

        with open("{0}.yml".format(self.source_file_name), 'w') as file:
            documents = yaml.dump(source_map, file)
            
    @staticmethod
    def _parse(filename):
        """
        Attempt to parse the parameters file and return he default
        CloudFormation parameter base object if not found. Returning
        Base CloudFormation Parameters here since if the user was using
        Any other type (SC, ECS) they would require a parameter file (global.json)
        and thus this would not fail.
        """
        try:
            with open("{0}.json".format(filename)) as file:
                return json.load(file)
        except FileNotFoundError:
            try:
                with open("{0}.yml".format(filename)) as file:
                    return yaml.load(file, Loader=yaml.FullLoader)
            except yaml.scanner.ScannerError:
                print(f'Invalid Yaml for {filename}.yml')
            except FileNotFoundError:
                print(f'Could not open {filename}.yml')

def main():
    print(SOURCE_EVENT)
    source_event_parsed = json.loads(SOURCE_EVENT)
    deployment_map_file = "{0}/deployment_map.yml".format(CODEBUILD_SRC_DIR)
    update_pipelines = UpdatePipelines(source_event_parsed, deployment_map_file)
    update_pipelines.update_deployment_map()

if __name__ == '__main__':
    main()
