# Pandy AI 打标器 - Web 版使用说明

## 🎯 项目介绍

Pandy AI 打标器 Web 版是一个现代化的图片打标工具，采用 **Web UI (HTML/CSS/JS) + Python Flask 后端** 架构，支持多 API 渠道、批量处理、实时预览等功能。

### ✨ 核心特性

- 🎨 **现代化界面**：基于 TailwindCSS + Alpine.js，卡片式布局，响应式设计
- 🔌 **多渠道支持**：SiliconFlow (硅基流动)、ModelScope (魔塔)、Tuzi API
- 🖼️ **瀑布流网格**：3-4 列自适应布局，缩略图预览
- 📝 **批量操作**：重命名、裁切、添加文本、清空文本
- 🤖 **AI 打标**：支持单图/批量反推，实时进度显示
- 💾 **数据导出**：一键打包 ZIP，包含图片和对应 txt 文件
- 🖥️ **桌面应用**：使用 pywebview 打包成原生桌面程序

---

## 📦 安装步骤

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements_web.txt
```

依赖列表：
- `flask` - Web 框架
- `flask-cors` - 跨域支持
- `pillow` - 图片处理
- `requests` - HTTP 请求
- `pywebview` - 桌面窗口（可选）

### 2. 目录结构

```
pandy_taggertools/
├── backend/
│   ├── app.py              # Flask 主服务
│   ├── api_handler.py      # Vision API 调用
│   ├── image_processor.py  # 图片处理
│   └── config.json         # 配置文件（自动生成）
├── frontend/
│   ├── index.html          # 主界面
│   ├── css/styles.css      # 样式
│   └── js/app.js           # 交互逻辑
├── desktop_launcher.py     # 桌面启动器
├── requirements_web.txt    # 依赖配置
└── README_WEB.md          # 本说明文档
```

---

## 🚀 启动方式

### 方式一：浏览器模式（开发/调试）

1. 启动后端服务：
```bash
cd backend
python app.py
```

2. 打开浏览器访问：
```
http://localhost:5000
```

### 方式二：桌面应用模式（推荐）

直接运行桌面启动器：
```bash
python desktop_launcher.py
```

这将自动启动 Flask 后端并打开桌面窗口。

---

## 🎮 使用指南

### 1️⃣ 配置 API Key

首次使用需要配置 API：

1. 点击右上角 **⚙️ 设置** 按钮
2. 选择 API 渠道（SiliconFlow / ModelScope / Tuzi）
3. 输入对应的 **API Key**
4. 点击 **保存配置**

> **提示**：配置会保存在 `backend/config.json` 文件中

### 2️⃣ 导入图片

**方式一：选择图片**
- 点击界面中央的 **📂 选择图片** 按钮
- 在弹出的输入框中输入图片路径（多个路径用逗号分隔）

**方式二：选择文件夹**
- 点击 **📁 选择文件夹** 按钮
- 输入文件夹路径，程序会自动递归扫描所有图片

> **支持格式**：JPG、PNG、JPEG、WEBP

### 3️⃣ 单图打标

1. 点击图片卡片，打开详情弹窗
2. 左侧显示大图预览
3. 右侧文本编辑框可以手动编辑或点击 **✨ AI 反推** 自动生成
4. 点击 **💾 保存** 保存修改

### 4️⃣ 批量打标

1. 勾选需要处理的图片
2. 点击顶部工具栏的 **✨ 开始反推** 按钮
3. 等待处理完成（可查看进度条）
4. 处理结果会实时更新到卡片上

### 5️⃣ 批量操作

**全选**：快速选中所有图片

**重命名**：
- 勾选图片后点击 **🔄 重命名**
- 输入文件名前缀（如 `lora_data`）
- 导出时会自动按顺序命名（lora_data_001, lora_data_002...）

**裁切**：
- 勾选图片后点击 **✂ 裁切**
- 输入最长边大小（默认 1024px）
- 导出时会自动等比例缩放

**添加文本**：
- 勾选图片后点击 **📝 添加文本**
- 输入要添加的文本（如 `PD_style`）
- 文本会添加到现有标注的开头

**清空文本**：
- 勾选图片后点击 **🗑 清空文本**
- 确认后清空所选图片的所有标注

### 6️⃣ 导出数据集

1. 勾选需要导出的图片
2. 点击 **⬇️ 导出数据集** 按钮
3. 程序会自动生成 ZIP 文件，包含：
   - 图片文件（应用了重命名和裁切设置）
   - 对应的 `.txt` 标注文件
   - 文件名一一对应

---

## 🎨 界面说明

### 左侧边栏
- **Logo 区域**：显示应用名称
- **选择模型**：下拉选择 Vision 模型
- **系统提示词**：可折叠，自定义 AI 系统指令
- **用户指令**：可折叠，自定义 AI 用户提示词
- **保存配置**：保存当前模型和提示词设置

### 顶部工具栏
- **左侧**：批量操作按钮（全选、重命名、裁切等）
- **右侧**：扩展功能（AI 翻译、图像编辑模型反推 - 未来实现）
- **设置按钮**：打开 API 配置弹窗

### 主内容区
- **图片卡片网格**：瀑布流布局，响应式自适应
- **卡片信息**：
  - 左上角：复选框（多选）
  - 右上角：图片分辨率
  - 中间：缩略图（点击查看详情）
  - 底部：文本预览（3 行截断）+ 文件名 + 状态图标

### 状态图标
- ✅ **成功**：已完成打标
- ⏳ **处理中**：正在 AI 反推
- ❌ **失败**：处理失败
- ⚪ **空闲**：未处理

---

## 🔧 API 端点说明

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/config` | GET | 获取配置 |
| `/api/config` | POST | 保存配置 |
| `/api/images/add` | POST | 添加图片 |
| `/api/images` | GET | 获取所有图片 |
| `/api/images/{id}` | PUT | 更新图片信息 |
| `/api/images/{id}` | DELETE | 删除图片 |
| `/api/images/tag/{id}` | POST | 单图打标 |
| `/api/images/tag` | POST | 批量打标 |
| `/api/tasks/{task_id}` | GET | 获取任务状态 |
| `/api/batch/rename` | POST | 批量重命名 |
| `/api/batch/add-text` | POST | 批量添加文本 |
| `/api/batch/clear-text` | POST | 批量清空文本 |
| `/api/batch/resize` | POST | 批量裁切 |
| `/api/export` | POST | 导出数据集 |
| `/api/select-folder` | POST | 选择文件夹 |

---

## 📱 打包成桌面应用

### 使用 PyInstaller 打包

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包（Windows）
pyinstaller --onefile --windowed --name "PandyTagger" ^
    --add-data "frontend;frontend" ^
    --add-data "backend;backend" ^
    desktop_launcher.py

# 打包（macOS/Linux）
pyinstaller --onefile --windowed --name "PandyTagger" \
    --add-data "frontend:frontend" \
    --add-data "backend:backend" \
    desktop_launcher.py
```

打包完成后，可执行文件位于 `dist/PandyTagger.exe`（Windows）或 `dist/PandyTagger`（macOS/Linux）。

---

## ❓ 常见问题

### Q: 图片无法加载？
A: 检查图片路径是否正确，确保文件存在且格式为 JPG/PNG/WEBP。

### Q: API 调用失败？
A: 
1. 检查 API Key 是否正确
2. 检查网络连接
3. 查看 Flask 后端日志是否有错误信息

### Q: 浏览器模式下无法选择文件？
A: 由于浏览器安全限制，建议使用桌面应用模式。或者可以手动输入文件路径。

### Q: 如何修改提示词？
A: 在左侧边栏展开"系统提示词"和"用户指令"，编辑后点击"保存配置"。

### Q: 导出的 ZIP 文件在哪里？
A: 默认保存在当前工作目录，文件名格式为 `dataset_YYYYMMDD_HHMMSS.zip`。

---

## 🔄 从旧版 Tkinter 迁移

如果你之前使用的是 `pandy_tagger.py`（Tkinter 版本），可以无缝切换到 Web 版：

1. **配置文件兼容**：Web 版会读取 `config.json`，无需重新配置
2. **功能一致**：所有核心功能都已实现
3. **性能提升**：Web 版内存占用更低，界面更流畅
4. **扩展性更强**：后续功能更新只需修改 HTML/CSS/JS

---

## 🛠️ 技术栈

- **前端**：HTML5 + TailwindCSS + Alpine.js
- **后端**：Flask + Flask-CORS
- **图片处理**：Pillow
- **桌面打包**：pywebview
- **API 调用**：requests

---

## 📝 更新日志

### v2.0.0 (2024-12-12)
- ✨ 全新 Web UI 界面
- 🔌 支持多 API 渠道
- 🎨 瀑布流网格布局
- 📱 桌面应用支持
- 🚀 性能优化

---

## 💬 反馈与支持

如有问题或建议，欢迎提交 Issue 或 PR！

GitHub: https://github.com/7BEII/pandy_taggertools
