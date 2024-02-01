import argparse
import subprocess
import os

"""
定义全局环境变量
"""
DRY_RUN = False


def backup_yaml(resource_type, resource_name, namespace):
    # 创建备份目录
    backup_dir = "singleReplica_backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    cmd = f"kubectl get {resource_type} {resource_name} -n {namespace} -o yaml"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        yaml_data = stdout
        backup_filename = f"{backup_dir}/{namespace}_{resource_type}_{resource_name}.yaml"
        with open(backup_filename, 'w') as backup_file:
            backup_file.write(yaml_data)
        print(f"Backup saved to: {backup_filename}")
    else:
        print(f"Error backing up {resource_type} {resource_name} in namespace {namespace}")
        print(f"Error output: {stderr}")


def adjust_replica_count(resource_type, resource_name, namespace, new_replica_count):
    cmd = f"kubectl scale {resource_type} {resource_name} --replicas={new_replica_count} -n {namespace}"
    if not DRY_RUN:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True)
        process.communicate()

        if process.returncode == 0:
            print(f"Successfully adjusted replicas for {resource_type} {resource_name} in namespace {namespace}")
        else:
            print(f"Error adjusting replicas for {resource_type} {resource_name} in namespace {namespace}")
    else:
        print(f"Successfully adjusted replicas for {resource_type} {resource_name} in namespace {namespace}")


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


def main():
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

    resource_types = ["deployment", "statefulset"]
    # StatefulSet namespace前缀白名单
    ns_prefix_whitelist = ["tpaas-rds", "mysql", "pg-", "tpaas-mongodb", "mongo-", "ck-", "tpaas-es", "tpaas-kafka",
                           "digger-kafka", "kafka-", "redis", "tpaas-etcd", "hips-etcd", "tpaas-zk", "zk-",
                           "bastion-ops", "jd-bomp"]
    """
    1、tpaas-operator、tpaas-cluster-proxy目前只能单点
    2、cassandra为sgm提供服务，数量为1、或3
    3、digger k8s-watch、loki-compactor、loki-frontend-leader比较特殊，只能启动一个
    """
    whitelist = [("jd-tpaas", "tpaas-operator"), ("jd-tpaas", "tpaas-cluster-proxy"), ("jdd-paas", "uas-k8s-watch"), ("jdd-paas", "cassandra"),
                 ("digger", "digger-k8s-watch"), ("digger", "digger-master-loki-compactor"), ("digger", "digger-master-loki-frontend-leader"),
                 ("kube-system", "dns-autoscaler"), ("gatekeeper-system", "gatekeeper-audit"), ("magicflow", "magicflow"), ("opencloud", "finops"), ("store-managed", "jdock-install-job")]
    all_namespaces = get_all_namespaces()
    for namespace in all_namespaces:
        # 检查命名空间是否不在白名单中
        if any(namespace.startswith(namespace_prefix) for namespace_prefix in ns_prefix_whitelist):
            print(f"Skipping {namespace} due to whitelist.")
            continue

        print(f"\nProcessing namespace: {namespace}")
        for resource_type in resource_types:
            cmd = f"kubectl get {resource_type} -n {namespace} --output=jsonpath='{{.items[?(@.spec.replicas==1)].metadata.name}}'"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       universal_newlines=True)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                resources_to_adjust = stdout.strip().split()
                for resource_name in resources_to_adjust:
                    if (namespace, resource_name) not in whitelist:
                        backup_yaml(resource_type, resource_name, namespace)
                        adjust_replica_count(resource_type, resource_name, namespace, 2)
                    else:
                        print(f"Skipping {resource_type} {resource_name} in namespace {namespace} due to whitelist.")
            else:
                print(f"Error querying {resource_type} in namespace {namespace}")
                print(f"Error output: {stderr}")


if __name__ == "__main__":
    main()
