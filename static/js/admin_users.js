/* static/js/admin_users.js */
/* 用户管理页面脚本：角色切换确认、删除二次确认、表格交互 */

(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        // 角色选择下拉框变更时的确认提示
        const roleSelects = document.querySelectorAll('.role-select');
        roleSelects.forEach(function(select) {
            select.addEventListener('change', function(e) {
                const newRole = select.value;
                const row = select.closest('tr');
                let username = '该用户';
                if (row) {
                    const nameCell = row.querySelector('td:nth-child(2)');
                    if (nameCell) {
                        username = nameCell.textContent.trim();
                    }
                }
                const confirmed = confirm(`确定要将用户 "${username}" 的角色更改为 "${newRole === 'admin' ? '管理员' : '普通用户'}" 吗？`);
                if (!confirmed) {
                    // 恢复原来的值
                    e.preventDefault();
                    // 找到 selected 属性恢复
                    const options = select.querySelectorAll('option');
                    options.forEach(function(opt) {
                        if (opt.defaultSelected) {
                            select.value = opt.value;
                        }
                    });
                    return false;
                }
                // 确认后，表单会自动提交
            });
        });

        // 删除按钮增强确认（HTML 已有 onsubmit 确认，此处可添加更友好的提示）
        const deleteForms = document.querySelectorAll('form[action*="/user/delete/"]');
        deleteForms.forEach(function(form) {
            form.addEventListener('submit', function(e) {
                const row = form.closest('tr');
                let username = '该用户';
                if (row) {
                    const nameCell = row.querySelector('td:nth-child(2)');
                    if (nameCell) {
                        username = nameCell.textContent.trim();
                    }
                }
                const confirmed = confirm(`警告：即将永久删除用户 "${username}" 及其所有数据！\n\n此操作不可恢复，确定要继续吗？`);
                if (!confirmed) {
                    e.preventDefault();
                    return false;
                }
                // 二次确认
                const doubleConfirm = confirm(`请再次确认：真的要删除用户 "${username}" 吗？`);
                if (!doubleConfirm) {
                    e.preventDefault();
                    return false;
                }
            });
        });

        // 表格行悬停高亮效果（纯视觉增强）
        const tableRows = document.querySelectorAll('.users-table tbody tr');
        tableRows.forEach(function(row) {
            row.addEventListener('mouseenter', function() {
                row.style.backgroundColor = 'var(--btn-secondary-bg)';
            });
            row.addEventListener('mouseleave', function() {
                row.style.backgroundColor = '';
            });
        });
    });

})();