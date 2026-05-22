/* static/js/admin_upload.js */
/* 文件上传处理页面脚本：文件选择预览、上传验证、按钮状态控制 */

(function() {
    'use strict';

    const fileInput = document.getElementById('document');
    const fileNameSpan = document.getElementById('file-name');
    const uploadForm = document.querySelector('.upload-form');
    const uploadBtn = document.querySelector('.btn-upload');

    // 文件选择后显示文件名
    if (fileInput && fileNameSpan) {
        fileInput.addEventListener('change', function() {
            if (fileInput.files && fileInput.files.length > 0) {
                const fileName = fileInput.files[0].name;
                fileNameSpan.textContent = fileName;
                // 检查扩展名（前端友好提示）
                if (!fileName.toLowerCase().endsWith('.docx')) {
                    fileNameSpan.textContent = '（请选择 .docx 文件）';
                    fileNameSpan.style.color = 'var(--alert-danger-text)';
                    fileInput.value = ''; // 清除无效选择
                } else {
                    fileNameSpan.style.color = 'var(--text-secondary)';
                }
            } else {
                fileNameSpan.textContent = '未选择文件';
                fileNameSpan.style.color = 'var(--text-secondary)';
            }
        });
    }

    // 表单提交：防止重复点击、简单验证
    if (uploadForm && uploadBtn) {
        uploadForm.addEventListener('submit', function(e) {
            // 检查是否有文件
            if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
                e.preventDefault();
                alert('请先选择一个 .docx 文件');
                return false;
            }

            const file = fileInput.files[0];
            if (!file.name.toLowerCase().endsWith('.docx')) {
                e.preventDefault();
                alert('仅支持 .docx 格式的文件');
                return false;
            }

            // 禁用按钮，显示加载状态
            uploadBtn.disabled = true;
            uploadBtn.textContent = '处理中，请稍候...';
            // 表单会继续提交，页面将刷新
            // 注意：如果服务器处理时间较长，按钮会在新页面中恢复，这里只是视觉反馈
        });
    }

    // 页面加载完成后的状态恢复（防止用户刷新后按钮仍被禁用）
    document.addEventListener('DOMContentLoaded', function() {
        if (uploadBtn && uploadBtn.disabled) {
            uploadBtn.disabled = false;
            uploadBtn.textContent = '🚀 开始处理';
        }
        if (fileNameSpan && fileNameSpan.textContent === '未选择文件') {
            // 如果之前有选择但页面刷新，重置为空状态
        }
    });

})();