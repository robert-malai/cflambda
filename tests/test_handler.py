from textwrap import dedent
from unittest import TestCase

from botocore.stub import Stubber, ANY

from main import sqs, handler
from trigger import dynamodb


class TestMainHandler(TestCase):
    max_items = 5
    event = {
        "time": "2019-05-02T12:00:00Z",
        'name': 'Test Report',
        'params': {
            'MaxItems': max_items,
        },
    }
    trigger_query = dedent("""
        SELECT TOP %(MaxItems)s
            usr.UserId,
            usr.FirstName,
            usr.LastName,
            usr.EmailAddress,
            StartDate = DATEADD(month, DATEDIFF(month, 0, %(TriggeredAt)s), 0),
            EndDate = %(TriggeredAt)s
        FROM Users usr
            JOIN UserOrgProfile UOP on usr.UserId = UOP.UserID
            JOIN BusinessRole BR on UOP.BusinessRoleID = BR.BusinessRoleID
        WHERE usr.isActive = 1
            AND UOP.OrgID = 19
            AND BR.BusinessRoleType = 8
    """)
    report_query = dedent("""
        SELECT 
            F.FormName,
            VisitsMade = COUNT(*)
        FROM FormVisit fv
            JOIN Forms F on fv.FormId = F.FormId
        WHERE F.OrgId = 19
            AND fv.UserId = %(UserId)s
            AND fv.CreatedOn BETWEEN %(StartDate)s AND %(EndDate)s
        GROUP BY F.FormName
    """)
    report_template = dedent("""
        {% set Envelope = {'To': 'rmalai@mobileinsight.com',
                           'Subject': 'Test Report'} -%}
        For the month {{ StartDate.strftime('%Y, %M') }}, you have made the following visits:
        {% for stats in Data -%}
        {{ stats.FormName }} - {{ stats.VisitsMade }}
        {% endfor -%}
    """)
    dynamo_response = {
        'Item': {
            'ReportName': {'S': 'Test Report'},
            'Definition': {'M': {
                'DataSource': {'S': '/mi/database/staging'},
                'TriggerQuery': {'S': trigger_query},
                'ReportQuery': {'S': report_query},
                'ReportTemplate': {'S': report_template},
            }},
        }
    }

    def setUp(self) -> None:
        import trigger
        trigger.reports_definition_table = dynamodb.Table('DUMMY')

        self._dynamodb = Stubber(dynamodb.meta.client)
        self._dynamodb.add_response('get_item', self.dynamo_response, {'TableName': ANY, 'Key': ANY})
        self._dynamodb.activate()

        self._sqs = Stubber(sqs)
        for i in range(self.max_items):
            self._sqs.add_response('send_message', {}, {'QueueUrl': ANY, 'MessageBody': ANY})
        self._sqs.activate()

    def test_handler(self):
        handler(self.event, None)

        self._dynamodb.assert_no_pending_responses()
        self._sqs.assert_no_pending_responses()
