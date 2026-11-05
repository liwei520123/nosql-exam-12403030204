# -*- coding: utf-8 -*-
"""第一题 初始化脚本：建立个人数据库与 courses 集合的初始数据。
与业务操作代码（task1.py）分开，业务验证时不得重复执行本脚本。
"""
from pymongo import MongoClient

SID = "12403030204"

client = MongoClient("mongodb://127.0.0.1:27017")
examDB = client["exam_" + SID]

examDB.courses.delete_many({})

examDB.courses.insert_many([
    {
        "_id": "COURSE-" + SID + "-01",
        "title": "NoSQL数据库",
        "teacher": "张老师",
        "status": "OPEN",
        "chapters": [
            {"chapterId": "CH01", "title": "MongoDB基础", "hours": 2},
            {"chapterId": "CH02", "title": "Redis基础", "hours": 2},
        ],
    },
    {
        "_id": "COURSE-" + SID + "-02",
        "title": "数据库原理",
        "teacher": "张老师",
        "status": "CLOSED",
        "chapters": [
            {"chapterId": "CH01", "title": "关系模型", "hours": 2},
        ],
    },
    {
        "_id": "COURSE-" + SID + "-03",
        "title": "机器学习",
        "teacher": "李老师",
        "status": "OPEN",
        "chapters": [
            {"chapterId": "CH01", "title": "分类", "hours": 2},
            {"chapterId": "CH02", "title": "聚类", "hours": 2},
        ],
    },
])

print("数据库: exam_%s，courses 集合文档数: %d" % (SID, examDB.courses.count_documents({})))
