"""
utils.py - 工具函数
提供日志记录、权限装饰器、文件检查等辅助功能。
"""
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user
from database import db_session
from models import UserActivity, AuditLog


def admin_required(f):
    """装饰器：要求管理员权限，否则重定向到首页并提示"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            flash('需要管理员权限才能访问该页面', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def log_activity(user_id, action, details=None):
    """
    记录用户活动到 UserActivity 表，并自动提交。
    同时可根据需要写入 AuditLog，此处仅记录普通活动。
    """
    activity = UserActivity(
        user_id=user_id,
        action=action,
        details=details
    )
    db_session.add(activity)
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise


def log_audit(user_id, action, details=None):
    """
    记录审计日志（用于更关键的操作，如管理员操作、系统事件）。
    调用后会自动提交。
    """
    audit = AuditLog(
        user_id=user_id,
        action=action,
        details=details
    )
    db_session.add(audit)
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise


def allowed_file(filename, allowed_extensions=None):
    """
    检查文件扩展名是否在允许列表中。
    默认只允许 'docx'。
    """
    if allowed_extensions is None:
        allowed_extensions = {'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions