# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Main
"""

#!/usr/bin/env python3

import os
from concurrent.futures import ThreadPoolExecutor
import boto3
from src import read_config_files, delete_default_vpc
from organizations import Organizations
from logger import configure_logger
from parameter_store import ParameterStore
from sts import STS
import json


LOGGER = configure_logger(__name__)
ACCOUNTS_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'adf-accounts'))

def main():
    accounts = read_config_files(ACCOUNTS_FOLDER)
    if not bool(accounts):
        LOGGER.info(f"Found {len(accounts)} account(s) in configuration file(s). Account provisioning will not continue.")
        return
    LOGGER.info(f"Found {len(accounts)} account(s) in configuration file(s).")
    organizations = Organizations(boto3)
    all_accounts = organizations.get_accounts()
    parameter_store = ParameterStore(os.environ.get('AWS_REGION', 'ap-southeast-2'), boto3)
    adf_role_name = parameter_store.fetch_parameter('cross_account_access_role')
    modified_accounts = []
    for account in accounts:
        try:
            account_id = next(acc["Id"] for acc in all_accounts if acc["Name"] == account.full_name)
        except StopIteration: # If the account does not exist yet..
            account_id = None
    
        account_id, modified = create_or_update_account(organizations, account, adf_role_name, account_id)
        if modified:
            modified_accounts.append(account_id)
    
    if modified_accounts:
        send_accounts_modified_event(modified_accounts)

def create_or_update_account(org_session, account, adf_role_name, account_id=None):
    """Creates or updates a single AWS account.
    :param org_session: Instance of Organization class
    :param account: Instance of Account class
    """
    if not account_id:
        LOGGER.info(f'Creating new account {account.full_name}')
        account.full_name = str(account.full_name)
        account_id = org_session.create_account(account, adf_role_name)
    sts = STS()
    role = sts.assume_cross_account_role(
        'arn:aws:iam::{0}:role/{1}'.format(
            account_id,
            adf_role_name
        ), 'delete_default_vpc'
    )

    LOGGER.info(f'Ensuring account {account_id} (alias {account.alias}) is in OU {account.ou_path}')
    org_session.move_account(account_id, account.ou_path)
    if account.delete_default_vpc:
        ec2_client = role.client('ec2')
        all_regions = [
            region['RegionName']
            for region in ec2_client.describe_regions(
                AllRegions=False,
                Filters=[
                    {
                        'Name': 'opt-in-status',
                        'Values': [
                            'opt-in-not-required',
                        ]
                    }
                ]
            )['Regions']
        ]
        args = (
            (account_id, region, role)
            for region in all_regions
        )
        with ThreadPoolExecutor(max_workers=10) as executor:
            for _ in executor.map(lambda f: schedule_delete_default_vpc(*f), args):
                pass

    if account.alias:
        LOGGER.info(f'Ensuring account alias for {account_id} of {account.alias}')
        org_session.create_account_alias(account.alias, role)

    if account.tags:
        LOGGER.info(f'Ensuring tags exist for account {account_id}: {account.tags}')
        org_session.create_account_tags(account_id, account.tags)
    
    account_parameter_modified = []
    if account.parameters:
        LOGGER.info(f'Ensuring parameters exist in account {account_id}: {account.parameters}')
        parameter_store_target_account = ParameterStore(os.environ.get('AWS_REGION', 'ap-southeast-2'), role)
        for param in account.parameters:
            for key, value in param.items():
               account_parameter_modified.append(parameter_store_target_account.put_parameter('/account/' + key, value))
    
    return account_id, any(account_parameter_modified)

def send_accounts_modified_event(accounts):
    events = boto3.client('events')

    detail = json.dumps({"accounts": accounts})
    event_entry = [
            {
                "Source": "adf-accounts-updated",
                "DetailType": "account-parameters-changed",
                "Detail": detail
            }
        ]
    LOGGER.info(f'Sending event {json.dumps(event_entry, indent=4)}')
    response = events.put_events(
        Entries=event_entry
    )
    LOGGER.info(response)

def schedule_delete_default_vpc(account_id, region, role):
    """Schedule a delete_default_vpc on a thread
    :param account_id: The account ID to remove the VPC from
    :param org_session: The Organization class instance
    :param region: The name of the region the VPC is resided
    """
    ec2_client = role.client('ec2', region_name=region)
    delete_default_vpc(ec2_client, account_id, region, role)

if __name__ == '__main__':
    main()
