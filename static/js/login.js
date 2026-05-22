/* static/js/login.js */
/* 登录页面脚本：验证码刷新、表单验证辅助 */

(function() {
    'use strict';

    const captchaImg = document.getElementById('captcha-img');

    // 刷新验证码函数
    function refreshCaptcha() {
        if (captchaImg) {
            // 添加随机参数避免浏览器缓存
            captchaImg.src = '/auth/captcha?' + new Date().getTime();
        }
    }

    // 点击验证码图片刷新
    if (captchaImg) {
        captchaImg.addEventListener('click', refreshCaptcha);
    }

    // 简单的前端表单验证（作为后端验证的补充）
    const loginForm = document.querySelector('.login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            const captcha = document.getElementById('captcha').value.trim();

            if (!username || !password || !captcha) {
                e.preventDefault();
                alert('请填写所有必填项');
                return false;
            }

            if (captcha.length !== 4) {
                e.preventDefault();
                alert('验证码为4位数字');
                return false;
            }

            // 可以添加更多检查，但不强制
        });
    }

})();