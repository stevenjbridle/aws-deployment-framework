# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
The Org Event handler that is called by SNS in US-EAST-1 for Org Events (move) to trigger StepFunctions
"""
import json
import boto3
import os
client = boto3.client('stepfunctions')

def lambda_handler(event, context):
    # TODO implement
    print (event['Records'][0]['Sns']['Message'])
    stateMachine = os.environ['StepFunctionName']
    response = client.start_execution(
        stateMachineArn=stateMachine,
        input=event['Records'][0]['Sns']['Message']
        )
    print (response)
    return {
        'statusCode': 200
    }

