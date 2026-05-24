"""
auth.py - 认证蓝图
提供登录、注册、验证码生成、登出功能。
"""
import io
import random
import string
import base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, make_response, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer

from database import db_session
from models import User, UserActivity, AuditLog
from utils import log_activity

auth_bp = Blueprint('auth', __name__)

# 验证码配置
CAPTCHA_WIDTH = 160
CAPTCHA_HEIGHT = 60
CAPTCHA_LENGTH = 4

def generate_captcha_text(length=CAPTCHA_LENGTH):
    return ''.join(random.choices(string.digits, k=length))

def generate_captcha_image(text):
    image = Image.new('RGB', (CAPTCHA_WIDTH, CAPTCHA_HEIGHT), color='white')
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype('arial.ttf', 38)
    except IOError:
        font = ImageFont.load_default()

    for i, char in enumerate(text):
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        x = 15 + i * 32 + random.randint(-3, 3)
        y = random.randint(6, 14)
        draw.text((x, y), char, fill=color, font=font)

    for _ in range(3):
        x1 = random.randint(0, CAPTCHA_WIDTH)
        y1 = random.randint(0, CAPTCHA_HEIGHT)
        x2 = random.randint(0, CAPTCHA_WIDTH)
        y2 = random.randint(0, CAPTCHA_HEIGHT)
        draw.line(((x1, y1), (x2, y2)), fill=(random.randint(0, 150), random.randint(0, 150), random.randint(0, 150)), width=1)

    for _ in range(30):
        x = random.randint(0, CAPTCHA_WIDTH)
        y = random.randint(0, CAPTCHA_HEIGHT)
        draw.point((x, y), fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)))

    image = image.filter(ImageFilter.SMOOTH)
    output = io.BytesIO()
    image.save(output, format='PNG')
    output.seek(0)
    return output

# ---------- 签名 Token 辅助函数 ----------
def _get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def _generate_captcha_token(text):
    s = _get_serializer()
    return s.dumps({'captcha': text})

def _verify_captcha_token(token):
    s = _get_serializer()
    try:
        data = s.loads(token, max_age=300)
        return data.get('captcha')
    except Exception:
        return None

# ---------- 登录 ----------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        captcha_input = request.form.get('captcha', '').strip()
        captcha_token = request.form.get('captcha_token', '')

        captcha_text = _verify_captcha_token(captcha_token)
        if not captcha_text or captcha_input != captcha_text:
            flash('验证码错误，请重新输入', 'danger')
            new_text = generate_captcha_text()
            new_token = _generate_captcha_token(new_text)
            img_io = generate_captcha_image(new_text)
            captcha_img_data = base64.b64encode(img_io.getvalue()).decode('utf-8')
            return render_template('login.html',
                                   captcha_img_data=captcha_img_data,
                                   captcha_token=new_token)

        # 验证码正确，验证用户
        user = db_session.query(User).filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash('用户名或密码错误', 'danger')
            new_text = generate_captcha_text()
            new_token = _generate_captcha_token(new_text)
            img_io = generate_captcha_image(new_text)
            captcha_img_data = base64.b64encode(img_io.getvalue()).decode('utf-8')
            return render_template('login.html',
                                   captcha_img_data=captcha_img_data,
                                   captcha_token=new_token)

        # 登录成功
        login_user(user, remember=False)
        log_activity(user.id, 'login', f'用户 {username} 登录成功')
        db_session.commit()

        if user.role == 'admin':
            return redirect(url_for('admin.settings'))
        else:
            return redirect(url_for('user.chat'))

    # GET 请求
    new_text = generate_captcha_text()
    new_token = _generate_captcha_token(new_text)
    img_io = generate_captcha_image(new_text)
    captcha_img_data = base64.b64encode(img_io.getvalue()).decode('utf-8')
    return render_template('login.html',
                           captcha_img_data=captcha_img_data,
                           captcha_token=new_token)
    
# ---------- 注册 ----------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面（仅限普通用户）"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('register.html')

        if len(username) < 2 or len(password) < 6:
            flash('用户名至少2个字符，密码至少6位', 'danger')
            return render_template('register.html')

        existing = db_session.query(User).filter_by(username=username).first()
        if existing:
            flash('用户名已被注册', 'danger')
            return render_template('register.html')

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_pw, role='user')
        db_session.add(new_user)
        db_session.commit()

        log_activity(new_user.id, 'register', f'新用户注册: {username}')
        db_session.commit()

        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


# ---------- 登出 ----------
@auth_bp.route('/logout')
@login_required
def logout():
    """登出"""
    user = current_user
    log_activity(user.id, 'logout', f'用户 {user.username} 登出')
    db_session.commit()
    logout_user()
    return redirect(url_for('auth.login'))


# ---------- 修改密码 ----------
@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if not check_password_hash(current_user.password_hash, current_pw):
            flash('当前密码错误', 'danger')
            return render_template('change_password.html')

        if not new_pw or len(new_pw) < 6:
            flash('新密码至少需要6位', 'danger')
            return render_template('change_password.html')

        if new_pw != confirm_pw:
            flash('两次新密码输入不一致', 'danger')
            return render_template('change_password.html')

        current_user.password_hash = generate_password_hash(new_pw)
        db_session.commit()
        log_activity(current_user.id, 'change_password', '用户修改了密码')
        flash('密码修改成功，请重新登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('change_password.html')
