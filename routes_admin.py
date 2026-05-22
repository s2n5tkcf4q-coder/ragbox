"""
routes_admin.py - 管理员功能蓝图
提供系统设置、用户管理、文件处理、文件列表等页面和 API。
"""
import os
import time
import logging
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, current_app, jsonify
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from database import db_session
from models import User, SystemConfig, Document, Chunk, AuditLog, UserActivity
from llm_client import test_connection, APIClient, OllamaClient, get_llm_client
from rag_engine import process_document
from utils import admin_required, log_activity

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, template_folder='templates')


@admin_bp.before_request
@login_required
@admin_required
def before_request():
    """确保所有管理页面请求都经过管理员验证"""
    pass


# ---------- 系统设置 ----------

@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """系统设置页面"""
    if request.method == 'POST':
        # 获取表单数据并保存配置
        configs = {
            'llm_mode': request.form.get('llm_mode', 'api'),
            'local_chat_model': request.form.get('local_chat_model', ''),
            'local_embedding_model': request.form.get('local_embedding_model', ''),
            'api_chat_model': request.form.get('api_chat_model', ''),
            'api_embedding_model': request.form.get('api_embedding_model', ''),
            'api_base_url': request.form.get('api_base_url', ''),
            'api_key': request.form.get('api_key', ''),
            'ollama_base_url': request.form.get('ollama_base_url', 'http://localhost:11434'),
            'system_prompt': request.form.get('system_prompt', ''),
            'similarity_threshold': request.form.get('similarity_threshold', '0.7'),
            'top_n': request.form.get('top_n', '5'),
            'vector_weight': request.form.get('vector_weight', '0.5'),
            'temperature': request.form.get('temperature', '0.7'),
            'top_p': request.form.get('top_p', '0.9'),
            'presence_penalty': request.form.get('presence_penalty', '0.0'),
            'frequency_penalty': request.form.get('frequency_penalty', '0.0'),
            'max_tokens': request.form.get('max_tokens', '1024'),
        }

        for key, value in configs.items():
            SystemConfig.set_value(db_session, key, value)

        # 测试连接
        test_result = test_connection()

        if test_result['success']:
            flash('设置已保存，模型连接测试成功！', 'success')
        else:
            flash(f'设置已保存，但模型连接测试失败: {test_result["message"]}', 'warning')

        # 记录日志
        log_activity(current_user.id, 'config_change',
                     f'管理员修改系统配置: {configs}')
        db_session.commit()
        return redirect(url_for('admin.settings'))

    # GET 请求：加载当前配置并显示页面
    config = {}
    config_keys = [
        'llm_mode', 'local_chat_model', 'local_embedding_model',
        'api_base_url', 'api_key', 'ollama_base_url',
        'system_prompt', 'similarity_threshold', 'top_n',
        'vector_weight', 'temperature', 'top_p',
        'presence_penalty', 'frequency_penalty', 'max_tokens',
        'api_chat_model', 'api_embedding_model'
    ]
    for key in config_keys:
        config[key] = SystemConfig.get_value(db_session, key, '')

    return render_template('admin_settings.html', config=config)


@admin_bp.route('/test_connection', methods=['POST'])
def test_llm_connection():
    """接受前端传来的临时配置，测试连接，不保存数据库"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '缺少配置参数'})

    # 从请求中提取参数
    mode = data.get('mode', 'api')
    chat_model = data.get('chat_model', '')
    embedding_model = data.get('embedding_model', '')
    api_base_url = data.get('api_base_url', '')
    api_key = data.get('api_key', '')
    ollama_base_url = data.get('ollama_base_url', 'http://localhost:11434')

    try:
        # 根据模式临时创建客户端（避免污染全局配置）
        if mode == 'api':
            chat_client = APIClient(chat_model, api_key=api_key, base_url=api_base_url)
            embed_client = APIClient(embedding_model, api_key=api_key, base_url=api_base_url)
        elif mode == 'ollama':
            chat_client = OllamaClient(chat_model, base_url=ollama_base_url)
            embed_client = OllamaClient(embedding_model, base_url=ollama_base_url)
        else:
            return jsonify({'success': False, 'message': f'未知模式: {mode}'})

        # 测试两个连接
        chat_ok = chat_client.test_connection()
        embed_ok = embed_client.test_connection()

        if chat_ok and embed_ok:
            return jsonify({'success': True, 'message': '连接成功：对话模型和嵌入模型均可用'})
        else:
            msg = []
            if not chat_ok:
                msg.append('对话模型连接失败')
            if not embed_ok:
                msg.append('嵌入模型连接失败')
            return jsonify({'success': False, 'message': '；'.join(msg)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ---------- 用户管理 ----------

@admin_bp.route('/users')
def users():
    """用户管理页面"""
    all_users = db_session.query(User).order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=all_users)


@admin_bp.route('/user/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """删除用户（不能删除自己）"""
    if user_id == current_user.id:
        flash('不能删除自己', 'danger')
        return redirect(url_for('admin.users'))

    user = db_session.query(User).get(user_id)
    if not user:
        flash('用户不存在', 'danger')
        return redirect(url_for('admin.users'))

    username = user.username
    db_session.delete(user)
    log_activity(current_user.id, 'user_deleted', f'删除用户 {username}')
    db_session.commit()
    flash(f'用户 {username} 已删除', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/user/role/<int:user_id>', methods=['POST'])
def change_role(user_id):
    """修改用户角色"""
    user = db_session.query(User).get(user_id)
    if not user:
        flash('用户不存在', 'danger')
        return redirect(url_for('admin.users'))

    new_role = request.form.get('role', 'user')
    if new_role not in ('admin', 'user'):
        flash('无效的角色', 'danger')
        return redirect(url_for('admin.users'))

    old_role = user.role
    user.role = new_role
    log_activity(current_user.id, 'role_change',
                 f'用户 {user.username} 角色从 {old_role} 改为 {new_role}')
    db_session.commit()
    flash(f'用户 {user.username} 角色已更新', 'success')
    return redirect(url_for('admin.users'))


# ---------- 文件处理 ----------

def allowed_file(filename):
    """检查文件扩展名"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'docx'


@admin_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """文件上传与处理页面"""
    if request.method == 'POST':
        # 检查是否有文件
        if 'document' not in request.files:
            flash('未选择文件', 'danger')
            return render_template('admin_upload.html')

        file = request.files['document']
        if file.filename == '':
            flash('未选择文件', 'danger')
            return render_template('admin_upload.html')

        if not allowed_file(file.filename):
            flash('仅支持 .docx 文件', 'danger')
            return render_template('admin_upload.html')

        # 保存文件
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        save_name = f"{timestamp}_{filename}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], save_name)
        file.save(upload_path)
        file_size = os.path.getsize(upload_path)

        # ---- 检测 Embedding 模型是否可用 ----
        try:
            llm = get_llm_client()
            test_embeddings = llm.embed(["test"])
            if not test_embeddings or len(test_embeddings[0]) == 0:
                flash('嵌入模型未正确加载或返回空向量，请先在系统设置中配置并测试通过。', 'danger')
                os.remove(upload_path)
                return render_template('admin_upload.html')
        except Exception as e:
            flash(f'嵌入模型连接失败：{str(e)}，请检查模型配置后重试。', 'danger')
            os.remove(upload_path)
            return render_template('admin_upload.html')
        # ---- 检测结束 ----

        try:
            # 调用 rag_engine 处理文件
            doc = process_document(
                file_path=upload_path,
                original_filename=filename,
                user_id=current_user.id,
                file_size=file_size
            )
            flash(f'文件 "{filename}" 处理成功！共生成 {doc.chunk_count} 个文本块。', 'success')
            log_activity(current_user.id, 'file_upload',
                         f'上传并处理文件 {filename}，ID={doc.id}，块数={doc.chunk_count}')
        except Exception as e:
            flash(f'文件处理失败: {str(e)}', 'danger')
            logger.error(f"文件上传处理失败: {e}")
            # 不删除上传的文件，便于排查

        return redirect(url_for('admin.upload'))

    return render_template('admin_upload.html')


# ---------- 文件列表 ----------

@admin_bp.route('/files')
def files():
    """文件列表页面"""
    all_docs = db_session.query(Document).order_by(Document.upload_time.desc()).all()
    return render_template('admin_files.html', documents=all_docs)


@admin_bp.route('/file/<int:doc_id>/chunks')
def file_chunks(doc_id):
    """获取某个文件的块列表（JSON 或部分渲染）"""
    doc = db_session.query(Document).get(doc_id)
    if not doc:
        return jsonify({'error': '文件不存在'}), 404

    chunks = db_session.query(Chunk).filter_by(document_id=doc_id).order_by(Chunk.chunk_index).all()
    chunks_data = [{
        'index': c.chunk_index,
        'content': c.content,
        'char_count': c.char_count
    } for c in chunks]

    return jsonify({
        'document': {
            'id': doc.id,
            'original_filename': doc.original_filename,
            'status': doc.status,
            'chunk_count': doc.chunk_count
        },
        'chunks': chunks_data
    })


@admin_bp.route('/file/delete/<int:doc_id>', methods=['POST'])
def delete_document(doc_id):
    """删除文档及其块记录和向量数据（需谨慎）"""
    doc = db_session.query(Document).get(doc_id)
    if not doc:
        flash('文件不存在', 'danger')
        return redirect(url_for('admin.files'))

    # 删除 ChromaDB 中的向量
    try:
        from rag_engine import _get_collection
        collection = _get_collection()
        # 方法1：通过元数据 doc_id 删除（更可靠）
        collection.delete(where={"doc_id": str(doc_id)})
        logger.info(f"从 ChromaDB 删除文档 {doc_id} 的所有向量（where doc_id）")
    except Exception as e:
        logger.warning(f"按 doc_id 删除向量失败，尝试按 embedding_id 删除: {e}")
        # 备选方法：使用块记录中的 embedding_id
        try:
            chunk_ids = [chunk.embedding_id for chunk in doc.chunks if chunk.embedding_id]
            if chunk_ids:
                collection.delete(ids=chunk_ids)
                logger.info(f"从 ChromaDB 删除 {len(chunk_ids)} 个向量（按 embedding_id）")
        except Exception as e2:
            logger.error(f"删除向量完全失败: {e2}")
            flash(f'删除向量数据时出错: {e2}', 'warning')

    # 删除本地文件
    upload_dir = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_dir, doc.filename)
    if not os.path.exists(file_path):
        for f in os.listdir(upload_dir):
            if f.endswith('_' + doc.original_filename) or f == doc.original_filename:
                file_path = os.path.join(upload_dir, f)
                break
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"已删除文件: {file_path}")

    # 数据库删除
    db_session.delete(doc)
    try:
        db_session.commit()
        # 强制清除会话缓存，确保后续查询获取最新数据
        db_session.expire_all()
        logger.info(f"文档 {doc_id} 已从数据库中删除")
        flash(f'文档 "{doc.original_filename}" 已删除', 'success')
    except Exception as e:
        db_session.rollback()
        logger.error(f"数据库删除失败: {e}")
        flash(f'删除失败: {e}', 'danger')

    # 记录日志
    log_activity(current_user.id, 'document_deleted',
                 f'删除文档 {doc.original_filename} 及其所有块')

    return redirect(url_for('admin.files'))
