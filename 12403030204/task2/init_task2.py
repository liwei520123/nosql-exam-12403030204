# -*- coding: utf-8 -*-
"""第二题 初始化脚本：建立个人数据库中的 inventory / orders 集合初始数据。
业务测试脚本 task2.py 的每个场景都会自行按参数重置数据，本脚本只做一次基线初始化。
学号: 12403030204   参数: S=4, A=1, C=4  ->  Stock=5+C=9, Buy=1+A=2
"""
import os

from pymongo import MongoClient
from pymongo.errors import PyMongoError

SID = "12403030204"
S = int(SID[-2:])
A = S % 3
C = S % 5
STOCK = 5 + C          # 9
BUY = 1 + A            # 2
BOOK = "BOOK-" + SID

# 连接候选：优先环境变量，其次本机 27017（正式副本集），最后 27018（临时副本集）
CANDIDATES = [
    os.environ.get("MONGO_URI"),
    "mongodb://127.0.0.1:27017/?replicaSet=rsExam",
    "mongodb://127.0.0.1:27018/?replicaSet=rsExam",
]


def connect():
    tried = []
    for uri in CANDIDATES:
        if not uri:
            continue
        cli = MongoClient(uri, serverSelectionTimeoutMS=3000)
        try:
            cli.admin.command("hello")
        except PyMongoError:
            tried.append(uri)
            cli.close()
            continue
        print("已连接副本集: %s" % uri)
        return cli
    raise SystemExit(
        "无法连接任何副本集，已尝试:\n  " + "\n  ".join(tried)
        + "\nMongoDB 必须以副本集方式启动才能使用事务（参见 readme.txt 的环境准备步骤）。"
    )


client = connect()
examDB = client["exam_" + SID]

examDB.inventory.delete_many({})
examDB.orders.delete_many({})

examDB.inventory.insert_one({
    "_id": BOOK,
    "title": "NoSQL数据库教材",
    "stock": STOCK,
})

print("数据库: exam_%s" % SID)
print("教师用书库存文档: %s" % examDB.inventory.find_one({"_id": BOOK}))
print("orders 文档数: %d" % examDB.orders.count_documents({}))
