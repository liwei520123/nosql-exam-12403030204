# -*- coding: utf-8 -*-
"""第二题 业务脚本：MongoDB 原子扣减与事务验证
学号: 12403030204   S=4, A=1, B=0, C=4  ->  Stock=5+C=9, Buy=1+A=2
运行前提: MongoDB 必须为副本集（单节点副本集即可），事务才能生效。
连接串可用环境变量 MONGO_URI 覆盖，默认 mongodb://127.0.0.1:27017/?replicaSet=rsExam
"""
import os

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

SID = "12403030204"
S = int(SID[-2:])
A = S % 3
C = S % 5
STOCK = 5 + C                      # 9
BUY = 1 + A                        # 2
BOOK = "BOOK-" + SID

# 连接候选：优先环境变量，其次本机 27017（正式副本集），最后 27018（临时副本集）
CANDIDATES = [
    os.environ.get("MONGO_URI"),
    "mongodb://127.0.0.1:27017/?replicaSet=rsExam",
    "mongodb://127.0.0.1:27018/?replicaSet=rsExam",
]


def connect():
    """自动挑选可用副本集，事务必须运行在副本集上。"""
    global URI_USED
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
        URI_USED = uri
        print("已连接副本集: %s" % uri)
        return cli
    raise SystemExit(
        "无法连接任何副本集，已尝试:\n  " + "\n  ".join(tried)
        + "\nMongoDB 必须以副本集方式启动才能使用事务（参见 readme.txt 的环境准备步骤）。"
    )


URI_USED = None
client = connect()
examDB = client["exam_" + SID]
inventory = examDB.inventory
orders = examDB.orders


def line(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def reset(stock):
    """场景隔离：单独重置 inventory 与 orders，不让前一场景影响后一场景。"""
    inventory.delete_many({})
    orders.delete_many({})
    inventory.insert_one({"_id": BOOK, "title": "NoSQL数据库教材", "stock": stock})
    return stock


# ================================================== 1. 单文档原子扣减（无条件查询）
def deduct(book_id=BOOK):
    """把库存条件检查与扣减合并为一次单文档原子更新。

    返回 (状态, 扣减后的库存文档或 None)
    """
    try:
        doc = inventory.find_one_and_update(
            {"_id": book_id, "stock": {"$gte": BUY}},   # 编号 + 库存条件同时筛选
            {"$inc": {"stock": -BUY}},                  # 条件满足才扣减
            return_document=ReturnDocument.AFTER,
        )
    except PyMongoError as e:                            # 数据库/驱动层异常
        return ("数据库执行异常（%s）" % type(e).__name__, None)

    if doc is not None:
        return ("扣减成功", doc)
    # 返回 None：要么库存不足，要么教材不存在，用一次存在性查询区分
    if inventory.count_documents({"_id": book_id}) == 0:
        return ("教材不存在", None)
    return ("库存不足", None)


# ======================================================== 3. 事务化订购（题3）
class InsufficientStock(Exception):
    """库存不足：用于在事务内部中止并回滚。"""


def place_order(request_id, force_error=False):
    """订购函数：库存扣减与订单插入在同一事务、同一会话内完成。

    只有事务提交成功才返回 True。
    """

    def txn(session):
        doc = inventory.find_one_and_update(
            {"_id": BOOK, "stock": {"$gte": BUY}},
            {"$inc": {"stock": -BUY}},
            session=session,                       # 与下面 insert 共用同一会话
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            raise InsufficientStock("库存低于购买数量，扣减未执行")

        if force_error:
            # 扣减已发生、订单尚未插入时主动抛异常 -> 事务回滚
            raise RuntimeError("forceError=True：扣减后、插入订单前主动抛出异常")

        orders.insert_one(
            {
                "_id": request_id,
                "bookId": BOOK,
                "studentId": SID,
                "quantity": BUY,
            },
            session=session,
        )
        return doc["stock"]

    with client.start_session() as session:
        try:
            left = session.with_transaction(txn)   # 自动 commit / abort / 重试瞬态错误
            return True, left, ""
        except InsufficientStock as e:
            return False, None, str(e)
        except Exception as e:                     # 含 forceError 抛出的 RuntimeError
            return False, None, "%s: %s" % (type(e).__name__, e)


line("题目参数")
print("SID = %s" % SID)
print("S = %d, A = %d, B = %d, C = %d" % (S, A, S % 4, C))
print("Stock = 5+C = %d,  Buy = 1+A = %d,  教材编号 = %s" % (STOCK, BUY, BOOK))
print("连接: %s" % URI_USED)

# ------------------------------------------------------------ 1. 原子扣减演示
line("1. 实现原子扣减（筛选编号+库存条件，一次更新完成）")
reset(STOCK)
print("扣减前库存: %d" % inventory.find_one({"_id": BOOK})["stock"])
state, doc = deduct()
print("状态: %s，扣减后库存: %d" % (state, doc["stock"]))

# ------------------------------------------------------------ 2. 三种结果判定
line("2. 根据数据库返回结果判断操作结果")
reset(STOCK)
state, doc = deduct()
print("（1）库存充足      -> %s（返回文档 stock=%d）" % (state, doc["stock"]))
reset(BUY - 1)
state, doc = deduct()
print("（2）库存不足      -> %s（返回 None 且文档存在）" % state)
state, doc = deduct("BOOK-NOT-EXIST")
print("    教材不存在    -> %s（返回 None 且文档不存在）" % state)
reset(STOCK)
try:
    inventory.find_one_and_update({"_id": BOOK}, {"$inc": {"stock": -BUY}, "$badOperator": {}})
except PyMongoError as e:
    print("（3）数据库执行异常 -> 捕获 %s，程序继续运行" % type(e).__name__)

# ------------------------------------------------------------ 3. 事务化订购演示
line("3. 实现事务 place_order(request_id, force_error=False)")
print("接口: 返回 (是否成功, 剩余库存, 说明)；扣减与插单在同一 session、同一事务内")

# 3.1 force_error=False：正常订购，提交事务
reset(STOCK)
print("\n[forceError=False] 订购前  库存=%d  订单=%d"
      % (inventory.find_one({"_id": BOOK})["stock"], orders.count_documents({})))
ok, left, msg = place_order("REQ-%s-S3-01" % SID, force_error=False)
print("[forceError=False] 订购后  库存=%d  订单=%d  返回: 成功=%s 剩余=%s"
      % (inventory.find_one({"_id": BOOK})["stock"], orders.count_documents({}), ok, left))
print("                   订单文档: %s"
      % [dict(o) for o in orders.find({}, {"_id": 1, "bookId": 1, "quantity": 1})])

# 3.2 forceError=True：扣减后插单前抛异常，事务回滚
reset(STOCK)
print("\n[forceError=True ] 订购前  库存=%d  订单=%d"
      % (inventory.find_one({"_id": BOOK})["stock"], orders.count_documents({})))
ok, left, msg = place_order("REQ-%s-S3-02" % SID, force_error=True)
print("[forceError=True ] 订购后  库存=%d  订单=%d  返回: 成功=%s 说明=%s"
      % (inventory.find_one({"_id": BOOK})["stock"], orders.count_documents({}), ok, msg))
print("                   结论: 扣减已执行但事务回滚，库存与订单均回到订购前状态")

# ---------------------------------------------------------------- 4. 系统测试
line("4. 系统测试（每个场景前单独重置 inventory 和 orders）")
print("%-10s %-8s %-8s %-10s %-10s %-10s %-12s %s"
      % ("场景", "初始库存", "购买数量", "成功次数", "失败次数", "最终库存", "最终订单数量", "核验"))

cases = [
    # (场景编号, 初始库存, 订购次数, forceError)
    ("T1", STOCK, 1, False),
    ("T2", BUY - 1, 1, False),
    ("T3", STOCK, 1, True),
    ("T4", STOCK, STOCK // BUY + 1, False),
]

all_passed = True
for name, init_stock, times, force_error in cases:
    start_stock = reset(init_stock)

    ok = fail = 0
    reasons = []
    for i in range(times):
        request_id = "REQ-%s-%s-%02d" % (SID, name, i + 1)   # 每次订购编号唯一
        success, _, msg = place_order(request_id, force_error=force_error)
        if success:
            ok += 1
        else:
            fail += 1
            reasons.append(msg)

    final_stock = inventory.find_one({"_id": BOOK})["stock"]
    final_orders = orders.count_documents({"bookId": BOOK})

    # 预期值由参数推导，不写死
    capacity = start_stock // BUY
    exp_success = 0 if force_error else min(times, capacity)
    exp_fail = times - exp_success
    exp_stock = start_stock - exp_success * BUY
    exp_orders = exp_success

    passed = (ok == exp_success and fail == exp_fail
              and final_stock == exp_stock and final_orders == exp_orders)
    all_passed = all_passed and passed

    print("%-10s %-8d %-8d %-10d %-10d %-10d %-12d %s"
          % (name, start_stock, BUY, ok, fail, final_stock, final_orders,
             "通过" if passed else "不通过"))
    if reasons:
        print("           失败原因: %s" % reasons[0])
    print("           预期: 成功%d/失败%d/库存%d/订单%d"
          % (exp_success, exp_fail, exp_stock, exp_orders))

print("\n全部场景核验结果: %s" % ("全部通过" if all_passed else "存在不通过场景"))

