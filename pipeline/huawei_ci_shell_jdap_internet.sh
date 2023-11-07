#!/bin/bash
aliapi_timestamp_rpc() {
    # ISO8601 UTC
    date -u +%Y%m%dT%H%M%SZ
}

aliapi_signature_nonce() {
    local nonce=""
    if [[ -f /proc/sys/kernel/random/uuid ]]; then
        nonce=$(</proc/sys/kernel/random/uuid)
    else
        nonce=$(date "+%s%N")
    fi
    echo "$RANDOM${nonce//-/}$RANDOM"
}

aliapi_urlencode() {
    local result
    local _curl_out=$(mktemp)
    result=$(curl --get --silent --output "$_curl_out" --write-out "%{url_effective}" --data-urlencode "=$1" "") && cat "$_curl_out" - <<< ""
    rm -f "$_curl_out"
    result="${result//+/%20}" # 替换 + 为 %20
    echo "${result#*/?}"
}

deploy_app_group() {
  JdapAccessKeyId="JDC_687CCFD076AC81ADF58ED60BA8D2"
  JdapAccessKeySecret="79C5E2A56FF5AA3775A62D3A7F17A229"
  # shellcheck disable=SC1091
  local -r _JdapAccessKeyId=$JdapAccessKeyId _JdapAccessKeySecret=$JdapAccessKeySecret

  #alias
  local _x_content_type="application/json"
  local _x_host="apigw.online70.cvessel.jdcloud.com"
  local _x_jdcloud_algorithm="JDCLOUD2-HMAC-SHA256"
  local _x_jdcloud_date="$(aliapi_timestamp_rpc)"
  local _x_jdcloud_date_simple="$(date -u +%Y%m%d)"
  local _x_jdcloud_nonce="$(aliapi_signature_nonce)"

  #step1:构造规范化请求
  local _url_encode_project_id="$(aliapi_urlencode "jdap")"
  local _url_encode_app_id="$(aliapi_urlencode "app-e4713369")"
  local _url_encode_group_id="$(aliapi_urlencode "group-5943e777")"
  local _x_deploy_uri="/v1/projects/jdap/applications/app-e4713369/groups/group-5943e777/deploy"

  local _image_url="$(aliapi_urlencode "artifacthub.online70.cvessel.jdcloud.com/demo-seckill/seckill/seckill-web:2.4.1")"
  _x_query_str+="imageUrl=${_image_url}"
  _canonical_request_str="GET\n${_x_deploy_uri}\n${_x_query_str}\ncontent-type:application/json\nhost:${_x_host}\nx-jdcloud-date:${_x_jdcloud_date}\nx-jdcloud-nonce:${_x_jdcloud_nonce}\n\ncontent-type;host;x-jdcloud-date;x-jdcloud-nonce\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  echo "_canonical_request_str:   $_canonical_request_str"
  #待签名字符串
  local _canonical_request_sha=$(echo -en "$_canonical_request_str" | openssl sha256 -hex | cut -d " " -f 2)
  echo "_canonical_request_sha:   $_canonical_request_sha"

  #step2：创建待签字符串
  local _credential_scope="$_x_jdcloud_date_simple/jdcloud-api/jdap/jdcloud2_request"
  local _str_to_sign="${_x_jdcloud_algorithm}\n${_x_jdcloud_date}\n${_credential_scope}\n${_canonical_request_sha}"
  echo "_str_to_sign:   $_str_to_sign"

  #step3：计算签名
  local _k_date_hex=$(echo -n "$_x_jdcloud_date_simple" | openssl sha256 -hmac "JDCLOUD2$_JdapAccessKeySecret" -hex | cut -d " " -f 2 )
  local _k_region_hex=$(echo -n "jdcloud-api" | openssl sha256 -mac HMAC -macopt hexkey:$_k_date_hex -hex | cut -d " " -f 2)
  local _k_service_hex=$(echo -n "jdap" | openssl sha256 -mac HMAC -macopt hexkey:$_k_region_hex -hex | cut -d " " -f 2)
  local _k_credentials_hex=$(echo -n "jdcloud2_request" | openssl sha256 -mac HMAC -macopt hexkey:$_k_service_hex -hex | cut -d " " -f 2)
  local _x_signature=$(echo -en "$_str_to_sign" | openssl sha256 -mac HMAC -macopt hexkey:$_k_credentials_hex -hex | cut -d " " -f 2)

  echo "_k_date_hex: $_k_date_hex"
  echo "_k_region_hex: $_k_region_hex"
  echo "_k_service_hex: $_k_service_hex"
  echo "_k_credentials_hex: $_k_credentials_hex"
  echo "_x_signature: $_x_signature"

  #step4：向 HTTP 请求添加签名
  local _x_authorization="${_x_jdcloud_algorithm} Credential=$_JdapAccessKeyId/$_x_jdcloud_date_simple/jdcloud-api/jdap/jdcloud2_request, SignedHeaders=content-type;host;x-jdcloud-date;x-jdcloud-nonce, Signature=${_x_signature}"

  local _curl_out
  local _http_url="http://114.67.94.237${_x_deploy_uri}?${_x_query_str}"
  echo $_http_url

  _curl_out=$(mktemp)
  ALIYUN_SDK_LAST_HTTP_CODE=$(curl -v --location --silent --show-error --request "GET" \
      --header "host: $_x_host" \
      --header "x-jdcloud-date: $_x_jdcloud_date" \
      --header "x-jdcloud-nonce: $_x_jdcloud_nonce" \
      --header "authorization: $_x_authorization" \
      --header "content-type:application/json" \
      --output "$_curl_out" --write-out "%{http_code}" --connect-timeout 3 "$_http_url") && cat "$_curl_out" - <<< ""
  rm -f "$_curl_out"
  [[ $ALIYUN_SDK_LAST_HTTP_CODE -eq 200 ]] && return 0 || return 1
}
deploy_app_group
