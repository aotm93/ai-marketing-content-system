# Antigravity AI 系统 Google Search Console 配置指南

本指南将指导您如何使用“服务账号 (Service Account)”将 Google Search Console (GSC) 连接到 Antigravity AI 系统。这是独立于 Rank Math 的连接，专门用于让 AI 代理获取数据进行分析。

---

## 为什么要单独连接？
Rank Math 仅在 WordPress 后台为**人类**展示图表。  
而我们需要下载原始数据供 **AI 代理** (Python 后端) 使用，以便进行机会评分、自动选题和内容规划。AI 无法读取 Rank Math 的图表。

---

## 第一步：创建 Google 服务账号 (Service Account)
1.  访问 [Google Cloud Console (谷歌云控制台)](https://console.cloud.google.com/)。
2.  创建一个 **新项目 (New Project)** (例如命名为 "Antigravity-SEO")。
3.  在该项目中启用 **Google Search Console API**。
    *   在搜索框输入 "Google Search Console API" -> 点击启用 (Enable)。
4.  进入 **IAM & Admin (IAM 和管理)** > **Service Accounts (服务账号)**。
5.  点击 **Create Service Account (创建服务账号)** (例如命名为 `seo-bot`)。
6.  创建完成后，点击该账号进入详情。
7.  点击 **Keys (密钥)** 标签页 > **Add Key (添加密钥)** > **Create New Key (创建新密钥)** > 选择 **JSON**。
8.  一个 `.json` 文件会自动下载到您的电脑。**请妥善保管此文件。**

## 第二步：在 Search Console 中授权
1.  打开刚才下载的 JSON 文件，复制里面的 `client_email` 地址 (例如 `seo-bot@antigravity.iam.gserviceaccount.com`)。
2.  进入 [Google Search Console](https://search.google.com/search-console)。
3.  选择您的网站资源 (`sc-domain:example.com` 或 `https://...`)。
4.  点击左侧 **Settings (设置)** > **Users and permissions (用户和权限)**。
5.  点击 **Add User (添加用户)**。
6.  粘贴刚才复制的 `client_email` 地址。
7.  权限选择：**Full (完整)** (Restricted 也可以，但完整权限能避免读取错误)。

## 第三步：配置 Antigravity 管理后台
1.  打开本地管理后台：`http://localhost:8000/admin`。
2.  滚动到 **Google Search Console (P1)** 区域。
3.  **Site URL (网站地址)**: 准确输入 GSC 中的资源名称 (例如 `sc-domain:mysite.com` 或 URL)。
4.  **Auth Method (认证方式)**: 选择 `Service Account`。
5.  **Service Account JSON Content**: 用文本编辑器打开您的 JSON 文件，复制 **全部内容** (从 `{` 开始到 `}` 结束)，粘贴到此输入框中。
6.  点击 **Save All Changes (保存所有更改)**。

## 第四步：验证
1.  如果在后台修改了配置，建议重启后端服务以确保生效 (Ctrl+C 然后重新运行 `uvicorn`)。
2.  系统将会根据配置 (默认每 24 小时) 自动同步数据。
