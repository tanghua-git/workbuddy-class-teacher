# 初始化引导 — 班主任班务记录（飞书 CLI 版）

## 超简三步安装

相比手动 API 配置方案，使用飞书 CLI 后操作大幅简化：

### 第一步：安装飞书 CLI（一次性）

```bash
npm install -g @larksuite/cli
```

### 第二步：配置认证（一次性）

```bash
lark-cli config init
# 输入 App ID 和 App Secret（需先在 open.feishu.cn 创建应用）

lark-cli auth login --recommend
# 浏览器打开授权页面 → 点击确认
```

### 第三步：启动班务记录

在 WorkBuddy 对话中说：

> **初始化班务记录**

AI 将自动：
1. 检测飞书 CLI 状态
2. 创建多维表格 + 三张数据表
3. 保存配置

---

## 前置准备清单

- [ ] 飞书企业账号（标准版/企业版）
- [ ] 在 [open.feishu.cn](https://open.feishu.cn/app) 创建企业自建应用
- [ ] 应用添加「机器人」能力
- [ ] 权限已配置（使用 `--recommend` 自动最小权限）
- [ ] 已获取 App ID 和 App Secret
- [ ] Node.js 16+ 已安装

### 创建飞书应用的步骤

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 创建「企业自建应用」→ 名称建议：**班主任班务助手**
3. 添加「机器人」能力
4. 获取 App ID 和 App Secret（凭证与基础信息页面）
5. 发布应用 → 创建版本 → 管理员审批

---

## 权限说明

飞书 CLI 的 `--recommend` 会自动选择最小必要权限，涵盖：

```
base:app:* (多维表格应用)
base:table:* (数据表)
base:field:* (字段)
base:record:* (记录)
base:view:* (视图)
```

无需手动逐条勾选！

---

## 数据存储

所有凭证安全存储于操作系统原生密钥链：
- macOS：钥匙串
- Windows：凭据管理器
- Linux：Secret Service

无明文 `.env` 文件，更安全。

---

## 验证安装

```bash
lark-cli auth status      # 检查认证状态
lark-cli doctor           # 综合诊断
```

---

## 常用命令速查

```bash
# 查看 Base 信息
lark-cli base +base-get --base-token bascnXXX

# 列出所有表
lark-cli base +table-list --base-token bascnXXX

# 查询记录
lark-cli base +record-list --base-token bascnXXX --table-id tblXXX --page-all

# 写入记录
lark-cli base +record-upsert --base-token bascnXXX --table-id tblXXX \
  --json '{"fields":{"学生姓名":"张三","科目":"数学","成绩":95}}'
```

---

遇到问题？在 WorkBuddy 对话中描述你的问题，AI 会协助排查。
