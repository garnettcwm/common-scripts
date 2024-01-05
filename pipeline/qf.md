
##port-forward
```
kubectl port-forward svc/mysql-cluster-mysql-master 3306:3306 -n mysql --kubeconfig=~/.kube/config
kubectl port-forward svc/kafka-kafka-bootstrap 9092:9092 -n tpaas-kafka --kubeconfig=~/.kube/config
kubectl port-forward svc/prometheus-server 8080:80 -n monitoring --kubeconfig=~/.kube/config
```

##protoc
```
protoc --proto_path=. \
--proto_path=./third_party \
--go_out=paths=source_relative:. \
internal/conf/conf.proto
```

##swagger
```
java -jar /d/software/swagger-codegen-cli.jar --help

```

##kafka
###测试消息发送
kubectl -n tpaas-kafka exec -it kafka-kafka-0 -c kafka -- bin/kafka-console-producer.sh --bootstrap-server kafka-kafka-bootstrap.tpaas-kafka.svc:9092 --topic cmdb_event_compensate

```json
{
    "serviceCode":"mongodb",
    "region":"cn-north-1",
    "pin":"jdap1",
    "resourceId":"mongo-npd4e69rgs"
}
```

```json
{
    "specversion":"1.0",
    "id":"1",
    "source":"jdcloud.mongodb",
    "type":"mongodb:Instance:CreateCompleted",
    "subject":"jdcloud.mongodb",
    "data_base64":"eyJzZXJ2aWNlQ29kZSI6Im1vbmdvZGIiLCJyZWdpb24iOiJjbi1ub3J0aC0xIiwicGluIjoiamRhcDEiLCJyZXNvdXJjZUlkIjoibW9uZ28tbnBkNGU2OXJncyJ9"
}
```


###查看所有consumer分组
kubectl -n tpaas-kafka exec -it kafka-kafka-0 -c kafka -- bin/kafka-consumer-groups.sh --bootstrap-server kafka-kafka-bootstrap:9092 --list

###查看consumer分组的consumer情况
kubectl -n tpaas-kafka exec -it kafka-kafka-0 -c kafka -- bin/kafka-consumer-groups.sh --bootstrap-server kafka-kafka-bootstrap:9092 --group jd-cmdb-resPayment --describe --members

###创建topic
kubectl -n tpaas-kafka exec -it kafka-kafka-0 -c kafka -- bin/kafka-topics.sh --bootstrap-server kafka-kafka-bootstrap:9092 --create --topic topicname --partitions 1 --replication-factor 1

###查看topic
kubectl -n tpaas-kafka exec -it kafka-kafka-0 -c kafka -- bin/kafka-topics.sh --bootstrap-server kafka-kafka-bootstrap:9092 --topic cmdb_event_compensate --describe

###启动一个consumer接收指定topic的消息
kubectl -n tpaas-kafka exec -it kafka-kafka-0 -c kafka -- bin/kafka-console-consumer.sh --bootstrap-server kafka-kafka-bootstrap:9092 --topic cmdb_event_compensate --partition 0 --max-messages 1

###测试消息发送
kubectl -n tpaas-kafka exec -it kafka-kafka-0 -c kafka -- bin/kafka-console-producer.sh --bootstrap-server kafka-kafka-bootstrap.tpaas-kafka.svc:9092 --topic cmdb_event_compensate


cmdb_event_compensate
JCloudResInstCreatedTopic   = "order_produce_result_topic"
JCloudResInstDeletedTopic   = "resource_delete_result_topic"
JCloudResPaymentResultTopic = "order_payment_result_topic"
JCloudResStatusTopic        = "product_resource_status"

// JDAP 应用事件type
JdapCreateApp = "jd.jdap.application.create.finished"
JdapUpdateApp = "jd.jdap.application.update.finished"
JdapDeleteApp = "jd.jdap.application.delete.finished"

// JDAP应用和实例关系事件type
PaasAppRelationCreate = "jd_jdap_paas_relation_create"
PaasAppRelationDelete = "jd_jdap_paas_relation_delete"
