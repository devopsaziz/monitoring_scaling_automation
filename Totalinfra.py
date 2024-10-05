import boto3

# Initialize boto3 clients
ec2_client = boto3.client('ec2')
elbv2_client = boto3.client('elbv2')
autoscaling_client = boto3.client('autoscaling')
sns_client = boto3.client('sns')
iam_client = boto3.client('iam')

def create_security_group(vpc_id):
    response = ec2_client.create_security_group(
        Description='Allow HTTP and HTTPS traffic',
        GroupName='app-sg-1',
        VpcId=vpc_id
    )
    sg_id = response['GroupId']

    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 443,
                'ToPort': 443,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )

    return sg_id

def create_load_balancer(subnets, security_groups):
    response = elbv2_client.create_load_balancer(
        Name='app-alb',
        Subnets=subnets,
        SecurityGroups=security_groups,
        Scheme='internet-facing',
        Tags=[
            {'Key': 'Name', 'Value': 'app-alb'}
        ]
    )
    return response['LoadBalancers'][0]['LoadBalancerArn']

def create_target_group(vpc_id):
    response = elbv2_client.create_target_group(
        Name='app-target-group',
        Protocol='HTTP',
        Port=80,
        VpcId=vpc_id,
        HealthCheckProtocol='HTTP',
        HealthCheckPort='80',
        HealthCheckPath='/',
        HealthCheckIntervalSeconds=30,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        TargetType='instance'
    )
    return response['TargetGroups'][0]['TargetGroupArn']

def create_listener(load_balancer_arn, target_group_arn):
    response = elbv2_client.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol='HTTP',
        Port=80,
        DefaultActions=[
            {
                'Type': 'forward',
                'TargetGroupArn': target_group_arn
            }
        ]
    )
    return response['Listeners'][0]['ListenerArn']

def create_launch_template(image_id, instance_type, sg_id):
    response = ec2_client.create_launch_template(
        LaunchTemplateName='app-Template',
        LaunchTemplateData={
            'ImageId': image_id,
            'InstanceType': instance_type,
            'SecurityGroupIds': [sg_id],
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'app-ec2'}
                    ]
                }
            ]
        }
    )
    return response['LaunchTemplate']['LaunchTemplateId']

def create_auto_scaling_group(launch_template_id, subnets):
    response = autoscaling_client.create_auto_scaling_group(
        AutoScalingGroupName='app-asg-1',
        LaunchTemplate={'LaunchTemplateId': launch_template_id},
        MinSize=1,
        MaxSize=5,
        DesiredCapacity=1,
        VPCZoneIdentifier=','.join(subnets),
        Tags=[
            {
                'ResourceId': 'app-asg-1',
                'ResourceType': 'auto-scaling-group',
                'Key': 'Name',
                'Value': 'app-asg-1',
                'PropagateAtLaunch': True
            }
        ]
    )
    return response

def create_scaling_policy(auto_scaling_group_name):
    autoscaling_client.put_scaling_policy(
        AutoScalingGroupName=auto_scaling_group_name,
        PolicyName='cpu-utilization-policy',
        PolicyType='TargetTrackingScaling',
        TargetTrackingConfiguration={
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'ASGAverageCPUUtilization'
            },
            'TargetValue': 50.0
        }
    )

def create_sns_topic(topic_name):
    response = sns_client.create_topic(
        Name=topic_name
    )
    return response['TopicArn']

def create_sns_subscription(topic_arn, protocol, endpoint):
    sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol=protocol,
        Endpoint=endpoint
    )

def create_infrastructure(image_id, instance_type, vpc_id, subnets, email):
    sg_id = create_security_group(vpc_id)
    load_balancer_arn = create_load_balancer(subnets, [sg_id])
    target_group_arn = create_target_group(vpc_id)
    create_listener(load_balancer_arn, target_group_arn)
    
    launch_template_id = create_launch_template(image_id, instance_type, sg_id)
    create_auto_scaling_group(launch_template_id, subnets)
    create_scaling_policy('app-asg-1')
    
    topic_arn = create_sns_topic('scaling-events')
    create_sns_subscription(topic_arn, 'email', email)
    print("Infrastructure created successfully.")

# Replace the placeholders with your values
image_id = 'ami-01312848387ace2b4'
instance_type = 't2.micro'
vpc_id = 'vpc-0f22c13329dc40837'
subnets = ['subnet-0dc085f68a4254e66', 'subnet-05c5c244dc8e4409a']
email = 'ajfaraziz@gmail.com'

create_infrastructure(image_id, instance_type, vpc_id, subnets, email)
