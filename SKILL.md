---
name: class-teacher
description: >-
  班主任班务记录技能。使用飞书多维表格作为数据存储，支持学生基本信息、考试成绩、表扬批评等日常表现的自动录入与管理。
  可从文本消息和图片中提取结构化信息自动分类存入对应字段，支持多维度组合查询，并能根据所有数据生成个人综合评价报告（Markdown 或 Word 格式）。
  触发条件：学生记录、班级管理、成绩录入、学生评价、班务记录、考试分析、表扬批评、学生查询、评价报告等。
agent_created: true
---
# 班主任班务记录技能

## 概述

本技能帮助班主任高效管理班级事务。核心能力：
- **信息录入**：从文本/图片中自动提取学生信息、考试成绩、表现记录
- **自动分类**：按内容类型自动写入飞书多维表格的对应表和字段
- **多维度查询**：按学生、科目、考试、时间、类型等组合查询
- **报告生成**：基于全部数据生成个人综合评价报告

**技术方案**：使用飞书 CLI (`lark-cli`) 操作飞书多维表格，无需手写 API 调用代码。

---

## 触发条件（精确匹配）

### 激活触发词（检测到以下意图时立即激活本技能）

**初始化类**（仅首次使用）：
- "初始化班务记录"、"初始化班级管理"、"开始使用班务记录"
- "设置班务助手"、"配置班务系统"

**录入类**：
- 包含"录入"+"成绩/考试/分数"等组合
- 包含"记录"+"表扬/批评/表现/学生"等组合
- "录入学生信息"、"登记成绩"、"记一下"
- 用户上传图片 + 提及学生/成绩/考试相关内容

**查询类**：
- "查一下XX的成绩"、"XX最近表现怎么样"
- "XX考试情况"、"XX的表扬记录"、"XX的批评记录"
- "班级成绩汇总"、"XX科目成绩"

**报告类**：
- "生成XX的评价报告"、"XX的综合评价"
- "写XX的学期评语"、"XX的期末评价"
- "全班评价报告"、"批量生成报告"

**通用触发**：用户消息中同时出现以下**任意2个以上维度**的关键词时激活：
- 人物维度：学生、同学、姓名
- 学业维度：成绩、分数、考试、科目、排名
- 行为维度：表扬、批评、表现、行为、奖惩
- 管理维度：班级、班主任、班务、记录

### 消歧规则
- 纯闲聊（"今天怎么样"）即便是班主任也不触发
- 仅在上下文中明确涉及学生数据管理时才触发
- 如果用户明确拒绝（"不用记录"、"取消"），退出当前工作流

---

## 前置条件检查（每次激活时执行）

### 状态感知：三步检查

**每次激活本技能时，必须在执行任何操作前完成以下检查：**

```
Step 0a: 检查飞书 CLI
  执行: lark-cli auth status
  如果返回错误或未安装:
    → 告知用户需要安装飞书 CLI
    → 提供安装指引: npm install -g @larksuite/cli
    → 然后: lark-cli config init
    → 然后: lark-cli auth login --recommend
    → 等待用户确认完成后再继续

Step 0b: 检查初始化状态
  读取: assets/feishu_config.json
  如果文件不存在:
    → 状态 = 未初始化
    → 需要执行「初始化工作流」
  如果文件存在:
    → 读取 app_token
    → 执行: lark-cli base +base-get --base-token <app_token>
    → 如果成功: 状态 = 已初始化，直接进入用户请求的工作流
    → 如果失败(base不存在): 状态 = 需要重新初始化，询问用户是否重建

Step 0c: 缓存表信息
  如果已初始化:
    → 执行: lark-cli base +table-list --base-token <app_token>
    → 缓存 table_id 映射到内存（不写文件，config.json 已有）
```

### 关键规则：绝不重复创建
- 如果 `assets/feishu_config.json` 存在且 `lark-cli base +base-get` 成功 → **跳过初始化**
- 如果 config.json 存在但 base 已删 → **询问用户**后再决定重建
- 如果 config.json 不存在 → 执行初始化流程

---

## 工作流 1：初始化（仅首次 / 重建时）

### 触发
- 状态检查发现未初始化
- 用户明确说"初始化班务记录"

### 步骤

**1. 飞书 CLI 安装引导**
```
告知用户：
「首次使用需要安装飞书 CLI，请依次执行以下命令：

npm install -g @larksuite/cli

lark-cli config init
（输入 App ID 和 App Secret）

lark-cli auth login --recommend
（浏览器授权即可）

完成后请告诉我，我将自动创建多维表格。」
```

等待用户确认完成后继续。

**2. 创建多维表格 Base**
```bash
lark-cli base +base-create --json '{"name":"班主任班务记录"}'
```
解析返回结果，提取 `app_token`。

**3. 创建三张数据表（使用 table_defs.json 中的字段定义）**

```bash
# 创建学生信息表
lark-cli base +table-create \
  --base-token <app_token> \
  --name "学生信息表" \
  --fields @assets/table_defs.json#student_info

# 创建考试成绩表
lark-cli base +table-create \
  --base-token <app_token> \
  --name "考试成绩表" \
  --fields @assets/table_defs.json#exam_scores

# 创建日常表现表
lark-cli base +table-create \
  --base-token <app_token> \
  --name "日常表现表" \
  --fields @assets/table_defs.json#daily_records
```

**4. 获取 table_id 并保存配置**

```bash
lark-cli base +table-list --base-token <app_token>
```

解析返回结果，提取每张表的 `table_id`。

将配置写入 `assets/feishu_config.json`：

```json
{
  "app_token": "bascnXXX",
  "app_url": "https://bytedance.feishu.cn/base/bascnXXX",
  "tables": {
    "student_info": {"table_id": "tblXXX", "name": "学生信息表"},
    "exam_scores": {"table_id": "tblYYY", "name": "考试成绩表"},
    "daily_records": {"table_id": "tblZZZ", "name": "日常表现表"}
  },
  "initialized_at": "<当前时间ISO格式>"
}
```

**5. 完成提示**

```
🎉 初始化完成！

📊 多维表格：https://bytedance.feishu.cn/base/<app_token>

已创建 3 张数据表：
  · 学生信息表 — 学生基本档案（学号、姓名、性别、班级...）
  · 考试成绩表 — 各科考试成绩及排名
  · 日常表现表 — 表扬、批评、行为记录

💡 现在可以对我说「录入学生信息」或「记录考试成绩」开始使用了！
```

---

## 工作流 2：信息录入

### 前置确认
- 状态检查已完成，确认已初始化
- 读取 `assets/feishu_config.json` 获取 `app_token` 和 `table_ids`

### 步骤

**1. 接收输入**

用户可能提供：
- 纯文本：如 "张三期中考试数学95分、语文88分，李四数学92分"
- 纯文本：如 "表扬张三主动帮助同学打扫卫生"
- 图片：成绩单截图、手写评语照片（通过 WorkBuddy 的 Read 工具读取）

**2. 解析内容**

调用 `scripts/parse_input.py` 进行结构化解析：

```bash
python scripts/parse_input.py --text "<用户输入文本>" --output /tmp/parsed_result.json
```

如果是图片：先用 WorkBuddy 的 Read 工具读取图片内容，提取文字，再传给 parse_input.py。

解析结果 JSON 格式：
```json
{
  "records": [
    {"type": "exam", "table": "exam_scores", "fields": {"学生姓名":"张三","考试名称":"期中考试","科目":"数学","成绩":95,"满分":100}},
    {"type": "performance", "table": "daily_records", "fields": {"学生姓名":"张三","记录类型":"表扬","具体内容":"主动帮助同学打扫卫生"}}
  ],
  "new_fields": [
    {"table": "exam_scores", "field_name": "科目", "value": "信息技术"}
  ],
  "summary": {"total": 2, "exam_count": 1, "performance_count": 1, "student_count": 0}
}
```

**3. 展示解析结果并请求确认**

将解析结果以清晰格式展示给用户：
```
📝 已识别以下信息，请确认：

【考试成绩】
  1. 张三 - 数学 - 95分 - 期中考试
  2. 张三 - 语文 - 88分 - 期中考试

【日常表现】
  3. [表扬] 张三 - 主动帮助同学打扫卫生

📊 共计 3 条记录待录入。

⚠️ 检测到可能需要新增的字段：
  · 考试成绩表 → 科目 =「信息技术」

请问是否全部正确？(确认/修改/取消)
```

**4. 处理新字段（如有）**

如果 `new_fields` 非空，先处理新字段：
```bash
# 向单选字段添加新选项
lark-cli base +field-update \
  --base-token <app_token> \
  --table-id <table_id> \
  --field-id <field_name> \
  --json '{"property":{"options":[{"name":"信息技术"}]}}'
```
提示用户新字段已添加。

**5. 写入飞书多维表格**

按表分组，逐表写入：

```bash
# 写入考试成绩表
lark-cli base +record-upsert \
  --base-token <app_token> \
  --table-id <exam_scores_table_id> \
  --json '{"fields":{"学生姓名":"张三","考试名称":"期中考试","科目":"数学","成绩":95,"满分":100,"考试日期":"<今日日期>"}}'

# 多条记录逐一调用（飞书 CLI 支持单条 upsert）
```

**写入策略**：
- 先按表分组
- 每条记录调用一次 `+record-upsert`（飞书 CLI 尚无批量 upsert 命令）
- 如果某条写入失败，记录错误并继续写入下一条
- 写入完成后，输出汇总

**6. 反馈结果**

```
✅ 录入完成！

- 考试成绩表：新增 2 条记录
- 日常表现表：新增 1 条记录

飞书多维表格已同步更新 ✓
查看：https://bytedance.feishu.cn/base/<app_token>
```

---

## 工作流 3：信息查询

### 步骤

**1. 解析查询意图**

从用户消息中提取查询参数：
- 学生姓名：如 "张三"
- 科目：如 "数学"
- 考试名称：如 "期中考试"
- 记录类型：表扬 / 批评 / 行为记录 / 奖惩
- 时间范围：如 "最近"、"上周"、"3月"

**2. 执行查询**

```bash
# 查询学生基本信息
lark-cli base +record-list \
  --base-token <app_token> \
  --table-id <student_info_table_id> \
  --page-all

# 查询考试成绩（按学生+科目过滤）
# 飞书 CLI 的 filter 需要构造为飞书 filter 表达式
lark-cli base +record-list \
  --base-token <app_token> \
  --table-id <exam_scores_table_id> \
  --page-all

# 查询日常表现
lark-cli base +record-list \
  --base-token <app_token> \
  --table-id <daily_records_table_id> \
  --page-all
```

**3. 筛选与跨表汇总**

CLI 返回的原始数据由 AI 进行筛选、关联和格式化：
- 按学生姓名筛选成绩记录
- 按科目/时间进一步过滤
- 跨表关联：通过"姓名"字段关联学生信息表
- 排序：按日期降序展示

**4. 格式化输出**

以清晰的表格/列表展示结果：

```
📊 查询结果 — 张三

👤 基本信息：张三 | 学号 202401001 | 男 | 高一(3)班

📝 考试成绩（最近 5 条）：
| 考试 | 科目 | 成绩 | 班级排名 | 日期 |
|------|------|------|---------|------|
| 期中 | 数学 | 95 | 3 | 2024-04-15 |
| 期中 | 语文 | 88 | 8 | 2024-04-15 |

📋 日常表现（最近 5 条）：
· 2024-03-15 | 🌟 表扬 | 主动帮助同学打扫卫生
· 2024-03-10 | 📌 行为记录 | 参加校运动会100米获第2名

📊 统计：成绩 8 条 | 表现 3 条 | 表扬 1 次 | 批评 0 次
```

---

## 工作流 4：报告生成

### 步骤

**1. 拉取数据**

为指定学生从三张表拉取全部数据：

```bash
lark-cli base +record-list \
  --base-token <app_token> \
  --table-id <student_info_table_id> \
  --page-all

lark-cli base +record-list \
  --base-token <app_token> \
  --table-id <exam_scores_table_id> \
  --page-all

lark-cli base +record-list \
  --base-token <app_token> \
  --table-id <daily_records_table_id> \
  --page-all
```

**2. 调用报告生成脚本**

将 CLI 返回的原始数据保存为临时 JSON 文件，调用报告生成脚本：

```bash
python scripts/generate_report.py \
  --student "张三" \
  --data /tmp/student_data.json \
  --format md
```

**3. 输出报告**

默认以 Markdown 格式在对话中展示。用户可要求导出为 Word：

```
如需 Word 格式，使用 docx 技能将 Markdown 内容转换导出。
```

**4. 批量模式**

如果用户请求"全班评价报告"：

```bash
# 先获取班级学生名单
lark-cli base +record-list --base-token <app_token> --table-id <student_info_table_id> --page-all

# AI 筛选出指定班级的学生
# 对每个学生依次执行步骤 1-3
# 将每份报告保存为独立文件
```

---

## 数据表结构速查

### 学生信息表 (student_info)
| 字段名 | type | 属性 |
|--------|------|------|
| 学号 | 1 (文本) | 主键 |
| 姓名 | 1 (文本) | |
| 性别 | 3 (单选) | 男/女 |
| 出生日期 | 5 (日期) | yyyy/MM/dd |
| 班级 | 1 (文本) | |
| 联系电话 | 13 (电话) | |
| 家庭地址 | 1 (文本) | |
| 备注 | 1 (文本) | |

### 考试成绩表 (exam_scores)
| 字段名 | type | 属性 |
|--------|------|------|
| 学生姓名 | 1 (文本) | |
| 考试名称 | 1 (文本) | |
| 科目 | 3 (单选) | 语数英物化生史地政 |
| 成绩 | 2 (数字) | 支持小数 |
| 满分 | 2 (数字) | |
| 考试日期 | 5 (日期) | yyyy/MM/dd |
| 班级排名 | 2 (数字) | |
| 年级排名 | 2 (数字) | |
| 班级 | 1 (文本) | |
| 备注 | 1 (文本) | |

### 日常表现表 (daily_records)
| 字段名 | type | 属性 |
|--------|------|------|
| 学生姓名 | 1 (文本) | |
| 记录类型 | 3 (单选) | 表扬/批评/行为记录/奖惩 |
| 具体内容 | 1 (文本) | |
| 记录日期 | 5 (日期) | yyyy/MM/dd |
| 科目场景 | 1 (文本) | |
| 严重程度 | 3 (单选) | 一般/较重/严重 |
| 班级 | 1 (文本) | |

---

## 参考资源

- **飞书 CLI 安装与认证**：参考 `references/feishu_cli_guide.md`
- **表格字段定义**：`assets/table_defs.json`（JSON 格式，供 `+table-create --fields @` 使用）
- **初始化引导**：参考 `assets/init_guide.md`（首次使用教程）
- **排错指南**：参考 `references/troubleshooting.md`
- **信息解析逻辑**：`scripts/parse_input.py` — 独立的文本解析脚本，无外部依赖
- **报告生成**：`scripts/generate_report.py` — 接收 JSON 数据生成 Markdown 报告

---

## 错误处理

### 飞书 CLI 未安装
```
❌ 检测到飞书 CLI 未安装。

请执行：npm install -g @larksuite/cli
安装完成后运行：lark-cli config init
然后：lark-cli auth login --recommend
最后告诉我「已完成」，我将继续。
```

### 认证过期
```
⚠️ 飞书认证已过期。

请执行：lark-cli auth login --recommend
完成后告诉我。
```

### 写入失败
某条记录写入失败时：
```
⚠️ 以下记录写入失败：
  · 张三 - 数学 - 95分：理由=字段不存在
其他 4 条记录已成功写入。
```

### 配置丢失
```
⚠️ 本地配置丢失但多维表格仍然存在。

请提供多维表格的 URL 链接（如 https://bytedance.feishu.cn/base/bascnXXX），
我将从链接中提取 app_token 并重建本地配置。
```
