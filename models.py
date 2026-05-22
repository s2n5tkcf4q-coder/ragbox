"""
models.py - 数据库模型定义
包含用户、配置、文件、分块、对话、消息、活动日志等模型。
"""
import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
)
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(10), nullable=False, default='user')  # 'admin' 或 'user'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # 关系
    conversations = relationship('Conversation', back_populates='user', lazy='dynamic')
    activities = relationship('UserActivity', back_populates='user', lazy='dynamic')

    def update_last_active(self):
        self.last_active_at = datetime.datetime.utcnow()

    def is_admin(self):
        return self.role == 'admin'

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<User {self.username}>'


class SystemConfig(Base):
    __tablename__ = 'system_config'

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=True)

    @staticmethod
    def get_value(session, key, default=None):
        """辅助方法：从数据库获取配置值"""
        config = session.query(SystemConfig).filter_by(key=key).first()
        if config:
            return config.value
        return default

    @staticmethod
    def set_value(session, key, value):
        """辅助方法：设置配置值，存在则更新，不存在则插入"""
        config = session.query(SystemConfig).filter_by(key=key).first()
        if config:
            config.value = value
        else:
            config = SystemConfig(key=key, value=value)
            session.add(config)
        session.commit()

    def __repr__(self):
        return f'<SystemConfig {self.key}={self.value}>'


class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(256), nullable=False)          # 存储在 uploads/ 下的文件名
    original_filename = Column(String(256), nullable=False) # 用户上传时的原始文件名
    file_size = Column(Integer, default=0)
    uploaded_by = Column(Integer, ForeignKey('users.id'))
    upload_time = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(20), default='pending')          # pending, processing, completed, failed
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # 关系
    uploader = relationship('User', backref='documents')
    chunks = relationship('Chunk', back_populates='document', lazy='dynamic',
                          cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Document {self.original_filename}>'


class Chunk(Base):
    __tablename__ = 'chunks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'))
    chunk_index = Column(Integer, nullable=False)           # 块在该文档内的序号
    content = Column(Text, nullable=False)                  # 块文本内容
    char_count = Column(Integer, default=0)                 # 字符数
    embedding_id = Column(String(128), nullable=True)       # ChromaDB 中的向量 ID（方便追溯）

    # 关系
    document = relationship('Document', back_populates='chunks')

    def __repr__(self):
        return f'<Chunk {self.id} doc={self.document_id} idx={self.chunk_index}>'


class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # 关系
    user = relationship('User', back_populates='conversations')
    messages = relationship('Message', back_populates='conversation', lazy='dynamic',
                            cascade='all, delete-orphan', order_by='Message.created_at')

    def __repr__(self):
        return f'<Conversation {self.id} title={self.title}>'


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id', ondelete='CASCADE'))
    role = Column(String(20), nullable=False)               # 'user' 或 'assistant'
    content = Column(Text, nullable=False)                  # 回答内容（用户问题或助手最终答案）
    thinking = Column(Text, nullable=True)                  # 思维链内容（仅助手消息有）
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # 关系
    conversation = relationship('Conversation', back_populates='messages')

    def __repr__(self):
        return f'<Message {self.id} role={self.role}>'


class UserActivity(Base):
    __tablename__ = 'user_activities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String(128), nullable=False)            # e.g., 'login', 'ask', 'upload', 'config_change'
    details = Column(Text, nullable=True)                   # 补充信息
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # 关系
    user = relationship('User', back_populates='activities')

    def __repr__(self):
        return f'<UserActivity {self.action} by user {self.user_id}>'


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)                # 操作者 ID，可能为系统
    action = Column(String(128), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.action}>'


# --- 默认数据初始化 ---
def init_default_data(session):
    """初始化默认管理员账户和系统配置"""
    # 创建默认管理员（如果不存在）
    admin = session.query(User).filter_by(username='admin').first()
    if not admin:
        from werkzeug.security import generate_password_hash
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),  # 请在生产环境修改
            role='admin'
        )
        session.add(admin)
        session.commit()
        # 记录日志
        log = AuditLog(
            user_id=None,
            action='system_init',
            details='Created default admin user'
        )
        session.add(log)
        session.commit()

    # 初始化系统配置（如果不存在则插入默认值）
    default_configs = {
        'llm_mode': 'api',
        'local_chat_model': 'gpt-3.5-turbo',
        'local_embedding_model': 'text-embedding-ada-002',
        'api_chat_model': 'gpt-3.5-turbo',
        'api_embedding_model': 'text-embedding-ada-002',
        'system_prompt': '你是一个专业的知识库问答助手。请严格依据提供的上下文信息回答问题，不要添加额外猜测。如果上下文不足以回答问题，请明确告知用户。',
        'similarity_threshold': '0.5',
        'top_n': '5',
        'vector_weight': '0.5',
        'temperature': '0.7',
        'top_p': '0.9',
        'presence_penalty': '0.0',
        'frequency_penalty': '0.0',
        'max_tokens': '1024',
        'api_base_url': '',
        'api_key': '',
    }
    for key, value in default_configs.items():
        existing = session.query(SystemConfig).filter_by(key=key).first()
        if not existing:
            config = SystemConfig(key=key, value=value)
            session.add(config)
    session.commit()
