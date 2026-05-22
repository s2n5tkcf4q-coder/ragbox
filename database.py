"""
database.py - 数据库初始化
使用 SQLAlchemy 连接到 SQLite 数据库，提供引擎和会话。
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

Base = declarative_base()
engine = None
db_session = None


def init_db(app):
    """初始化数据库引擎和会话，创建所有表"""
    global engine, db_session

    # 确保数据目录存在
    db_dir = os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # 创建引擎
    engine = create_engine(
        app.config['SQLALCHEMY_DATABASE_URI'],
        echo=False,  # 生产环境建议 False，调试时可设为 True
        connect_args={"check_same_thread": False} if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI'] else {}
    )

    # 创建会话工厂
    session_factory = sessionmaker(bind=engine)
    db_session = scoped_session(session_factory)

    # 导入所有模型，确保它们被注册到 Base 元数据中
    import models  # noqa

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 将 scoped_session 存储到 app 上下文中，方便后续获取
    app.extensions['db_session'] = db_session

    # 日志输出
    app.logger.info(f"数据库初始化完成: {app.config['SQLALCHEMY_DATABASE_URI']}")
