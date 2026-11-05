# -*- coding: utf-8 -*-
"""第一题 业务操作脚本：MongoDB 课程信息查询与维护
学号: 12403030204   参数: S=4, A=1, B=0, C=4
运行前提: 已执行 init_task1.py 完成初始化（业务操作不重复初始化）
"""
from pymongo import MongoClient

SID = "12403030204"
S = int(SID[-2:])          # 4
A = S % 3                  # 1
COURSE01 = "COURSE-" + SID + "-01"
NEW_TITLE = "Redis基础与应用-%d" % S      # Redis基础与应用-4
NEW_HOURS = 2 + A                         # 3

client = MongoClient("mongodb://127.0.0.1:27017")
examDB = client["exam_" + SID]
courses = examDB.courses


def line(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


# ---------------------------------------------------------------- 1. 查询课程
line("1. 查询由“张老师”授课且状态为 OPEN 的课程")
pipeline = [
    {"$match": {"teacher": "张老师", "status": "OPEN"}},
    {"$project": {
        "_id": 0,
        "课程编号": "$_id",
        "课程名称": "$title",
        "章节数量": {"$size": "$chapters"},     # 由数组元素个数计算，不写死
    }},
    {"$sort": {"课程编号": 1}},
]
print("%-24s %-12s %s" % ("课程编号", "课程名称", "章节数量"))
for d in courses.aggregate(pipeline):
    print("%-24s %-12s %d" % (d["课程编号"], d["课程名称"], d["章节数量"]))

# ------------------------------------------------------------ 2. 修改章节标题
line("2. 将第01门课程中 CH02 章节标题改为 %s（局部更新）" % NEW_TITLE)
res = courses.update_one(
    {"_id": COURSE01, "chapters.chapterId": "CH02"},
    {"$set": {"chapters.$.title": NEW_TITLE}},     # $ 定位到匹配的那个数组元素
)
print("matched_count = %d, modified_count = %d" % (res.matched_count, res.modified_count))
doc = courses.find_one({"_id": COURSE01})
print("更新后的课程文档:")
for k, v in doc.items():
    print("  %-10s %s" % (k, v))

# ------------------------------------------------------ 3. 增加章节并防止重复
line("3. 向第01门课程增加章节 CH03（连续执行两次，要求不重复）")
for i in range(1, 3):
    res = courses.update_one(
        {"_id": COURSE01, "chapters.chapterId": {"$ne": "CH03"}},   # 已存在则不再匹配
        {"$addToSet": {"chapters": {                                # $addToSet 天然去重
            "chapterId": "CH03",
            "title": "Redis高级操作",
            "hours": NEW_HOURS,
        }}},
    )
    print("第%d次新增: matched_count = %d, modified_count = %d"
          % (i, res.matched_count, res.modified_count))

# ---------------------------------------------------------------- 4. 验证与解释
line("4. 核验结果")
doc = courses.find_one({"_id": COURSE01})
ch02 = [c for c in doc["chapters"] if c["chapterId"] == "CH02"]
ch03 = [c for c in doc["chapters"] if c["chapterId"] == "CH03"]

print("（1）修改后 CH02 的标题        : %s" % ch02[0]["title"])
print("（2）两次新增后 CH03 的数量    : %d" % len(ch03))
print("（3）最终章节总数              : %d" % len(doc["chapters"]))
print("（4）teacher / status 是否保持  : %s / %s（原值 张老师 / OPEN）"
      % (doc["teacher"], doc["status"]))
print("    最终章节明细:")
for c in doc["chapters"]:
    print("      %-5s %-16s %d 学时" % (c["chapterId"], c["title"], c["hours"]))


