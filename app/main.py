"""
Auto start-stop functionality for the account's EC2 containers.

In order to enable the feature on a container, define the following configured tags on it:
  - ENABLE_TAG (start-stop:enable) with a value of 1, True, Yes of Enabled (case insensitive); optional, if missing we
  consider a True value for it.
  - START_TAG (start-stop:start) with a valid cron expression (5 or 6 columns)
  - STOP_TAG (start-stop:stop) with a valid cron expression
"""

import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import boto3
from croniter import croniter, CroniterBadDateError, CroniterBadCronError
from dateutil import tz
from dateutil.parser import parse as parse_datetime

# Script constants
ENABLE_TAG = 'start-stop:enable'
START_TAG = 'start-stop:start'
STOP_TAG = 'start-stop:stop'

# Environment variables
TIMEZONE = tz.gettz(os.getenv('TIMEZONE', 'America/New_York'))

# One time initializations
ec2 = boto3.resource('ec2')


@dataclass(frozen=True)
class StartStopConfig(object):
    """
    Holds start-stop configuration for an EC2 instance.
    """
    prev_start: datetime = None
    prev_stop: datetime = None
    enabled: bool = True

    @staticmethod
    def from_instance_tags(instance, now: datetime) -> Optional['StartStopConfig']:
        enabled, prev_start, prev_stop = True, None, None
        try:
            for tag in instance.tags:
                if tag['Key'] == START_TAG:
                    prev_start = croniter(tag['Value'], now, ret_type=datetime).get_prev()
                if tag['Key'] == STOP_TAG:
                    prev_stop = croniter(tag['Value'], now, ret_type=datetime).get_prev()
                if tag['Key'] == ENABLE_TAG:
                    enabled = tag['Value'].lower() in ['enabled', 'yes', 'true', '1', 'on']
        except (CroniterBadDateError, CroniterBadCronError, TypeError) as e:
            print(f"Bad cron expression: {e}")
            return None
        else:
            if prev_start or prev_stop:
                return StartStopConfig(prev_start=prev_start, prev_stop=prev_stop, enabled=enabled)
            else:
                print("Bad cron expression: you have to provide at least one expression (start or stop)")
                return None


class StartStopAction(Enum):
    START = 'start'
    STOP = 'stop'


def do_start_stop_action(instance, action: StartStopAction = None):
    """
    Logic to perform a simple start ort stop on the designated instance, checking for proper state before performing
    the action.
    """
    if action:
        if action == StartStopAction.START:
            if instance.state['Name'] in ['stopped']:
                print(f"Starting instance {instance.id}")
                instance.start()
        if action == StartStopAction.STOP:
            if instance.state['Name'] in ['running']:
                print(f"Stopping instance {instance.id}")
                instance.stop()


def handler(event, context):
    """
    Will search through all the instances from this account filtered based on the tags START_TAG and STOP_TAG. Will
    extract the parameters out of the instance tags and then will run either in schedule detection mode or in trigger
    detection mode.
    """
    trigger = parse_datetime(event['time']).astimezone(TIMEZONE)
    now = datetime.now(TIMEZONE)

    print(f"Triggered execution at {trigger}")

    for instance in ec2.instances.filter(Filters=[{'Name': f'tag:{START_TAG}', 'Values': ['*']},
                                                  {'Name': f'tag:{STOP_TAG}', 'Values': ['*']}]):

        print(f"Inspecting instance {instance.id}")
        config = StartStopConfig.from_instance_tags(instance, now)
        if config and config.enabled:
            action: Optional[StartStopAction] = None
            if config.prev_start and config.prev_stop:
                print("Operate in schedule mode")
                if config.prev_stop < config.prev_start:
                    # instance should be running
                    action = StartStopAction.START
                else:
                    # instance should be stopped
                    action = StartStopAction.STOP
            else:
                print("Operate in trigger mode")
                if config.prev_start == trigger:
                    # we should start the instance
                    action = StartStopAction.START
                if config.prev_stop == trigger:
                    # we should stop the instance
                    action = StartStopAction.STOP

            do_start_stop_action(instance, action)
