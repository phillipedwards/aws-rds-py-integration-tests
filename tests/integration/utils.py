from time import sleep
import os
import subprocess

# ensure we wait until our ECS service has been given time to be fully deployed
# tasks can take some time to pull the provided docker image and become available
def wait_for_ecs_service(client, service_name: str, cluster_name: str):
    print("waiting for ecs service to come online...")
    count = 0

    while True:
        sleep(5)
        if count > 20:
            print("reached maximum iterations of 20")
            return

        ecs_services = client.describe_services(
            cluster=cluster_name,
            services=[service_name]
        )
        
        service = ecs_services["services"][0]
        deployments = service["deployments"]

        # order deployments by createdAt date so we can select the latest deployment
        deployments.sort(key=lambda s: s["createdAt"])
        deployment = deployments[0]

        if deployment["failedTasks"] > 0:
            print("failed ecs tasks encoutered")
            return

        deployment_status = deployment["rolloutState"]
        pending_count = deployment["pendingCount"]
        if deployment_status == "COMPLETED" and pending_count == 0:
            print("ecs tasks fully online...")
            return

        if deployment_status == "IN_PROGRES" or pending_count > 0:
            print("ecs tasks pending...")
            continue
        
        count = count + 1


def bootstrap_environment(work_dir: str):
    print("preping virtual env...")

    subprocess.run([
        "python",
        "-m",
        "venv",
        "venv"
    ], check=True,cwd=work_dir,capture_output=True)

    py_path = os.path.join("venv", "bin", "python3")
    subprocess.run([
        py_path,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip"
    ], check=True,cwd=work_dir,capture_output=True)

    py_path = os.path.join("venv", "bin", "pip")
    subprocess.run([
        py_path,
        "install",
        "-r",
        "requirements.txt"
    ], check=True,cwd=work_dir,capture_output=True)

    print("virutal env created")