/* static/js/common.js */
/* 全局公共脚本：日/夜模式切换、自动登出计时、工具函数 */

(function() {
    'use strict';

    // ---------- 日/夜模式切换 ----------
    const body = document.body;
    const themeToggle = document.getElementById('theme-toggle');

    // 读取本地存储的主题偏好，默认日间模式
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        body.classList.remove('light-mode');
        body.classList.add('dark-mode');
    } else {
        body.classList.add('light-mode');
        body.classList.remove('dark-mode');
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            if (body.classList.contains('light-mode')) {
                body.classList.remove('light-mode');
                body.classList.add('dark-mode');
                localStorage.setItem('theme', 'dark');
            } else {
                body.classList.remove('dark-mode');
                body.classList.add('light-mode');
                localStorage.setItem('theme', 'light');
            }
        });
    }

    // ---------- 自动登出（空闲1小时自动跳转登录页） ----------
    const IDLE_TIMEOUT = 60 * 60 * 1000; // 1小时
    let idleTimer;

    function resetIdleTimer() {
        clearTimeout(idleTimer);
        idleTimer = setTimeout(logoutDueToInactivity, IDLE_TIMEOUT);
    }

    function logoutDueToInactivity() {
        // 清除本地存储的敏感信息（如有）
        // 跳转到登出地址
        window.location.href = '/auth/logout';
    }

    // 监听用户活动事件，重置计时器
    ['mousemove', 'keydown', 'scroll', 'click', 'touchstart'].forEach(function(eventName) {
        document.addEventListener(eventName, resetIdleTimer, { passive: true });
    });

    // 初始化计时器
    resetIdleTimer();

    // 页面加载完成后的公共操作
    document.addEventListener('DOMContentLoaded', function() {
        // 可为所有 AJAX 请求设置 CSRF token（如需要）
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            const csrfToken = csrfMeta.getAttribute('content');
            // 为所有 fetch 请求添加默认头（示例）
            const originalFetch = window.fetch;
            window.fetch = function(url, options = {}) {
                if (options.headers === undefined) {
                    options.headers = {};
                }
                if (typeof options.headers === 'object' && !options.headers['X-CSRFToken']) {
                    options.headers['X-CSRFToken'] = csrfToken;
                }
                return originalFetch(url, options);
            };
        }
    });

})();