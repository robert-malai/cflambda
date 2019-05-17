from datetime import datetime, date, time, timedelta
from unittest import TestCase

from botocore.stub import Stubber, ANY
from dateutil.tz import tzutc
from freezegun import freeze_time

from main import ec2, handler, TIMEZONE, ENABLE_TAG, START_TAG, STOP_TAG

RUNNING_INSTANCE = {'Code': 123, 'Name': 'running'}
STOPPED_INSTANCE = {'Code': 123, 'Name': 'stopped'}


class TestMainHandler(TestCase):
    ec2_list = {
        'Reservations': [
            {
                'Instances': [
                    {
                        'InstanceId': 'i-0ff1234',
                        'State': STOPPED_INSTANCE,
                        'Tags': [
                            {'Key': ENABLE_TAG, 'Value': 'True'},
                            {'Key': START_TAG, 'Value': '0 6 * * *'},
                            {'Key': STOP_TAG, 'Value': '0 18 * * *'},
                        ]
                    },
                    {
                        'InstanceId': 'i-0ff1235',
                        'State': STOPPED_INSTANCE,
                        'Tags': [
                            {'Key': ENABLE_TAG, 'Value': 'False'},
                            {'Key': START_TAG, 'Value': '0 6 * * *'},
                            {'Key': STOP_TAG, 'Value': '0 18 * * *'},
                        ]
                    },
                    {
                        'InstanceId': 'i-0ff1236',
                        'State': RUNNING_INSTANCE,
                        'Tags': [
                            {'Key': ENABLE_TAG, 'Value': 'True'},
                            {'Key': START_TAG, 'Value': '0 8 * * *'},
                            {'Key': STOP_TAG, 'Value': '0 18 * * *'},
                        ]
                    },
                ],
            }
        ]
    }

    def setUp(self) -> None:
        self._ec2 = Stubber(ec2.meta.client)
        self._ec2.activate()

    def tearDown(self) -> None:
        self._ec2.deactivate()

    def test_handler(self):
        self._ec2.add_response('describe_instances', self.ec2_list, {'Filters': ANY})
        self._ec2.add_response('start_instances', {}, {'InstanceIds': ['i-0ff1234']})
        self._ec2.add_response('stop_instances', {}, {'InstanceIds': ['i-0ff1236']})

        trigger = datetime.combine(date.today(), time(hour=6, tzinfo=TIMEZONE)).astimezone(tzutc())

        with freeze_time(trigger + timedelta(seconds=3)):
            handler({'time': trigger.isoformat()}, None)

        self._ec2.assert_no_pending_responses()
