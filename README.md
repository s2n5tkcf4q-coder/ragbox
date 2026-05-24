# RAG 知识库问答系统

基于大语言模型（LLM）的 RAG（Retrieval‑Augmented Generation）智能问答系统，支持 **API** 与 **本地 Ollama** 两种模式，可用于个人及企业文档、规章制度、报告等领域的知识管理与检索式问答。 系统本地部署使用ollama所有数据及运算都在本地处理运行，**可放心处理隐私和绝密文件** ，不存在泄密的可能。

---

## 功能特性

- 同时支持 OpenAI 兼容 API 和本地 Ollama 模型，Chat 与 Embedding 模型可独立配置。
- 管理员可上传 .docx 文件，自动分块、向量化并存入 ChromaDB 向量数据库。
- 用户提问后先检索相关知识片段，再结合 LLM 生成回答，附带思维链（Chain of Thought）。
- 区分管理员与普通用户，管理员可管理用户、配置系统、处理文件；普通用户仅可使用问答功能。
- 登录验证码、会话超时自动退出、完整的用户操作日志和系统日志。
- 纯 Python 实现，可在 Windows、macOS、Linux 上运行，适配手机与桌面浏览器。

---

## 环境要求

- **Python 3.9+**（推荐 3.11）
- **pip** 包管理工具
- **Ollama**（使用本地模型时需要）

---

## 安装与运行

### 1. 获取项目文件
- 点击code直接下载zip文件到本地后解压缩。
- 或使用git安装。
```bash
git clone https://github.com/s2n5tkcf4q-coder/ragbox.git
```

### 2. 创建虚拟环境（推荐）
- 打开cmd/终端，运行以下命令。 
```bash
cd 实际路径/ragbox-main    #或ragbox
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 启动应用
- windows需使用PowerShell
```bash
python app.py
```
- 系统使用**8080**端口，启动后直接访问 [http://127.0.0.1:8080](http://127.0.0.1:8080)
- 如需更改端口，可在app.py文件中找到以下代码，直接修改**8080**到你想要的端口。
```python
app.run(host='0.0.0.0', port=8080, debug=False)
```
- 修改端口注意避开系统默认端口比如：0-1023，1433，3306，5432等。

### 5. windows系统完整部署步骤
- 以下载在d:\ragbox-main为例。
- 到python官网下载python，版本3.9到3.12推荐使用3.11。
#### 1. 以管理员身份运行cmd
```bash
cd d:\ragbox-main
# 创建虚环境
python -m venv venv
# 如果系统有多个python版本，这里需要指定版本
# python3.11 -m venv venv
venv\Scripts\activate
# 安装依赖py包
pip install -r requirements.txt
# 下载失败或速度慢可以尝试使用国内镜像，以下为阿里云镜像。
# pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

#### 2. 以管理员身份运行Windows PowerShell
```bash
cd d:\ragbox-main
# 激活虚拟环境
.\venv\Scripts\Activate.ps1
# 启动主程序
python app.py
# 如果系统禁止脚本运行时需要操作输入以下命令：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# 输入y
```

#### 3. ollama操作
```bash
# 下载安装ollama并确认其在后台运行。
# 运行cmd
# 下载9b的qwen3.5模型
ollama pull qwen3.5:9b
# 下载8b的qwen3-embedding模型
ollama pull qwen3-embedding:8b
# 本地模型下载选择可在ollama官网搜索选择，能够下载的仅为开源模型。
# 查看已下载的模型
ollama list
```

### 6. 登陆系统
- 系统首次启动时初始化管理员用户密码分别为**admin / admin123**。

![登陆界面](/static/img/login.png)

- 登陆界面可自行注册，注册的账户没有管理员的功能，注册登陆后直接跳转问答界面。

### 7. 系统配置
- 管理员登陆后自动跳转到系统配置页面。

![系统设置](/static/img/settings.png)

- 系统需要两个模型，一个为对话模型，一个为嵌入模型。嵌入模型用于文档处理为知识库，对话模型用于基于知识库的问答。
- **ollama**URL固定为 http://127.0.0.1:11434。
- **API**模式URL需在服务商处获取，例如：硅基流动API URL为 https://api.siliconflow.cn/v1
- **ollama**模式可根据部署电脑性能选择模型，对话模型尽量不要选用小参数模型，小模型上下文不足会导致无法运行。ps:测试时使用的都是通义千问的模型，使用0.8b的chat模型无法运行；使用chat模型qwen3.5:9b，Embedding模型qwen3-embedding:8b,在系统默认参数下运行良好。
- **API**模式可在服务商模型广场搜索，模型名中有Embedding的为嵌入模型。
- 选定模型后将模型名称填入相应文本框，**API**模式需提供的API Key可在服务商处获得。
- 模型选择：大量文档检索整理建议使用通用型模型；关联分析建议使用推理型模型。

![系统设置](/static/img/settings2.png)

- 系统提示词用于约束对话，比如希望系统简短回答，直接在文本框内添加"简短回答即可"。
- 其余参数都为默认参数，如果对话给出的答案不理想，可以尝试调整这里的参数。
- 如果使用较大参数的模型，建议调调大参数。
- 文本块最大字符数为500，相邻块重叠字符数为50。用户如需调整可在config.py文件中修改。
```python
    # 文本分块参数
    DEFAULT_CHUNK_SIZE = 500  # 文本块最大字符数
    DEFAULT_CHUNK_OVERLAP = 50  # 相邻块重叠字符数
```
- 设置好后点击保存设置，系统会自动测试两个模型连接是否成功并返回结果。

### 8. 文档处理
- 设置完成并确定模型连接成功后，即可点击处理文件上传文件构建知识库。
- 点击浏览文件(目前仅支持docx文件)上传文件后点击开始处理。处理完成后系统会返回处理结果。

![文件处理](/static/img/files.png)

- 处理完成后可在文件列表内看到刚上传的文件及处理情况，点击查看分块可以查看文档分块详情。

![文件列表](/static/img/files2.png)

- 上传文档理论上没有上限，可以通过对话从大量文档中快速检索。

### 9. 问答系统
- 文档处理完成后即可使用问答系统。如果未上传文档或模型连接失败则直接返回提示。
- **ollama**模式回答的速度取决于选择的会话模型和电脑配置。**API**模式速度取决于服务商。

![问答系统](/static/img/chat.png)

### 10. 注意事项
- logs文件夹下为系统运行日志，频繁使用需定期清理。
- 文件构架清晰，各模块文档均为独立，方便用户进行二次开发。
- 删除文件时，只是删除保存在uploads内的文件和嵌入式数据库存储向量和索引；并不能删除已经上传并处理的文件分块内容；因此chroma_db文件夹会越来越大，如果要删除很多处理过的文件，建议重建知识库；即删除所有上传文件然后手动删除chroma_db文件夹下所有文件；然后再上传需要的文件。
- 重置系统；将chroma_db/data/logs/uploads四个文件夹里内容全部删除后，重新运行app.py，系统就会自动初始化。
