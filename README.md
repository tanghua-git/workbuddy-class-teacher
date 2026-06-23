# 班主任班务记录技能 (Class Teacher Record Skill)

面向中小学班主任的 WorkBuddy AI 技能，使用飞书多维表格管理班级事务。

## 核心功能

- **信息录入** — 从文本/图片中自动提取学生信息、考试成绩、表现记录
- **自动分类** — 按内容类型自动写入飞书多维表格对应表和字段
- **多维度查询** — 按学生、科目、考试、时间、类型等组合查询
- **报告生成** — 基于全部数据生成个人综合评价报告（Markdown / Word）

## 安装前提

1. **飞书企业账号**（标准版/企业版）
2. 在 [飞书开放平台](https://open.feishu.cn/app) 创建企业自建应用
3. **Node.js 16+** + 飞书 CLI

## 快速开始

```bash
npm install -g @larksuite/cli

lark-cli config init          # 输入 App ID / App Secret
lark-cli auth login --recommend

cp -r class-teacher/ ~/.workbuddy/skills/class-teacher/
```

然后在 WorkBuddy 中说：**"初始化班务记录"**

## 技能结构

```
class-teacher/
├── SKILL.md                    # 技能主文件
├── assets/
│   ├── table_defs.json         # 三张表字段定义
│   └── init_guide.md           # 初始化引导
├── references/
│   ├── feishu_cli_guide.md     # 飞书 CLI 命令速查
│   └── troubleshooting.md      # 排错指南
└── scripts/
    ├── parse_input.py           # 文本解析引擎
    └── generate_report.py       # 报告生成
```

## 数据表设计

| 表名 | 用途 | 核心字段 |
|------|------|---------|
| 学生信息表 | 学生基本档案 | 学号、姓名、性别、班级、电话 |
| 考试成绩表 | 各科考试记录 | 学生、科目、成绩、排名、日期 |
| 日常表现表 | 表扬/批评/行为 | 学生、类型、内容、严重程度 |

## 常见问题

请看 `references/troubleshooting.md`
