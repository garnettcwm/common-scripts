import subprocess
import json

def get_node_info():
    # 执行 kubectl get nodes 命令并捕获输出
    cmd = "kubectl get nodes -o json"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 检查命令是否执行成功
    if result.returncode != 0:
        print("Error executing kubectl command:")
        print(result.stderr)
        return None

    # 解析 JSON 输出
    nodes_json_info = json.loads(result.stdout)
    nodes_map = {}

    # 提取所需信息并打印
    for item in nodes_json_info.get("items", []):
        name = item.get("metadata", {}).get("name", "")
        labels = item.get("metadata", {}).get("labels", {})
        is_master = "node-role.kubernetes.io/master" in labels
        is_node = "node-role.kubernetes.io/node" in labels
        roles = []
        if is_master:
            roles.append("Master")
        if is_node:
            roles.append("Node")

        scheduler_zone = labels.get("topology.jdos.io/scheduler-zone", "")
        zone = labels.get("topology.jdos.io/zone", "")
        rack = labels.get("topology.jdos.io/rack", "")

        node_item = {"name": name, "roles": {', '.join(roles)}, "scheduler_zone": scheduler_zone, "zone": zone, "rack": rack}
        nodes_map[name] = node_item

        print(f"Name: {name}, Roles: {', '.join(roles)}, Scheduler Zone: {scheduler_zone}, Zone: {zone}, Rack: {rack}")

    for key, node_item in nodes_map.items():
        print(f"Name: {node_item.name}, Roles: {node_item.roles}, Scheduler Zone: {node_item.scheduler_zone}, Zone: {node_item.zone}, Rack: {node_item.rack}")

if __name__ == "__main__":
    get_node_info()