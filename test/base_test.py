import logging
import re
import tempfile

import yaml

yamlDemo = """
apiVersion: v1
data:
  apiserver_host: http://jvessel-apiserver-clusterip.jd-tpaas
  auto_expose: open
  auto_expose_service_code: '[jdock-demo, dts, elasticsearch]'
  blackGVKs: |-
    - group: openapi.tpaas.jd.com
      version: v1
      kind: TPAASHelmChart
  custom_domain_suffix: .corp.jvessel-custom.jdcloud.com
  def_lb: glbv2
  default_white_strategy: ""
  dis_servicecode: "1"
  domain_id: "12485"
  domain_managed: jvessel2
  domain_suffix: .jvessel2-stack.dev51.cvessel.jdcloud.com
  expose_token: TqMW8ZO4u8tskk3m
  glb_cidr: 10.52.1.1/24
  glb_cluster_name: cv-poc
  headless_secgroup: open
  inner_apigw: apisix-gateway.ingress-apisix.svc
  matrix_host: http://jvessel-matrix-clusterip.jd-tpaas
  max_nic: "6"
  np_api: http://npapi.dev51.cvessel.jdcloud.com
  region_short: stack-north-1:sn1;cn-taikang-1:tk1;
  role_account_ak: AE544EB77E052EFAD994CC9267581CC2
  role_account_sk: 8F447E59793BF849187F79EDBE2F47D3
  service_account_ak: 43602F556E0241CEF60200028F29DABB
  service_account_sk: A02FE510652EA9C6AB0B92A349F79016
  service_pin: admin
  switcher: |-
    watchNode: false
    watchPod: false
    watchEvent: false
    watchSecret: true
    watchBusinessCR: true
    turnOnWhiteGVKFilter: true
    turnOnBlackGVKFilter: false
  system_account_ak: 0504F5B2A069C90BE00109F7EFF4A542
  system_account_sk: 6E6949BBC48660EB94C82A39E6641306
  vessel_auto_sync: close
  visible_header_mode: openAdmin
  vm_pwd: '!Jvessel888'
  vpc_endpoint: apigw.dev51.cvessel.jdcloud.com
  vpc_id: vpc-r78zl556xr
  whiteGVKs: |-
    - group: jvessel.jdcloud.com
      version: v1
      kind: Release
kind: ConfigMap
metadata:
  annotations:
    meta.helm.sh/release-name: jvessel-controller
    meta.helm.sh/release-namespace: jd-tpaas
  name: sys-info
  namespace: jd-tpaas
"""


yamlDemo2 = """
apiVersion: v1
data:
  apiserver_host: http://jvessel-apiserver-clusterip.jd-tpaas
  auto_expose: open
  auto_expose_service_code: |-
    - kafka
    - jvessel2
    - jmsf
    - dts
    - jdock-demo
    - stardbplus
    - terrabase
    - elasticsearch
  blackGVKs: |-
    - group: openapi.tpaas.jd.com
      version: v1
      kind: TPAASHelmChart
  custom_domain_suffix: .corp.jvessel-custom.jdcloud.com
  def_lb: glbv2
  default_white_strategy: ""
  dis_servicecode: "1"
  domain_id: "12485"
  domain_managed: jvessel2
  domain_suffix: .jvessel2-stack.dev51.cvessel.jdcloud.com
  expose_token: TqMW8ZO4u8tskk3m
  glb_cidr: 10.52.1.1/24
  glb_cluster_name: cv-poc
  headless_secgroup: open
  inner_apigw: apisix-gateway.ingress-apisix.svc
  matrix_host: http://jvessel-matrix-clusterip.jd-tpaas
  max_nic: "6"
  np_api: http://npapi.dev51.cvessel.jdcloud.com
  region_short: stack-north-1:sn1;cn-taikang-1:tk1;
  role_account_ak: AE544EB77E052EFAD994CC9267581CC2
  role_account_sk: 8F447E59793BF849187F79EDBE2F47D3
  service_account_ak: 43602F556E0241CEF60200028F29DABB
  service_account_sk: A02FE510652EA9C6AB0B92A349F79016
  service_pin: admin
  switcher: |-
    watchNode: false
    watchPod: false
    watchEvent: false
    watchSecret: true
    watchBusinessCR: true
    turnOnWhiteGVKFilter: true
    turnOnBlackGVKFilter: false
  system_account_ak: 0504F5B2A069C90BE00109F7EFF4A542
  system_account_sk: 6E6949BBC48660EB94C82A39E6641306
  vessel_auto_sync: close
  visible_header_mode: openAdmin
  vm_pwd: '!Jvessel888'
  vpc_endpoint: apigw.dev51.cvessel.jdcloud.com
  vpc_id: vpc-r78zl556xr
  whiteGVKs: |-
    - group: jvessel.jdcloud.com
      version: v1
      kind: Release
kind: ConfigMap
metadata:
  annotations:
    meta.helm.sh/release-name: jvessel-controller
    meta.helm.sh/release-namespace: jd-tpaas
  name: sys-info
  namespace: jd-tpaas
"""


def extract_protocol_address_port(url):
    # 非空检查
    if not url or url.isspace():
        return None, None, None

    # 更新正则表达式以使端口部分可选
    pattern = r'^(http|https)://([^:/]+)(?::(\d*))?$'

    # 使用re.match()尝试匹配字符串
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
if __name__ == "__main__":
    # 测试函数
    urls = ["http://example.com:8080", "https://example.com", "http://example.com", "", "   "]

    for url in urls:
        protocol, address, port = extract_protocol_address_port(url)
        if protocol and address and port:
            print(f"URL: {url} -> 协议: {protocol}, 地址: {address}, 端口: {port}")
        else:
            print(f"URL: {url} -> 输入的URL无效或不符合指定的HTTP地址格式。")

if __name__ == "__main__":
    # log level
    log_format = "[%(levelname)s] %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=log_format)
    cmSysInfo= yaml.load(yamlDemo, Loader=yaml.FullLoader)
    if cmSysInfo:
        auto_expose = cmSysInfo["data"]["auto_expose"]
        auto_expose_service_codes = cmSysInfo["data"]["auto_expose_service_code"]
        logging.info("auto_expose_service_codes: %s", auto_expose_service_codes)
        list_object = auto_expose_service_codes.strip("[]").split(", ")
        logging.info("auto_expose_service_code: %s", list_object)
        for serviceCode in list_object:
            logging.info("%s", serviceCode)

    cmSysInfo2 = yaml.load(yamlDemo2, Loader=yaml.FullLoader)
    if cmSysInfo2:
        auto_expose = cmSysInfo2["data"]["auto_expose"]
        auto_expose_service_codes = cmSysInfo2["data"]["auto_expose_service_code"]
        logging.info("auto_expose_service_codes: %s", auto_expose_service_codes)
        list_object = yaml.safe_load(auto_expose_service_codes)
        logging.info("auto_expose_service_code: %s", list_object)
        for serviceCode in list_object:
            logging.info("%s", serviceCode)