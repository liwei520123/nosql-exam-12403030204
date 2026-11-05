# task3 Redis 学习信息与排行榜（30 分）

键前缀 `exam:12403030204:`，集群为三主三从（127.0.0.1:7001~7006）。

## 文件

| 文件 | 说明 |
|---|---|
| `task3.py` | 学生信息 Hash、已完成章节 Set、成绩 ZSet、会话 TTL、数据类型核验 |
| `result.txt` | 实际运行输出 |

## 执行

```bash
python task3.py
```

脚本自动探测 7001~7006，可用 `REDIS_NODES="host:port,..."` 覆盖。

## 数据类型核验与选择理由

| 键 | 实际类型 | 选择理由 |
|---|---|---|
| `exam:<SID>:student` | hash | 一条学生记录是「多个字段组成的一个对象」，Hash 按字段读写：改 `status` 只需 `HSET` 一个字段，其余字段天然保留，无覆盖风险 |
| `exam:<SID>:chapters` | set | 已完成章节要求去重、无序；`SADD` 天然幂等，重复提交 CH02 数量不变，`SISMEMBER` 可 O(1) 判断某章是否完成 |
| `exam:<SID>:score` | zset | 排行榜要按分数排序取前 3 并给出名次；ZSet 按 score 有序，`ZREVRANGE` 直接取前列，`ZREVRANK` 直接得名次，不需要客户端排序 |
| `exam:<SID>:session` | string | 会话是一个整体值，配 `EX` 由 Redis 自动过期删除，`TTL` 可随时查询剩余寿命 |

## 结果摘要

Hash 改 status 后 5 个字段全部保留；Set 依次提交 CH01/CH02/CH02/CH03 后数量为 3，重复提交 CH02 不增加；ZSet 本人 74 分加 20 后为 94 分，排名第 1；会话 5 秒有效，等待 7 秒后 `EXISTS=0`、`TTL=-2`，过期验证通过。
