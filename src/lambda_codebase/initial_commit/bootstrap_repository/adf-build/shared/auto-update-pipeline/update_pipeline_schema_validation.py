# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Schema Validation for Update Pipeline Automation
"""

from schema import Schema, And, Use, Or, Optional, Regex

'''
Schema:

update:
    pipeline: str
    targets: [update_target]

update_target:
    path: str
    cfns: [cfn_definition]

cfn_definition:
    stack_name: str
    template_filename: str
    role: str
'''

CFN_SCHEMA = {
    "stack_name": And(str, len),
    "template_filename": And(str, len),
    Optional('role'): str
}
PROPERTIES_SCHEMA = {
    "properties": CFN_SCHEMA
}
TARGET_SCHEMA = {
    "path": And(str, len),
    "cfns": [PROPERTIES_SCHEMA]
}
UPDATE_SCHEMA = {
    "pipeline": And(str, len),
    "targets": [TARGET_SCHEMA]
}
TOP_LEVEL_SCHEMA = {
    "updates": [UPDATE_SCHEMA]
}

class UpdateSchemaValidation:
    def __init__(self, map_input: dict):
        self.validated = Schema(TOP_LEVEL_SCHEMA).validate(map_input)
