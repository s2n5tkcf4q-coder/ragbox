"""
config.py - 应用配置
包含所有默认系统参数、路径、安全密钥等。
"""
import os


class Config:
    # --- 安全密钥 ---
    SECRET_KEY = 'a-very-strong-random-string-123456'

    # --- 数据库 ---
    # SQLite 数据库文件存放于 data/app.db
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(DATA_DIR, "app.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- 目录路径 ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    CHROMA_DB_DIR = os.path.join(BASE_DIR, 'chroma_db')

    # --- 日志 ---
    LOG_LEVEL = 'INFO'

    # --- 默认 LLM 配置 ---
    # 模式：'api' 或 'ollama'
    DEFAULT_LLM_MODE = 'ollama'

    # 对话模型名称
    # API 模式示例：'gpt-3.5-turbo', 'gpt-4'
    # Ollama 模式示例：'llama2', 'mistral'
    DEFAULT_CHAT_MODEL = 'gpt-3.5-turbo'

    # 嵌入模型名称
    # API 模式示例：'text-embedding-ada-002'
    # Ollama 模式示例：'nomic-embed-text'
    DEFAULT_EMBEDDING_MODEL = 'text-embedding-ada-002'

    # 系统提示词
    DEFAULT_SYSTEM_PROMPT = (
        "你是一个专业的知识库问答助手。"
        "请严格依据提供的上下文信息回答问题，不要添加额外猜测。"
        "如果上下文不足以回答问题，请明确告知用户。"
    )

    # 文本分块参数
    DEFAULT_CHUNK_SIZE = 500  # 文本块最大字符数
    DEFAULT_CHUNK_OVERLAP = 50  # 相邻块重叠字符数

    # 检索参数默认值
    DEFAULT_SIMILARITY_THRESHOLD = 0.5   # 相似度阈值
    DEFAULT_TOP_N = 5                    # 检索返回的块数
    DEFAULT_VECTOR_WEIGHT = 0.5          # 向量相似度权重（0~1，剩余为关键词权重，预留）

    # 生成参数默认值
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_TOP_P = 0.9
    DEFAULT_PRESENCE_PENALTY = 0.0
    DEFAULT_FREQUENCY_PENALTY = 0.0
    DEFAULT_MAX_TOKENS = 2048

    # --- 文件上传限制 ---
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 最大上传 32MB

    # --- 会话与安全 ---
    PERMANENT_SESSION_LIFETIME = 3600     # 1 小时
