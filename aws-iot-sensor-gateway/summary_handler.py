import boto3
import json
import logging
import os
import io
from botocore.exceptions import ClientError


SENDER = os.getenv('alert_email_sender')
RECIPIENT = os.getenv('alert_email_recipient')
SUBJECT = os.getenv('alert_email_subject', "Moisture Sensor Alert Summary")
EMAIL_TEMPLATE_MAIN = os.getenv('email_template_main', "summary_email_template_main.html")
EMAIL_TEMPLATE_HEADING = os.getenv('email_template_main', "summary_email_template_heading.html")
EMAIL_TEMPLATE_LINE = os.getenv('email_template_main', "summary_email_template_line.html")
CHARSET = 'utf-8'
DEBUG = os.getenv('debug', True)

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO if not DEBUG else logging.DEBUG)

cw = boto3.client('cloudwatch')
client = boto3.client('ses')

def parse_event(event):
    for record in event.get("Records", []):
        sns_message = record.get("Sns", {})
        sns_data = sns_message.get("Message")
        if sns_data:
            yield json.loads(sns_data)


def run(event, context):

    logger.debug(f"{json.dumps(event)}")


    alarms = cw.describe_alarms(
        AlarmNamePrefix='Moisture Sensor',
        StateValue='ALARM'
    )
    nodata = cw.describe_alarms(
        AlarmNamePrefix='Moisture Sensor',
        StateValue='INSUFFICIENT_DATA'
    )

    logger.debug(f"{alarms}")

    with open(EMAIL_TEMPLATE_MAIN, 'r', encoding='utf-8') as f:
        main_template = f.read()
    with open(EMAIL_TEMPLATE_HEADING, 'r', encoding='utf-8') as f:
        heading_template = f.read()
    with open(EMAIL_TEMPLATE_LINE, 'r', encoding='utf-8') as f:
        line_template = f.read()

    all_lines = []

    if len(alarms["MetricAlarms"]):
        all_lines.append(heading_template.replace("{{heading_text}}", "Alarms in ALERT"))
        for line in alarms["MetricAlarms"]:
            all_lines.append(line_template.replace("{{alert_name}}", line["AlarmName"]))

    if len(nodata["MetricAlarms"]):
        all_lines.append(heading_template.replace("{{heading_text}}", "Insufficient Data"))
        for line in nodata["MetricAlarms"]:
            all_lines.append(line_template.replace("{{alert_name}}", line["AlarmName"]))
        

    # if there is nothing to report, then skip
    if len(all_lines) == 0:
        return

    email_body = main_template.replace("{{alert_content}}", "\n".join(all_lines))


    subject = SUBJECT


    mail_response = client.send_email(
    Destination={
        'ToAddresses': [
            RECIPIENT,
        ],
    },
    Message={
        'Body': {
            'Html': {
                'Charset': CHARSET,
                'Data': email_body,
            },
        },
        'Subject': {
            'Charset': CHARSET,
            'Data': subject,
        },
    },
    Source=SENDER,
    )

    logger.debug(mail_response)
    # return response