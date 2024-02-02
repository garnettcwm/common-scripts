import argparse
import os
import subprocess
import json
import sys


"""
定义全局环境变量
"""
DRY_RUN = False


def run_command(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,  # 如果命令执行失败，则引发 CalledProcessError 异常
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8"
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        sys.exit(1)


def backup_topology_constraints(namespace, resource_type):
    # 创建备份目录
    backup_dir = "topologySpreadConstraint_backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # 查询带有 topologySpreadConstraints 的资源的名称
    command = f"kubectl get {resource_type} --namespace={namespace} -o json"
    resource_json = run_command(command)
    resources = json.loads(resource_json)["items"]

    for resource in resources:
        if resource["spec"].get("template", {}).get("spec", {}).get("topologySpreadConstraints"):
            # 备份 YAML 文件
            filename = f"{backup_dir}/{namespace}_{resource_type.lower()}_{resource['metadata']['name']}.yaml"
            run_command(f"kubectl get {resource_type} --namespace={namespace} {resource['metadata']['name']} -o yaml > {filename}")
            print(f"Backup created for {namespace} {resource_type} - {resource['metadata']['name']}")


def remove_topology_constraints(namespace, resource_type):
    # 查询带有 topologySpreadConstraints 的资源的名称
    command = f"kubectl get {resource_type} --namespace={namespace} -o json"
    resource_json = run_command(command)
    resources = json.loads(resource_json)["items"]

    for resource in resources:
        if resource["spec"].get("template", {}).get("spec", {}).get("topologySpreadConstraints"):
            # 删除 topologySpreadConstraints
            if DRY_RUN is True:
                print(f"--dry-run Removed topologySpreadConstraints for {resource_type} - {resource['metadata']['name']}")
            else:
                run_command(f"kubectl patch {resource_type} --namespace={namespace} {resource['metadata']['name']} --type=json -p="
                            f"'[{{\"op\":\"remove\", \"path\":\"/spec/template/spec/topologySpreadConstraints\"}}]'")
                print(f"Removed topologySpreadConstraints for {resource_type} - {resource['metadata']['name']}")


def backup_and_remove_topology_constraints(namespace, resource_type):
    # 创建备份目录
    backup_dir = "topologySpreadConstraint_backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # 查询带有 topologySpreadConstraints 的资源的名称
    command = f"kubectl get {resource_type} --namespace={namespace} -o json"
    resource_json = run_command(command)
    resources = json.loads(resource_json)["items"]

    for resource in resources:
        if resource["spec"].get("template", {}).get("spec", {}).get("topologySpreadConstraints"):
            # 备份 YAML 文件
            filename = f"{backup_dir}/{namespace}_{resource_type.lower()}_{resource['metadata']['name']}.yaml"
            run_command(f"kubectl get {resource_type} --namespace={namespace} {resource['metadata']['name']} -o yaml > {filename}")
            print(f"Backup created for {namespace} {resource_type} - {resource['metadata']['name']}")

            # 删除 topologySpreadConstraints
            if DRY_RUN is True:
                print(f"--dry-run Removed topologySpreadConstraints for {resource_type} - {resource['metadata']['name']}")
            else:
                run_command(f"kubectl patch {resource_type} --namespace={namespace} {resource['metadata']['name']} --type=json -p="
                            f"'[{{\"op\":\"remove\", \"path\":\"/spec/template/spec/topologySpreadConstraints\"}}]'")
                print(f"Removed topologySpreadConstraints for {resource_type} - {resource['metadata']['name']}")


def get_all_namespaces():
    cmd = "kubectl get namespaces --output=jsonpath='{.items[*].metadata.name}'"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        return stdout.strip().split()
    else:
        print(f"Error getting namespaces")
        print(f"Error output: {stderr}")
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A script with command line arguments.')
    parser.add_argument('--dry-run', action='store_true', help='simulate an migrate')
    args = parser.parse_args()

    # 是否dry-run
    if args.dry_run is not None:
        DRY_RUN = args.dry_run

    if DRY_RUN:
        print(f"{DRY_RUN} 1")
    else:
        print(f"{DRY_RUN} 2")

    ns_prefix_whitelist = ["mysql", "pg-", "tpaas-mongodb", "mongo-", "ck-", "tpaas-es", "tpaas-kafka", "digger-kafka", "kafka-", "redis", "tpaas-etcd", "hips-etcd", "tpaas-zk", "zk-"]
    whitelist = [("excluded_namespace1", "excluded_workload1"), ("excluded_namespace2", "excluded_workload2")]
    all_namespaces = get_all_namespaces()

    for namespace in all_namespaces:
        # 检查命名空间是否不在白名单中
        if any(namespace.startswith(namespace_prefix) for namespace_prefix in ns_prefix_whitelist):
            print(f"Skipping {namespace} due to whitelist.")
            continue

        print(f"\nProcessing namespace: {namespace}")

        # 备份和删除 Deployment
        backup_and_remove_topology_constraints(namespace, "Deployment")

        # 备份和删除 StatefulSet
        backup_and_remove_topology_constraints(namespace, "StatefulSet")
