#!/bin/bash
echo "jdap: the start_deploy request is submitted"

#去除首尾的空格
gaia_jdap_ak="JDC_991B44D990B912DA788F21827619"
gaia_jdap_sk="C16014C06AFD4A56E53A75BA447A3ED1"
gaia_jdap_project_id="jdap1"
gaia_jdap_app_id="app-4a238741"
gaia_jdap_group_id="group-0e057831"
gaia_jdap_image_url="artifacthub.dev51.cvessel.jdcloud.com/jdap1/jdap/crccheck-hello-world:latest"

#/d/myshell/data.txt
deploy_result_file_path="/etc/jdcloud/jdap-connector-jpipe/data/result_deploy_app_group.json"
#先清理之前的部署结果，避免重试时拿到旧的结果
rm -rf ${deploy_result_file_path}
#开始部署逻辑
cd /
./jdap-connector-jpipe deploy-appgroup  --user-ak=${gaia_jdap_ak} --user-sk=${gaia_jdap_sk} --jdap-project-id=${gaia_jdap_project_id} --jdap-app-id=${gaia_jdap_app_id} --jdap-group-id=${gaia_jdap_group_id} --image-url=${gaia_jdap_image_url}
begin_loop_time=$(date "+%s")
# 部署命令执行后，先等待x秒，等待返回结果
sleep 5
while (true)
do
  # 通过 传递部署请求调用结果; 如果结果未返回，等待x秒
  if [ ! -s ${deploy_result_file_path} ];then
    wait_time=$(($(date "+%s") - ${begin_loop_time}))
    echo "jdap: wait for start_deploy response...${wait_time}s"
    sleep 2
    continue;
  else
    echo "jdap: received start_deploy response, the response is "
    echo `cat ${deploy_result_file_path}`
    #所有业务逻辑都已处理完成, 退出循环
    break;
  fi
done

#获取当前关心的字段
concerned_result_json=`cat ${deploy_result_file_path} | jq '.'`
deploy_result_code=`echo ${concerned_result_json} |  jq -r '.code'`
deploy_result_deploy_order_id=`echo ${concerned_result_json} |  jq -r '.data.deployOrderId'`
deploy_result_jindow_app_id=`echo ${concerned_result_json} |  jq -r '.data.jindowAppId'`
deploy_result_app_name=`echo ${concerned_result_json} |  jq -r '.data.appName'`
deploy_result_group_name=`echo ${concerned_result_json} |  jq -r '.data.groupName'`
echo "deploy order id is ${deploy_result_deploy_order_id}"
# 执行轮训部署结果命令
export JPIPE_VIEW_TYPE=kv
if [ ${deploy_result_code} == 0 ];then
  echo "jdap: start deploy success"
  JDAP_DEPLOY_URL="${GAIA_HOME_URL}/jdap/appManage/hideSideMenuDetail/${gaia_jdap_app_id}/deployRoot/deploy/${deploy_result_jindow_app_id}?deployType=image&project=${gaia_jdap_project_id}"
  export JPIPE_VIEW_DATA='[{"key":{"value":"应用"}, "value":{"value":"'"${gaia_jdap_app_id}(${deploy_result_app_name})"'", "color": "black", "float_value":"'"${gaia_jdap_app_id}(${deploy_result_app_name})"'"}}, {"key":{"value":"分组"}, "value":{"value":"'"${gaia_jdap_group_id}(${deploy_result_group_name})"'", "color": "black", "float_value":"'"${gaia_jdap_group_id}(${deploy_result_group_name})"'"}},{"key":{"value":"部署结果"}, "value":{"value":"查看详情", "link": "'"${JDAP_DEPLOY_URL}"'"}}]'
  echo "jdap: 提交jdap部署成功，请前往jdap应用平台查看部署进展详情"
else
  deploy_result_message=`echo ${concerned_result_json} |  jq '.message'`
  echo "jdap: start deploy failed"
  export JPIPE_VIEW_DATA='[{"key":{"value":"应用id"}, "value":{"value":"'"${gaia_jdap_app_id}"'", "color": "black", "float_value":"'"${gaia_jdap_app_id}"'"}}, {"key":{"value":"分组id"}, "value":{"value":"'"${gaia_jdap_group_id}"'", "color": "black", "float_value":"'"${gaia_jdap_group_id}"'"}}]'
  echo "jdap: start deploy failed, ${deploy_result_message}"
  echo "jdap: 提交jdap部署失败，请依据错误日志排查 或 联系技术支持人员"
  exit -1
fi
