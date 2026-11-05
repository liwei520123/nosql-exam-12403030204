# task1 MongoDB 课程信息查询与维护（20 分）

学号 12403030204，个人数据库 `exam_12403030204`，集合 `courses`。

## 文件

| 文件 | 说明 |
|---|---|
| `init_task1.py` | 初始化 3 门课程（仅执行一次；验证业务操作重复执行时不再初始化） |
| `task1.py` | 业务操作：查询、局部更新、防重复新增、核验 |
| `result.txt` | 实际运行输出 |

## 执行

```bash
python init_task1.py     # 仅首次
python task1.py
```

## 实现要点

1. 查询「张老师 + OPEN」课程：用投影 + `$size` 在数据库端计算 `chapters` 数组长度，章节数量不写死。
2. CH02 改标题用 `$set` + 定位符 `$`，只改数组内命中的那个元素，`title`、`teacher`、`status` 及其他章节原样保留。
3. CH03 新增用 `chapters.chapterId: {$ne: "CH03"}` 作为更新条件，实现幂等：章节不存在才 `$push`；连续执行两次 `matched_count` 第二次为 0，CH03 只出现一次。没有先删后插，也没有整档读回替换。
4. 核验：CH02 标题为 `Redis基础与应用-4`，CH03 数量 1，章节总数 3，`teacher`/`status` 保持 `张老师`/`OPEN`。
