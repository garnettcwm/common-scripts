_newline='
'
str="GET\n/v1/projects/jdap1/applications/app-4a238741/groups/group-0e057831/deploy\nimageUrl=artifacthub.dev51.cvessel.jdcloud.com%2Fjdap1%2Fjdap%2Fcrccheck-hello-world%3Alatest\ncontent-type:application/json\nhost:apisix-gateway.ingress-apisix\nx-jdcloud-date:20221206T063216Z\nx-jdcloud-nonce:83d7aab0-9818-4eb6-a305-21e47d343a82\n\ncontent-type;host;x-jdcloud-date;x-jdcloud-nonce\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
echo "$str"
hex=$(echo -en "$str" | shasum -a 256 | cut -d " " -f 1) &&  echo $hex
hex=$(echo -en "$str" | openssl sha256 -hex | cut -d " " -f 2) &&  echo $hex

_k_temp_bin=$(mktemp)
_k_date=$(echo -n "20221212" | openssl sha256 -hmac "JDCLOUD2" -binary)
echo $_k_date
