from re import S
import sys
from typing import List
import os
import boto3
from botocore.config import Config
from pulumi import automation as auto

from utils import bootstrap_environment, wait_for_ecs_service
from integration_tests import (
    TestFailure,
    validate_ecs_service,
    validate_web_service
)

# command line values are optional
# if command line args are provided, both of stack_name and aws_region; aws_profile is optional
# NOTE: this can be made more robust by using an argument parser library

stack_name = "integration_test"
aws_region = "us-west-2"
aws_profile = ""

args = sys.argv[1:]
if len(args) > 0:
    print("parsing command line config values...")
    stack_name = args[0]
    aws_region = args[1]
    if len(args) > 2:
        aws_profile = args[2]
else:
    print("using default config values...")

work_dir = os.path.join(os.path.dirname(__file__), "../..")

bootstrap_environment(work_dir)

stack = auto.create_or_select_stack(stack_name, work_dir=work_dir)

print(f"setting {stack_name} stack configuration...")

stack.set_config("aws:region", auto.ConfigValue(value=aws_region))
print(f"using AWS region {aws_region}")

if aws_profile != "":
    stack.set_config("aws:profile", auto.ConfigValue(value=aws_profile))
    print(f"using AWS profile {aws_profile}")

print("refreshing the stack...")
stack.refresh(on_output=print)

print("updating the stack...")
up_result = stack.up(on_output=print)

# ================ Integration Tests =============
test_failures: List[TestFailure] = []
ecs_client = None
if aws_profile == "":
    ecs_client = boto3.client("ecs", config=Config(
        region_name=aws_region,
    ))
else:
    session = boto3.Session(profile_name=aws_profile)
    ecs_client = session.client("ecs", config=Config(
        region_name=aws_region,
    ))

cluster_name = up_result.outputs["ECS Cluster Name"].value
service_name = up_result.outputs["ECS Service Name"].value

# wait for fargate tasks to be deployed and LB to be attached
wait_for_ecs_service(ecs_client, service_name, cluster_name)

# expect a 200 response from our web service
web_service_url = up_result.outputs["Web Service URL"].value
web_result = validate_web_service(web_service_url)
if web_result is not None:
    test_failures.append(web_result)

service_result = validate_ecs_service(ecs_client, service_name, cluster_name)
if service_result is not None and len(service_result) > 0:
    test_failures.extend(service_result)

# ==============================================

# add more tests as needed
# ==================================

# These errors could be written back to a PR somewhere if github/gitlab/etc is the 
print("\n###################### Integration Test Results #####################\n")
if len(test_failures) == 0:
    print("application and environment successfully validated")
else:
    print("1 or more integration test failures encounted")
    for fail in test_failures:
        print(f"{fail.property} failed test valdation. Message:: {fail.error}")

print("\n#####################################################################\n")

# only delete resources if all tests succeed
if len(test_failures) == 0:
    # ======= Destroy the stack and resources ==============
    print("automatically destroying the stack due to all tests passing...")
    stack.destroy(on_output=print)
    stack.workspace.remove_stack(stack_name)