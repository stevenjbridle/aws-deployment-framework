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
import glob

from schema import Schema
from update_pipeline_schema_validation import UpdateSchemaValidation

CODEBUILD_SRC_DIR = os.environ["CODEBUILD_SRC_DIR"]
ADF_PROJECT_NAME = os.environ["ADF_PROJECT_NAME"]

def main():
    
    '''
    updates:
        - pipeline: sample-server-deploy
            targets:  # Deployment stages
            - path: '<accountNumber>'
                cfns:
                - properties:
                    stack_name: PREFIX-10-CFN-test
                    template_filename: PREFIX-10-CFN-test.yml
                    role: cloudteam-cloudformation-role-1
                - properties:
                    stack_name: PREFIX-20-CFN-test
                    template_filename: PREFIX-20-CFN-test.yml
                - properties:
                    stack_name: PREFIX-05-CFN-test
                    template_filename: PREFIX-05-CFN-test.yml
                    role: cloudteam-cloudformation-role-2
    '''
    path = CODEBUILD_SRC_DIR
    print(glob.glob('{0}/*.yml'.format(CODEBUILD_SRC_DIR)))
    print(ADF_PROJECT_NAME)
    print(os.getcwd())
    original_path = os.getcwd()
    os.chdir(path)
    pipeline_name = ADF_PROJECT_NAME
    print(os.path.dirname(os.getcwd()))
    # walk file system and generate event
    result = {"updates": [{"pipeline": pipeline_name, "targets": []}]}
    targets = result["updates"][0]["targets"]

    for file in glob.glob('*.yml'):
        print(file)

        if file not in 'buildspec.yml':
            # get the first section
            # account_name|ou # stack_name #
            # absweb_735055453237_PREFIX-03-CFN-test
            
            name_pieces = file[:-4].split('_')
            account_name = name_pieces[0]
            target_path = name_pieces[1]

            cfn_name_suffix = name_pieces[2]
            cfn_name = "adf-{0}-{1}".format(account_name, cfn_name_suffix)

            props = {
                "properties": {
                    "stack_name": cfn_name, 
                    "template_filename": file
                }
            }

            found = False
            for t in targets:
                if target_path == t.get('path'):
                    # add
                    t.get('cfns').append(props)
                    found = True
            if not found:
                new_entry = {
                    "path": target_path,
                    "cfns": [props]
                }
                targets.append(new_entry)

    events = boto3.client('events')

    detail = json.dumps(UpdateSchemaValidation(result).validated)
    event_entry = [
            {
                "Source": "adf-created-pipeline",
                "DetailType": "update-pipeline-definition",
                "Detail": detail
            }
        ]
    print(f'Sending event {json.dumps(event_entry, indent=4)}')
    response = events.put_events(
        Entries=event_entry
    )

if __name__ == '__main__':
    main()
