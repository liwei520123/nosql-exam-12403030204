# -*- coding: utf-8 -*-
"""第三题 Redis 学习信息与排行榜
学号: 12403030204   S=4, A=1, B=0, C=4
键前缀: exam:12403030204:
运行环境: 三主三从 Redis Cluster（默认探测本机 7001-7006，可用环境变量 REDIS_NODES 覆盖，
          格式 "host:port,host:port,..."）
依赖: pip install redis>=5.0
"""
import os
import time

from redis.cluster import ClusterNode, RedisCluster

SID = "12403030204"
S = int(SID[-2:])
A = S % 3
B = S % 4
C = S % 5
SCORE = 70 + C                      # 74
PREFIX = "exam:%s:" % SID

HKEY = PREFIX + "student"           # Hash
SKEY = PREFIX + "chapters"          # Set
ZKEY = PREFIX + "score"             # Sorted Set
SESSION_KEY = PREFIX + "session"    # String

NODES_ENV = os.environ.get("REDIS_NODES")
CANDIDATES = [
    NODES_ENV,
    "127.0.0.1:7001,127.0.0.1:7002,127.0.0.1:7003,"
    "127.0.0.1:7004,127.0.0.1:7005,127.0.0.1:7006",
]


def connect():
    """自动探测可用的 Redis Cluster 起始节点。"""
    errors = []
    for spec in CANDIDATES:
        if not spec:
            continue
        try:
            nodes = []
            for item in spec.split(","):
                host, port = item.strip().split(":")
                nodes.append(ClusterNode(host, int(port)))
            # protocol=2：redis-py 8.x 默认走 RESP3(HELLO 3)，Redis 5.x 不支持，会报 unknown command `HELLO`
            client = RedisCluster(startup_nodes=nodes, decode_responses=True,
                                  protocol=2, socket_connect_timeout=2)
            client.ping()
            print("已连接 Redis Cluster: %s" % spec)
            return client
        except Exception as e:
            errors.append("%s -> %s" % (spec, e))
    raise SystemExit(
        "无法连接 Redis Cluster。已尝试:\n  " + "\n  ".join(errors)
        + "\n请先启动 7001-7006 六个实例并执行 redis-cli --cluster create"
    )


r = connect()


def line(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


line("题目参数")
print("SID = %s, S = %d, A = %d, B = %d, C = %d" % (SID, S, A, B, C))
print("键前缀: %s" % PREFIX)
print("本人成绩: 70+C = %d" % SCORE)

# ============================================================= 1. 学生信息维护
line("1. 学生信息维护（Hash）")
print("键: %s" % HKEY)
r.delete(HKEY)

r.hset(HKEY, mapping={
    "studentId": SID,
    "name": "张三",
    "className": "大数据管理与应用二班",
    "courseId": "COURSE-%s-01" % SID,
    "status": "learning",
})
print("（1）创建后完整 Hash: %s" % r.hgetall(HKEY))

r.hset(HKEY, "status", "completed")
print("（2）status 修改为 completed")

print("（3）单独读取 name   = %s" % r.hget(HKEY, "name"))
print("    单独读取 status = %s" % r.hget(HKEY, "status"))

full = r.hgetall(HKEY)
print("（4）完整 Hash: %s" % full)
print("    其余字段是否保留: %s（共 %d 个字段）" % (len(full) == 5, len(full)))

# =========================================================== 2. 已完成章节记录
line("2. 已完成章节记录（Set，依次提交 CH01；CH02；CH02；CH03）")
print("键: %s" % SKEY)
r.delete(SKEY)

for ch in ["CH01", "CH02", "CH02", "CH03"]:
    r.sadd(SKEY, ch)
    print("提交 %s 后，已完成章节数量 = %d" % (ch, r.scard(SKEY)))

print("（2）最终全部章节: %s" % sorted(r.smembers(SKEY)))
print("（3）CH02 是否已完成: %s" % bool(r.sismember(SKEY, "CH02")))
print("    CH04 是否已完成: %s" % bool(r.sismember(SKEY, "CH04")))

before = r.scard(SKEY)
r.sadd(SKEY, "CH02")
after = r.scard(SKEY)
print("（4）重复提交 CH02: 提交前 %d -> 提交后 %d，数量%s"
      % (before, after, "未增加" if before == after else "增加了（异常）"))

# =============================================================== 3. 成绩排行榜
line("3. 成绩排行榜（Sorted Set）")
print("键: %s" % ZKEY)
r.delete(ZKEY)

r.zadd(ZKEY, {
    "Student:%s" % SID: SCORE,
    "demo:01": 85,
    "demo:02": 90,
    "demo:03": 60,
    "demo:04": 80,
})
me = "Student:%s" % SID


def show_top3(tag):
    rows = r.zrevrange(ZKEY, 0, 2, withscores=True)
    print("%s前3名: %s" % (tag, ", ".join("%s=%d" % (m, int(s)) for m, s in rows)))


print("（1）初始成绩表: %s" % {m: int(s) for m, s in r.zrevrange(ZKEY, 0, -1, withscores=True)})
show_top3("（1）")

new_score = r.zincrby(ZKEY, 20, me)
print("（2）本人分数增加 20 分: %d -> %d" % (SCORE, int(new_score)))

show_top3("（3）")

rank = r.zrevrank(ZKEY, me) + 1          # zrevrank 从 0 开始，名次 = 索引 + 1
print("（4）本人更新后分数 = %d，名次 = 第%d名（降序位置，不并列）"
      % (int(r.zscore(ZKEY, me)), rank))

# =============================================================== 4. 会话生命周期
line("4. 会话生命周期（String + TTL，有效期 5 秒）")
print("键: %s" % SESSION_KEY)
session_value = "sess-%s-zhangsan" % SID
r.set(SESSION_KEY, session_value, ex=5)

session_type = r.type(SESSION_KEY)        # 过期前检查数据类型
print("（1）创建后立即输出: 键值 = %s，TTL = %d 秒"
      % (r.get(SESSION_KEY), r.ttl(SESSION_KEY)))

print("（2）等待 7 秒 ...")
time.sleep(7)

exists = r.exists(SESSION_KEY)
ttl = r.ttl(SESSION_KEY)
print("（3）等待后: 是否存在 = %d（0 表示不存在），TTL = %d（-2 表示键已过期删除）"
      % (exists, ttl))
print("（4）过期验证: %s" % ("通过" if exists == 0 and ttl == -2 else "未通过"))

# ========================================================= 5. 数据类型核验与说明
line("5. 数据类型核验与说明")
print("student 键（Hash）        : %s" % r.type(HKEY))
print("chapters 键（Set）        : %s" % r.type(SKEY))
print("score 键（Sorted Set）    : %s" % r.type(ZKEY))
print("session 键（过期前检查）  : %s" % session_type)

