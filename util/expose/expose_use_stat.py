import argparse
import array
import concurrent
import json
import logging
import subprocess
import sys
import tempfile
import yaml
import concurrent.futures
from collections import defaultdict

"""
全局变量
"""
EXECUTE_MODE_CV_IN_CLUSTER = "cv-in-cluster"
EXECUTE_MODE_CV_JVESCTL = "cv-jvesctl"
EXECUTE_MODE = EXECUTE_MODE_CV_IN_CLUSTER
DRY_RUN = False
DEBUG = False

class ServiceStat:
    def __init__(self):
        self.use_expose_annotation = "unknown"
        self.use_expose_api = "unknown"
        self.use_custom_domain = "unknown"
        self.use_white_list = "unknown"
        self.use_recycle = "unknown"


"""
全局变量-业务相关
"""
# 创建一个 defaultdict，使用 ServiceStat 类作为默认工厂函数（即class的__init__方法）
SERVICE_STAT_DICT = defaultdict(ServiceStat)
CLUSTER_NETWORK_MODE_DICT = defaultdict(str)
CLUSTER_AUTO_EXPOSE_DICT = defaultdict(bool)
CLUSTER_K8s_CLIENT_DICT = defaultdict()
# 全局变量，用于缓存 CRD 数据
GLOBAL_CACHED_CRD_NAMES = None


def shell(command: str):
    logging.debug("start execute cmd: %s", command)
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        e.stdout = e.stdout.rstrip()
        msg = "failed to execute cmd(%d): %s, stdout: %s" % (e.returncode, e.cmd, e.stdout.decode("utf-8"))
        logging.error(msg)
        raise e
    logging.debug("success executed cmd: %s", command)
    return output


class K8sClient(object):
    def __init__(self, kubeconfig=None):
        self.kubeconfig = kubeconfig
        self.kubeconfig_env = ""
        if kubeconfig:
            self.kubeconfig_env = "KUBECONFIG=" + kubeconfig if kubeconfig else ""

    def get_k8s_resource_items(self, kind, namespace="", option="") -> list:
        k8s_resources = self.get_k8s_resource(kind=kind, namespace=namespace, option=option)
        return k8s_resources.get("items") if k8s_resources.get("items") else []

    def get_k8s_resource(self, kind, namespace="", name="", option="") -> dict:
        cmd = f"get {kind} {name} {option}"
        if namespace:
            if namespace == "all":
                cmd += f" --all-namespaces=true "
            else:
                cmd += f" --namespace={namespace} "
        try:
            result = self.__get_kubectl_output_json(cmd)
        except subprocess.CalledProcessError as e:
            return dict()
        return result

    def get_k8s_resource_yaml(self, kind, namespace="", name="", option="") -> dict:
        cmd = f"get {kind} {name} {option}"
        if namespace:
            if namespace == "all":
                cmd += f" --all-namespaces=true "
            else:
                cmd += f" --namespace={namespace} "
        try:
            result = self.__get_kubectl_output_yaml(cmd)
        except subprocess.CalledProcessError as e:
            return dict()
        return result

    def __get_kubectl_output_yaml(self, kube_command) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            filename = f"{tmp_dir}/k8s_resource.json"
            self.kubectl(f"{kube_command} -oyaml > {filename}")
            with open(filename) as f:
                release_yaml = f.read()
                release = yaml.load(release_yaml, Loader=yaml.FullLoader)
                return release

    def __get_kubectl_output_json(self, kube_command) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            filename = f"{tmp_dir}/k8s_resource.json"
            self.kubectl(f"{kube_command} -ojson > {filename}")
            with open(filename) as f:
                return json.load(f)

    def kubectl(self, parameters):
        shell(self.kubeconfig_env + " kubectl " + parameters)


def get_all_crds_names(k8sClient: K8sClient):
    global GLOBAL_CACHED_CRD_NAMES
    try:
        # 获取所有CRD的JSON数据
        items = k8sClient.get_k8s_resource_items("crds", "all")

        # 缓存数据
        GLOBAL_CACHED_CRD_NAMES = [crd["metadata"]["name"] for crd in items]
    except subprocess.CalledProcessError:
        # 如果命令返回非零状态码，则忽略错误，保持缓存不变
        pass

def check_crd_existence(k8sClient: K8sClient, crd_name: str) -> bool:
    global GLOBAL_CACHED_CRD_NAMES
    if GLOBAL_CACHED_CRD_NAMES is None:
        # 如果缓存为空，则获取所有 CRD 数据
        print(f"Info: GLOBAL_CACHED_CRD_NAMES is None, cached from server")
        get_all_crds_names(k8sClient)

    # 本地过滤，检查是否存在指定名称的 CRD
    exists = crd_name in GLOBAL_CACHED_CRD_NAMES
    return exists

def get_all_services(k8sClient: K8sClient) -> dict:
    items = k8sClient.get_k8s_resource_items("service", "all")
    itemDict = {}
    for item in items:
        name = item["metadata"]["name"]
        itemDict[name] = item
    return itemDict

def get_all_releases(k8sClient: K8sClient) -> dict:
    items = k8sClient.get_k8s_resource_items("releases.jvessel.jdcloud.com", "all")
    itemDict = {}
    for item in items:
        name = item["metadata"]["name"]
        itemDict[name] = item
    return itemDict

def get_release(k8sClient: K8sClient, namespace: str, name: str) -> dict:
    item = k8sClient.get_k8s_resource(kind="releases.jvessel.jdcloud.com", namespace=namespace, name=name)
    return item

def get_all_exposes(k8sClient: K8sClient) -> dict:
    items = k8sClient.get_k8s_resource_items("exposes.dlb.jdt.com", "all")
    itemDict = {}
    for item in items:
        name = item["metadata"]["name"]
        itemDict[name] = item
    return itemDict

def get_configmap(k8sClient: K8sClient, namespace: str, name: str) -> dict:
    item = k8sClient.get_k8s_resource(kind="configmap", namespace=namespace, name=name)
    return item


def get_service_stat(service_code: str):
    serviceStat = SERVICE_STAT_DICT.get(service_code)
    if not serviceStat:
        serviceStat = ServiceStat()
        SERVICE_STAT_DICT.update({service_code: serviceStat})
    return serviceStat

def stat_f_service(k8sClient: K8sClient, clusterId: str, serviceName: str, service: dict):
    serviceAnnotations = service["metadata"].get("annotations")
    if serviceAnnotations:
        annotationsExpose = serviceAnnotations.get("jvessel.jdcloud.com/expose")
        if annotationsExpose:
            serviceLabels = service["metadata"].get("labels")
            if serviceLabels:
                releaseName = serviceLabels.get("app.kubernetes.io/instance")
                if releaseName:
                    release = get_release(k8sClient, service["metadata"]["namespace"], releaseName)
                    # service对应的release存在
                    if release:
                        serviceCode = release["spec"]["serviceMeta"]["serviceCode"]
                        get_service_stat(serviceCode).use_expose_annotation = "yes"
            else:
                logging.info(f"[{clusterId}] service [{serviceName}] didn't have labels")
    else:
        logging.info(f"[{clusterId}] service [{serviceName}] didn't have annotations")

def stat_f1(k8sClient: K8sClient, clusterId: str, releaseName: str, release: dict):
    serviceCode = release["spec"]["serviceMeta"]["serviceCode"]
    # 判断是否使用了白名单功能
    whiteListArr = release["spec"]["serviceMeta"].get("whiteList")
    if len(whiteListArr) > 1 or whiteListArr[0] != "0.0.0.0/0":
        logging.info(f"[{clusterId}] release [{releaseName}] use whiteList")
        get_service_stat(serviceCode).use_white_list = "yes"

    # 判断是否使用了自定义域名
    customDomains = release["spec"]["serviceMeta"].get("customDomains")
    if customDomains and len(customDomains) > 0:
        logging.info(f"[{clusterId}] release [{releaseName}] use customDomains")
        get_service_stat(serviceCode).use_custom_domain = "yes"

    # 判断是否使用了回收站功能
    suspended = release["spec"]["serviceMeta"].get("suspended")
    if suspended is not None:
        logging.info(f"[{clusterId}] release [{releaseName}] use recycle")
        get_service_stat(serviceCode).use_recycle = "yes"


def stat_f2(k8sClient: K8sClient, clusterId: str, exposeName: str, expose: dict):
    exposeLabels = expose["metadata"].get("labels")
    if exposeLabels:
        releaseName = expose["metadata"]["labels"].get("app.kubernetes.io/instance")
        if releaseName:
            release = get_release(k8sClient, expose["metadata"]["namespace"], releaseName)
            # expose对应的release存在
            if release:
                serviceCode = release["spec"]["serviceMeta"]["serviceCode"]
                if get_service_stat(serviceCode).use_expose_annotation is None or get_service_stat(serviceCode).use_expose_annotation == "unknown":
                    get_service_stat(serviceCode).use_expose_api = "yes"
    else:
        logging.info(f"[{clusterId}] expose [{exposeName}] didn't have labels")

def stat_cvessel_cluster_service(k8sClient: K8sClient, clusterId: str):
    logging.info(f"[{clusterId}]开始统计service...")
    cniMode = CLUSTER_NETWORK_MODE_DICT.get(clusterId)
    # 网络拉平环境, 按service是否有注解[jvessel.jdcloud.com/expose]设置
    if cniMode is not None and cniMode == "vlan":
        allServiceDict = get_all_services(k8sClient)
        # with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        #     futures = [executor.submit(stat_f_service, k8sClient=k8sClient, clusterId=clusterId, serviceName=serviceName, service=service) for
        #                serviceName, service in allServiceDict.items()]
        #     results = [f.result() for f in concurrent.futures.as_completed(futures)]
        for serviceName, service in allServiceDict.items():
            stat_f_service(k8sClient = k8sClient, clusterId = clusterId, serviceName = serviceName, service = service)

def stat_cvessel_cluster_release(k8sClient: K8sClient, clusterId: str):
    networkMode = CLUSTER_NETWORK_MODE_DICT.get(clusterId)
    if check_crd_existence(k8sClient=k8sClient, crd_name="releases.jvessel.jdcloud.com"):
        allReleaseDict = get_all_releases(k8sClient)
        # with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        #     futures = [executor.submit(stat_f1, k8sClient=k8sClient, clusterId=clusterId, releaseName=releaseName, release=release) for
        #                releaseName, release in allReleaseDict.items()]
        #     results = [f.result() for f in concurrent.futures.as_completed(futures)]
        for releaseName, release in allReleaseDict.items():
            stat_f1(k8sClient = k8sClient, clusterId = clusterId, releaseName = releaseName, release = release)
    else:
        logging.warning(f"[{clusterId}] 未找到release crd")


def stat_cvessel_cluster_expose(k8sClient: K8sClient, clusterId: str):
    networkMode = CLUSTER_NETWORK_MODE_DICT.get(clusterId)
    if networkMode == "vlan":
        logging.info(f"[{clusterId}] 网络拉平模式: 忽略处理expose cr")
        return

    # 判断是否使用了服务暴露
    if check_crd_existence(k8sClient=k8sClient, crd_name="exposes.dlb.jdt.com"):
        allExposeDict = get_all_exposes(k8sClient)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            # futures = [executor.submit(stat_f2, k8sClient=k8sClient, clusterId=clusterId, exposeName=exposeName, expose=expose) for
            #            exposeName, expose in allExposeDict.items()]
            # results = [f.result() for f in concurrent.futures.as_completed(futures)]
            for exposeName, expose in allExposeDict.items():
                stat_f2(k8sClient = k8sClient, clusterId = clusterId, exposeName = exposeName, expose = expose)
    else:
        logging.warning(f"[{clusterId}] 未找到expose crd")


def stat_cvessel_cluster_common(clusterId: str) -> K8sClient:
    if clusterId is None or clusterId == "":
        k8sClient = K8sClient()
    else:
        kubeConfigFilePath = f"/tmp/config_{clusterId}"
        cmdSetKubeConfig = f"jvesctl cluster config -i {clusterId} -f {kubeConfigFilePath}"
        shell(cmdSetKubeConfig)
        k8sClient = K8sClient(kubeconfig=kubeConfigFilePath)

    # 获取networkSolution配置
    networkSolution = k8sClient.get_k8s_resource(kind="networksolution", namespace="jd-tpaas", name="jvessel-" + clusterId)
    if networkSolution:
        cniMode = networkSolution["spec"]["clusterNetworkBaseInfo"].get("cniMode")
        logging.info(f"[{clusterId}] 网络模式: cniMode={cniMode}")
        if cniMode is not None and (cniMode == "vlan"):
            CLUSTER_NETWORK_MODE_DICT.update({clusterId: cniMode})
            logging.info(f"[{clusterId}] 网络拉平模式: cniMode={cniMode}")
    else:
        logging.warning(f"[{clusterId}] 未配置networkSolution: {clusterId}")

    # 获取sys_info configmap
    cmSysInfo = k8sClient.get_k8s_resource(kind="configmap", namespace="jd-tpaas", name="sys-info")
    autoExpose = False
    if cmSysInfo:
        auto_expose = cmSysInfo["data"].get("auto_expose")
        if auto_expose and auto_expose == "open":
            autoExpose = True
            CLUSTER_AUTO_EXPOSE_DICT.update({clusterId: autoExpose})
        else:
            logging.info(f"[{clusterId}] 未配置auto_expose")

    cniMode = CLUSTER_NETWORK_MODE_DICT.get(clusterId)
    # 非网络拉平环境 & 自动暴露场景, 按auto_expose_service_code设置use_expose_annotation
    if cniMode is None or (cniMode != "vlan"):
        if autoExpose:
            auto_expose_service_codes = cmSysInfo["data"].get("auto_expose_service_code")
            if auto_expose_service_codes:
                if auto_expose_service_codes.startswith('['):
                    service_code_list = auto_expose_service_codes.strip("[]").split(", ")
                else:
                    service_code_list = yaml.load(auto_expose_service_codes, Loader=yaml.FullLoader)
                if len(service_code_list) > 0:
                    for serviceCode in service_code_list:
                        get_service_stat(serviceCode).use_expose_annotation = "yes"

    # 设置集群的k8sClient
    CLUSTER_K8s_CLIENT_DICT.update({clusterId: k8sClient})

    # 缓存所有crds
    get_all_crds_names(k8sClient=k8sClient)
    return k8sClient

def stat_cvessel_others(clusterId: str):
    futures = []
    logging.info(f"[{clusterId}]开始统计release...")
    # futures.append(global_executor.submit(stat_cvessel_cluster_release, k8sClient=CLUSTER_K8s_CLIENT_DICT.get(clusterId), clusterId=clusterId))
    stat_cvessel_cluster_release(k8sClient = CLUSTER_K8s_CLIENT_DICT.get(clusterId), clusterId = clusterId)

    logging.info(f"[{clusterId}]开始统计expose...")
    # futures.append(global_executor.submit(stat_cvessel_cluster_expose, k8sClient=CLUSTER_K8s_CLIENT_DICT.get(clusterId), clusterId=clusterId))
    #results = [f.result() for f in concurrent.futures.as_completed(futures)]
    stat_cvessel_cluster_expose(k8sClient = CLUSTER_K8s_CLIENT_DICT.get(clusterId), clusterId = clusterId)


def stat_cvessel(clusterIds: any):
    for clusterId in clusterIds:
        logging.info(f"[{clusterId}]开始统计...")
        stat_cvessel_cluster_common(clusterId=clusterId)

    for clusterId in clusterIds:
        cniMode = CLUSTER_NETWORK_MODE_DICT.get(clusterId)
        # 网络拉平环境, 按service是否有注解[jvessel.jdcloud.com/expose]设置
        if cniMode is not None and cniMode == "vlan":
            logging.info(f"[{clusterId}]网络拉平环境, 暂时忽略service上的annotation")
            # stat_cvessel_cluster_service(k8sClient=CLUSTER_K8s_CLIENT_DICT.get(clusterId), clusterId=clusterId)

    # 在全局范围内定义线程池
    # global_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    # futures = [global_executor.submit(stat_cvessel_others, clusterId=clusterId) for clusterId in clusterIds]
    # results = [f.result() for f in concurrent.futures.as_completed(futures)]
    for clusterId in clusterIds:
        stat_cvessel_others(clusterId = clusterId)

    for service_code in SERVICE_STAT_DICT:
        service_stat: ServiceStat = SERVICE_STAT_DICT.get(service_code)
        max_length = 25
        logging.info(
            f"service_code: {service_code:<{max_length}} use_expose_annotation: {service_stat.use_expose_annotation:<{max_length}} use_expose_api: {service_stat.use_expose_api:<{max_length}} use_custom_domain: {service_stat.use_custom_domain:<{max_length}} use_white_list: {service_stat.use_white_list:<{max_length}} use_recycle: {service_stat.use_recycle:<{max_length}}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A script with command line arguments.')
    parser.add_argument('-d', '--dry-run', action='store_true', default=True, help='simulate an migrate')
    parser.add_argument('-v', '--debug', action='store_true', default=False, help='debug model')
    parser.add_argument('-m', '--execute-mode', default="cv-in-cluster", help='execute-mode')
    parser.add_argument('-c', '--cluster-id', default='', help='cluster id')
    args = parser.parse_args()
    if args.dry_run is not None:
        DRY_RUN = args.dry_run
    if args.debug is not None:
        DEBUG = args.debug
    if args.execute_mode is not None:
        EXECUTE_MODE = args.execute_mode

    # log level
    log_level = logging.DEBUG if DEBUG else logging.INFO
    log_format = "[%(levelname)s] %(message)s"
    logging.basicConfig(level=log_level, format=log_format)

    if DRY_RUN:
        logging.info("run in DRY_RUN mode")

    # 集群id
    if EXECUTE_MODE == EXECUTE_MODE_CV_IN_CLUSTER:
        stat_cvessel([""])
    elif EXECUTE_MODE == EXECUTE_MODE_CV_JVESCTL:
        clusterIds = args.cluster_id
        if clusterIds is None or clusterIds == "":
            logging.fatal("param cluster-id is required")
            sys.exit(1)
        clusterIds = clusterIds.split(",")
        stat_cvessel(clusterIds)
