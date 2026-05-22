"""
routes_user.py - 普通用户问答蓝图
提供聊天页面、对话管理、流式问答等功能。
"""
import json
import time
import logging
from flask import (
    Blueprint, render_template, request, jsonify, Response,
    stream_with_context, current_app, abort, make_response
)
from flask_login import login_required, current_user
from llm_client import get_llm_client
from database import db_session
from models import Conversation, Message, UserActivity
from rag_engine import generate_answer, split_thinking_answer, is_knowledge_base_empty
from utils import log_activity

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)


@user_bp.before_request
@login_required
def restrict_to_user():
    """确保普通用户（或管理员）可访问，管理员也可访问，普通用户只能访问自己的问答"""
    if current_user.role not in ('user', 'admin'):
        abort(403)


# ---------- 聊天主页面 ----------

@user_bp.route('/chat')
def chat():
    """问答页面，加载历史对话列表及当前对话消息"""
    conversations = (
        db_session.query(Conversation)
        .filter_by(user_id=current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    current_conv = None
    messages = []
    conv_id = request.args.get('conversation_id', type=int)

    if conv_id:
        # 加载指定对话（需确保属于当前用户）
        current_conv = (
            db_session.query(Conversation)
            .filter_by(id=conv_id, user_id=current_user.id)
            .first()
        )
    elif conversations:
        # 默认加载最近更新的对话
        current_conv = conversations[0]

    if current_conv:
        messages = (
            db_session.query(Message)
            .filter_by(conversation_id=current_conv.id)
            .order_by(Message.created_at.asc())
            .all()
        )

    response = make_response(render_template(
        'chat.html',
        conversations=conversations,
        current_conv=current_conv,
        messages=messages
    ))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ---------- 对话管理 ----------

@user_bp.route('/conversation/new', methods=['POST'])
def new_conversation():
    """创建新对话"""
    conv = Conversation(
        user_id=current_user.id,
        title='新对话'
    )
    db_session.add(conv)
    db_session.commit()
    log_activity(current_user.id, 'new_conversation', f'创建对话 {conv.id}')
    return jsonify({'id': conv.id, 'title': conv.title})


@user_bp.route('/conversation/<int:conv_id>/delete', methods=['DELETE'])
def delete_conversation(conv_id):
    """删除指定对话"""
    conv = db_session.query(Conversation).filter_by(
        id=conv_id, user_id=current_user.id
    ).first()
    if not conv:
        return jsonify({'error': '对话不存在'}), 404

    db_session.delete(conv)  # 级联删除消息
    db_session.commit()
    log_activity(current_user.id, 'delete_conversation', f'删除对话 {conv_id}')
    return jsonify({'success': True})


@user_bp.route('/conversation/<int:conv_id>/messages')
def get_messages(conv_id):
    """获取指定对话的所有消息（JSON格式，供前端加载历史）"""
    conv = db_session.query(Conversation).filter_by(
        id=conv_id, user_id=current_user.id
    ).first()
    if not conv:
        return jsonify({'error': '对话不存在'}), 404

    msgs = (
        db_session.query(Message)
        .filter_by(conversation_id=conv_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    messages_data = [{
        'id': msg.id,
        'role': msg.role,
        'content': msg.content,
        'thinking': msg.thinking,
        'created_at': msg.created_at.isoformat()
    } for msg in msgs]
    return jsonify({'messages': messages_data})


# ---------- 问答流式响应 ----------

@user_bp.route('/chat/send', methods=['POST'])
def send_message():
    """接收用户消息并返回 SSE 流式回答（思维链与答案分离）"""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': '缺少消息内容'}), 400

    user_message = data['message'].strip()
    if not user_message:
        return jsonify({'error': '消息不能为空'}), 400

    conv_id = data.get('conversation_id')
    # 创建或获取对话
    if conv_id:
        conv = db_session.query(Conversation).filter_by(
            id=conv_id, user_id=current_user.id
        ).first()
        if not conv:
            return jsonify({'error': '对话不存在'}), 404
    else:
        # 创建新对话
        conv = Conversation(
            user_id=current_user.id,
            title=user_message[:20]  # 用提问前20字作为标题
        )
        db_session.add(conv)
        db_session.commit()
        conv_id = conv.id  # 用于后续返回

    # 存储用户消息
    user_msg = Message(
        conversation_id=conv.id,
        role='user',
        content=user_message
    )
    db_session.add(user_msg)
    db_session.commit()

    # 立刻创建占位助手消息（表示“生成中”）
    placeholder_msg = Message(
        conversation_id=conv.id,
        role='assistant',
        content='正在生成回答，请稍候...',
        thinking=''
    )
    db_session.add(placeholder_msg)
    db_session.commit()


    # 检查 chat 模型是否可用
    try:
        llm = get_llm_client()
        # 尝试调用 test_connection 或简单发送一个空消息测试
        if not llm.test_connection():
            placeholder_msg.content = '没有可用的大模型，请通知管理员'
            placeholder_msg.thinking = ''
            db_session.commit()
            def chat_unavailable_events():
                yield f"data: {json.dumps({'type': 'error', 'message': placeholder_msg.content})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return Response(stream_with_context(chat_unavailable_events()), mimetype='text/event-stream')
    except Exception as e:
        placeholder_msg.content = f'大模型连接异常：{str(e)}'
        placeholder_msg.thinking = ''
        db_session.commit()
        def chat_error_events():
            yield f"data: {json.dumps({'type': 'error', 'message': placeholder_msg.content})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return Response(stream_with_context(chat_error_events()), mimetype='text/event-stream')

    # 检查知识库是否为空
    if is_knowledge_base_empty():
        # 直接更新占位消息的内容
        placeholder_msg.content = '知识库为空，请联系管理员上传文档。'
        placeholder_msg.thinking = ''
        db_session.commit()

        def empty_events():
            yield f"data: {json.dumps({'type': 'answer', 'content': '知识库为空，请联系管理员上传文档。'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return Response(stream_with_context(empty_events()), mimetype='text/event-stream')

    # 获取历史消息用于上下文（取最近5轮）
    history = (
        db_session.query(Message)
        .filter_by(conversation_id=conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history_pairs = []
    # 转换为角色列表，但generate_answer期望的是[{"role": "...", "content": "..."}]
    # 简单起见，直接传入历史消息列表，但需过滤掉系统提示
    # generate_answer内部会拼接系统提示和对话历史，因此我们传递完整的消息列表（仅用户和助手）
    for msg in history:
        if msg.role in ('user', 'assistant'):
            history_pairs.append({"role": msg.role, "content": msg.content})

    # 生成回答（非流式，但我们可以拆分后模拟流式推送）
    try:
        full_response = generate_answer(
            query=user_message,
            conversation_history=history_pairs,
            stream=False
        )
    except Exception as e:
        logger.error(f"生成回答失败: {e}")
        # 存储错误消息，并返回错误 SSE
        placeholder_msg.content = '抱歉，生成回答时出错，请稍后重试。'
        placeholder_msg.thinking = f'错误详情: {str(e)}'
        db_session.commit()

        def error_events():
            yield f"data: {json.dumps({'type': 'error', 'message': placeholder_msg.content})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return Response(stream_with_context(error_events()), mimetype='text/event-stream')

    # 分离思维链和答案
    thinking, answer = split_thinking_answer(full_response)

    if not answer or not answer.strip():
        logger.warning(f"分离后答案为空，将原始响应作为答案。原始长度: {len(full_response)}")
        answer = full_response
        thinking = ''

    # 存储助手消息
    placeholder_msg.content = answer
    placeholder_msg.thinking = thinking
    db_session.commit()

    # 更新对话标题（第一次回答时用提问前20字）
    if not conv.title or conv.title == '新对话':
        conv.title = user_message[:20]
        db_session.commit()

    log_activity(
        current_user.id, 'chat',
        f'对话 {conv.id} 提问: {user_message[:30]}...'
    )

    # 生成 SSE 事件流
    def generate_events():
        yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': conv.id})}\n\n"
        # 1. 发送思维链（整体）
        if thinking:
            event_data = json.dumps({'type': 'thinking', 'content': thinking})
            yield f"data: {event_data}\n\n"
        # 2. 模拟流式发送答案（按字符分批，每批几个字）
        chunk_size = 5  # 每次推送5个字符
        for i in range(0, len(answer), chunk_size):
            chunk = answer[i:i+chunk_size]
            event_data = json.dumps({'type': 'answer', 'content': chunk})
            yield f"data: {event_data}\n\n"
            time.sleep(0.05)  # 模拟流式延迟，可根据需要调整
        # 3. 完成事件
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return Response(
        stream_with_context(generate_events()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  # 防止 nginx 缓冲
        }
    )
