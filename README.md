# RAG 知识库问答系统

基于大语言模型（LLM）的 RAG（Retrieval‑Augmented Generation）智能问答系统，支持 **API** 与 **本地 Ollama** 两种模式，可用于企业文档、规章制度、审计报告等领域的知识管理与检索式问答。

---

## 功能特性

- **多模式大模型接入**  
  同时支持 OpenAI 兼容 API 和本地 Ollama 模型，Chat 与 Embedding 模型可独立配置。
- **知识库管理**  
  管理员可上传 .docx 文件，自动分块、向量化并存入 ChromaDB 向量数据库，支持 200 万字级文档。
- **RAG 问答**  
  用户提问后先检索相关知识片段，再结合 LLM 生成回答，附带可折叠思维链（Chain of Thought）。
- **用户权限**  
  区分管理员与普通用户，管理员可管理用户、配置系统、处理文件；普通用户仅可使用问答功能。
- **现代化聊天界面**  
  对话界面，支持历史对话管理、Markdown 渲染、一键复制。
- **安全与日志**  
  登录验证码、会话超时自动退出、完整的用户操作日志和系统日志。
- **跨平台**  
  纯 Python 实现，可在 Windows、macOS、Linux 上运行，适配手机与桌面浏览器。

---

## 技术栈

| 类型 | 技术 |
|------|------|
| 后端框架 | Flask + Flask‑Login |
| 数据库 | SQLite + SQLAlchemy |
| 向量存储 | ChromaDB（持久化，余弦相似度） |
| 大模型调用 | OpenAI Python SDK / Ollama HTTP API |
| 文档解析 | python‑docx |
| 前端 | Jinja2 + 原生 JavaScript + CSS（Flex / Grid） |
| 验证码 | Pillow 生成纯数字图片 |

---

## 环境要求

- **Python 3.9+**（推荐 3.11）
- **pip** 包管理工具
- **Ollama**（可选，使用本地模型时需要）

---

## ⚙️ 安装与运行

### 1. 获取项目文件
将所有代码及文件夹（`templates/`、`static/`、`data/`、`uploads/`、`chroma_db/`、`logs/`）放置在同一目录下。

### 2. 创建虚拟环境（推荐）
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

### 3. 安装依赖
```bash
pip install -r requirements.txt

### 4. 启动应用
```bash
python app.py


