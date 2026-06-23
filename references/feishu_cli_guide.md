# 飞书 CLI 常用命令速查

## 认证与管理

```bash
lark-cli auth status              # 检查认证状态
lark-cli auth login --recommend   # 登录（自动最小权限）
lark-cli config init              # 交互式配置 App ID/Secret
lark-cli doctor                   # 综合诊断
```

## Base（多维表格应用）

```bash
# 创建 Base
lark-cli base +base-create --json '{"name":"班主任班务记录"}'

# 获取 Base 信息
lark-cli base +base-get --base-token bascnXXX

# 复制 Base
lark-cli base +base-copy --base-token bascnXXX --json '{"name":"备份"}'
```

## 数据表

```bash
# 创建表（带字段定义）
lark-cli base +table-create \
  --base-token bascnXXX \
  --name "学生信息表" \
  --fields @assets/table_defs.json#student_info

# 列出所有表
lark-cli base +table-list --base-token bascnXXX

# 获取表详情
lark-cli base +table-get --base-token bascnXXX --table-id tblXXX
```

## 记录

```bash
# 列出记录（全量）
lark-cli base +record-list \
  --base-token bascnXXX \
  --table-id tblXXX \
  --page-all

# 创建/更新记录
lark-cli base +record-upsert \
  --base-token bascnXXX \
  --table-id tblXXX \
  --json '{"fields":{"学生姓名":"张三","科目":"数学","成绩":95}}'

# 获取单条记录
lark-cli base +record-get \
  --base-token bascnXXX \
  --table-id tblXXX \
  --record-id recXXX

# 删除记录
lark-cli base +record-delete \
  --base-token bascnXXX \
  --table-id tblXXX \
  --record-id recXXX \
  --dry-run
```

## 字段

```bash
# 列出字段
lark-cli base +field-list --base-token bascnXXX --table-id tblXXX

# 创建字段
lark-cli base +field-create \
  --base-token bascnXXX \
  --table-id tblXXX \
  --json '{"field_name":"新科目","type":3,"property":{"options":[{"name":"选项1"}]}}'

# 更新字段（添加选项）
lark-cli base +field-update \
  --base-token bascnXXX \
  --table-id tblXXX \
  --field-id fldXXX \
  --json '{"property":{"options":[{"name":"新选项"}]}}'
```

## 字段类型编码

| 编码 | 类型 | 说明 |
|------|------|------|
| 1 | 文本 | 普通文字 |
| 2 | 数字 | 支持小数 |
| 3 | 单选 | 需要 options |
| 4 | 多选 | 需要 options |
| 5 | 日期 | 毫秒时间戳 |
| 7 | 复选框 | true/false |
| 11 | 人员 | 飞书用户ID |
| 13 | 电话号码 | |
| 15 | 超链接 | |
| 17 | 附件 | |
| 18 | 单向关联 | |
| 21 | 双向关联 | |
