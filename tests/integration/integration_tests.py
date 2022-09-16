from typing import List
import requests

class TestFailure:
    def __init__(self, property, error):
        self.property = property
        self.error = error

def validate_web_service(url: str) -> TestFailure:
    # we expect our webpage to return a HTTP 200 status code. any other code is viewed as a failure
    response = requests.get(url)
    if response.status_code != 200:
        return TestFailure("Web Service URL", f"received unexpected status code from Web Service :: expected status_code 200, received {response.status_code}")

    return None

def validate_ecs_service(client, service_name: str, cluster_name: str) -> List[TestFailure]:
    test_failures = []

    # retrieve the ECS service just deployed
    ecs_services = client.describe_services(
        cluster=cluster_name,
        services=[service_name]
    )

    service = ecs_services["services"][0]

    # ensure desired count and running count are the same
    desired_count = service["desiredCount"]
    running_count = service["runningCount"]
    if desired_count != running_count:
        test_failures.append(TestFailure("RunningCount", f"expected {desired_count}, actual {running_count}. DesiredCount must equal RunningCount"))

    # we expect to have only a single load balancer that is forwarding traffic to our tasks on port 80
    load_balancers = service["loadBalancers"]
    if len(load_balancers) > 1 or len(load_balancers) < 1:
        test_failures.append(TestFailure("LoadBalancer", f"expected 1 load balancer, actual {len(load_balancers)}"))
    else:
        load_balancer = load_balancers[0]
        container_port = load_balancer["containerPort"]
        if (container_port != 80):
            test_failures.append("ContainerPort", f"containerPort:: expected 80, actual {container_port}")

    network_config = service["networkConfiguration"]
    vpc_config = network_config["awsvpcConfiguration"]

    # NOTE: the 2nd test case has been setup to fail. Current configuration has this value being set to ENALBED (true) on the ECS Service
    # Current VPC architecture of the deployed app will not support ECS Tasks in a private subnet, meaning Tasks will fail to deploy if they are not assigned a public ip; no internet gateway is present.
    assign_public_ip = vpc_config["assignPublicIp"]
    if assign_public_ip != "ENABLED":
        test_failures.append(TestFailure("AssignPublicIp", f"expected AssignPublicIp to be enabled, actual value is {assign_public_ip}"))

    # UNCOMMENT THIS TEST CASE TO SEE A FAILURE
    # if assign_public_ip == "ENABLED":
    #     test_failures.append(TestFailure("AssignPublicIp", "expected AssignPublicIp to be disabled, actual value is enabled"))

    return test_failures