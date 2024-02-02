import argparse
import json
import subprocess
import sys

"""
定义全局环境变量
"""
DRY_RUN = False


def run_command_exit_if_err(command):
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


def run_command(command):
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.decode('utf-8'), result.stderr.decode('utf-8'), result.returncode


# 自定义函数用于解析布尔类型
def str_to_bool(value):
    if value.lower() in {'true', 'yes', '1'}:
        return True
    elif value.lower() in {'false', 'no', '0'}:
        return False
    else:
        raise argparse.ArgumentTypeError("Invalid boolean value: Use 'true' or 'false'.")


def get_all_namespaces():
    cmd = "kubectl get namespaces --output=jsonpath='{.items[*].metadata.name}'"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        return stdout.strip().split()
    else:
        print(f"Error getting namespaces. Error: {stderr}")
        raise Exception(f"Error getting namespaces. Error: {stderr}")
        sys.exit(1)


def get_all_deployments(namespace="default"):
    command = f"kubectl get deployments --namespace={namespace} -o=jsonpath={{.items[*].metadata.name}}"
    stdout = run_command_exit_if_err(command)

    deployments = stdout.split()
    return deployments


def get_all_statefulsets(namespace="default"):
    command = f"kubectl get statefulset --namespace={namespace} -o json"
    stdout = run_command_exit_if_err(command)
    statefulsets = json.loads(stdout)["items"]
    return statefulsets


def trigger_rolling_restart_deployment(deployment, namespace="default"):
    command = f"kubectl rollout restart deployment {deployment} --namespace={namespace}"
    if DRY_RUN is True:
        print(f"Info: --dry-run Rolling restart deployment {deployment} in namespace:{namespace} success")
    else:
        run_command_exit_if_err(command)
        print(f"Info: Rolling restart deployment {deployment} in namespace:{namespace} success")


def trigger_rolling_restart_statefulset(statefulset_name, namespace="default"):
    command = f"kubectl rollout restart statefulset {statefulset_name} --namespace={namespace}"
    if DRY_RUN is True:
        print(f"Info: --dry-run Rolling restart statefulset {statefulset_name} in namespace:{namespace} success")
    else:
        run_command_exit_if_err(command)
        print(f"Info: Rolling restart statefulset {statefulset_name} in namespace:{namespace} success")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A script with command line arguments.')
    parser.add_argument('--dry-run', action='store_true', help='simulate an migrate')

    args = parser.parse_args()

    # 是否dry-run
    if args.dry_run is not None:
        DRY_RUN = args.dry_run

    # StatefulSet namespace前缀白名单
    sts_ns_prefix_whitelist = ["mysql", "pg-", "tpaas-mongodb", "mongo-", "ck-", "tpaas-es", "tpaas-kafka", "digger-kafka", "kafka-", "redis", "tpaas-etcd", "hips-etcd", "tpaas-zk", "zk-"]
    # 遍历处理所有namespace
    all_namespaces = get_all_namespaces()
    statefulsets_without_pvc = []
    statefulsets_with_pvc = []

    for namespace in all_namespaces:
        print(f"\nInfo: Processing namespace: {namespace}")
        """
        处理deployment相关逻辑
        """
        try:
            # 获取所有的 Deployments
            deployments = get_all_deployments(namespace)

            # 触发重新调度
            for deployment in deployments:
                trigger_rolling_restart_deployment(deployment, namespace)

            print("Rolling restart triggered for all Deployments in namespace:", namespace)
        except Exception as e:
            print(f"Error: {e}")

        """
        处理StatefulSet相关逻辑
        """
        try:
            statefulsets = get_all_statefulsets(namespace)
            for statefulset in statefulsets:
                pvc_list = statefulset.get("spec", {}).get("volumeClaimTemplates", [])
                if not pvc_list:
                    # 没有 PVC 的 StatefulSet
                    statefulsets_without_pvc.append((namespace, statefulset["metadata"]["name"]))
                    trigger_rolling_restart_statefulset(statefulset["metadata"]["name"], namespace)
                else:
                    # 有 PVC 的 StatefulSet
                    statefulsets_with_pvc.append((namespace, statefulset["metadata"]["name"]))
            print("Rolling restart triggered for all Deployments in namespace:", namespace)
        except Exception as e:
            print(f"Error: {e}")

    """
    打印含pvc的StatefulSet，需人工接入处理
    """
    print("\n以下StatefulSet含pvc，请人工介入迁移:")
    # 遍历具有 PVC 的 StatefulSet 列表
    for namespace, statefulset_name in statefulsets_with_pvc:
        # 检查命名空间是否不在白名单中
        if not any(namespace.startswith(namespace_prefix) for namespace_prefix in sts_ns_prefix_whitelist):
            # 如果命名空间不在白名单中，打印相关信息
            print(f"namespace: {namespace}, statefulset name: {statefulset_name}")
