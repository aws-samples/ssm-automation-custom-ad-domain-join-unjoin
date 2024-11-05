import boto3
import os
import re

def lambda_handler(event, context):
    region = os.environ.get('AWS_REGION')
    resources = event['resources']
    instance_id = resources[0]
    instance_id_match = re.search('i-[a-f0-9]{8}(?:[a-f0-9]{9})?$',instance_id)
    instance_id = instance_id_match.group(0)
    automation_runbook_arn = 'arn:aws:ssm:AWSRegion:AWSAccountId:automation-definition/SSMAutomationRunbookName'
    ec2_client = boto3.client('ec2',region)
    ssm_client = boto3.client('ssm',region)
    instance_state_code = ec2_client.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['State']['Code']
    tags_output = ec2_client.describe_tags(Filters=[{'Name': 'resource-id','Values': [instance_id]}])['Tags']

    for tag_output in tags_output:
        tag_output_key = tag_output['Key']
        tag_output_value = tag_output['Value']
        if tag_output_key == "StartEvent":
            if tag_output_value == "Join" or tag_output_value == "Unjoin":
                if instance_state_code == 80:
                    ec2_client.start_instances(InstanceIds=[instance_id])
                instance_status = ec2_client.describe_instance_status(InstanceIds=[instance_id,],)['InstanceStatuses'][0]['InstanceStatus']['Details'][0]['Status']
                while instance_status != 'passed':
                    waiter_running = ec2_client.get_waiter('instance_running')
                    waiter_status_ok = ec2_client.get_waiter('instance_status_ok')
                    waiter_running.wait(InstanceIds=[instance_id])
                    waiter_status_ok.wait(InstanceIds=[instance_id])
                ssm_response = ssm_client.start_automation_execution(DocumentName=automation_runbook_arn,DocumentVersion="$DEFAULT",Parameters={"InstanceId":[instance_id],"DomainJoinActivity":[tag_output_value]})
                print(ssm_response)
                break
            else:
                print("The tag value for " + tag_output_key + " is not valid to perform the domain join/unjoin automation. Value must be Join or Unjoin.")
            break
