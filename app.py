"""
app.py - 应用入口
创建 Flask 实例，加载配置，注册蓝图，初始化数据库，配置登录管理和全局错误处理。
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from flask import Flask, redirect, url_for, session, request, current_app
from flask_login import LoginManager

from config import Config
from database import init_db
from models import init_default_data, User

os.environ['ANONYMIZED_TELEMETRY'] = 'False'

def create_app() -> Flask:
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False

    # 确保必要目录存在
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['LOG_DIR'], exist_ok=True)
    os.makedirs(app.config['CHROMA_DB_DIR'], exist_ok=True)

    # 配置日志系统
    setup_logging(app)

    # 初始化数据库
    init_db(app)
    init_default_data(app.extensions['db_session'])

    # 配置 Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面。'
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id):
        """根据用户 ID 加载用户对象"""
        sess = current_app.extensions['db_session']
        return sess.get(User, int(user_id))

    # 设置永久会话生命周期为 1 小时
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

    # 请求前钩子：更新最后活跃时间，检查会话超时
    @app.before_request
    def before_request():
        from flask_login import current_user
        if current_user.is_authenticated:
            # 更新最后活跃时间
            current_user.update_last_active()
            current_app.extensions['db_session'].commit()
        # 如果会话不是永久的，设置过期时间（可选）
        session.permanent = True

    # 注册蓝图
    from auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from routes_admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from routes_user import user_bp
    app.register_blueprint(user_bp, url_prefix='/user')

    # 主页重定向：未登录去登录页，登录后根据角色跳转
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.settings'))
            else:
                return redirect(url_for('user.chat'))
        return redirect(url_for('auth.login'))

    # 错误处理
    @app.errorhandler(403)
    def forbidden(error):
        return redirect(url_for('auth.login'))

    @app.errorhandler(404)
    def not_found(error):
        return redirect(url_for('auth.login'))

    # 处理未授权访问
    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for('auth.login'))

    # 日志：记录应用启动
    app.logger.info("Flask 应用启动成功")

    return app


def setup_logging(app: Flask):
    """配置日志记录器"""
    log_level = app.config.get('LOG_LEVEL', logging.INFO)
    log_dir = app.config['LOG_DIR']
    log_file = os.path.join(log_dir, 'app.log')

    # 创建根日志记录器
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # 清除已有处理器（避免重复）
    if logger.hasHandlers():
        logger.handlers.clear()

    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 文件处理器（按大小滚动，保留10个备份）
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=10, encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 设置第三方库日志级别（避免刷屏）
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=False)
