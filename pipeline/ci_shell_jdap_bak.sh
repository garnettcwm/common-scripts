#!/usr/bin/env bash

# 使用的 OpenAPI
# CAS: https://help.aliyun.com/document_detail/126507.html
# CDN：https://help.aliyun.com/document_detail/106661.html

# 可配合 acme.sh 使用的 renewHook 脚本：自动将新证书上传至阿里云并更新对应 CDN 域名，然后删除对应域名的旧证书。
# 每次 API 执行都会检测是否失败，如果失败，会中断脚本执行并返回自定义错误代码。

AliAccessKeyId="JDC_991B44D990B912DA788F21827619"
AliAccessKeySecret="C16014C06AFD4A56E53A75BA447A3ED1"
# shellcheck disable=SC1091
#!/bin/bash

for _aliapi_command in openssl curl; do
    if ! command -v $_aliapi_command &> /dev/null; then
        echo "Aliyun OpenAPI SDK: $_aliapi_command command not found"
        exit 127
    fi
done
unset _aliapi_command

ALIYUN_SDK_LAST_HTTP_CODE=0

# aliapi_rpc <http_method> <host> <api_version> <api_action> [<--key> <value>...]
aliapi_rpc() {
    _aliapi_check_vars || return $?

    if [[ $# -lt 4 ]];then
        echo "aliapi_rpc: not enough parameters" >&2
        return 2
    fi

    local -r _AliAccessKeyId=$AliAccessKeyId _AliAccessKeySecret=$AliAccessKeySecret

    local -u _http_method=$1
    local _http_host=$2
    local _api_version=$3
    local _api_action=$4
    shift 4

    local -A _api_params
    _api_params=(
        ["AccessKeyId"]=$_AliAccessKeyId
        ["Action"]=$_api_action
        ["Format"]="JSON"
        ["SignatureMethod"]="HMAC-SHA1"
        ["SignatureVersion"]="1.0"
        ["SignatureNonce"]=$(_aliapi_signature_nonce)
        ["Timestamp"]=$(_aliapi_timestamp_rpc)
        ["Version"]=$_api_version
    )
    # 解析其余参数
    while [[ $# -ne 0 ]]
    do
        case $1 in
            --*)
                if [[ $# -le 1 ]]; then
                    echo "aliapi_rpc: '$1' has no value" >&2
                    return 2
                fi
                _api_params[${1:2}]="$2"
                shift 2
                ;;
            *)
                echo "aliapi_rpc: '$1' is unknown parameter" >&2
                return 2
                ;;
        esac
    done

    #alias
    local _x_content_type="application/json"
    #local _x_host="apisix-gateway.ingress-apisix"
    local _x_host="apigw.dev51.cvessel.jdcloud.com"
    local _x_jdcloud_algorithm="JDCLOUD2-HMAC-SHA256"
    local _x_jdcloud_date="$(_aliapi_timestamp_rpc)"
    local _x_jdcloud_date_simple="$(date -u +%Y%m%d)"
    local _x_jdcloud_nonce="$(_aliapi_signature_nonce)"
    #local _x_jdcloud_date="20221206T063216Z"
    #local _x_jdcloud_date_simple="20221206"
    #local _x_jdcloud_nonce="83d7aab0-9818-4eb6-a305-21e47d343a82"
    local -A _api_headers
    _api_headers=(
      ["x-jdcloud-algorithm"]=${_x_jdcloud_algorithm}
      ["x-jdcloud-date"]=${_x_jdcloud_date}
      ["x-jdcloud-nonce"]=${_x_jdcloud_nonce}
      ["authorization"]="HMAC-SHA1"
    )

    #step1:构造规范化请求
    local _url_encode_project_id=$(_aliapi_urlencode "jdap1")
    local _url_encode_app_id=$(_aliapi_urlencode "app-4a238741")
    local _url_encode_group_id=$(_aliapi_urlencode "group-0e057831")
    local _x_deploy_uri="/v1/projects/jdap1/applications/app-4a238741/groups/group-0e057831/deploy"
    #local _canonical_deploy_uri=$(_aliapi_urlencode "/v1/projects/jdap1/applications/app-4a238741/groups/group-0e057831/deploy")
    #echo "$_canonical_deploy_uri"
    local _image_url=$(_aliapi_urlencode "artifacthub.dev51.cvessel.jdcloud.com/jdap1/jdap/crccheck-hello-world:latest")
    _x_query_str+="imageUrl=${_image_url}"
    _canonical_request_str="GET\n${_x_deploy_uri}\n${_x_query_str}\ncontent-type:application/json\nhost:${_x_host}\nx-jdcloud-date:${_x_jdcloud_date}\nx-jdcloud-nonce:${_x_jdcloud_nonce}\n\ncontent-type;host;x-jdcloud-date;x-jdcloud-nonce\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    echo "_canonical_request_str:   $_canonical_request_str"
    #待签名字符串
    local _canonical_request_sha=$(echo -en "$_canonical_request_str" | shasum -a 256 | cut -d " " -f 1)
    echo "_canonical_request_sha:   $_canonical_request_sha"

    #step2：创建待签字符串
    local _credential_scope="$_x_jdcloud_date_simple/jdcloud-api/jdap/jdcloud2_request"
    local _str_to_sign="${_x_jdcloud_algorithm}\n${_x_jdcloud_date}\n${_credential_scope}\n${_canonical_request_sha}"
    echo "_str_to_sign:   $_str_to_sign"

    #step3：计算签名
    local _signature=TODO
    local _k_temp_bin=$(mktemp)
    #echo $PAYLOAD_BASE64 | base64 -d | openssl sha256 -hex -mac HMAC -macopt hexkey:$KEY_HEX
    #local _k_date_base64=$(echo -n "$_x_jdcloud_date_simple" | openssl sha256 -hmac "JDCLOUD2$_AliAccessKeySecret" -binary | openssl base64 -e -A)
    #local _k_region_base64=$(echo -n "jdcloud-api" | openssl sha256 -hmac $(echo -n "$_k_date_base64" | openssl base64 -d) -binary | openssl base64 -e -A)
    #local _k_service_base64=$(echo -n "jdap" | openssl sha256 -hmac $(echo -n "$_k_region_base64" | openssl base64 -d) -binary | openssl base64 -e -A)
    #local _x_credentials=$(echo -n "jdcloud2_request" | openssl sha256 -hmac $(echo -n "$_k_service_base64" | openssl base64 -d) -binary | openssl base64 -e -A)
    #local _x_signature=$(echo -en "$_str_to_sign" | openssl sha256 -hmac $(echo -n "$_x_credentials" | openssl base64 -d) -hex | cut -d " " -f 2)

    local _k_date_base64=$(echo -n "$_x_jdcloud_date_simple" | openssl sha256 -hmac "JDCLOUD2$_AliAccessKeySecret" -hex | cut -d " " -f 2 )
    local _k_region_base64=$(echo -n "jdcloud-api" | openssl sha256 -mac HMAC -macopt hexkey:$_k_date_base64 -hex | cut -d " " -f 2)
    local _k_service_base64=$(echo -n "jdap" | openssl sha256 -mac HMAC -macopt hexkey:$_k_region_base64 -hex | cut -d " " -f 2)
    local _x_credentials=$(echo -n "jdcloud2_request" | openssl sha256 -mac HMAC -macopt hexkey:$_k_service_base64 -hex | cut -d " " -f 2)
    local _x_signature=$(echo -en "$_str_to_sign" | openssl sha256 -mac HMAC -macopt hexkey:$_x_credentials -hex | cut -d " " -f 2)

    echo "_k_date_base64: $_k_date_base64"
    echo "_k_region_base64: $_k_region_base64"
    echo "_k_service_base64: $_k_service_base64"
    echo "_x_credentials: $_x_credentials"
    echo "_x_signature: $_x_signature"

    #step4：向 HTTP 请求添加签名
    local _x_authorization="${_x_jdcloud_algorithm} Credential=$_AliAccessKeyId/$_x_jdcloud_date_simple/jdcloud-api/jdap/jdcloud2_request, SignedHeaders=content-type;host;x-jdcloud-date;x-jdcloud-nonce, Signature=${_x_signature}"
    _api_headers["authorization"]=${_x_authorization}
    echo "_x_authorization: $_x_authorization"

    #local _signature
    #_signature=$(_aliapi_signature_rpc "$_http_method" "${_x_query_str:0:-1}")

    local _curl_out _http_url="http://${_x_host}${_x_deploy_uri}?${_x_query_str}"
    echo $_http_url

    _curl_out=$(mktemp)
    ALIYUN_SDK_LAST_HTTP_CODE=$(curl -v --location --silent --show-error --request "GET" \
      --header "x-jdcloud-date: $_x_jdcloud_date" \
      --header "x-jdcloud-nonce: $_x_jdcloud_nonce" \
      --header "authorization: $_x_authorization" \
      --header "content-type:application/json" \
      --output "$_curl_out" --write-out "%{http_code}" --connect-timeout 3 "$_http_url") && cat "$_curl_out" - <<< ""
    rm -f "$_curl_out"
    [[ $ALIYUN_SDK_LAST_HTTP_CODE -eq 200 ]] && return 0 || return 1
}

_aliapi_check_vars() {
    if [[ ! -v AliAccessKeyId || ! -v AliAccessKeySecret ]]; then
        echo "Aliyun OpenAPI SDK: 'AliAccessKeyId' or 'AliAccessKeySecret' environment variable not found" >&2
        return 3
    fi
}

_jdcloudapi_signature_rpc() {
    local -u _http_method=$1
    local _str=$2 _query_str _sign_str
    local _newline='
'
    _str=$(LC_ALL=C sort <<< "${_str//&/$_newline}")
    _query_str=${_str//$_newline/&}
    _sign_str="$_http_method&$(_aliapi_urlencode "/")&$(_aliapi_urlencode "$_query_str")"
    echo -n "$_sign_str" | openssl sha256 -hmac "$_AliAccessKeySecret&" -binary | openssl base64 -e
}

_aliapi_signature_rpc() {
    local -u _http_method=$1
    local _str=$2 _query_str _sign_str
    local _newline='
'
    _str=$(LC_ALL=C sort <<< "${_str//&/$_newline}")
    _query_str=${_str//$_newline/&}
    _sign_str="$_http_method&$(_aliapi_urlencode "/")&$(_aliapi_urlencode "$_query_str")"
    echo -n "$_sign_str" | openssl sha1 -hmac "$_AliAccessKeySecret&" -binary | openssl base64 -e
}

_aliapi_timestamp_rpc() {
    # ISO8601 UTC
    date -u +%Y%m%dT%H%M%SZ
}

_aliapi_signature_nonce() {
    local nonce=""
    if [[ -f /proc/sys/kernel/random/uuid ]]; then
        nonce=$(</proc/sys/kernel/random/uuid)
    else
        nonce=$(date "+%s%N")
    fi
    echo "$RANDOM${nonce//-/}$RANDOM"
}

_aliapi_urlencode() {
    local result
    result=$(curl --get --silent --output /dev/null --write-out "%{url_effective}" --data-urlencode "=$1" "")
    result="${result//+/%20}" # 替换 + 为 %20
    echo "${result#*\?}"
}


# 如果值以 () 结尾，那么 SDK 会假设它是一个已定义函数，获取值时会判断函数是否存在并执行，如果不存在则使用原始值。

get_show_size() {
    echo 50
}

# 获取 SSL 证书列表：https://help.aliyun.com/document_detail/126511.html
# 解析参数时会执行函数 (所以 ShowSize 的值是 50)
aliapi_rpc GET cas.aliyuncs.com 2018-07-13 DescribeUserCertificateList --CurrentPage 1 --ShowSize "get_show_size()"
# $? == 0 代表 HTTP CODE == 200 反之 $? == 1
# 可以通过 ALIYUN_SDK_LAST_HTTP_CODE 变量获取最后一次的 HTTP CODE
# 只要 curl 的退出代码 == 0 就会返回接收到的数据
if [[ $? -eq 0 ]]; then
    # 执行成功
    echo 0
else
    # 执行失败
    echo 1
fi
