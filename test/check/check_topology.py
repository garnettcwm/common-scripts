import argparse
import subprocess
import json

# 高可用级别
ZONE_LEVEL = "zone"
RACK_LEVEL = "rack"
ha_topology_level_list = [ZONE_LEVEL, RACK_LEVEL]
ha_topology_level = ZONE_LEVEL

def get_pods_with_labels(label_selector, namespace="all"):
    # 获取符合标签筛选条件的 Pod 列表
    cmd = f"kubectl get pods -o json --selector={label_selector} --namespace={namespace}"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 检查命令是否执行成功
    if result.returncode != 0:
        print("Error executing kubectl command:")
        print(result.stderr)
        return None

    # 解析 JSON 输出
    pods_info = json.loads(result.stdout)
    return pods_info.get("items", [])

def get_group_labelvalue(label_selector, group_label_key, namespace="all"):
    # 获取符合标签筛选条件的 Pod 列表
    cmd = f"kubectl get pods -o json --selector={label_selector} --namespace={namespace}"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 检查命令是否执行成功
    if result.returncode != 0:
        print("Error executing kubectl command:")
        print(result.stderr)
        return None

    # 解析 JSON 输出
    pods_info = json.loads(result.stdout)

    # 提取标签值并去重
    label_values = set()
    for pod in pods_info.get("items", []):
        labels = pod.get("metadata", {}).get("labels", {})
        for label_key, label_value in labels.items():
            if label_key == group_label_key:
                label_values.add(label_value)

    return list(label_values)

def get_pod_info(pod):
    return f"Pod Name: {pod.get('metadata', {}).get('name', '')}, Namespace: {pod.get('metadata', {}).get('namespace', '')}"

def check_topology_constraints(pods, constraint_topology_key, label_selector):
    # 检查一批 Pod 所在节点的 rack 是否都不相同
    if len(pods) <= 0:
        return False, "check_topology_constraints pods is empty", constraint_topology_key, label_selector

    racks = set()
    for pod in pods:
        node_name = pod.get("spec", {}).get("nodeName", "")
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        labels = json.loads(labels.stdout).get("metadata", {}).get("labels", {})
        rack = labels.get(constraint_topology_key, "")
        if rack in racks:
            return False, constraint_topology_key, get_pod_info(pod), label_selector
        racks.add(rack)
    return True, constraint_topology_key, None, None

def check_topology_not_intersection_constraints(pods1, pods2, constraint_topology_key):
    # 检查两批 Pod 所在节点的 zone 是否都不相同
    if len(pods1) <= 0 or len(pods2) <= 0:
        return False, "check_topology_not_intersection_constraints pods is empty", "", constraint_topology_key

    topology_values1 = set()
    topology_values2 = set()
    for pod in pods1:
        node_name = pod.get("spec", {}).get("nodeName", "")
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        labels = json.loads(labels.stdout).get("metadata", {}).get("labels", {})
        topology_value = labels.get(constraint_topology_key, "")
        topology_values1.add(topology_value)

    for pod in pods2:
        node_name = pod.get("spec", {}).get("nodeName", "")
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        labels = json.loads(labels.stdout).get("metadata", {}).get("labels", {})
        topology_value = labels.get(constraint_topology_key, "")
        topology_values2.add(topology_value)

    if topology_values1.intersection(topology_values2):
        return False, get_pod_info(pods1[0]), get_pod_info(pods2[0]), constraint_topology_key
    return True, None, None, None

def check_topology_skew_constraints(pods, constraint_topology_key, label_selector):
    # 检查一批 Pod 所在节点的分类计数是否满足相差小于等于1的条件
    if len(pods) <= 0:
        return False, "check_topology_skew_constraints pods is empty", constraint_topology_key, label_selector

    node_counts = {}
    for pod in pods:
        node_name = pod.get("spec", {}).get("nodeName", "")
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        labels = json.loads(labels.stdout).get("metadata", {}).get("labels", {})
        constraint_value = labels.get(constraint_topology_key, "")
        node_counts[constraint_value] = node_counts.get(constraint_value, 0) + 1

    max_count = max(node_counts.values())
    min_count = min(node_counts.values())

    if max_count - min_count > 1:
        return False, get_pod_info(pods[0]), constraint_topology_key, label_selector
    return True, None, None, None

def check_node_required_labels_constraints(pods, required_labels, label_selector):
    # 检查一批 Pod 所在节点的 labels 是否包含指定的 label
    if len(pods) <= 0:
        return False, "check_node_required_labels_constraints pods is empty", required_labels, label_selector

    for pod in pods:
        node_name = pod.get("spec", {}).get("nodeName", "")
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        labels = json.loads(labels.stdout).get("metadata", {}).get("labels", {})

        # 检查是否包含所有必需的 labels
        if not all(label in labels for label in required_labels):
            return False, get_pod_info(pod), required_labels, label_selector

    return True, None, None, None

def check_node_forbidden_labels_constraints(pods, forbidden_labels, label_selector):
    # 检查一批 Pod 所在节点的 labels 是否包含指定的 label
    if len(pods) <= 0:
        return False, "check_node_forbidden_labels_constraints pods is empty", forbidden_labels, label_selector

    for pod in pods:
        node_name = pod.get("spec", {}).get("nodeName", "")
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        labels = json.loads(labels.stdout).get("metadata", {}).get("labels", {})

        for forbidden_label in forbidden_labels:
            if forbidden_label in labels:
                return False, get_pod_info(pod), forbidden_label, label_selector

    return True, None, None, None


def get_namespaces_with_prefix(prefix):
    # 使用 kubectl 命令获取所有的 namespace 信息
    cmd = "kubectl get namespaces -o json"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 检查命令是否执行成功
    if result.returncode != 0:
        print("Error executing kubectl command:")
        print(result.stderr)
        return None

    # 解析 JSON 输出
    namespaces_info = json.loads(result.stdout)

    # 获取满足指定前缀的 namespace 名称
    matching_namespaces = [ns["metadata"]["name"] for ns in namespaces_info.get("items", []) if ns["metadata"]["name"].startswith(prefix)]

    return matching_namespaces


def check_runtime_kafka_topology():
    print(f"Info: check kafka runtime topology started")
    instances = [
        {
            "namespace": "tpaas-kafka",
            "broker_name": "kafka-kafka",
            "zookeeper_name": "kafka-zookeeper"
        },
        {
            "namespace": "digger-kafka",
            "broker_name": "digger-kafka-kafka",
            "zookeeper_name": "digger-kafka-zookeeper"
        }]
    for instance in instances:
        namespace = instance.get("namespace")
        # 检查broker拓扑分布
        broker_name = instance.get("broker_name")
        print(f"Info: check kafka {broker_name} topology started")

        label_selector_broker = f"app.kubernetes.io/component=kafka,strimzi.io/name={broker_name}"
        pods_kafka_broker = get_pods_with_labels(label_selector_broker, namespace)
        if ha_topology_level == ZONE_LEVEL:
            # check broker topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_kafka_broker, "topology.jdos.io/zone", label_selector_broker)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # check broker rack topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_kafka_broker, "topology.jdos.io/rack", label_selector_broker)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # broker必须位于非仲裁区
            required_scheduler_zone_labels = ["topology.jdos.io/scheduler-zone"]
            constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_kafka_broker, required_scheduler_zone_labels, label_selector_broker)
            if not constraints_satisfied:
                print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

        if ha_topology_level == RACK_LEVEL:
            # check broker rack topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_kafka_broker, "topology.jdos.io/rack", label_selector_broker)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        # 检查zookeeper拓扑分布
        zookeeper_name = instance.get("zookeeper_name")
        label_selector_zookeeper = f"strimzi.io/name={zookeeper_name}"
        pods_kafka_zookeeper = get_pods_with_labels(label_selector_zookeeper, namespace)
        if ha_topology_level == ZONE_LEVEL:
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_kafka_zookeeper, "topology.jdos.io/zone", label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

        if ha_topology_level == RACK_LEVEL:
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_kafka_zookeeper, "topology.jdos.io/rack", label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

    print(f"Info: check kafka runtime topology finished")


def check_runtime_redis_topology():
    print(f"Info: check redis runtime topology started")
    instances = [
        {
            "namespace": "redis",
            "instance_name": "rediscluster"
        },
        {
            "namespace": "redis",
            "instance_name": "digger-rediscluster"
        }]
    for instance in instances:
        # redis.jdcloud.com/role=master
        # redis.jdcloud.com/role=replica
        # redis.jdcloud.com/shard=shard-0
        namespace = instance.get("namespace")
        instance_name = instance.get("instance_name")
        print(f"Info: check redis {instance_name} topology started")
        label_selector_master = f"app.kubernetes.io/component=redis,app.kubernetes.io/instance={instance_name},redis.jdcloud.com/role=master"
        label_selector_replica = f"app.kubernetes.io/component=redis,app.kubernetes.io/instance={instance_name},redis.jdcloud.com/role=replica"
        pods_redis_master = get_pods_with_labels(label_selector_master, namespace)
        pods_redis_replica = get_pods_with_labels(label_selector_replica, namespace)

        # shard数，理论上shard数和master数量一致
        shard_num: int = len(pods_redis_master)
        print(f"Info: check redis {instance_name} shard num is {shard_num}")

        if ha_topology_level == ZONE_LEVEL:
            # master、slave分布在不同AZ
            constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_redis_master, pods_redis_replica, "topology.jdos.io/zone")
            if not constraints_satisfied:
                print(f"Error: Topology intersection constraint violation! {error_info}. {error_info2}. topology_key: {topology_key}")

        if ha_topology_level == ZONE_LEVEL or ha_topology_level == RACK_LEVEL:
            # 保证所有不同分片的master在机架（或主机）级别均衡分布
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_master, "topology.jdos.io/rack", label_selector_master)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}.Label Selector: {selector_info}")

            # 同一shard的master、replica不能在同一机架
            for i in range(0, shard_num):
                label_selector_master_shard_x = label_selector_master + f",redis.jdcloud.com/shard=shard-{i}"
                label_selector_replica_shard_x = label_selector_replica + f",redis.jdcloud.com/shard=shard-{i}"
                pods_redis_master_shard_x = get_pods_with_labels(label_selector_master_shard_x, namespace)
                pods_redis_replica_shard_x = get_pods_with_labels(label_selector_replica_shard_x, namespace)
                constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_redis_master_shard_x, pods_redis_replica_shard_x, "topology.jdos.io/rack")
                if not constraints_satisfied:
                    print(f"Error: Topology intersection constraint violation! {error_info}. {error_info2}. topology_key: {topology_key}")

        # proxy
        proxy_instance_name = instance_name + "-proxy"
        label_selector_proxy = f"app.kubernetes.io/component=predixy,app.kubernetes.io/instance={proxy_instance_name}"
        pods_redis_proxy = get_pods_with_labels(label_selector_proxy, namespace)
        if ha_topology_level == ZONE_LEVEL:
            # 可用区topology maxSkew检验
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_proxy, "topology.jdos.io/zone", label_selector_proxy)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # proxy必须位于非仲裁区
            required_scheduler_zone_labels = ["topology.jdos.io/scheduler-zone"]
            constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_redis_proxy, required_scheduler_zone_labels, label_selector_proxy)
            if not constraints_satisfied:
                print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

        if ha_topology_level == RACK_LEVEL:
            # 机架topology maxSkew检验
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_proxy, "topology.jdos.io/rack", label_selector_proxy)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

    print(f"Info: check redis runtime topology finished")


def check_runtime_es_topology():
    print(f"Info: check es runtime topology started")
    instances = [
        {
            "namespace": "tpaas-es",
            "instance_name": "tpaas-es",
        },
        {
            "namespace": "tpaas-es",
            "instance_name": "digger-tpaas-es",
        },
        {
            "namespace": "tpaas-es",
            "instance_name": "es-biz",
        },
        {
            "namespace": "tpaas-es",
            "instance_name": "es-sgm",
        },
        {
            "namespace": "tpaas-es",
            "instance_name": "stardb-tpaas-es",
        }]
    for instance in instances:
        # redis.jdcloud.com/role=master
        # redis.jdcloud.com/role=replica
        # redis.jdcloud.com/shard=shard-0
        namespace = instance.get("namespace")
        instance_name = instance.get("instance_name")
        print(f"Info: check es {instance_name} topology started")
        label_selector_master = f"app.kubernetes.io/name=elasticsearch,app.kubernetes.io/instance={instance_name},statefulset-name={instance_name}-masters"
        label_selector_node = f"app.kubernetes.io/name=elasticsearch,app.kubernetes.io/instance={instance_name},statefulset-name={instance_name}-nodes"
        pods_es_master = get_pods_with_labels(label_selector_master, namespace)
        pods_es_node = get_pods_with_labels(label_selector_node, namespace)

        if ha_topology_level == ZONE_LEVEL:
            # check master topology skew
            # 存在没有master节点的集群
            if len(pods_es_master) != 0:
                constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_es_master, "topology.jdos.io/zone", label_selector_master)
                if not constraints_satisfied:
                    print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # check node topology skew
            constraints_satisfied, error_info, constraint_topology_key, label_selector_master = check_topology_skew_constraints(pods_es_node, "topology.jdos.io/zone", label_selector_node)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # node节点必须位于非仲裁区
            required_scheduler_zone_labels = ["topology.jdos.io/scheduler-zone"]
            constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_es_node, required_scheduler_zone_labels, label_selector_node)
            if not constraints_satisfied:
                print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

        if ha_topology_level == RACK_LEVEL:
            # check master topology skew
            if len(pods_es_master) != 0:
                constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_es_master, "topology.jdos.io/rack", label_selector_master)
                if not constraints_satisfied:
                    print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # check node topology skew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_es_node, "topology.jdos.io/rack", label_selector_node)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

    print(f"Info: check es runtime topology finished")


def check_runtime_etcd_topology():
    print(f"Info: check etcd runtime topology started")
    instances = [
        {
            "namespace": "tpaas-etcd",
            "instance_name": "tpaas-etcd"
        },
        {
            "namespace": "hips-etcd",
            "instance_name": "hips-etcd"
        }]
    for instance in instances:
        namespace = instance.get("namespace")
        # 检查broker拓扑分布
        instance_name = instance.get("instance_name")
        print(f"Info: check etcd {instance_name} topology started")

        label_selector_etcd_data = f"app.kubernetes.io/component=etcd-cluster,app.kubernetes.io/instance={instance_name}"
        pods_etcd_data = get_pods_with_labels(label_selector_etcd_data, namespace)
        if ha_topology_level == ZONE_LEVEL:
            # check etcd data topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_etcd_data, "topology.jdos.io/zone", label_selector_etcd_data)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        if ha_topology_level == RACK_LEVEL:
            # check etcd data topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_etcd_data, "topology.jdos.io/rack", label_selector_etcd_data)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

    print(f"Info: check etcd runtime topology finished")


def check_runtime_zookeeper_topology():
    print(f"Info: check zookeeper runtime topology started")
    instances = [
        {
            "namespace": "tpaas-zk",
            "instance_name": "tpaas-zookeeper"
        }]
    for instance in instances:
        namespace = instance.get("namespace")
        # 检查broker拓扑分布
        instance_name = instance.get("instance_name")
        print(f"Info: check zookeeper {instance_name} topology started")

        label_selector_zookeeper = f"app.kubernetes.io/component=zk,app.kubernetes.io/instance={instance_name}"
        pods_zookeeper = get_pods_with_labels(label_selector_zookeeper, namespace)
        if ha_topology_level == ZONE_LEVEL:
            # check zookeeper topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_zookeeper, "topology.jdos.io/zone", label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        if ha_topology_level == RACK_LEVEL:
            # check zookeeper topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_zookeeper, "topology.jdos.io/rack", label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

    print(f"Info: check zookeeper runtime topology finished")


def check_runtime_mysql_topology():
    print(f"Info: check mysql runtime topology started")
    instances = [
        {
            "namespace": "mysql",
            "instance_name": "mysql-cluster",
        },
        {
            "namespace": "mysql",
            "instance_name": "digger-mysql-cluster",
        }]
    for instance in instances:
        # role: master   role: master
        namespace = instance.get("namespace")
        instance_name = instance.get("instance_name")
        print(f"Info: check mysql {instance_name} topology started")
        label_selector_all = f"app.kubernetes.io/name=mysql-cluster,app.kubernetes.io/instance={instance_name}"
        label_selector_master = f"{label_selector_all},role=master"
        label_selector_node = f"{label_selector_all},role=replica"
        pods_mysql_all = get_pods_with_labels(label_selector_all, namespace)
        pods_mysql_master = get_pods_with_labels(label_selector_master, namespace)
        pods_mysql_replica = get_pods_with_labels(label_selector_node, namespace)

        if ha_topology_level == ZONE_LEVEL:
            # master、replica分布在不同AZ
            constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_mysql_master, pods_mysql_replica, "topology.jdos.io/zone")
            if not constraints_satisfied:
                print(f"Error: Topology intersection constraint violation! {error_info}. {error_info2}. topology_key: {topology_key}")

            # master节点必须位于非仲裁区
            required_scheduler_zone_labels = ["topology.jdos.io/scheduler-zone"]
            constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_mysql_master, required_scheduler_zone_labels, label_selector_master)
            if not constraints_satisfied:
                print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

            # replica必须位于非仲裁区
            constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_mysql_replica, required_scheduler_zone_labels, label_selector_node)
            if not constraints_satisfied:
                print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

        if ha_topology_level == RACK_LEVEL:
            # 所有节点不能在同一rack
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_mysql_all, "topology.jdos.io/rack", label_selector_all)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

    print(f"Info: check mysql runtime topology finished")

def check_runtime_mongodb_topology():
    print(f"Info: check mongodb runtime topology started")
    instances = [
        {
            "namespace": "mongo-cvessel",
            "instance_name": "mongo-cvessel"
        }]
    for instance in instances:
        namespace = instance.get("namespace")
        # 检查broker拓扑分布
        instance_name = instance.get("instance_name")
        print(f"Info: check mongodb {instance_name} topology started")

        label_selector_mongod = f"app.kubernetes.io/component=mongod,app.kubernetes.io/instance={instance_name}"
        pods_mongod = get_pods_with_labels(label_selector_mongod, namespace)
        if ha_topology_level == ZONE_LEVEL:
            # check mongod topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_mongod, "topology.jdos.io/zone", label_selector_mongod)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        if ha_topology_level == RACK_LEVEL:
            # 所有节点不能在同一rack
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_mongod, "topology.jdos.io/rack", label_selector_mongod)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

    print(f"Info: check mongodb runtime topology finished")

def check_runtime_clickhouse_topology():
    print(f"Info: check clickhouse runtime topology started")
    instances = [
        {
            "namespace": "ck-csa",
            "instance_name": "ck-csa"
        },
        {
            "namespace": "ck-themis",
            "instance_name": "ck-themis"
        }]
    for instance in instances:
        # app.kubernetes.io/component: cluster_clickhouse
        # clickhouse.altinity.com/shard: "0"
        # redis.jdcloud.com/shard=shard-0
        namespace = instance.get("namespace")
        instance_name = instance.get("instance_name")
        print(f"Info: check clickhouse {instance_name} topology started")

        label_selector_clickhouse = f"app.kubernetes.io/component=cluster_clickhouse,app.kubernetes.io/instance={instance_name}"
        pods_clickhouse = get_pods_with_labels(label_selector_clickhouse, namespace)
        # 所有ck集群节点必须位于非仲裁区
        required_scheduler_zone_labels = ["topology.jdos.io/scheduler-zone"]
        constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_clickhouse, required_scheduler_zone_labels, label_selector_clickhouse)
        if not constraints_satisfied:
            print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

        # 获取shard list
        shard_str_list = get_group_labelvalue(label_selector_clickhouse, "clickhouse.altinity.com/shard", namespace)
        # 将字符串列表转换为整数列表
        shard_integer_list = [int(num_str) for num_str in shard_str_list]
        # shard 从0开始，因此num = max + 1
        shard_num = max(shard_integer_list) + 1
        print(f"Info: check clickhouse {instance_name} shard num is {shard_num}")

        for shard_index in range(0, shard_num):
            label_selector_shard_x = label_selector_clickhouse + f",clickhouse.altinity.com/shard={shard_index}"
            pods_clickhouse_shard_x = get_pods_with_labels(label_selector_shard_x, namespace)
            if ha_topology_level == ZONE_LEVEL:
                # ck不分主从，同一shard在zone上均衡分布

                constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_clickhouse_shard_x, "topology.jdos.io/zone", label_selector_shard_x)
                if not constraints_satisfied:
                    print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}.Label Selector: {selector_info}")

            if ha_topology_level == RACK_LEVEL:
                # 所有节点不能在同一rack
                constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_clickhouse_shard_x, "topology.jdos.io/rack", label_selector_shard_x)
                if not constraints_satisfied:
                    print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

        # 检查zookeeper拓扑分布
        label_selector_zookeeper = f"app.kubernetes.io/component=cluster_zk,app.kubernetes.io/instance={instance_name}"
        pods_clickhouse_zookeeper = get_pods_with_labels(label_selector_zookeeper, namespace)
        if ha_topology_level == ZONE_LEVEL:
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_clickhouse_zookeeper, "topology.jdos.io/zone", label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

        if ha_topology_level == RACK_LEVEL:
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_clickhouse_zookeeper, "topology.jdos.io/rack", label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

    print(f"Info: check clickhouse runtime topology finished")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A script with command line arguments.')
    parser.add_argument('-l', '--ha-level', type=str, help='定义更可用级别, 取值: zone、rack')

    args = parser.parse_args()

    # 使用参数键获取传递的值
    ha_topology_level = args.ha_level
    if ha_topology_level not in ha_topology_level_list:
        print(f"Error: the passed-in parameter ha-level [{ha_topology_level}] is invalid, The supported values are {ha_topology_level_list}")
        exit(1)

    prefix = "redis-"
    matching_namespaces = get_namespaces_with_prefix(prefix)

    if matching_namespaces:
        # 遍历并打印满足指定前缀的 namespace 的名称
        for namespace in matching_namespaces:
            print(namespace)
    else:
        print("No matching namespaces found.")

    # 检查runtime kafka topology
    check_runtime_kafka_topology()

    # 检查runtime redis topology
    check_runtime_redis_topology()

    # 检查runtime es topology
    check_runtime_es_topology()

    # 检查runtime etcd topology
    check_runtime_etcd_topology()

    # 检查runtime zookeeper topology
    check_runtime_zookeeper_topology()

    # 检查runtime mysql topology
    check_runtime_mysql_topology()

    # 检查runtime mongodb topology
    check_runtime_mongodb_topology()

    # 检查runtime clickhouse topology
    check_runtime_clickhouse_topology()
