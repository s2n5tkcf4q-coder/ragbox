/* static/js/chat.js */
/* 聊天页面脚本：发送消息、SSE 流式接收、思维链折叠、复制消息、对话管理 */

(function() {
    'use strict';

    // ---------- DOM 元素 ----------
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const conversationList = document.getElementById('conversation-list');

    // 当前对话 ID（从 URL 获取或由后端返回）
    let currentConversationId = getCurrentConversationIdFromUrl();

    // ---------- 工具函数 ----------
    function getCurrentConversationIdFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const id = params.get('conversation_id');
        return id ? parseInt(id, 10) : null;
    }

    function scrollToBottom() {
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    // HTML 转义（防止 XSS）
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 简单的 Markdown 转 HTML（支持标题、粗体、斜体、列表、代码块等）
    function markdownToHtml(text) {
        // 先转义 HTML 特殊字符，防止 XSS
        let html = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // 标题
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

        // 粗体和斜体
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

        // 无序列表
        html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
        html = html.replace(/((?:<li>.*?<\/li>\s*)+)/g, '<ul>$1</ul>');

        // 换行转段落
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';

        return html;
    }

    // 添加一条用户消息到界面
    function appendUserMessage(content) {
        if (!chatMessages) return;
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message message-user';
        msgDiv.innerHTML = '<div class="message-content">' + escapeHtml(content) + '</div>';
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    // 添加一条助手消息（带思维链占位）到界面，返回该消息容器以便后续追加内容
    function appendAssistantMessagePlaceholder() {
        if (!chatMessages) return null;
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message message-assistant';

        // 思维链区域（默认隐藏）
        const thinkingBlock = document.createElement('div');
        thinkingBlock.className = 'thinking-block';
        thinkingBlock.innerHTML = '<button class="btn-thinking-toggle" onclick="toggleThinking(this)">💭 思考过程</button>' +
                                   '<div class="thinking-text" style="display: none;"></div>';

        // 思考中指示器
        const thinkingIndicator = document.createElement('div');
        thinkingIndicator.className = 'thinking-indicator';
        thinkingIndicator.innerHTML = '<span class="dot-pulse"></span> 思考中...';

        const msgContentDiv = document.createElement('div');
        msgContentDiv.className = 'message-content';
        msgContentDiv.appendChild(thinkingBlock);
        msgContentDiv.appendChild(thinkingIndicator);   // 只有思考中，无答案区

        msgDiv.appendChild(msgContentDiv);
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
        return msgDiv;
    }

    // 获取或创建正在流式输出的助手消息（用于追加答案文本）
    function getStreamingAssistantMessage() {
        if (!chatMessages) return null;
        const msgs = chatMessages.querySelectorAll('.message.message-assistant');
        // 最后一个助手消息
        if (msgs.length > 0) {
            return msgs[msgs.length - 1];
        }
        return null;
    }

    // 清空输入框
    function clearInput() {
        if (userInput) {
            userInput.value = '';
            userInput.style.height = 'auto';
        }
    }

    // 复制到剪贴板
    async function copyMessageToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            // 视觉反馈：显示复制成功的小提示（可忽略或简单 alert）
        } catch (err) {
            console.error('复制失败:', err);
        }
    }

    window.copyMessage = function(btn) {
        const answerDiv = btn.closest('.answer-text');
        if (!answerDiv) return;
        const span = answerDiv.querySelector('.answer-content');
        const raw = answerDiv.dataset.rawMarkdown || (span ? span.textContent : '');
        const thinkingBlock = btn.closest('.message')?.querySelector('.thinking-text');
        const thinking = thinkingBlock?.textContent || '';
        const full = thinking ? thinking + '\n\n' + raw : raw;
        copyMessageToClipboard(full);
    };

    // ---------- 思维链折叠切换 ----------
    window.toggleThinking = function(btn) {
        const thinkingText = btn.nextElementSibling;
        if (thinkingText) {
            if (thinkingText.style.display === 'none' || thinkingText.style.display === '') {
                thinkingText.style.display = 'block';
                btn.innerHTML = '💭 隐藏思考过程';
                // 转换为 Markdown（仅转换一次）
                if (!thinkingText.dataset.rawThinking) {
                    const raw = thinkingText.textContent.trim();
                    thinkingText.dataset.rawThinking = raw;
                    thinkingText.innerHTML = markdownToHtml(raw);
                }
            } else {
                thinkingText.style.display = 'none';
                btn.innerHTML = '💭 思考过程';
            }
        }
    };

    // ---------- 发送消息核心 ----------
    async function sendMessage() {
        const message = userInput ? userInput.value.trim() : '';
        if (!message) return;

        // 禁用发送按钮，防止重复发送
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.textContent = '发送中...';
        }
        if (userInput) userInput.disabled = true;

        // 显示用户消息
        appendUserMessage(message);
        clearInput();

        // 添加助手消息占位
        appendAssistantMessagePlaceholder();

        try {
            // 发起 SSE 请求
            const response = await fetch('/user/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // 如有 CSRF token 可在此添加
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: currentConversationId
                })
            });

            if (!response.ok) {
                throw new Error('请求失败：' + response.statusText);
            }

            // 读取 SSE 流
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let thinkingReceived = false;
            let assistantMsgDiv = getStreamingAssistantMessage();
            if (!assistantMsgDiv) {
                assistantMsgDiv = appendAssistantMessagePlaceholder();
            }
            const thinkingTextDiv = assistantMsgDiv.querySelector('.thinking-text');

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6).trim();
                        if (!dataStr) continue;
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.type === 'conversation_id') {
                                currentConversationId = data.conversation_id;
                                window.history.replaceState({}, '', '/user/chat?conversation_id=' + data.conversation_id);
                            } else if (data.type === 'thinking') {
                                if (thinkingTextDiv) {
                                    thinkingTextDiv.textContent += data.content;
                                    const toggleBtn = assistantMsgDiv.querySelector('.btn-thinking-toggle');
                                    if (toggleBtn && !thinkingReceived) {
                                        thinkingTextDiv.style.display = 'block';
                                        toggleBtn.innerHTML = '💭 隐藏思考过程';
                                        thinkingReceived = true;
                                    }
                                }
                                                        } else if (data.type === 'answer') {
                                // 动态创建答案区
                                let answerDiv = assistantMsgDiv.querySelector('.answer-text');
                                let answerSpan = answerDiv?.querySelector('.answer-content');
                                if (!answerDiv) {
                                    // 移除思考中
                                    const indicator = assistantMsgDiv.querySelector('.thinking-indicator');
                                    if (indicator) indicator.remove();

                                    answerDiv = document.createElement('div');
                                    answerDiv.className = 'answer-text';
                                    answerSpan = document.createElement('span');
                                    answerSpan.className = 'answer-content';
                                    answerDiv.appendChild(answerSpan);

                                    // 创建复制按钮
                                    const copyBtn = document.createElement('button');
                                    copyBtn.className = 'btn-copy-message';
                                    copyBtn.textContent = '📋';
                                    copyBtn.addEventListener('click', function(e) {
                                        e.stopPropagation();
                                        const raw = answerDiv.dataset.rawMarkdown || answerSpan.textContent;
                                        const thinkingContent = assistantMsgDiv.querySelector('.thinking-text')?.textContent || '';
                                        const full = thinkingContent ? thinkingContent + '\n\n' + raw : raw;
                                        copyMessageToClipboard(full);
                                    });
                                    answerDiv.appendChild(copyBtn);

                                    assistantMsgDiv.querySelector('.message-content').appendChild(answerDiv);
                                }
                                if (answerSpan) {
                                    answerSpan.textContent += data.content;
                                }
                            } else if (data.type === 'done') {
                                const answerSpan = assistantMsgDiv?.querySelector('.answer-content');
                                if (answerSpan) {
                                    const rawMarkdown = answerSpan.textContent.trim();
                                    const answerDiv = answerSpan.closest('.answer-text');
                                    if (answerDiv) answerDiv.dataset.rawMarkdown = rawMarkdown;
                                    answerSpan.innerHTML = markdownToHtml(rawMarkdown);
                                }
                                const thinkingDiv = assistantMsgDiv?.querySelector('.thinking-text');
                                if (thinkingDiv && thinkingDiv.style.display !== 'none') {
                                    const rawThinking = thinkingDiv.textContent.trim();
                                    thinkingDiv.dataset.rawThinking = rawThinking;
                                    thinkingDiv.innerHTML = markdownToHtml(rawThinking);
                                }
                            } else if (data.type === 'error') {
                                let answerDiv = assistantMsgDiv.querySelector('.answer-text');
                                if (!answerDiv) {
                                    const indicator = assistantMsgDiv.querySelector('.thinking-indicator');
                                    if (indicator) indicator.remove();
                                    answerDiv = document.createElement('div');
                                    answerDiv.className = 'answer-text';
                                    assistantMsgDiv.querySelector('.message-content').appendChild(answerDiv);
                                }
                                answerDiv.textContent = data.message || '发生未知错误';
                            }
                        } catch (e) {
                            console.error('解析 SSE 数据失败:', e);
                        }
                    }
                }
                scrollToBottom();
            }
        } catch (error) {
            // 网络错误或解析异常
            const assistantMsg = getStreamingAssistantMessage();
            if (assistantMsg) {
                const answerDiv = assistantMsg.querySelector('.answer-text');
                if (answerDiv && !answerDiv.textContent) {
                    answerDiv.textContent = '抱歉，请求失败：' + error.message;
                }
            }
            console.error('发送消息失败:', error);
        } finally {
            // 恢复输入状态
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.textContent = '发送';
            }
            if (userInput) userInput.disabled = false;
            userInput?.focus();
        }

        // 如果此次发送创建了新对话，更新 URL 和左侧列表（可选）
        // 这里简化：刷新页面或异步更新列表，暂时先不处理，用户可以手动刷新
        // 也可以在后端返回时带上 conversation_id，然后更新 currentConversationId
    }

    // ---------- 新建对话 ----------
    async function createNewConversation() {
        try {
            const response = await fetch('/user/conversation/new', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (response.ok) {
                const data = await response.json();
                // 跳转到新对话页面
                window.location.href = '/user/chat?conversation_id=' + data.id;
            } else {
                alert('创建新对话失败');
            }
        } catch (error) {
            console.error('创建对话错误:', error);
            alert('创建新对话时发生错误');
        }
    }

    // 删除对话
    async function deleteConversation(convId) {
        if (!confirm('确定要删除这个对话吗？')) return;
        try {
            const response = await fetch('/user/conversation/' + convId + '/delete', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            if (response.ok) {
                // 如果删除的是当前对话，跳转到无对话页
                if (currentConversationId === convId) {
                    window.location.href = '/user/chat';
                } else {
                    // 否则刷新页面以更新列表
                    window.location.reload();
                }
            } else {
                alert('删除失败');
            }
        } catch (error) {
            console.error('删除对话错误:', error);
            alert('删除时发生错误');
        }
    }

    // ---------- 事件绑定 ----------
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }

    if (userInput) {
        userInput.addEventListener('keydown', function(e) {
            // Shift+Enter 换行，Enter 发送
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        // 自动调整高度
        userInput.addEventListener('input', function() {
            userInput.style.height = 'auto';
            userInput.style.height = Math.min(userInput.scrollHeight, 150) + 'px';
        });
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', createNewConversation);
    }

    // 绑定删除对话按钮
    if (conversationList) {
        // 使用事件委托
        conversationList.addEventListener('click', function(e) {
            const deleteBtn = e.target.closest('.btn-delete-conv');
            if (deleteBtn) {
                e.preventDefault();
                e.stopPropagation();
                const convId = parseInt(deleteBtn.getAttribute('data-id'), 10);
                if (convId) {
                    deleteConversation(convId);
                }
            }
        });
    }

    // 页面加载完成后滚动到底部
    document.addEventListener('DOMContentLoaded', function() {

        // 转换所有历史答案的 Markdown（保留原始文本供复制）
        document.querySelectorAll('.answer-content').forEach(span => {
            const raw = span.textContent.trim();
            if (raw) {
                span.dataset.rawMarkdown = raw;
                span.innerHTML = markdownToHtml(raw);
            }
        });

        // 转换所有历史思维链的 Markdown（如果可见）
        document.querySelectorAll('.thinking-text').forEach(div => {
            if (div.style.display !== 'none' && div.textContent.trim()) {
                const raw = div.textContent.trim();
                div.dataset.rawThinking = raw;
                div.innerHTML = markdownToHtml(raw);
            }
        });

        // 强制所有答案区域可见（优先级最高，防止隐藏）
        document.querySelectorAll('.answer-text').forEach(el => {
            el.style.display = 'block';
        });

        // 清理任何不在答案区内的复制按钮
        document.querySelectorAll('.btn-copy-message').forEach(btn => {
            if (!btn.closest('.answer-text')) {
                btn.remove();
            }
        });

        // 确保所有历史助手消息的答案可见，思维链默认折叠但可点击展开
        document.querySelectorAll('.message-assistant').forEach(msg => {
            const thinkingText = msg.querySelector('.thinking-text');
            const toggleBtn = msg.querySelector('.btn-thinking-toggle');
            if (thinkingText && toggleBtn) {
                thinkingText.style.display = 'block';
                toggleBtn.innerHTML = '💭 思考过程';
            }
        });

        scrollToBottom();
        if (userInput) userInput.focus();
    });

})();