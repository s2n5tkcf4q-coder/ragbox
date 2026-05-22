/* static/js/register.js */
/* 注册页面脚本：密码确认校验、前端验证辅助 */

(function() {
    'use strict';

    const passwordInput = document.getElementById('password');
    const confirmInput = document.getElementById('confirm_password');
    const hintSpan = document.getElementById('password-match-hint');
    const registerForm = document.querySelector('.login-form'); // 复用 login-form class

    // 实时监听确认密码输入，显示匹配提示
    if (confirmInput && passwordInput && hintSpan) {
        function checkPasswordMatch() {
            const password = passwordInput.value;
            const confirm = confirmInput.value;

            if (confirm.length === 0) {
                hintSpan.textContent = '';
                hintSpan.className = 'form-hint';
                return;
            }

            if (password === confirm) {
                hintSpan.textContent = '✓ 两次密码一致';
                hintSpan.className = 'form-hint match-success';
            } else {
                hintSpan.textContent = '✗ 两次密码不一致';
                hintSpan.className = 'form-hint match-error';
            }
        }

        passwordInput.addEventListener('input', checkPasswordMatch);
        confirmInput.addEventListener('input', checkPasswordMatch);
    }

    // 表单提交前的验证
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const username = document.getElementById('username').value.trim();
            const password = passwordInput ? passwordInput.value : '';
            const confirm = confirmInput ? confirmInput.value : '';

            // 用户名长度检查
            if (username.length < 2) {
                e.preventDefault();
                alert('用户名至少需要2个字符');
                return false;
            }

            // 密码长度检查
            if (password.length < 6) {
                e.preventDefault();
                alert('密码至少需要6位字符');
                return false;
            }

            // 密码一致性检查
            if (password !== confirm) {
                e.preventDefault();
                alert('两次输入的密码不一致，请重新输入');
                return false;
            }

            // 可添加更多规则，如密码强度等
        });
    }

})();