# task2 MongoDB 原子扣减与事务验证（40 分）

参数：`Stock = 5+C = 9`，`Buy = 1+A = 2`，教材 `BOOK-12403030204`，数据库 `exam_12403030204`。

## 文件

| 文件 | 说明 |
|---|---|
| `init_task2.py` | 初始化 `inventory` / `orders`，每个场景开始前单独重置 |
| `task2.py` | 原子扣减、事务订购、T1~T4 场景测试 |
| `result.txt` | 实际运行输出 |

## 执行前提

事务要求副本集，单节点副本集即可：

```bash
mongod --dbpath <data> --replSet rsExam --port 27017
mongosh --eval "rs.initiate()"
```

默认连接 `mongodb://127.0.0.1:27017/?replicaSet=rsExam`，可用 `MONGO_URI` 覆盖。

## 实现要点

1. 扣减用一次 `find_one_and_update({_id, stock: {$gte: qty}}, {$inc: {stock: -qty}})`，条件检查与扣减在服务端单文档内原子完成，不存在「先查再无条件扣减」。
2. 依据返回文档区分三种结果：返回文档 → 成功；返回 `None` 且文档存在 → 库存不足；文档不存在 → 教材不存在；驱动异常 → 捕获后继续运行。
3. 订购函数接收 `requestId` 与 `forceError`，扣减与插单在同一 `session`、同一事务内；扣减失败不生成订单；`forceError=True` 时在扣减后、插单前抛异常触发回滚；只有提交成功才返回成功。
4. T1~T4 各自重置数据，T4 连续发起 `⌊Stock/Buy⌋+1 = 5` 次、每次不同 `requestId`，实际值与预期值逐项比对。
