您可以使用mysqldump命令来备份数据而不备份表。以下是一个示例命令：
mysqldump -u username -p database_name --no-create-info table_name > backup.sql

如果您想要恢复备份，可以使用以下命令：
mysql -u username -p database_name < backup.sql


除了使用mysqldump命令，还有其他备份数据而不备份表的方法。以下是一些可能有用的方法：

1. 直接复制数据文件：您可以直接复制MySQL数据目录中的数据文件来备份数据。但是，这种方法只适用于MyISAM表，而不适用于InnoDB表。⁵

2. 使用LVM快照：如果您使用的是Linux系统，并且您的MySQL数据目录位于LVM卷上，则可以使用LVM快照来备份数据。这种方法可以在不停止MySQL服务器的情况下备份数据，并且适用于所有类型的表。⁴

3. 使用XtraBackup：XtraBackup是一个免费的开源工具，可以备份InnoDB和XtraDB表而不锁定它们。它使用了与mysqldump相同的技术，但速度更快，并且可以在不停止MySQL服务器的情况下进行备份。³

希望这可以帮到您！如果您有任何其他问题，请随时问我。

源: 与必应的对话， 2023/7/1
(1) Mysql 备份的三种方式_石硕页的博客-CSDN博客. https://blog.csdn.net/u014209205/article/details/117957402.
(2) 学习MySQL备份一篇就够了！！！（完全备份、增量备份、备份恢复）_备份mysql数据库_仇亚峰的博客-CSDN博客. https://blog.csdn.net/qyf158236/article/details/109220563.
(3) MySQL. https://www.mysql.com/.
(4) MySQL. https://www.mysql.com/it/.
(5) MySQL. https://www.mysql.com/jp/.
