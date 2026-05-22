/* static/js/admin_files.js */
/* 文件列表页面脚本：查看分块、删除确认、面板控制 */

(function() {
    'use strict';

    const chunksPanel = document.getElementById('chunks-panel');
    const chunksContent = document.getElementById('chunks-content');
    const chunksDocName = document.getElementById('chunks-doc-name');
    const closeChunksBtn = document.getElementById('close-chunks');

    // 存储当前选中的行元素
    let currentRow = null;

    // 关闭分块面板
    function closePanel() {
        if (chunksPanel) {
            chunksPanel.style.display = 'none';
        }
        if (currentRow) {
            currentRow.classList.remove('row-active');
            currentRow = null;
        }
    }

    // 绑定关闭按钮事件
    if (closeChunksBtn) {
        closeChunksBtn.addEventListener('click', closePanel);
    }

    // 格式化文件大小（可选）
    function formatSize(kb) {
        if (kb >= 1024) {
            return (kb / 1024).toFixed(2) + ' MB';
        }
        return kb + ' KB';
    }

    // 加载并显示分块
    async function loadChunks(docId, filename) {
        if (!chunksContent || !chunksPanel) return;

        // 显示加载状态
        chunksContent.innerHTML = '<div class="loading">加载中...</div>';
        chunksPanel.style.display = 'block';

        try {
            const response = await fetch('/admin/file/' + docId + '/chunks');
            if (!response.ok) {
                throw new Error('请求失败：' + response.statusText);
            }
            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }

            // 更新文档名称
            if (chunksDocName) {
                chunksDocName.textContent = filename + ' (' + data.document.chunk_count + ' 个分块)';
            }

            // 构建分块列表 HTML
            let html = '';
            const chunks = data.chunks;
            if (chunks.length === 0) {
                html = '<div class="no-data">该文档无文本块</div>';
            } else {
                chunks.forEach(function(chunk) {
                    html += '<div class="chunk-item">';
                    html += '<div class="chunk-index">分块 #' + (chunk.index + 1) + ' （' + chunk.char_count + ' 字符）</div>';
                    html += '<div class="chunk-text">' + escapeHtml(chunk.content) + '</div>';
                    html += '</div>';
                });
            }
            chunksContent.innerHTML = html;
        } catch (error) {
            chunksContent.innerHTML = '<div class="alert alert-danger">加载失败：' + error.message + '</div>';
        }
    }

    // 简单的 HTML 转义函数，防止 XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 绑定查看分块按钮事件
    function bindViewButtons() {
        const viewButtons = document.querySelectorAll('.view-chunks-btn');
        viewButtons.forEach(function(btn) {
            btn.addEventListener('click', function() {
                const row = btn.closest('.file-row');
                if (!row) return;

                // 高亮当前行
                if (currentRow) {
                    currentRow.classList.remove('row-active');
                }
                row.classList.add('row-active');
                currentRow = row;

                // 获取文档 ID 和文件名
                const docId = row.getAttribute('data-doc-id');
                const filenameCell = row.querySelector('td:nth-child(2)');
                const filename = filenameCell ? filenameCell.textContent.trim() : '文档';

                if (docId) {
                    loadChunks(docId, filename);
                }
            });
        });
    }

    // 删除按钮增强确认（HTML已有onsubmit，这里作为额外层）
    function bindDeleteButtons() {
        const deleteForms = document.querySelectorAll('form[action*="/admin/file/delete/"]');
        deleteForms.forEach(function(form) {
            form.addEventListener('submit', function(e) {
                const row = form.closest('tr');
                let filename = '该文件';
                if (row) {
                    const nameCell = row.querySelector('td:nth-child(2)');
                    if (nameCell) {
                        filename = nameCell.textContent.trim();
                    }
                }
                const confirmed = confirm('确定要永久删除文件 "' + filename + '" 及其所有分块数据吗？');
                if (!confirmed) {
                    e.preventDefault();
                    return false;
                }
                // 二次确认
                const doubleConfirm = confirm('再次确认：此操作不可恢复，是否继续？');
                if (!doubleConfirm) {
                    e.preventDefault();
                    return false;
                }
            });
        });
    }

    // 页面加载完成后初始化
    document.addEventListener('DOMContentLoaded', function() {
        bindViewButtons();
        bindDeleteButtons();

        // 初始隐藏面板
        if (chunksPanel) {
            chunksPanel.style.display = 'none';
        }
    });

})();