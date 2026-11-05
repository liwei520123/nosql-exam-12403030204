《NoSQL数据库》上机测验 提交说明
====================================================

学号：12403030204
姓名：张三（按题目要求，涉及个人姓名处统一代替）
班级：大数据管理与应用二班

一、个人参数
----------------------------------------------------
S = 学号末两位 = 4
A = S mod 3 = 1
B = S mod 4 = 0
C = S mod 5 = 4
MongoDB 数据库：exam_12403030204
Redis 键前缀：exam:12403030204:
第二题：Stock = 5+C = 9，Buy = 1+A = 2
第三题：本人成绩 = 70+C = 74
第四题：N = 1000+100C+S = 1404，Q = 100

二、运行环境与依赖
----------------------------------------------------
MongoDB 8.3（第二题需以副本集方式启动，单节点副本集 rsExam 即可，否则事务不可用）
Redis 5.0.14.1，三主三从集群 127.0.0.1:7001~7006（实验五搭建环境）
Python 3.13
依赖：pip install pymongo "redis>=5.0"

注意：redis-py 8.x 默认使用 RESP3（HELLO 3）握手，Redis 5.x 不支持该命令，
      因此 Redis 相关脚本的客户端均显式指定 protocol=2。

三、目录与执行方法
----------------------------------------------------
task1/  MongoDB 课程信息查询与维护（必做 20 分）
  init_task1.py  初始化 courses 集合（仅执行一次，之后不得重新初始化）
  task1.py       业务操作：查询、局部更新、防重复新增、核验
  result.txt     实际运行结果
  README.md      简短说明
  执行：python init_task1.py   然后   python task1.py

task2/  MongoDB 原子扣减与事务验证（必做 40 分）
  init_task2.py  按场景重置 inventory / orders
  task2.py       原子扣减、事务订购、T1~T4 测试
  result.txt     实际运行结果
  README.md      简短说明
  执行：python init_task2.py   然后   python task2.py

task3/  Redis 学习信息与排行榜（必做 30 分）
  task3.py       学生信息 Hash、章节 Set、排行榜 ZSet、会话 TTL、类型核验
  result.txt     实际运行结果
  README.md      简短说明（含数据类型选择理由）
  执行：python task3.py

task4/  Redis Pipeline 与性能比较（选做，加分）
  init_task4.py  清理本题写入的键
  task4.py       逐条写入与普通 Pipeline 分批写入，计时并核验完整性
  result.txt     实际运行结果（含指标表与结论）
  README.md      简短说明
  执行：python init_task4.py   然后   python task4.py

集群端口可用环境变量覆盖：
  set REDIS_NODES=host:port,host:port,...
  set MONGO_URI=mongodb://127.0.0.1:27017/?replicaSet=rsExam

四、提交日期
----------------------------------------------------
2026-11-05
