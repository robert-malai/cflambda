from unittest import TestCase
from datetime import datetime, date, time
from botocore.stub import Stubber, ANY

from main import ec2, handler


class TestMainHandler(TestCase):
    ec2_list = {
        'Reservations': [
            {
                'Groups': [],
                'Instances': [
                    {
                        'InstanceId': 'id 1',
                        'State': {
                            'Code': 123,
                            'Name': 'running'
                        },
                        'Tags': [
                            {
                                'Key': 'start-stop:enable',
                                'Value': 'True'
                            },
                            {
                                'Key': 'start-stop:start',
                                'Value': '0 6 * * *'
                            },
                            {
                                'Key': 'start-stop:stop',
                                'Value': '0 18 * * *'
                            },
                            {
                                'Key': 'Environment',
                                'Value': 'DEV'
                            },
                        ]
                    },
                    {
                        'InstanceId': 'id 2',
                        'State': {
                            'Code': 123,
                            'Name': 'running'
                        },
                        'Tags': [
                            {
                                'Key': 'start-stop:enable',
                                'Value': 'True'
                            },
                            {
                                'Key': 'start-stop:start',
                                'Value': '0 6 * * *'
                            },
                            {
                                'Key': 'start-stop:stop',
                                'Value': '0 18 * * *'
                            },
                            {
                                'Key': 'Environment',
                                'Value': 'PROD'
                            },
                        ]
                    }
                ],
                'OwnerId': 'SomeId',
                'RequesterId': 'SomeId',
                'ReservationId': 'SomeId'
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
        self._ec2.add_response('stop_instances', {}, {'InstanceIds': ['id 1']})

        event = {'time': datetime.combine(date.today(), time(hour=6, minute=0, second=0, microsecond=0)).isoformat()}

        handler(event, None)

        self._ec2.assert_no_pending_responses()
