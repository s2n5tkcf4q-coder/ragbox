/* static/js/admin.js */
/* 管理后台通用脚本：侧边栏折叠、移动端菜单、子配置显示切换 */

(function() {
    'use strict';

    const sidebarToggle = document.getElementById('sidebar-toggle');
    const adminSidebar = document.getElementById('admin-sidebar');

    // 侧边栏折叠/展开（移动端可见）
    if (sidebarToggle && adminSidebar) {
        sidebarToggle.addEventListener('click', function() {
            adminSidebar.classList.toggle('collapsed');
            // 可选：调整主内容区域
            const content = document.querySelector('.admin-content');
            if (content) {
                content.style.marginLeft = adminSidebar.classList.contains('collapsed') ? '0' : '';
            }
        });
    }

    // 页面加载完成后的初始化
    document.addEventListener('DOMContentLoaded', function() {
        // 高亮当前菜单项（通过 URL 匹配）
        const currentPath = window.location.pathname;
        const sidebarLinks = document.querySelectorAll('.sidebar-link');
        sidebarLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && currentPath.startsWith(href)) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });

        // 如果有其他通用初始化，可在此添加
    });

})();