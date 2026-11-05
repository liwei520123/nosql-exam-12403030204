# -*- coding: utf-8 -*-
"""第四题 初始化脚本：清空本题会写入的键（初始化与测量分开）
学号: 12403030204   S=4, A=1, B=0, C=4
删除 exam:<SID>:seq:* 与 exam:<SID>:pipe:*，让两次测量都从空库开始。
"""
import os

from redis.cluster import ClusterNode, RedisCluster

SID = "12403030204"
PREFIX = "exam:%s:" % SID
PATTERNS = [PREFIX + "seq:*", PREFIX + "pipe:*"]

DEFAULT_NODES = ("127.0.0.1:7001,127.0.0.1:7002,127.0.0.1:7003,"
                 "127.0.0.1:7004,127.0.0.1:7005,127.0.0.1:7006")


def build_client():
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
    client.ping()
    return client


if __name__ == "__main__":
    r = build_client()
    print("已连接 Redis Cluster，开始清理本题键 ...")
    total = 0
    for pattern in PATTERNS:
        batch = []
        for key in r.scan_iter(match=pattern, count=500):
            batch.append(key)
            if len(batch) >= 100:
                total += r.delete(*batch)
                batch = []
        if batch:
            total += r.delete(*batch)
        print("  %-24s 已清理" % pattern)
    print("清理完成，共删除 %d 个键。" % total)
