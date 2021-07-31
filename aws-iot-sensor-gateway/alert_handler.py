import boto3
import json
import logging
import os
from botocore.exceptions import ClientError


SENDER = os.getenv('alert_email_sender')
RECIPIENT = os.getenv('alert_email_recipient')
SUBJECT = os.getenv('alert_email_subject')
CHARSET = 'utf-8'
DEBUG = os.getenv('debug', True)

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO if not DEBUG else logging.DEBUG)

client = boto3.client('ses')

def parse_event(event):
    for record in event.get("Records", []):
        sns_message = record.get("Sns", {})
        sns_data = sns_message.get("Message")
        if sns_data:
            yield json.loads(sns_data)


def run(event, context):

    logger.debug(f"{json.dumps(event)}")

    for alert in parse_event(event):

        subject = alert.get("AlarmName", SUBJECT)
        new_state = alert.get("NewStateValue")
        old_state = alert.get("OldStateValue")
        message = alert.get("NewStateReason")

        response = client.send_email(
        Destination={
            'ToAddresses': [
                RECIPIENT,
            ],
        },
        Message={
            'Body': {
                # 'Html': {
                #     'Charset': CHARSET,
                #     'Data': alert,
                # },
                'Text': {
                    'Charset': CHARSET,
                    'Data': message,
                },
            },
            'Subject': {
                'Charset': CHARSET,
                'Data': f'{subject} - [{new_state}]',
            },
        },
        Source=SENDER,
        )

        logger.debug(response)
        # return response