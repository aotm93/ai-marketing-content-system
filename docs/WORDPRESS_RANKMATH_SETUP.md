# WordPress Rank Math SEO 插件配置指南

## 概述

本系统使用 **Rank Math SEO** 插件来优化 WordPress 网站的 SEO 设置。本指南将帮助您正确配置 Rank Math SEO 插件以与 AI 营销内容系统集成。

## 前提条件

1. WordPress 网站已安装并运行
2. 具有管理员权限的 WordPress 账户
3. WordPress REST API 已启用（默认启用）

## 第一步：安装 Rank Math SEO 插件

### 方法 1：通过 WordPress 后台安装

1. 登录 WordPress 管理后台
2. 导航到 **插件 → 安装插件**
3. 搜索 "Rank Math SEO"
4. 点击 **立即安装**
5. 安装完成后，点击 **启用**

### 方法 2：手动安装

1. 访问 [Rank Math SEO 官网](https://rankmath.com/)
2. 下载插件 ZIP 文件
3. 在 WordPress 后台，导航到 **插件 → 安装插件 → 上传插件**
4. 选择下载的 ZIP 文件并上传
5. 点击 **立即安装**，然后 **启用**

## 第二步：Rank Math SEO 初始设置

### 1. 运行设置向导

启用插件后，Rank Math 会自动启动设置向导：

1. **欢迎页面**：点击 "Start Wizard"
2. **导入设置**（可选）：如果从其他 SEO 插件迁移，选择导入；否则选择 "Skip"
3. **站点类型**：选择您的网站类型（例如：Business, Blog, E-commerce）
4. **Logo 和社交资料**：
   - 上传网站 Logo
   - 填写社交媒体链接（Facebook, Twitter, Instagram 等）
5. **Sitemap 设置**：保持默认设置，启用 XML Sitemap
6. **SEO 优化**：选择推荐的优化选项
7. **完成设置**：点击 "Finish" 完成向导

### 2. 配置 REST API 访问

为了让 AI 系统能够通过 API 发布内容，需要启用 REST API：

1. 在 WordPress 后台，导航到 **Rank Math → General Settings**
2. 点击 **Links** 标签
3. 确保 REST API 相关选项已启用
4. 保存更改

## 第三步：创建 WordPress 应用密码

为了安全地连接 AI 系统和 WordPress，需要创建应用密码：

1. 登录 WordPress 后台
2. 导航到 **用户 → 个人资料**
3. 滚动到页面底部，找到 **应用密码** 部分
4. 在 "新应用密码名称" 字段中输入：`AI Marketing System`
5. 点击 **添加新应用密码**
6. **重要**：复制生成的密码并保存到安全的地方（此密码只显示一次）
7. 在 AI 系统管理后台配置时使用此密码

## 第四步：配置 Rank Math SEO 设置

### 1. 文章和页面 SEO 设置

1. 导航到 **Rank Math → Titles & Meta**
2. 配置 **Posts** 标签：
   - SEO Title: `%title% %sep% %sitename%`
   - Meta Description: `%excerpt%`
   - 启用 "Show in Search Results"
3. 配置 **Pages** 标签（同上）
4. 保存更改
