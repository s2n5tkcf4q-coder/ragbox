/* static/js/admin_settings.js */
(function() {
    'use strict';

    const llmModeSelect = document.getElementById('llm_mode');
    const apiConfigDiv = document.getElementById('api-config');
    const ollamaConfigDiv = document.getElementById('ollama-config');
    const testBtn = document.getElementById('test-connection-btn');
    const testResultSpan = document.getElementById('test-result');

    function toggleConfigSections() {
        if (!llmModeSelect || !apiConfigDiv || !ollamaConfigDiv) return;
        const mode = llmModeSelect.value;
        if (mode === 'api') {
            apiConfigDiv.style.display = 'block';
            ollamaConfigDiv.style.display = 'none';
        } else if (mode === 'ollama') {
            apiConfigDiv.style.display = 'none';
            ollamaConfigDiv.style.display = 'block';
        }
    }

    if (llmModeSelect) {
        llmModeSelect.addEventListener('change', toggleConfigSections);
        toggleConfigSections();   // 初始显示
    }

    // 测试连接（已修复）
    if (testBtn && testResultSpan) {
        testBtn.addEventListener('click', async function() {
            // 测试连接
            if (testBtn && testResultSpan) {
                testBtn.addEventListener('click', async function() {
                    testBtn.disabled = true;
                    testBtn.textContent = '测试中...';
                    testResultSpan.textContent = '';
                    testResultSpan.className = 'test-result';

                    // 收集当前表单配置
                    const mode = document.getElementById('llm_mode').value;
                    let chatModel, embeddingModel;
                    let apiBaseUrl = '', apiKey = '', ollamaBaseUrl = '';

                    if (mode === 'api') {
                        chatModel = document.getElementById('api_chat_model').value.trim();
                        embeddingModel = document.getElementById('api_embedding_model').value.trim();
                        apiBaseUrl = document.getElementById('api_base_url').value.trim();
                        apiKey = document.getElementById('api_key').value.trim();
                    } else {
                        chatModel = document.getElementById('local_chat_model').value.trim();
                        embeddingModel = document.getElementById('local_embedding_model').value.trim();
                        ollamaBaseUrl = document.getElementById('ollama_base_url').value.trim();
                    }

                    const payload = {
                        mode: mode,
                        chat_model: chatModel,
                        embedding_model: embeddingModel,
                        api_base_url: apiBaseUrl,
                        api_key: apiKey,
                        ollama_base_url: ollamaBaseUrl
                    };

                    try {
                        const response = await fetch('/admin/test_connection', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload)
                        });
                        const data = await response.json();

                        if (data.success) {
                            testResultSpan.textContent = '✓ ' + (data.message || '连接成功');
                            testResultSpan.className = 'test-result success';
                        } else {
                            testResultSpan.textContent = '✗ ' + (data.message || '连接失败');
                            testResultSpan.className = 'test-result error';
                        }
                    } catch (error) {
                        testResultSpan.textContent = '✗ 请求失败: ' + error.message;
                        testResultSpan.className = 'test-result error';
                    } finally {
                        testBtn.disabled = false;
                        testBtn.textContent = '测试连接';
                    }
                });
            }
        });
    }
})();