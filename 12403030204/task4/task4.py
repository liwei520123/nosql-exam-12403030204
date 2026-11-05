# -*- coding: utf-8 -*-
"""第四题 Redis Pipeline 与性能比较（选做，加分题）
学号: 12403030204   S=4, A=1, B=0, C=4
N = 1000 + 100C + S = 1404，Q = 100

方案甲：键 exam:<SID>:seq:<i>，逐条写入，收到返回后再发下一条
方案乙：键 exam:<SID>:pipe:<i>，普通 Pipeline（transaction=False），每批最多 100 条

运行环境：实验五搭建的三主三从 Redis Cluster（默认探测 127.0.0.1:7001-7006，
          可用环境变量 REDIS_NODES="host:port,..." 覆盖）
运行方式：先 python init_task4.py 清空本题键，再 python task4.py
依赖：pip install redis>=5.0
"""
import os
import time

from redis.cluster import ClusterNode, RedisCluster

SID = "12403030204"
S = int(SID[-2:])                       # 4
A = S % 3                               # 1
B = S % 4                               # 0
C = S % 5                               # 4
N = 1000 + 100 * C + S                  # 1404
Q = 100                                 # 每批最多 100 条

PREFIX = "exam:%s:" % SID
SEQ_PREFIX = PREFIX + "seq:"
PIPE_PREFIX = PREFIX + "pipe:"

DEFAULT_NODES = ("127.0.0.1:7001,127.0.0.1:7002,127.0.0.1:7003,"
                 "127.0.0.1:7004,127.0.0.1:7005,127.0.0.1:7006")


def line(title=""):
    print("\n" + "=" * 78)
    if title:
        print(title)
        print("=" * 78)


def build_client():
    """新建客户端并预热：先建立一次经过槽路由的连接，避免把拓扑发现算进计时。"""
    spec = os.environ.get("REDIS_NODES") or DEFAULT_NODES
    nodes = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        host, port = item.split(":")
        nodes.append(ClusterNode(host, int(port)))
    client = RedisCluster(startup_nodes=nodes, decode_responses=True, protocol=2,
                          socket_connect_timeout=2)
    client.set(PREFIX + "warmup", "1")      # 触发一次完整路由
    client.delete(PREFIX + "warmup")
    print("已连接 Redis Cluster: %s" % spec)
    return client


def value_of(i):
    return "value-%s-%d" % (SID, i)


def count_keys(client, pattern):
    return sum(1 for _ in client.scan_iter(match=pattern, count=500))


def write_single(client):
    """方案甲：逐条写入，每条命令等到回复才发下一条。"""
    t0 = time.perf_counter()
    ok = 0
    for i in range(1, N + 1):
        if client.set(SEQ_PREFIX + str(i), value_of(i)):
            ok += 1
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return elapsed_ms, ok


def write_pipeline(client):
    """方案乙：普通 Pipeline 分批写入，每批最多 Q 条，全部回复到齐后再发下一批。"""
    batches = []
    ok = 0
    t0 = time.perf_counter()
    start = 1
    while start <= N:
        end = min(start + Q - 1, N)          # 最后一批不足 Q 条时按实际条数发送
        pipe = client.pipeline(transaction=False)   # 普通 Pipeline，不使用事务包装
        for i in range(start, end + 1):
            pipe.set(PIPE_PREFIX + str(i), value_of(i))
        replies = pipe.execute()             # 收到本批全部回复
        ok += sum(1 for r in replies if r)
        batches.append((start, end, len(replies)))
        start = end + 1
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return elapsed_ms, ok, batches


def verify(client, prefix, n):
    """核验数据完整性：逐条读回，校验键是否存在、值是否正确。"""
    missing = 0
    wrong = 0
    for i in range(1, n + 1):
        got = client.get(prefix + str(i))
        if got is None:
            missing += 1
        elif got != value_of(i):
            wrong += 1
    return missing, wrong


print("===== 第四题 运行结果 =====")
print("学号 %s  S=%d A=%d B=%d C=%d  时间 %s"
      % (SID, S, A, B, C, time.strftime("%Y-%m-%d %H:%M:%S")))
print("执行: python init_task4.py（清理）然后 python task4.py")

line("0. 参数与环境")
print("N = 1000 + 100C + S = 1000 + %d + %d = %d 条命令" % (100 * C, S, N))
print("Q = %d 条/批  ->  ceil(%d / %d) = %d 批，最后一批 %d 条"
      % (Q, N, Q, (N + Q - 1) // Q, N % Q if N % Q else Q))
print("方案甲键: %s<i>    方案乙键: %s<i>    i 从 1 到 %d"
      % (SEQ_PREFIX, PIPE_PREFIX, N))

line("1. 方案甲：逐条写入（每次收到返回后再发下一条）")
client_a = build_client()
seq_before = count_keys(client_a, SEQ_PREFIX + "*")
print("测量前 %s* 已有键: %d 个" % (SEQ_PREFIX, seq_before))
if seq_before:
    print("提示: 已有旧键，建议先执行 init_task4.py 清空，保证从空库开始")
cost_a, ok_a = write_single(client_a)
print("写入成功 %d / %d 条，耗时 %.3f ms（平均 %.4f ms/条）"
      % (ok_a, N, cost_a, cost_a / N))

line("2. 方案乙：普通 Pipeline 分批写入（transaction=False，每批最多 %d 条）" % Q)
client_b = build_client()
pipe_before = count_keys(client_b, PIPE_PREFIX + "*")
print("测量前 %s* 已有键: %d 个" % (PIPE_PREFIX, pipe_before))
cost_b, ok_b, batches = write_pipeline(client_b)
print("Pipeline 批次数: %d" % len(batches))
for idx, (s, e, cnt) in enumerate(batches, 1):
    note = "  <- 尾批" if idx == len(batches) else ""
    print("  第%2d批: i=%d~%d，发送 %d 条，收到回复 %d 条%s"
          % (idx, s, e, e - s + 1, cnt, note))
print("写入成功 %d / %d 条，耗时 %.3f ms（平均 %.4f ms/条）"
      % (ok_b, N, cost_b, cost_b / N))

line("3. 数据完整性核验（计时之外执行）")
miss_a, wrong_a = verify(client_a, SEQ_PREFIX, N)
miss_b, wrong_b = verify(client_b, PIPE_PREFIX, N)
cnt_a = count_keys(client_a, SEQ_PREFIX + "*")
cnt_b = count_keys(client_b, PIPE_PREFIX + "*")
print("方案甲: 应有 %d 键，实有 %d 键，缺失 %d，值错误 %d  -> %s"
      % (N, cnt_a, miss_a, wrong_a, "完整" if (cnt_a == N and miss_a == 0 and wrong_a == 0) else "不完整"))
print("方案乙: 应有 %d 键，实有 %d 键，缺失 %d，值错误 %d  -> %s"
      % (N, cnt_b, miss_b, wrong_b, "完整" if (cnt_b == N and miss_b == 0 and wrong_b == 0) else "不完整"))
tail = batches[-1]
print("尾批核验: 第%d批 i=%d~%d 共 %d 条，读回结果: %s"
      % (len(batches), tail[0], tail[1], tail[2],
         "全部存在且值正确"
         if all(client_b.get(PIPE_PREFIX + str(i)) == value_of(i)
                for i in range(tail[0], tail[1] + 1)) else "存在缺失"))

line("4. 指标汇总")
print("%-20s %s" % ("指标", "程序输出值"))
print("%-20s %d" % ("命令总数", N))
print("%-20s %d" % ("Pipeline 批次数", len(batches)))
print("%-20s %d" % ("最后一批数量", tail[2]))
print("%-20s %.3f" % ("方案甲耗时(ms)", cost_a))
print("%-20s %.3f" % ("方案乙耗时(ms)", cost_b))
print("%-20s %.3f" % ("方案甲平均每条(ms)", cost_a / N))
print("%-20s %.3f" % ("方案乙平均每条(ms)", cost_b / N))

line("5. 结论")
if cost_b < cost_a:
    print("方案乙（普通 Pipeline）更快：%.3f ms 对 %.3f ms，约为方案甲的 %.1f 倍。"
          % (cost_b, cost_a, cost_a / cost_b))
    print("原因: 逐条写入每条命令都要一次完整的往返(RTT)，%d 条就是 %d 次等待；"
          % (N, N))
    print("      Pipeline 把 %d 条命令压成 %d 批，每批只付一次往返，"
          % (N, len(batches)))
    print("      往返次数从 %d 降到 %d，省掉的主要是等待与系统调用开销。"
          % (N, len(batches)))
else:
    print("本次测量中方案乙并未更快：%.3f ms 对 %.3f ms。" % (cost_b, cost_a))

print("\n如果两种方式差异不明显，甚至 Pipeline 更慢，可能的原因：")
print("  1) 客户端与服务端在同一台机器，RTT 本身只有零点几毫秒，")
print("     网络往返不再是瓶颈，批量省下的时间被服务端执行开销淹没；")
print("  2) 集群客户端要按槽把一批命令拆分到三个主节点分别发送，")
print("     分组、逐节点发送与结果归并的客户端开销会吃掉一部分收益；")
print("  3) 单线程 Redis 处理命令的总工作量不变，Pipeline 只减少往返次数，")
print("     不减少服务端真正执行的 1404 条命令；")
print("  4) 测量次数少、或受连接建立、槽缓存刷新、Python 解释器预热等")
print("     一次性开销影响，单次测量波动可能盖过真实差距。")

print("\n说明: 计时包含命令构造、发送和回复接收；方案乙在最后一批 execute()")
print("      返回后才停止计时，未在计时区间内做任何数据核验。")
