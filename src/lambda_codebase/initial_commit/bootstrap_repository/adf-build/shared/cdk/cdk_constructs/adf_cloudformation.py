# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Construct related to CloudFormation Input
"""

import os
from aws_cdk import (
    core
)

from cdk_constructs import adf_codepipeline
from logger import configure_logger

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEFAULT_BUILD_TIMEOUT = 20
LOGGER = configure_logger(__name__)


class CloudFormation(core.Construct):
    def __init__(self, scope: core.Construct, id: str, **kwargs): #pylint: disable=W0622, W0235
        super().__init__(scope, id, **kwargs)

    @staticmethod
    def generate_actions(targets, region, map_params, target_approval_mode, override_run_order: None):
        _actions = []
        if not isinstance(targets, list):
            targets = [targets]
        
        if not override_run_order:
            override_run_order = 1

        for target in targets:
            LOGGER.info(f'target {target["name"]}')
            name = "{0}-{1}-{2}-create".format(target['name'], region, target.get('properties',{}).get('stack_name', override_run_order))
            _actions.append(
                adf_codepipeline.Action(
                    name=name,
                    provider="CloudFormation",
                    category="Deploy",
                    region=region,
                    target=target,
                    run_order=override_run_order, #1,
                    action_mode="CHANGE_SET_REPLACE",
                    map_params=map_params,
                    action_name=name
                ).config,
            )
            if target_approval_mode:
                override_run_order += 1
                name="{0}-{1}-{2}".format(target['name'], region, target.get('properties',{}).get('stack_name', override_run_order))
                _actions.append(
                    adf_codepipeline.Action(
                        name=name,
                        provider="Manual",
                        category="Approval",
                        region=region,
                        target=target,
                        run_order=override_run_order, #2,
                        map_params=map_params,
                        action_name=name
                    ).config
                )
            name="{0}-{1}-{2}-execute".format(target['name'], region, target.get('properties',{}).get('stack_name', override_run_order))
            override_run_order += 1
            _actions.append(
                adf_codepipeline.Action(
                    name=name,
                    provider="CloudFormation",
                    category="Deploy",
                    region=region,
                    target=target,
                    run_order=override_run_order,
                    #run_order=3 if target.get('properties', {}).get('change_set_approval') else 2,
                    action_mode="CHANGE_SET_EXECUTE",
                    map_params=map_params,
                    action_name=name
                ).config
            )
        return _actions
