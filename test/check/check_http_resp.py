import sys
sys.path.append('/Users/chenwenming10/workspace/garnettcwm/common-scripts')
import requests
import time
import json
from test.config.config import *
from concurrent.futures import ThreadPoolExecutor

headers = {
    'authority': test_domain,
    'accept': 'application/json',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'cache-control': 'no-cache',
    'cookie': cookie_value,  # 替换成你的实际 Cookie
    'pragma': 'no-cache',
    'referer': test_domain + '/omMiddle/backmonitoring/sgm-console-mobile/sgm-console-mobile-back/index',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'timeout': '3000',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'x-csrf-token': 'B3FylYfWJxPTnZPTAbGVgOHb',
}

def make_request():
    # 设置 verify 参数为 False 以忽略 HTTPS 证书验证
    url = test_domain + '/bizApi/backManage/menu/uas/user/auth/tree?platformCode=omPlatform'
    try:
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        response_json = response.json()
    except requests.exceptions.Timeout:
        # 处理超时异常
        print("Error: uas_auth_tree Request timed out.")
        response_json = {}
    return response_json

def make_etcd_describe_request():
    # 设置 verify 参数为 False 以忽略 HTTPS 证书验证
    url = test_domain + '/yunjian_console_etcd_runtime/openApi/etcd/describeInstances?_t=1703658824786&params=%7B%22filters%22:[%7B%22name%22:%22instanceName%22,%22values%22:[]%7D,%7B%22name%22:%22instanceId%22,%22values%22:[]%7D,%7B%22name%22:%22instanceStatus%22,%22values%22:[]%7D],%22pageNumber%22:1,%22pageSize%22:10,%22x-extra-header%22:%7B%22Accept-Language%22:%22cn%22%7D%7D&regionId=cn-north-1'
    try:
        response = requests.get(url, headers=headers, timeout=45, verify=False)
        response_json = response.json()
        # print(f"{response_json}")
    except requests.exceptions.Timeout:
        # 处理超时异常
        print("Error: etcd_describe Request timed out.")
        response_json = {}
    return response_json

def make_kafka_describe_request():
    # 设置 verify 参数为 False 以忽略 HTTPS 证书验证
    url = test_domain + '/yunjian_console_kafka_runtime/openApi/kafka/describeInstances?_t=1703669469182&params=%7B%22filters%22:[%7B%22name%22:%22instanceName%22,%22values%22:[]%7D,%7B%22name%22:%22instanceId%22,%22values%22:[]%7D,%7B%22name%22:%22instanceStatus%22,%22values%22:[]%7D],%22pageNumber%22:1,%22pageSize%22:10,%22x-extra-header%22:%7B%22Accept-Language%22:%22cn%22%7D%7D&regionId=cn-north-1'
    try:
        response = requests.get(url, headers=headers, timeout=45, verify=False)
        response_json = response.json()
    except requests.exceptions.Timeout:
        # 处理超时异常
        print("Error: etcd_describe Request timed out.")
        response_json = {}
    return response_json

def make_zookeeper_describe_request():
    # 设置 verify 参数为 False 以忽略 HTTPS 证书验证
    url = test_domain + '/yunjian_console_zk_runtime/openApi/zk/describeInstances?_t=1703672923468&params=%7B%22filters%22:[%7B%22name%22:%22instanceStatus%22,%22values%22:[]%7D],%22pageSize%22:10,%22pageNumber%22:1,%22x-extra-header%22:%7B%22Accept-Language%22:%22cn%22%7D%7D&regionId=cn-north-1'
    try:
        response = requests.get(url, headers=headers, timeout=45, verify=False)
        response_json = response.json()
    except requests.exceptions.Timeout:
        # 处理超时异常
        print("Error: etcd_describe Request timed out.")
        response_json = {}
    return response_json

def check_response_struct_is_right(*args, response_content):
    # 判断 JSON 对象是否不为空
    # args 是一个元组，包含了所有动态传入的参数
    if not args:
        origin = "default"
    else:
        # for arg in args:
            # print(f"Dynamic Argument: {arg}")

        # 这里可以根据需要使用 args 来访问动态传入的参数
        # 例如，获取第一个参数的值：
        if args:
            origin = args[0]

    if not response_content or not isinstance(response_content, dict):
        print(f"[{origin}] Error: response 对象为空或不是一个字典。{response_content}")
        return False

    # 判断是否包含 "requestId" 和 "result" 键
    if "requestId" not in response_content or "result" not in response_content:
        print(f"[{origin}] Error: response 对象缺少 'requestId' 和/或 'result' 键。")
        return False

    # 判断 "result" 是否是一个字典且包含 "instances" 键
    if not isinstance(response_content["result"], dict) or "instances" not in response_content["result"]:
        print(f"[{origin}] Error: response 对象的 'result' 键为空或不是一个字典，或缺少 'instances' 键。")
        return False

    # 判断 "instances" 是否是一个非空列表
    if not isinstance(response_content["result"]["instances"], list):
    #if not isinstance(response_content["result"]["instances"], list) or not response_content["result"]["instances"]:
        print(f"[{origin}] Error: response 对象的 'instances' 键为空或不是一个列表。")
        return False

    # 正确返回
    print(f"[{origin}] Success: response 对象不为空且满足指定结构。")
    return True


def check_response(response_content):
    if not response_content or not isinstance(response_content, dict):
        print(f"[uas_auth_tree] Error: response 对象为空或不是一个字典。")
        return False

    response_data = response_content.get('data', [])
    if not isinstance(response_data, list):
        print(f"[uas_auth_tree] Error: Response data is not an array!")
        print(f"[uas_auth_tree] Response Content: {json.dumps(response_content, indent=2)}")
        return False

    # print(f"Info: Response data is {response_data}")
    for data_item in response_data:
        groupName = data_item.get('groupName')
        print(f"[uas_auth_tree] Info: data_item's groupName [{groupName}]!")
        if groupName == "backruntime":
            group_children_data = data_item.get('children', [])
            if not group_children_data:
                print(f"[uas_auth_tree] Error: data[{response_data.index(data_item)}].children is empty!")
                return False

            # print(json.dumps(group_children_data, indent=2))
            # 检查每个元素的 'children'
            for item in group_children_data:
                if not item.get('children'):
                    print(f"[uas_auth_tree] Error: {groupName} has an element with empty 'children'!")
                    return False

            # 如果所有元素的 'children' 都不为空，则打印成功信息并退出循环
            print("[uas_auth_tree] Success: All elements have non-empty 'children'.")
            return True

def execute_request_and_check(executor, make_request_func, check_response_func, *args):
    start_time = time.time()

    # 判断 JSON 对象是否不为空
    # args 是一个元组，包含了所有动态传入的参数
    if not args:
        origin = "default"
    else:
        if args:
            origin = args[0]
    times = 1
    while True:
        if times != 1:
            print(f"[{origin}] {times} times retry!")

        response_content = make_request_func()

        if check_response_func(*args, response_content=response_content):
            break

        time.sleep(5)
        times = times + 1

    end_time = time.time()
    total_time = end_time - start_time
    return total_time


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 并发发起两个请求
        future_uas_auth_tree = executor.submit(execute_request_and_check, executor, make_request, check_response)
        future_etcd_list = executor.submit(execute_request_and_check, executor, make_etcd_describe_request, check_response_struct_is_right, "etcd_list")
        future_kafka_list = executor.submit(execute_request_and_check, executor, make_kafka_describe_request, check_response_struct_is_right, "kafka_list")
        future_zookeeper_list = executor.submit(execute_request_and_check, executor, make_zookeeper_describe_request, check_response_struct_is_right, "zookeeper_list")

        # 等待并获取两个请求的结果
        total_time_uas_auth_tree = future_uas_auth_tree.result()
        total_time_kafka_list = future_kafka_list.result()
        total_time_etcd_list = future_etcd_list.result()
        total_time_zookeeper_list = future_zookeeper_list.result()

    print(f"[uas_auth_tree] Request Total Time: {total_time_uas_auth_tree:.2f} seconds")
    print(f"[etcd_list] Request Total Time: {total_time_etcd_list:.2f} seconds")
    print(f"[zookeeper_list] Request Total Time: {total_time_zookeeper_list:.2f} seconds")
    print(f"[kafka_list] Request Total Time: {total_time_kafka_list:.2f} seconds")
