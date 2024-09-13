import argparse
import json
import logging
import os
import re
import subprocess
import tempfile

"""
组件对应的应用市场appinstance名称
"""
# 应用市场
STORE_CR_NAMESPACE = "jd-tpaas"
# mysql
APPINSTANCE_DIGGER_MYSQL_CLUSTER = "digger-mysql-cluster"
# es
APPINSTANCE_GLOBAL_ES_CLUSTER = "es-cluster"
APPINSTANCE_DIGGER_ES_CLUSTER = "digger-es-cluster"
APPINSTANCE_BIZ_ES_CLUSTER = "biz-es"
APPINSTANCE_SGM_ES_CLUSTER = "sgm-es"
# kafka
APPINSTANCE_DIGGER_KAFKA_CLUSTER = "digger-kafka-cluster"
# redis
APPINSTANCE_DIGGER_REDIS_CLUSTER = "digger-redis-cluster"
# etcd
APPINSTANCE_HIPS_ETCD_CLUSTER = "hips-etcd"
# clickhouse
APPINSTANCE_CLICKHOUSE_CLUSTER = "clickhouse-cluster"
APPINSTANCE_THEMIS_CK_CLUSTER = "themis-ck"
# 控制面应用
APPINSTANCE_FOUNDATION = "foundation"
APPINSTANCE_SGM = "sgm"
APPINSTANCE_PHEVOS_AGENT = "phevos-agent"
APPINSTANCE_AUDITTRAIL = "audittrail"
APPINSTANCE_HIPS = "hips"
APPINSTANCE_THEMIS = "themis"
APPINSTANCE_CSA = "csa"
APPINSTANCE_NF1 = "nf1"

# 中间件相关变量
PAAS_GLOBAL_ES_CLUSTER_NAME = "tpaas-es"
PAAS_DIGGER_ES_CLUSTER_NAME = "paas-es"
PAAS_SGM_ES_CLUSTER_NAME = "es-sgm"
PAAS_BIZ_ES_CLUSTER_NAME = "es-biz"

"""
全局变量
"""
DRY_RUN = False
DEBUG = False
GLOBAL_CACHED_APPINSTANCE_LIST = None


def main():
    gaia_k8s_client = K8sClient()
    global_config = gaia_k8s_client.get_global_config()

    """更新全局环境变量"""
    global_envs = {
        # es
        "JDOS_ES_CLUSTER_NAME": "tpaas-es",
        "JDOS_ES_TCP_ADDRESS": "tpaas-es-nodes.tpaas-es.svc",
        "JDOS_ES_TCP_PORT": "9300",
        # etcd
        "JDOS_ETCD_ADDRESS": "tpaas-etcd-client.tpaas-etcd.svc",
        "JDOS_ETCD_PORT": "2379",
    }
    gaia_k8s_client.config_global_envs(global_envs)

    """更新产品级变量"""
    # foundation
    upgrade_foundation(gaia_k8s_client)
    # audittrail
    upgrade_audittrail(gaia_k8s_client)
    # sgm
    upgrade_sgm(gaia_k8s_client)
    # hips
    upgrade_hips(gaia_k8s_client)
    # csa
    upgrade_csa(gaia_k8s_client)


def upgrade_foundation(gaia_k8s_client):
    global APPINSTANCE_FOUNDATION
    logging.info("upgrade %s begin...", APPINSTANCE_FOUNDATION)
    if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_FOUNDATION) is False:
        logging.info("%s isn't installed, skip upgrade", APPINSTANCE_FOUNDATION)
        return

    foundation_envs = gaia_k8s_client.get_product_envs(app_id=APPINSTANCE_FOUNDATION)
    # mysql
    paas_mysql_address = foundation_envs.get("PAAS_MYSQL_ADDRESS", "").strip()
    if paas_mysql_address:
        gaia_k8s_client.config_product_envs(app_id=APPINSTANCE_FOUNDATION,
                                            envs=get_mysql_envs(address=foundation_envs.get("PAAS_MYSQL_ADDRESS", ""),
                                                                username=foundation_envs.get("PAAS_MYSQL_USER", ""),
                                                                password=foundation_envs.get("PAAS_MYSQL_PWD", "")))
    else:
        logging.warning("%s 's PAAS_MYSQL_ADDRESS value isn't exist, please check : %s", APPINSTANCE_FOUNDATION, paas_mysql_address)

    # es
    global APPINSTANCE_DIGGER_ES_CLUSTER
    paas_es_address = foundation_envs.get("PAAS_ES_ADDRESS", "").strip()
    paas_es_address_segments = [] if not paas_es_address else paas_es_address.split(":")
    if len(paas_es_address_segments) == 2:
        upgrade_es = True
        # 如果变量引用的是默认的digger-tpaas-es, 并且安装了, 则更新; 否则如果未安装, 则不更新
        if paas_es_address.startswith("digger-tpaas-es-"):
            es_http_address = "digger-tpaas-es-http.tpaas-es.svc"
            if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_DIGGER_ES_CLUSTER) is False:
                upgrade_es = False
                logging.warning("%s 's dependency %s isn't installed, skip upgrade es-dependency, please check it", APPINSTANCE_FOUNDATION, APPINSTANCE_DIGGER_ES_CLUSTER)
        else:
            # 如果不是使用默认的digger-tpaas-es, 说明实施时有特殊处理, 使用实施时指定的
            es_http_address = ""
            logging.warning("%s 's es-dependency isn't supplied by jdock-runtime, please check it", APPINSTANCE_FOUNDATION)
        if upgrade_es:
            # foundation使用的tcp方式
            gaia_k8s_client.config_product_envs(app_id=APPINSTANCE_FOUNDATION,
                                                envs=get_elasticsearch_envs(address=es_http_address,
                                                                            username=foundation_envs.get("PAAS_ES_USERNAME", ""),
                                                                            password=foundation_envs.get("PAAS_ES_PWD", ""),
                                                                            cluster_name=foundation_envs.get("PAAS_ES_CLUSER_NAME", ""),
                                                                            tcp_address=paas_es_address_segments[0]))
    else:
        logging.warning("%s 's PAAS_ES_ADDRESS value isn't correct, should be split with ':' and length is 2, current values is %s", APPINSTANCE_FOUNDATION, paas_es_address)

    # kafka
    paas_kafka_address = foundation_envs.get("PAAS_KAFKA_ADDRESS", "").strip()
    paas_kafka_address_segments = [] if not paas_kafka_address else paas_kafka_address.split(":")
    if len(paas_kafka_address_segments) == 2:
        gaia_k8s_client.config_product_envs(app_id=APPINSTANCE_FOUNDATION,
                                            envs=get_kafka_envs(address=paas_kafka_address_segments[0],))
    else:
        logging.warning("%s 's PAAS_KAFKA_ADDRESS value isn't correct, should be split with ':' and length is 2, current values is %s", APPINSTANCE_FOUNDATION, paas_kafka_address)

    # redis
    paas_redis_address = foundation_envs.get("PAAS_REDIS_ADDRESS", "").strip()
    paas_redis_address_segments = [] if not paas_redis_address else paas_redis_address.split(":")
    if len(paas_redis_address_segments) == 2:
        gaia_k8s_client.config_product_envs(app_id=APPINSTANCE_FOUNDATION,
                                            envs=get_redis_envs(address=paas_redis_address_segments[0],
                                                                password=foundation_envs.get("PAAS_REDIS_PWD", ""),
                                                                proxy_address="digger-rediscluster-proxy-svc.redis.svc",))
    else:
        logging.warning("%s 's PAAS_REDIS_ADDRESS value isn't correct, should be split with ':' and length is 2, current values is %s", APPINSTANCE_FOUNDATION, paas_redis_address)


def upgrade_audittrail(gaia_k8s_client):
    global APPINSTANCE_AUDITTRAIL
    logging.info("upgrade %s begin...", APPINSTANCE_AUDITTRAIL)
    if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_AUDITTRAIL) is False:
        logging.info("%s isn't installed, skip upgrade", APPINSTANCE_AUDITTRAIL)
        return

    appinstance_envs = gaia_k8s_client.get_product_envs(app_id=APPINSTANCE_AUDITTRAIL)
    # es
    global APPINSTANCE_BIZ_ES_CLUSTER
    paas_es_address = appinstance_envs.get("PAAS_ES_ADDRESS", "").strip()
    if not paas_es_address:
        logging.warning("%s 's PAAS_ES_ADDRESS value is empty, skip upgrade es-dependency, please check it", APPINSTANCE_AUDITTRAIL)
    else:
        paas_es_address_segments = [] if not paas_es_address else paas_es_address.split(":")
        if len(paas_es_address_segments) == 2:
            upgrade_es = True
            # 如果变量引用的是默认的es-biz, 并且安装了, 则更新; 否则如果未安装, 则不更新
            if paas_es_address.startswith("es-biz-"):
                es_tcp_address = "es-biz-nodes.tpaas-es.svc"
                if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_BIZ_ES_CLUSTER) is False:
                    upgrade_es = False
                    logging.warning("%s 's dependency %s isn't installed, skip upgrade es-dependency, please check it", APPINSTANCE_AUDITTRAIL, APPINSTANCE_BIZ_ES_CLUSTER)
            else:
                # 如果不是使用默认的es-biz, 说明实施时有特殊处理, 使用实施时指定的
                es_tcp_address = ""
                logging.warning("%s 's es-dependency isn't supplied by jdock-runtime, please check it", APPINSTANCE_AUDITTRAIL)
            if upgrade_es:
                gaia_k8s_client.config_product_envs(app_id=APPINSTANCE_AUDITTRAIL,
                                                    envs=get_elasticsearch_envs(address=paas_es_address_segments[0],
                                                                                username=appinstance_envs.get("PAAS_ES_USERNAME", ""),
                                                                                password=appinstance_envs.get("PAAS_ES_PWD", ""),
                                                                                cluster_name=appinstance_envs.get("PAAS_ES_CLUSER_NAME", ""),
                                                                                tcp_address=es_tcp_address,))
        else:
            logging.warning("%s 's PAAS_ES_ADDRESS value isn't correct, should be split with ':' and length is 2, current values is %s , please check it", APPINSTANCE_AUDITTRAIL, paas_es_address)


def upgrade_sgm(gaia_k8s_client):
    global APPINSTANCE_SGM
    logging.info("upgrade %s begin...", APPINSTANCE_SGM)
    if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_SGM) is False:
        logging.info("%s isn't installed, skip upgrade", APPINSTANCE_SGM)
        return

    appinstance_envs = gaia_k8s_client.get_product_envs(app_id=APPINSTANCE_SGM)
    # es
    global APPINSTANCE_SGM_ES_CLUSTER
    paas_es_address = appinstance_envs.get("PAAS_ES_ADDRESS", "").strip()
    if not paas_es_address:
        logging.warning("%s 's PAAS_ES_ADDRESS value is empty, skip upgrade es-dependency, please check it", APPINSTANCE_SGM)
    else:
        paas_es_address_segments = [] if not paas_es_address else paas_es_address.split(":")
        if len(paas_es_address_segments) == 2:
            upgrade_es = True
            # 如果变量引用的是默认的es-sgm, 并且安装了, 则更新; 否则如果未安装, 则不更新
            if paas_es_address.startswith("es-sgm-"):
                es_tcp_address = "es-sgm-nodes.tpaas-es.svc"
                if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_SGM_ES_CLUSTER) is False:
                    upgrade_es = False
                    logging.warning("%s 's dependency %s isn't installed, skip upgrade es-dependency, please check it", APPINSTANCE_SGM, APPINSTANCE_SGM_ES_CLUSTER)
            else:
                # 如果不是使用默认的es-sgm, 说明实施时有特殊处理
                es_tcp_address = ""
                logging.warning("%s 's es-dependency isn't supplied by jdock-runtime, please check it", APPINSTANCE_SGM)
            if upgrade_es:
                gaia_k8s_client.config_product_envs(app_id=APPINSTANCE_SGM,
                                                    envs=get_elasticsearch_envs(address=paas_es_address_segments[0],
                                                                                username=appinstance_envs.get("PAAS_ES_USERNAME", ""),
                                                                                password=appinstance_envs.get("PAAS_ES_PWD", ""),
                                                                                cluster_name=appinstance_envs.get("PAAS_ES_CLUSER_NAME", ""),
                                                                                tcp_address=es_tcp_address,))
        else:
            logging.warning("%s 's PAAS_ES_ADDRESS value isn't correct, should be split with ':' and length is 2, current values is %s , please check it", APPINSTANCE_SGM, paas_es_address)

    # kafka
    global APPINSTANCE_DIGGER_KAFKA_CLUSTER
    paas_kafka_address = appinstance_envs.get("PAAS_KAFKA_ADDRESS", "").strip()
    if not paas_kafka_address:
        logging.warning("%s 's PAAS_KAFKA_ADDRESS value is empty, skip upgrade kafka-dependency, please check it", APPINSTANCE_SGM)
    else:
        paas_kafka_address_segments = [] if not paas_kafka_address else paas_kafka_address.split(":")
        if len(paas_kafka_address_segments) == 2:
            upgrade_kafka = True
            # 如果变量引用的是默认的digger-kafka, 并且安装了, 则更新; 否则如果未安装, 则不更新
            if paas_kafka_address.startswith("digger-kafka-"):
                if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_DIGGER_KAFKA_CLUSTER) is False:
                    upgrade_kafka = False
                    logging.warning("%s 's dependency %s isn't installed, skip upgrade kafka-dependency, please check it", APPINSTANCE_SGM, APPINSTANCE_DIGGER_KAFKA_CLUSTER)
            else:
                # 如果不是使用默认的digger-kafka, 说明实施时有特殊处理, 使用实施时指定的
                logging.warning("%s 's kafka-dependency isn't supplied by jdock-runtime, please check it", APPINSTANCE_SGM)
            if upgrade_kafka:
                gaia_k8s_client.config_product_envs(app_id=APPINSTANCE_SGM,
                                                    envs=get_kafka_envs(address=paas_kafka_address_segments[0],))
        else:
            logging.warning("%s 's PAAS_KAFKA_ADDRESS value isn't correct, should be split with ':' and length is 2, current values is %s , please check it", APPINSTANCE_SGM, paas_kafka_address)


def upgrade_hips(gaia_k8s_client):
    global APPINSTANCE_HIPS
    logging.info("upgrade %s begin...", APPINSTANCE_HIPS)
    if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_HIPS) is False:
        logging.info("%s isn't installed, skip upgrade", APPINSTANCE_HIPS)
        return

    appinstance_envs = gaia_k8s_client.get_product_envs(app_id=APPINSTANCE_HIPS)
    # etcd
    global APPINSTANCE_HIPS_ETCD_CLUSTER
    paas_etcd_address = appinstance_envs.get("HIPS_ETCD_HOST", "").strip()
    if not paas_etcd_address:
        logging.warning("%s 's HIPS_ETCD_HOST value is empty, skip upgrade etcd-dependency, please check it", APPINSTANCE_HIPS)
    else:
        protocol, address, port = extract_http_protocol_address_port(paas_etcd_address)
        if protocol and address and port:
            upgrade_etcd = True
            # 如果变量引用的是默认的hips-etcd, 并且安装了, 则更新; 否则如果未安装, 则不更新
            if "hips-etcd-client" in paas_etcd_address:
                if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_HIPS_ETCD_CLUSTER) is False:
                    upgrade_etcd = False
                    logging.warning("%s 's dependency %s isn't installed, skip upgrade etcd-dependency, please check it", APPINSTANCE_HIPS, APPINSTANCE_HIPS_ETCD_CLUSTER)
            else:
                # 如果不是使用默认的hips-etcd, 说明实施时有特殊处理, 使用实施时指定的
                logging.warning("%s 's etcd-dependency isn't supplied by jdock-runtime, please check it", APPINSTANCE_HIPS)
            if upgrade_etcd:
                gaia_k8s_client.config_product_envs(app_id=APPINSTANCE_HIPS,
                                                    envs=get_etcd_envs(address=address,
                                                                       port=port))
        else:
            logging.warning("%s 's HIPS_ETCD_HOST value isn't correct, should be match http url patten, current values is %s , please check it", APPINSTANCE_HIPS, paas_etcd_address)


def upgrade_csa(gaia_k8s_client):
    global APPINSTANCE_CSA
    logging.info("upgrade %s begin...", APPINSTANCE_CSA)
    if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_CSA) is False:
        logging.info("%s isn't installed, skip upgrade", APPINSTANCE_CSA)
        return

    appinstance_envs = gaia_k8s_client.get_product_envs(app_id=APPINSTANCE_CSA)
    # clickhouse
    global APPINSTANCE_CLICKHOUSE_CLUSTER
    paas_clickhouse_address = appinstance_envs.get("CSA_CK_SVC", "").strip()
    if not paas_clickhouse_address:
        logging.warning("%s 's CSA_CK_SVC value is empty, skip upgrade clickhouse-dependency, please check it", APPINSTANCE_CSA)
    else:
        upgrade_clickhouse = True
        # 如果变量引用的是默认的ck-csa, 并且安装了, 则更新; 否则如果未安装, 则不更新
        if "ck-csa" in paas_clickhouse_address:
            if check_appinstance_existence(gaia_k8s_client, appinstance_name=APPINSTANCE_CLICKHOUSE_CLUSTER) is False:
                upgrade_clickhouse = False
                logging.warning("%s 's dependency %s isn't installed, skip upgrade clickhouse-dependency, please check it", APPINSTANCE_CSA, APPINSTANCE_CLICKHOUSE_CLUSTER)
        else:
            # 如果不是使用默认的ck-csa, 说明实施时有特殊处理, 使用实施时指定的
            logging.warning("%s 's clickhouse-dependency isn't supplied by jdock-runtime, please check it", APPINSTANCE_CSA)
        if upgrade_clickhouse:
            gaia_k8s_client.config_product_envs(app_id=APPINSTANCE_CSA,
                                                envs=get_clickhouse_envs(address=appinstance_envs.get("CSA_CK_SVC", ""),
                                                                         username=appinstance_envs.get("CSA_CK_USER", ""),
                                                                         password=appinstance_envs.get("CSA_CK_PASSWD", ""),
                                                                         http_port=appinstance_envs.get("CSA_CK_HTTP_PORT", ""),
                                                                         tcp_port=appinstance_envs.get("CSA_CK_TCP_PORT", ""),))


def check_appinstance_existence(k8s_client, appinstance_name: str) -> bool:
    global GLOBAL_CACHED_APPINSTANCE_LIST
    if GLOBAL_CACHED_APPINSTANCE_LIST is None:
        # 如果缓存为空，则获取所有 CRD 数据
        print(f"Info: GLOBAL_CACHED_APPINSTANCE_LIST is None, cached from server")
        GLOBAL_CACHED_APPINSTANCE_LIST = k8s_client.get_appinstances()

    # 本地过滤，检查是否存在指定名称的 CRD
    for appinstance in GLOBAL_CACHED_APPINSTANCE_LIST:
        if appinstance["spec"]["appName"] == appinstance_name:
            return True
    return False


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
        self.kubeconfig_env = "KUBECONFIG=" + kubeconfig if kubeconfig else ""

    def get_appinstances_in_cluster(self, cluster_id: str):
        return [instance for instance in self.get_appinstances() if instance["spec"]["clusterId"] == cluster_id]

    def get_appinstances(self) -> list:
        return self.get_k8s_resource_items("appinstances.store.jdos.com", "jd-tpaas")

    def get_k8s_resource_items(self, kind, namespace="", option="") -> list:
        return self.get_k8s_resource(kind, namespace, option)["items"]

    def get_k8s_resource(self, kind, namespace="", name="", option="") -> dict:
        cmd = f"get {kind} {name} {option}"
        if namespace:
            cmd += f"-n {namespace} "
        return self.__get_kubectl_output_json(cmd)

    def get_jdosconfig(self, name: str) -> dict:
        global STORE_CR_NAMESPACE
        data = self.get_k8s_resource("jdosconfig", STORE_CR_NAMESPACE, name)
        config = {}
        for key, value in data["spec"]["data"].items():
            config[key] = value["value"]
        return config

    def get_jdosconfigs(self) -> dict:
        """ 获取所有环境变量配置 """
        global STORE_CR_NAMESPACE
        items = self.get_k8s_resource_items("jdosconfigs", STORE_CR_NAMESPACE)
        configs = {}
        for item in items:
            name = item["metadata"]["name"]
            envs = {k: v["value"] for k, v in item["spec"]["data"].items()}
            configs[name] = envs
        return configs

    def get_global_config(self) -> dict:
        """ 获取全局环境变量配置 """
        return self.get_jdosconfig("global")

    def config_global_envs(self, envs):
        """ 更新全局环境变量 """
        configs = self.get_jdosconfigs()
        if "global" not in configs:
            # 必然存在, 不存在报错
            raise Exception("global jdosconfig isn't exists")
        else:
            self._update_jdosconfig("global", envs)

    def get_cluster_envs(self, cluster_id: str) -> dict:
        return self.get_jdosconfig(cluster_id)

    def config_cluster_envs(self, cluster_id: str, envs: dict):
        """ 创建或更新集群级环境变量 """
        config_id = f"{cluster_id}"
        configs = self.get_jdosconfigs()
        if config_id not in configs:
            self.__create_jdosconfig(envs, cluster_id=cluster_id)
        else:
            self._update_jdosconfig(config_id, envs)

    def get_product_envs(self, app_id: str) -> dict:
        return self.get_jdosconfig(app_id)

    def config_product_envs(self, app_id: str, envs: dict):
        """ 创建或更新产品级环境变量 """
        config_id = f"{app_id}"
        configs = self.get_jdosconfigs()
        if config_id not in configs:
            self.__create_jdosconfig(envs, app_id)
        else:
            self._update_jdosconfig(config_id, envs)

    def __get_kubectl_output_json(self, kube_command) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            filename = f"{tmp_dir}/k8s_resource.json"
            self.kubectl(f"{kube_command} -ojson > {filename}")
            with open(filename) as f:
                return json.load(f)

    def __create_jdosconfig(self, envs: dict, app_id="", cluster_id=""):
        global STORE_CR_NAMESPACE
        global DRY_RUN
        config_name = "global"
        level = "0"
        labels = {}
        if app_id:
            level = "2"
            config_name = f"{app_id}"
            labels["application"] = app_id
            if cluster_id:
                level = "3"
                config_name = f"{app_id}-{cluster_id}"
                labels["clusterId"] = cluster_id
        elif cluster_id:
            level = "1"
            config_name = f"{cluster_id}"
            labels["clusterId"] = cluster_id
        labels["level"] = level
        config = {
            "apiVersion": "store.jdos.com/v1alpha1",
            "kind": "JdosConfig",
            "metadata": {
                "name": config_name,
                "namespace": STORE_CR_NAMESPACE,
                "labels": labels
            },
            "spec": {
                "level": int(level),
                "clusterId": cluster_id,
                "application": app_id,
                "data": envs_to_jdosconfig_items(envs)
            }
        }

        envs_json_dumps = json.dumps(envs, indent=4)
        if DRY_RUN is True:
            logging.info("--dry-run [create] jdosconfig [%s], envs: %s", config_name, envs_json_dumps)
        else:
            logging.info("[create] jdosconfig [%s], envs: %s", config_name, envs_json_dumps)
            with tempfile.TemporaryDirectory() as tmp_dir:
                filename = os.path.join(tmp_dir, f"{config_name}-jdosconfig.json")
                with open(filename, "w") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                self.kubectl(f"create -f {filename}")

    def _update_jdosconfig(self, name: str, envs: dict):
        global STORE_CR_NAMESPACE
        data = self.get_k8s_resource("jdosconfig", STORE_CR_NAMESPACE, name)
        for key, value in envs_to_jdosconfig_items(envs).items():
            data["spec"]["data"][key] = value

        envs_json_dumps = json.dumps(envs, indent=4)
        if DRY_RUN is True:
            logging.info("--dry-run [update] jdosconfig [%s], envs: %s", name, envs_json_dumps)
        else:
            logging.info("[update] jdosconfig [%s], envs: %s", name, envs_json_dumps)
            with tempfile.TemporaryDirectory() as tmp_dir:
                filename = os.path.join(tmp_dir, data["metadata"]["name"] + "-jdosconfig.json")
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.kubectl(f"apply -f {filename}")

    def kubectl(self, parameters):
        shell(self.kubeconfig_env + " kubectl " + parameters)


def envs_to_jdosconfig_items(envs: dict) -> dict:
    items = {}
    for key, value in envs.items():
        items[key] = {
            "description": "",
            "tag": "",
            "type": "",
            "value": value,
            "visable": True
        }
    return items


def extract_http_protocol_address_port(url):
    # 非空检查
    if not url or url.isspace():
        return None, None, None

    # 更新正则表达式以使端口部分可选
    pattern = r'^(http|https)://([^:/]+)(?::(\d*))?$'
    match = re.match(pattern, url)

    # 如果匹配成功，提取并返回协议、address和port
    # 根据协议设置默认端口
    if match:
        protocol, address, port = match.groups()
        if not port:  # 如果没有提供端口，则根据协议设置默认值
            port = '80' if protocol == 'http' else '443'
        return protocol, address, port
    else:
        return None, None, None


def get_mysql_envs(address: str, username: str, password: str) -> dict:
    return {
        "JDOS_MYSQL_ADDRESS": address,
        "JDOS_MYSQL_PORT": "3306",
        "JDOS_MYSQL_PWD": password,
        "JDOS_MYSQL_USER": username,
    }


def get_redis_envs(address: str, password: str, proxy_address: str) -> dict:
    return {
        "JDOS_REDIS_ADDRESS": address,
        "JDOS_REDIS_PORT": "6379",
        "JDOS_REDIS_PROXY_ADDRESS": proxy_address,
        "JDOS_REDIS_PWD": password,
    }


def get_etcd_envs(address: str, port: str) -> dict:
    return {
        "JDOS_ETCD_ADDRESS": address,
        "JDOS_ETCD_PORT": port,
    }


def get_elasticsearch_envs(address: str, username: str, password: str, cluster_name: str, tcp_address: str) -> dict:
    return {
        "JDOS_ES_TCP_ADDRESS": tcp_address,
        "JDOS_ES_TCP_PORT": "9300",
        "JDOS_ES_CLUSTER_NAME": cluster_name,
        "JDOS_ES_ADDRESS": address,
        "JDOS_ES_HTTP_PORT": "9200",
        "JDOS_ES_PWD": password,
        "JDOS_ES_SCHEMA": "http",
        "JDOS_ES_USER": username,
    }


def get_kafka_envs(address: str) -> dict:
    return {
        "JDOS_KAFKA_ADDRESS": address,
        "JDOS_KAFKA_PORT": "9092",
    }


def get_clickhouse_envs(address: str, username: str, password: str, http_port: str, tcp_port: str) -> dict:
    return {
        "JDOS_CK_ADDRESS": address,
        "JDOS_CK_HTTP_PORT": http_port if http_port else "8123",
        "JDOS_CK_TCP_PORT": tcp_port if tcp_port else "9000",
        "JDOS_CK_USER": username,
        "JDOS_CK_PWD": password,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A script with command line arguments.')
    # store_true Boolean值，选项会将参数的值解释为一个布尔值。如果参数存在于命令行上，值将是 True；否则，值将是 False。
    # 使用 default=True，则可以使得在没有提供 --dry-run 参数时，仍然将其视为 True。
    parser.add_argument('--dry-run', action='store_true', default=True, help='dry-run')
    parser.add_argument('--debug', action='store_true', default=True, help='debug model')
    args = parser.parse_args()
    # 是否dry-run
    if args.dry_run is not None:
        DRY_RUN = args.dry_run
    if args.debug is not None:
        DEBUG = args.debug
    log_level = logging.DEBUG if DEBUG else logging.INFO
    # log level
    log_format = "[%(levelname)s] %(message)s"
    logging.basicConfig(level=log_level, format=log_format)

    if DRY_RUN:
        logging.info("run in DRY_RUN mode")

    main()
