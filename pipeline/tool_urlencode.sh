_aliapi_urlencode() {
    local result
    local _curl_out=$(mktemp)
    result=$(curl --get --silent --output "$_curl_out" --write-out "%{url_effective}" --data-urlencode "=$1" "") && cat "$_curl_out" - <<< ""
    result="${result//+/%20}" # 替换 + 为 %20
    # The '\' character is a special character in Groovy. If you tried to compile this kind of code with the normal Groovy compiler, it would give you a better error message.
    echo "${result#*\?}"
    echo "${result#*/?}"
    echo "${result:2}"
}

_aliapi_urlencode $@
