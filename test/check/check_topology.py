import argparse
import subprocess
import json

# 高可用级别
TOPOLOGY_KEY_ZONE = "topology.jdos.io/zone"
TOPOLOGY_KEY_RACK = "topology.jdos.io/rack"
ZONE_LEVEL = "zone"
RACK_LEVEL = "rack"
HA_TOPOLOGY_LEVEL_LIST = [ZONE_LEVEL, RACK_LEVEL]
HA_TOPOLOGY_LEVEL = ZONE_LEVEL

# paas scope
PAAS_SCOPE_ALL = "all"
PAAS_SCOPE_TENANT = "tenant"
PAAS_SCOPE_RUNTIME = "runtime"
PAAS_SCOPE_LIST = [PAAS_SCOPE_ALL, PAAS_SCOPE_TENANT, PAAS_SCOPE_RUNTIME]
PAAS_SCOPE = PAAS_SCOPE_ALL

# 全局变量，用于缓存 CRD 数据
GLOBAL_CACHED_CRD_NAMES = None


def is_paas_tenant_included():
    if PAAS_SCOPE == PAAS_SCOPE_ALL or PAAS_SCOPE_ALL == PAAS_SCOPE_TENANT:
        return True
    return False


def is_paas_runtime_included():
    if PAAS_SCOPE == PAAS_SCOPE_ALL or PAAS_SCOPE_ALL == PAAS_SCOPE_RUNTIME:
        return True
    return False


def get_pods_with_labels(label_selector, namespace="all"):
    # 获取符合标签筛选条件的 Pod 列表
    cmd = f"kubectl get pods -o json --selector={label_selector} "
    if namespace == "all":
        cmd += f" --all-namespaces=true "
    else:
        cmd += f" --namespace={namespace} "
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 检查命令是否执行成功
    if result.returncode != 0:
        print(f"Error executing kubectl command: {cmd}, error:{result.stderr}")
        return None

    # 解析 JSON 输出
    pods_info = json.loads(result.stdout)
    return pods_info.get("items", [])


def get_all_crds_names():
    global GLOBAL_CACHED_CRD_NAMES
    try:
        # 获取所有CRD的JSON数据
        cmd = f"kubectl get crd -o json"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 解析 JSON 数据
        crds_data = json.loads(result.stdout)

        # 缓存数据
        GLOBAL_CACHED_CRD_NAMES = [crd["metadata"]["name"] for crd in crds_data.get("items", [])]
    except subprocess.CalledProcessError:
        # 如果命令返回非零状态码，则忽略错误，保持缓存不变
        pass


def check_crd_existence(crd_name):
    global GLOBAL_CACHED_CRD_NAMES
    if GLOBAL_CACHED_CRD_NAMES is None:
        # 如果缓存为空，则获取所有 CRD 数据
        print(f"Info: GLOBAL_CACHED_CRD_NAMES is None, cached from server")
        get_all_crds_names()

    # 本地过滤，检查是否存在指定名称的 CRD
    exists = crd_name in GLOBAL_CACHED_CRD_NAMES
    return exists


def get_cr_by_crd_name(crd_name, namespace="all"):
    is_crd_exists = check_crd_existence(crd_name)
    if not is_crd_exists:
        print(f"Info: {crd_name} isn't installed, skip it")
        return []

    # 获取符合标签筛选条件的 Pod 列表
    cmd = f"kubectl get {crd_name} -o json "
    if namespace == "all":
        cmd += f" --all-namespaces=true "
    else:
        cmd += f" --namespace={namespace} "
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 检查命令是否执行成功
    if result.returncode != 0:
        print(f"Error executing kubectl command: {cmd}, error: {result.stderr}")
        return None

    # 解析 JSON 输出
    pods_info = json.loads(result.stdout)
    return pods_info.get("items", [])


def get_cr_by_name(crd_name, cr_name, namespace="all"):
    # 获取符合标签筛选条件的 Pod 列表
    cmd = f"kubectl get {crd_name} {cr_name} -o json "
    if namespace == "all":
        cmd += f" --all-namespaces=true "
    else:
        cmd += f" --namespace={namespace} "
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 检查命令是否执行成功
    if result.returncode != 0:
        print(f"Error executing kubectl command: {cmd}, error: {result.stderr}")
        return None

    # 解析 JSON 输出
    pods_info = json.loads(result.stdout)
    return pods_info


def get_group_labelvalue(label_selector, group_label_key, namespace="all"):
    # 获取符合标签筛选条件的 Pod 列表
    cmd = f"kubectl get pods -o json --selector={label_selector} "
    if namespace == "all":
        cmd += f" --all-namespaces=true "
    else:
        cmd += f" --namespace={namespace} "
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 检查命令是否执行成功
    if result.returncode != 0:
        print(f"Error executing kubectl command: {cmd}, error:{result.stderr}")
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
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        labels = json.loads(labels.stdout).get("metadata", {}).get("labels", {})
        topology_value = labels.get(constraint_topology_key, "")
        topology_values1.add(topology_value)

    for pod in pods2:
        node_name = pod.get("spec", {}).get("nodeName", "")
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        labels = subprocess.run(f"kubectl get node {node_name} -o json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        labels = json.loads(labels.stdout).get("metadata", {}).get("labels", {})

        for forbidden_label in forbidden_labels:
            if forbidden_label in labels:
                return False, get_pod_info(pod), forbidden_label, label_selector

    return True, None, None, None


def get_namespaces_with_prefix(prefix):
    # 使用 kubectl 命令获取所有的 namespace 信息
    cmd = "kubectl get namespaces -o json"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 检查命令是否执行成功
    if result.returncode != 0:
        print(f"Error executing kubectl command: {cmd}, error:{result.stderr}")
        return None

    # 解析 JSON 输出
    namespaces_info = json.loads(result.stdout)

    # 获取满足指定前缀的 namespace 名称
    matching_namespaces = [ns["metadata"]["name"] for ns in namespaces_info.get("items", []) if ns["metadata"]["name"].startswith(prefix)]

    return matching_namespaces


def check_kafka_topology():
    print(f"Info: check kafka topology started")

    instances = get_kafka_instance()
    for instance in instances:
        namespace = instance.get("namespace")
        # 检查broker拓扑分布
        instance_name = instance.get("instance_name")
        broker_name = instance_name + "-kafka"
        print(f"Info: check kafka {broker_name} topology started")

        label_selector_broker = f"app.kubernetes.io/name=kafka,app.kubernetes.io/instance={instance_name},strimzi.io/name={broker_name}"
        pods_kafka_broker = get_pods_with_labels(label_selector_broker, namespace)
        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            # check broker topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_kafka_broker, TOPOLOGY_KEY_ZONE, label_selector_broker)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # check broker rack topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_kafka_broker, TOPOLOGY_KEY_RACK, label_selector_broker)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # broker必须位于非仲裁区
            required_scheduler_zone_labels = ["topology.jdos.io/scheduler-zone"]
            constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_kafka_broker, required_scheduler_zone_labels, label_selector_broker)
            if not constraints_satisfied:
                print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            # check broker rack topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_kafka_broker, TOPOLOGY_KEY_RACK, label_selector_broker)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        # 检查zookeeper拓扑分布
        zookeeper_name = instance_name + "-zookeeper"
        label_selector_zookeeper = f"app.kubernetes.io/name=kafka,app.kubernetes.io/instance={instance_name},strimzi.io/name={zookeeper_name}"
        pods_kafka_zookeeper = get_pods_with_labels(label_selector_zookeeper, namespace)
        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_kafka_zookeeper, TOPOLOGY_KEY_ZONE, label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_kafka_zookeeper, TOPOLOGY_KEY_RACK, label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

    print(f"Info: check kafka topology finished")


def get_kafka_instance():
    # [
    #     {
    #         "namespace": "tpaas-kafka",
    #         "instance_name": "kafka"
    #     },
    #     {
    #         "namespace": "digger-kafka",
    #         "instance_name": "digger-kafka"
    #     }]
    instances = []
    kafka_list = get_cr_by_crd_name("kafkas.kafka.strimzi.io")
    for kafka in kafka_list:
        instance_name = kafka.get("metadata", {}).get("name", "")
        instance_namespace = kafka.get("metadata", {}).get("namespace", "")

        instances.append({
            "namespace": instance_namespace,
            "instance_name": instance_name
        })
    return instances


def check_redis_topology():
    print(f"Info: check redis topology started")
    instances = get_redis_instance()

    for instance in instances:
        # redis.jdcloud.com/role=master
        # redis.jdcloud.com/role=replica
        # redis.jdcloud.com/shard=shard-0
        namespace = instance.get("namespace")
        instance_name = instance.get("instance_name")
        rediscluster = get_cr_by_name("redisclusters.redis.jdcloud.com", instance_name, namespace)
        if rediscluster is None or rediscluster == {}:
            print(f"Error: get rediscluster {instance_name} failed")
            return

        redis_type = rediscluster.get("spec", {}).get("redisType", "cluster")
        failure_domain = rediscluster.get("spec", {}).get("ha", {}).get("failureDomain", "")
        print(f"Info: check redis {instance_name} topology started, redis_type: {redis_type}, failure_domain:{failure_domain}")

        label_selector_master = f"app.kubernetes.io/component=redis,app.kubernetes.io/instance={instance_name},redis.jdcloud.com/role=master"
        label_selector_replica = f"app.kubernetes.io/component=redis,app.kubernetes.io/instance={instance_name},redis.jdcloud.com/role=replica"

        # print(f"Debug: redis {instance_name} {redis_type} {failure_domain}")

        # 根据redis架构类型检查
        if redis_type == "standalone":
            check_redis_standalone_topology(instance, label_selector_master, label_selector_replica)
        elif redis_type == "cluster":
            # 如果故障域是zone级别，则说明是SpecifyByCluster模式模式；否则是SpecifyByReplicaGroup模式部署
            if failure_domain == TOPOLOGY_KEY_ZONE:
                check_redis_cluster_topology(instance, label_selector_master, label_selector_replica)
            else:
                check_redis_replica_group_topology(instance, label_selector_master, label_selector_replica)
        else:
            print(f"Error: redis {instance_name} 's redis_type is None")
    print(f"Info: check redis topology finished")


def get_redis_instance():
    # [
    #     {
    #         "namespace": "redis",
    #         "instance_name": "rediscluster"
    #     },
    #     {
    #         "namespace": "redis",
    #         "instance_name": "digger-rediscluster"
    #     }]
    instances = []
    kafka_list = get_cr_by_crd_name("redisclusters.redis.jdcloud.com")
    for kafka in kafka_list:
        instance_name = kafka.get("metadata", {}).get("name", "")
        instance_namespace = kafka.get("metadata", {}).get("namespace", "")

        instances.append({
            "namespace": instance_namespace,
            "instance_name": instance_name
        })
    return instances


"""  
redis：检查"副本组"部署模式的redis集群拓扑
1、standalone redis只有一个master
2、standalone redis只有一个shard
"""
def check_redis_standalone_topology(instance, label_selector_master, label_selector_replica):
    namespace = instance.get("namespace")
    instance_name = instance.get("instance_name")
    pods_redis_master = get_pods_with_labels(label_selector_master, namespace)
    pods_redis_replica = get_pods_with_labels(label_selector_replica, namespace)

    if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
        # master、slave分布在不同AZ
        constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_redis_master, pods_redis_replica, TOPOLOGY_KEY_ZONE)
        if not constraints_satisfied:
            print(f"Error: Topology intersection constraint violation! {error_info}. {error_info2}. topology_key: {topology_key}")

    # 主、从所在的机架不相同 (podAntiAffinity)
    if HA_TOPOLOGY_LEVEL == ZONE_LEVEL or HA_TOPOLOGY_LEVEL == RACK_LEVEL:
        label_selector_master_shard_x = label_selector_master + f",redis.jdcloud.com/shard=shard-0"
        label_selector_replica_shard_x = label_selector_replica + f",redis.jdcloud.com/shard=shard-0"
        pods_redis_master_shard_x = get_pods_with_labels(label_selector_master_shard_x, namespace)
        pods_redis_replica_shard_x = get_pods_with_labels(label_selector_replica_shard_x, namespace)
        constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_redis_master_shard_x, pods_redis_replica_shard_x, TOPOLOGY_KEY_RACK)
        if not constraints_satisfied:
            print(f"Error: Topology intersection constraint violation! {error_info}. {error_info2}. topology_key: {topology_key}")

    # proxy
    # 标准版proxy的app.kubernetes.io/component=proxy
    # 集群版proxy的app.kubernetes.io/component=predixy
    label_selector_proxy = f"app.kubernetes.io/component=proxy,app.kubernetes.io/instance={instance_name}"
    pods_redis_proxy = get_pods_with_labels(label_selector_proxy, namespace)
    if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
        # 可用区topology maxSkew检验
        constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_proxy, TOPOLOGY_KEY_ZONE, label_selector_proxy)
        if not constraints_satisfied:
            print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        # proxy必须位于非仲裁区
        required_scheduler_zone_labels = ["topology.jdos.io/scheduler-zone"]
        constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_redis_proxy, required_scheduler_zone_labels, label_selector_proxy)
        if not constraints_satisfied:
            print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

    if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
        # 机架topology maxSkew检验
        constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_proxy, TOPOLOGY_KEY_RACK, label_selector_proxy)
        if not constraints_satisfied:
            print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")


"""  
redis：检查"副本组"部署模式的redis集群拓扑
"""
def check_redis_replica_group_topology(instance, label_selector_master, label_selector_replica):
    namespace = instance.get("namespace")
    instance_name = instance.get("instance_name")
    pods_redis_master = get_pods_with_labels(label_selector_master, namespace)
    pods_redis_replica = get_pods_with_labels(label_selector_replica, namespace)

    # shard数，理论上shard数和master数量一致
    shard_num: int = len(pods_redis_master)
    print(f"Info: check redis {instance_name} shard num is {shard_num}")

    if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
        # master、slave分布在不同AZ
        constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_redis_master, pods_redis_replica, TOPOLOGY_KEY_ZONE)
        if not constraints_satisfied:
            print(f"Error: Topology intersection constraint violation! {error_info}. {error_info2}. topology_key: {topology_key}")

    if HA_TOPOLOGY_LEVEL == ZONE_LEVEL or HA_TOPOLOGY_LEVEL == RACK_LEVEL:
        # 保证所有不同分片的master在机架（或主机）级别均衡分布 (topologySpreadConstraints)
        constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_master, TOPOLOGY_KEY_RACK, label_selector_master)
        if not constraints_satisfied:
            print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}.Label Selector: {selector_info}")

        # 同一shard的master、replica不能在同一机架
        for i in range(0, shard_num):
            label_selector_master_shard_x = label_selector_master + f",redis.jdcloud.com/shard=shard-{i}"
            label_selector_replica_shard_x = label_selector_replica + f",redis.jdcloud.com/shard=shard-{i}"
            pods_redis_master_shard_x = get_pods_with_labels(label_selector_master_shard_x, namespace)
            pods_redis_replica_shard_x = get_pods_with_labels(label_selector_replica_shard_x, namespace)
            constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_redis_master_shard_x, pods_redis_replica_shard_x, TOPOLOGY_KEY_RACK)
            if not constraints_satisfied:
                print(f"Error: Topology intersection constraint violation! {error_info}. {error_info2}. topology_key: {topology_key}")

    # proxy
    proxy_instance_name = instance_name + "-proxy"
    label_selector_proxy = f"app.kubernetes.io/component=predixy,app.kubernetes.io/instance={proxy_instance_name}"
    pods_redis_proxy = get_pods_with_labels(label_selector_proxy, namespace)
    # 存在没有proxy的情况
    if len(pods_redis_proxy) != 0:
        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            # 可用区topology maxSkew检验
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_proxy, TOPOLOGY_KEY_ZONE, label_selector_proxy)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # proxy必须位于非仲裁区
            required_scheduler_zone_labels = ["topology.jdos.io/scheduler-zone"]
            constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_redis_proxy, required_scheduler_zone_labels, label_selector_proxy)
            if not constraints_satisfied:
                print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            # 机架topology maxSkew检验
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_proxy, TOPOLOGY_KEY_RACK, label_selector_proxy)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")


"""  
redis：检查"cluster"部署模式的redis集群拓扑
"""
def check_redis_cluster_topology(instance, label_selector_master, label_selector_replica):
    namespace = instance.get("namespace")
    instance_name = instance.get("instance_name")
    pods_redis_master = get_pods_with_labels(label_selector_master, namespace)
    pods_redis_replica = get_pods_with_labels(label_selector_replica, namespace)

    # shard数，理论上shard数和master数量一致
    shard_num: int = len(pods_redis_master)
    print(f"Info: check redis {instance_name} shard num is {shard_num}")

    if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
        # 保证所有不同分片的master AZ级别均衡分布
        constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_master, TOPOLOGY_KEY_ZONE, label_selector_master)
        if not constraints_satisfied:
            print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}.Label Selector: {selector_info}")

        # 同一shard的master、replica不能在同一可用区
        for i in range(0, shard_num):
            label_selector_master_shard_x = label_selector_master + f",redis.jdcloud.com/shard=shard-{i}"
            label_selector_replica_shard_x = label_selector_replica + f",redis.jdcloud.com/shard=shard-{i}"
            pods_redis_master_shard_x = get_pods_with_labels(label_selector_master_shard_x, namespace)
            pods_redis_replica_shard_x = get_pods_with_labels(label_selector_replica_shard_x, namespace)
            constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_redis_master_shard_x, pods_redis_replica_shard_x, TOPOLOGY_KEY_ZONE)
            if not constraints_satisfied:
                print(f"Error: Topology intersection constraint violation! {error_info}. {error_info2}. topology_key: {topology_key}")

    if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
        # 保证所有不同分片的master在机架（或主机）级别均衡分布
        constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_master, TOPOLOGY_KEY_RACK, label_selector_master)
        if not constraints_satisfied:
            print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}.Label Selector: {selector_info}")

        # 同一shard的master、replica不能在同一机架
        for i in range(0, shard_num):
            label_selector_master_shard_x = label_selector_master + f",redis.jdcloud.com/shard=shard-{i}"
            label_selector_replica_shard_x = label_selector_replica + f",redis.jdcloud.com/shard=shard-{i}"
            pods_redis_master_shard_x = get_pods_with_labels(label_selector_master_shard_x, namespace)
            pods_redis_replica_shard_x = get_pods_with_labels(label_selector_replica_shard_x, namespace)
            constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_redis_master_shard_x, pods_redis_replica_shard_x, TOPOLOGY_KEY_RACK)
            if not constraints_satisfied:
                print(f"Error: Topology intersection constraint violation! {error_info}. {error_info2}. topology_key: {topology_key}")

    """
    check proxy
    """
    proxy_instance_name = instance_name + "-proxy"
    label_selector_proxy = f"app.kubernetes.io/component=predixy,app.kubernetes.io/instance={proxy_instance_name}"
    pods_redis_proxy = get_pods_with_labels(label_selector_proxy, namespace)
    # 存在没有proxy的情况
    if len(pods_redis_proxy) != 0:
        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            # 可用区topology maxSkew检验
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_proxy, TOPOLOGY_KEY_ZONE, label_selector_proxy)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            # 机架topology maxSkew检验
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_redis_proxy, TOPOLOGY_KEY_RACK, label_selector_proxy)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")


def check_es_topology():
    print(f"Info: check es topology started")

    instances = get_es_instance()
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

        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            # check master topology skew
            # 存在没有master节点的集群
            if len(pods_es_master) != 0:
                constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_es_master, TOPOLOGY_KEY_ZONE, label_selector_master)
                if not constraints_satisfied:
                    print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # check node topology skew
            constraints_satisfied, error_info, constraint_topology_key, label_selector_master = check_topology_skew_constraints(pods_es_node, TOPOLOGY_KEY_ZONE, label_selector_node)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # node节点必须位于非仲裁区
            required_scheduler_zone_labels = ["topology.jdos.io/scheduler-zone"]
            constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_es_node, required_scheduler_zone_labels, label_selector_node)
            if not constraints_satisfied:
                print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            # check master topology skew
            if len(pods_es_master) != 0:
                constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_es_master, TOPOLOGY_KEY_RACK, label_selector_master)
                if not constraints_satisfied:
                    print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

            # check node topology skew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_es_node, TOPOLOGY_KEY_RACK, label_selector_node)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

    print(f"Info: check es topology finished")


def get_es_instance():
    # [
    #     {
    #         "namespace": "tpaas-es",
    #         "instance_name": "tpaas-es",
    #     },
    #     {
    #         "namespace": "tpaas-es",
    #         "instance_name": "digger-tpaas-es",
    #     },
    #     {
    #         "namespace": "tpaas-es",
    #         "instance_name": "es-biz",
    #     },
    #     {
    #         "namespace": "tpaas-es",
    #         "instance_name": "es-sgm",
    #     },
    #     {
    #         "namespace": "tpaas-es",
    #         "instance_name": "stardb-tpaas-es",
    #     }]
    instances = []
    kafka_list = get_cr_by_crd_name("elasticsearches.es.jdcloud.com")
    for kafka in kafka_list:
        instance_name = kafka.get("metadata", {}).get("name", "")
        instance_namespace = kafka.get("metadata", {}).get("namespace", "")

        instances.append({
            "namespace": instance_namespace,
            "instance_name": instance_name
        })
    return instances


def check_etcd_topology():
    print(f"Info: check etcd topology started")
    instances = get_etcd_instance()
    for instance in instances:
        namespace = instance.get("namespace")
        instance_name = instance.get("instance_name")
        print(f"Info: check etcd {instance_name} topology started")

        label_selector_etcd_data = f"app.kubernetes.io/name=etcd-cluster,app.kubernetes.io/component=etcd-cluster,app.kubernetes.io/instance={instance_name}"
        pods_etcd_data = get_pods_with_labels(label_selector_etcd_data, namespace)
        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            # check etcd data topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_etcd_data, TOPOLOGY_KEY_ZONE, label_selector_etcd_data)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            # check etcd data topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_etcd_data, TOPOLOGY_KEY_RACK, label_selector_etcd_data)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

    print(f"Info: check etcd topology finished")


def get_etcd_instance():
    # [
    #     {
    #         "namespace": "tpaas-etcd",
    #         "instance_name": "tpaas-etcd"
    #     },
    #     {
    #         "namespace": "hips-etcd",
    #         "instance_name": "hips-etcd"
    #     }]
    instances = []
    kafka_list = get_cr_by_crd_name("etcdclusters.middleware.jdcloud.com")
    for kafka in kafka_list:
        instance_name = kafka.get("metadata", {}).get("name", "")
        instance_namespace = kafka.get("metadata", {}).get("namespace", "")

        instances.append({
            "namespace": instance_namespace,
            "instance_name": instance_name
        })
    return instances


def check_zookeeper_topology():
    print(f"Info: check zookeeper topology started")
    instances = get_zookeeper_instance()
    for instance in instances:
        namespace = instance.get("namespace")
        instance_name = instance.get("instance_name")
        print(f"Info: check zookeeper {instance_name} topology started")

        label_selector_zookeeper = f"app.kubernetes.io/name=zookeeper-cluster,app.kubernetes.io/component=zk,app.kubernetes.io/instance={instance_name}"
        pods_zookeeper = get_pods_with_labels(label_selector_zookeeper, namespace)
        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            # check zookeeper topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_zookeeper, TOPOLOGY_KEY_ZONE, label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            # check zookeeper topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_zookeeper, TOPOLOGY_KEY_RACK, label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

    print(f"Info: check zookeeper topology finished")


def get_zookeeper_instance():
    # [
    #     {
    #         "namespace": "tpaas-zk",
    #         "instance_name": "tpaas-zookeeper"
    #     }]
    instances = []
    kafka_list = get_cr_by_crd_name("zookeeperclusters.middleware.jdcloud.com")
    for kafka in kafka_list:
        instance_name = kafka.get("metadata", {}).get("name", "")
        instance_namespace = kafka.get("metadata", {}).get("namespace", "")

        instances.append({
            "namespace": instance_namespace,
            "instance_name": instance_name
        })
    return instances


def check_mysql_topology():
    print(f"Info: check mysql topology started")
    instances = get_mysql_instance()
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

        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            # master、replica分布在不同AZ
            constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_mysql_master, pods_mysql_replica, TOPOLOGY_KEY_ZONE)
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

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            # 所有节点不能在同一rack
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_mysql_all, TOPOLOGY_KEY_RACK, label_selector_all)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

    print(f"Info: check mysql topology finished")


def get_mysql_instance():
    # [
    #     {
    #         "namespace": "mysql",
    #         "instance_name": "mysql-cluster",
    #     },
    #     {
    #         "namespace": "mysql",
    #         "instance_name": "digger-mysql-cluster",
    #     }]
    instances = []
    kafka_list = get_cr_by_crd_name("mysqlclusters.mysql.presslabs.org")
    for kafka in kafka_list:
        instance_name = kafka.get("metadata", {}).get("name", "")
        instance_namespace = kafka.get("metadata", {}).get("namespace", "")

        instances.append({
            "namespace": instance_namespace,
            "instance_name": instance_name
        })
    return instances


def check_postgresql_topology():
    print(f"Info: check postgresql topology started")
    instances = get_postgresql_instance()
    for instance in instances:
        # role: master   role: master
        namespace = instance.get("namespace")
        instance_name = instance.get("instance_name")
        print(f"Info: check postgresql {instance_name} topology started")
        label_selector_all = f"app.kubernetes.io/name=postgres,app.kubernetes.io/instance={instance_name}"
        label_selector_master = f"{label_selector_all},role=master"
        label_selector_node = f"{label_selector_all},role=replica"
        pods_postgresql_all = get_pods_with_labels(label_selector_all, namespace)
        pods_postgresql_master = get_pods_with_labels(label_selector_master, namespace)
        pods_postgresql_replica = get_pods_with_labels(label_selector_node, namespace)

        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            # master、replica分布在不同AZ
            constraints_satisfied, error_info, error_info2, topology_key = check_topology_not_intersection_constraints(pods_postgresql_master, pods_postgresql_replica, TOPOLOGY_KEY_ZONE)
            if not constraints_satisfied:
                print(f"Error: Topology intersection constraint violation! {error_info}. {error_info2}. topology_key: {topology_key}")

            # master节点必须位于非仲裁区
            required_scheduler_zone_labels = ["topology.jdos.io/scheduler-zone"]
            constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_postgresql_master, required_scheduler_zone_labels, label_selector_master)
            if not constraints_satisfied:
                print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

            # replica必须位于非仲裁区
            constraints_satisfied, error_info, required_labels_info, selector_info = check_node_required_labels_constraints(pods_postgresql_replica, required_scheduler_zone_labels, label_selector_node)
            if not constraints_satisfied:
                print(f"Error: Node labels constraint violation! {error_info} contains required label {required_labels_info}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            # 所有节点不能在同一rack
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_postgresql_all, TOPOLOGY_KEY_RACK, label_selector_all)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

    print(f"Info: check postgresql topology finished")


def get_postgresql_instance():
    instances = []
    kafka_list = get_cr_by_crd_name("pgclusters.crunchydata.com")
    for kafka in kafka_list:
        instance_name = kafka.get("metadata", {}).get("name", "")
        instance_namespace = kafka.get("metadata", {}).get("namespace", "")

        instances.append({
            "namespace": instance_namespace,
            "instance_name": instance_name
        })
    return instances


def check_mongodb_topology():
    print(f"Info: check mongodb topology started")
    instances = get_mongodb_instance()
    for instance in instances:
        namespace = instance.get("namespace")
        instance_name = instance.get("instance_name")
        mongodb_cluster = get_cr_by_name("perconaservermongodbs.psmdb.percona.com", instance_name, namespace)
        if mongodb_cluster is None or mongodb_cluster == {}:
            print(f"Error: get perconaservermongodb {instance_name} failed")
            return

        # 获取mongodb集群类型
        mongodb_sharding_cfg = mongodb_cluster.get("spec", {}).get("sharding", {})
        mongodb_type = "sharding"
        # 如果sharding配置为空 或 sharding.enabled=false, 则表示副本组模式
        if mongodb_sharding_cfg == {} or mongodb_sharding_cfg.get("enabled") is False:
            mongodb_type = "replication"

        print(f"Info: check mongodb {instance_name} topology started, mongodb_type: {mongodb_type}")

        # 集群下涉及的replica_sets
        replica_sets = mongodb_cluster.get("spec", {}).get("replsets", [])
        if mongodb_type == "replication":
            check_mongodb_replication_topology(instance, replica_sets)
        elif mongodb_type == "sharding":
            check_mongodb_sharding_topology(instance, replica_sets)
        else:
            print(f"Error: mongodb {instance_name} 's mongodb_type is None")

    print(f"Info: check mongodb topology finished")


def check_mongodb_replication_topology(instance, replica_sets):
    namespace = instance.get("namespace")
    instance_name = instance.get("instance_name")
    label_selector_mongodb = f"app.kubernetes.io/name=mongodb,app.kubernetes.io/instance={instance_name}"
    if len(replica_sets) == 0:
        print(f"Error: mongodb {instance_name} in {namespace} 's replsets is empty")

    # 理论上副本组模式只有一个副本组
    for replica_set in replica_sets:
        replica_set_name = replica_set.get("name", "")
        label_selector_replica_set = label_selector_mongodb + f",app.kubernetes.io/replset={replica_set_name}"
        pods_replica_set = get_pods_with_labels(label_selector_replica_set, namespace)

        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            # check mongod topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_replica_set, TOPOLOGY_KEY_ZONE, label_selector_replica_set)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            # 所有节点不能在同一rack
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_replica_set, TOPOLOGY_KEY_RACK, label_selector_replica_set)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")


def check_mongodb_sharding_topology(instance, replica_sets):
    namespace = instance.get("namespace")
    instance_name = instance.get("instance_name")
    label_selector_mongodb = f"app.kubernetes.io/name=mongodb,app.kubernetes.io/instance={instance_name}"
    if len(replica_sets) == 0:
        print(f"Error: mongodb {instance_name} in {namespace} 's replsets is empty")

    """
    检查mongos拓扑
    """
    label_selector_mongos = label_selector_mongodb + f",app.kubernetes.io/component=mongos"
    pods_mongos = get_pods_with_labels(label_selector_mongos, namespace)

    if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
        # check mongod topology maxSkew
        constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_mongos, TOPOLOGY_KEY_ZONE, label_selector_mongos)
        if not constraints_satisfied:
            print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

    if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
        # 所有节点不能在同一rack
        constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_mongos, TOPOLOGY_KEY_RACK, label_selector_mongos)
        if not constraints_satisfied:
            print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")


    """
    检查replica_set拓扑（configserver也是一个replica_set）
    """
    for replica_set in replica_sets:
        replica_set_name = replica_set.get("name", "")
        label_selector_replica_set = label_selector_mongodb + f",app.kubernetes.io/replset={replica_set_name}"
        pods_replica_set = get_pods_with_labels(label_selector_replica_set, namespace)

        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            # check mongod topology maxSkew
            constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_replica_set, TOPOLOGY_KEY_ZONE, label_selector_replica_set)
            if not constraints_satisfied:
                print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            # 所有节点不能在同一rack
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_replica_set, TOPOLOGY_KEY_RACK, label_selector_replica_set)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")


def get_mongodb_instance():
    # [
    #     {
    #         "namespace": "mongo-cvessel",
    #         "instance_name": "mongo-cvessel"
    #     }]
    instances = []
    kafka_list = get_cr_by_crd_name("perconaservermongodbs.psmdb.percona.com")
    for kafka in kafka_list:
        instance_name = kafka.get("metadata", {}).get("name", "")
        instance_namespace = kafka.get("metadata", {}).get("namespace", "")

        instances.append({
            "namespace": instance_namespace,
            "instance_name": instance_name
        })
    return instances


def check_clickhouse_topology():
    print(f"Info: check clickhouse topology started")
    instances = get_clickhouse_instance()
    for instance in instances:
        # app.kubernetes.io/component: cluster_clickhouse
        # clickhouse.altinity.com/shard: "0"
        # redis.jdcloud.com/shard=shard-0
        namespace = instance.get("namespace")
        instance_name = instance.get("instance_name")
        print(f"Info: check clickhouse {instance_name} topology started")

        label_selector_clickhouse = f"app.kubernetes.io/name=clickhouse,app.kubernetes.io/component=cluster_clickhouse,app.kubernetes.io/instance={instance_name}"
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
            if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
                # ck不分主从，同一shard在zone上均衡分布

                constraints_satisfied, error_info, constraint_topology_key, selector_info = check_topology_skew_constraints(pods_clickhouse_shard_x, TOPOLOGY_KEY_ZONE, label_selector_shard_x)
                if not constraints_satisfied:
                    print(f"Error: Topology skew constraint violation! {error_info}. constraint_topology_key: {constraint_topology_key}.Label Selector: {selector_info}")

            if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
                # 所有节点不能在同一rack
                constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_clickhouse_shard_x, TOPOLOGY_KEY_RACK, label_selector_shard_x)
                if not constraints_satisfied:
                    print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

        # 检查zookeeper拓扑分布
        label_selector_zookeeper = f"app.kubernetes.io/name=clickhouse,app.kubernetes.io/component=cluster_zk,app.kubernetes.io/instance={instance_name}"
        pods_clickhouse_zookeeper = get_pods_with_labels(label_selector_zookeeper, namespace)
        if HA_TOPOLOGY_LEVEL == ZONE_LEVEL:
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_clickhouse_zookeeper, TOPOLOGY_KEY_ZONE, label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

        if HA_TOPOLOGY_LEVEL == RACK_LEVEL:
            constraints_satisfied, constraint_topology_key, error_info, selector_info = check_topology_constraints(pods_clickhouse_zookeeper, TOPOLOGY_KEY_RACK, label_selector_zookeeper)
            if not constraints_satisfied:
                print(f"Error: {constraint_topology_key} constraint violation! {error_info}. Label Selector: {selector_info}")

    print(f"Info: check clickhouse topology finished")


def get_clickhouse_instance():
    # [
    #     {
    #         "namespace": "ck-csa",
    #         "instance_name": "ck-csa"
    #     },
    #     {
    #         "namespace": "ck-themis",
    #         "instance_name": "ck-themis"
    #     }]
    instances = []
    kafka_list = get_cr_by_crd_name("clickhouseinstallations.clickhouse.altinity.com")
    for kafka in kafka_list:
        instance_name = kafka.get("metadata", {}).get("name", "")
        instance_namespace = kafka.get("metadata", {}).get("namespace", "")

        instances.append({
            "namespace": instance_namespace,
            "instance_name": instance_name
        })
    return instances


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A script with command line arguments.')
    parser.add_argument('-l', '--ha-level', type=str, help='定义更可用级别, 取值: zone、rack')
    parser.add_argument('-s', '--paas-scope', type=str, help='paas组件范围, 取值: all、tenant、runtime, 默认为all')

    args = parser.parse_args()

    # 高可用级别
    HA_TOPOLOGY_LEVEL = args.ha_level
    if HA_TOPOLOGY_LEVEL not in HA_TOPOLOGY_LEVEL_LIST:
        print(f"Error: the passed-in parameter ha-level [{HA_TOPOLOGY_LEVEL}] is invalid, The supported values are {HA_TOPOLOGY_LEVEL_LIST}")
        exit(1)

    # paas组件范围
    if args.paas_scope is not None:
        PAAS_SCOPE = args.paas_scope
        if PAAS_SCOPE not in PAAS_SCOPE_LIST:
            print(f"Error: the passed-in parameter paas-scope [{PAAS_SCOPE}] is invalid, The supported values are {PAAS_SCOPE_LIST}")
            exit(1)

    # 检查kafka topology
    check_kafka_topology()

    # 检查redis topology
    check_redis_topology()

    # 检查es topology
    check_es_topology()

    # 检查etcd topology
    check_etcd_topology()

    # 检查zookeeper topology
    check_zookeeper_topology()

    # 检查mysql topology
    check_mysql_topology()

    # 检查postgresql topology
    check_postgresql_topology()

    # 检查mongodb topology
    check_mongodb_topology()

    # 检查clickhouse topology
    check_clickhouse_topology()
