"""
auth.py - 认证蓝图
提供登录、注册、验证码生成、登出功能。
"""
import io
import random
import string
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, make_response
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db_session
from models import User, UserActivity, AuditLog
from utils import log_activity

auth_bp = Blueprint('auth', __name__)

# 验证码配置
CAPTCHA_WIDTH = 120
CAPTCHA_HEIGHT = 40
CAPTCHA_LENGTH = 4  # 纯数字


def generate_captcha_text(length=CAPTCHA_LENGTH):
    """生成随机数字验证码文本"""
    return ''.join(random.choices(string.digits, k=length))


def generate_captcha_image(text):
    """生成验证码图片，返回 PNG 字节流"""
    # 创建白色背景图像
    image = Image.new('RGB', (CAPTCHA_WIDTH, CAPTCHA_HEIGHT), color='white')
    draw = ImageDraw.Draw(image)

    # 使用默认字体，或尝试加载系统字体
    try:
        font = ImageFont.truetype('arial.ttf', 24)
    except IOError:
        font = ImageFont.load_default()

    # 绘制文字，每个字符带随机颜色和轻微偏移
    for i, char in enumerate(text):
        # 随机颜色
        color = (
            random.randint(0, 100),
            random.randint(0, 100),
            random.randint(0, 100)
        )
        x = 10 + i * 25 + random.randint(-3, 3)
        y = random.randint(2, 8)
        draw.text((x, y), char, fill=color, font=font)

    # 添加干扰线
    for _ in range(3):
        x1 = random.randint(0, CAPTCHA_WIDTH)
        y1 = random.randint(0, CAPTCHA_HEIGHT)
        x2 = random.randint(0, CAPTCHA_WIDTH)
        y2 = random.randint(0, CAPTCHA_HEIGHT)
        draw.line(
            ((x1, y1), (x2, y2)),
            fill=(random.randint(0, 150), random.randint(0, 150), random.randint(0, 150)),
            width=1
        )

    # 添加干扰点
    for _ in range(30):
        x = random.randint(0, CAPTCHA_WIDTH)
        y = random.randint(0, CAPTCHA_HEIGHT)
        draw.point((x, y), fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)))

    # 应用模糊滤镜，略微扭曲
    image = image.filter(ImageFilter.SMOOTH)

    # 将图片保存到字节流
    output = io.BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    return output


@auth_bp.route('/captcha')
def captcha():
    """生成验证码图片，并将文本存入 session"""
    text = generate_captcha_text()
    session['captcha'] = text
    img_io = generate_captcha_image(text)
    response = make_response(img_io.read())
    response.mimetype = 'image/png'
    return response


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面及处理"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        captcha_input = request.form.get('captcha', '').strip()

        # 验证码校验
        stored_captcha = session.get('captcha', '')
        if captcha_input.lower() != stored_captcha.lower():
            flash('验证码错误，请重新输入', 'danger')
            # 刷新验证码
            session.pop('captcha', None)
            return render_template('login.html')

        # 清除验证码，防止重用
        session.pop('captcha', None)

        # 查询用户
        user = db_session.query(User).filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('用户名或密码错误', 'danger')
            return render_template('login.html')

        # 登录
        login_user(user, remember=False)
        # 记录活动
        log_activity(user.id, 'login', f'用户 {username} 登录成功')
        db_session.commit()

        # 根据角色跳转
        if user.role == 'admin':
            return redirect(url_for('admin.settings'))
        else:
            return redirect(url_for('user.chat'))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面（仅限普通用户）"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 前端已做确认，后端再次校验
        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('register.html')

        if len(username) < 2 or len(password) < 6:
            flash('用户名至少2个字符，密码至少6位', 'danger')
            return render_template('register.html')

        # 检查用户名是否已存在
        existing = db_session.query(User).filter_by(username=username).first()
        if existing:
            flash('用户名已被注册', 'danger')
            return render_template('register.html')

        # 创建用户，角色固定为 'user'
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_pw, role='user')
        db_session.add(new_user)
        db_session.commit()

        # 记录日志
        log_activity(new_user.id, 'register', f'新用户注册: {username}')
        db_session.commit()

        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """登出"""
    user = current_user
    log_activity(user.id, 'logout', f'用户 {user.username} 登出')
    db_session.commit()
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        # 验证原密码是否正确
        if not check_password_hash(current_user.password_hash, current_pw):
            flash('当前密码错误', 'danger')
            return render_template('change_password.html')

        # 新密码不能为空，且长度至少6位
        if not new_pw or len(new_pw) < 6:
            flash('新密码至少需要6位', 'danger')
            return render_template('change_password.html')

        if new_pw != confirm_pw:
            flash('两次新密码输入不一致', 'danger')
            return render_template('change_password.html')

        # 更新密码
        current_user.password_hash = generate_password_hash(new_pw)
        db_session.commit()
        log_activity(current_user.id, 'change_password', '用户修改了密码')
        flash('密码修改成功，请重新登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('change_password.html')
