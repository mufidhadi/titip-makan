/**
 * Navigation Bar Controller
 * Handles mobile hamburger toggle, keyboard interactions, outside-click dismissal,
 * and active navigation link state highlighting.
 */
document.addEventListener('DOMContentLoaded', () => {
    const currentPath = window.location.pathname.replace(/\/$/, '') || '/';

    // 1. Highlight Active Nav Items
    const desktopLinks = document.querySelectorAll('.nav-item');
    desktopLinks.forEach(link => {
        const href = (link.getAttribute('href') || '').replace(/\/$/, '') || '/';
        const isCoordinator = href === '/coordinator';
        const isActive = href === '/' ? currentPath === '/' : currentPath.startsWith(href);

        if (isActive) {
            if (isCoordinator) {
                link.className = 'nav-item px-3 py-1.5 rounded-lg bg-indigo-600 text-white font-semibold shadow-xs transition flex items-center gap-1.5';
            } else {
                link.className = 'nav-item px-3 py-1.5 rounded-lg bg-slate-100 text-indigo-600 font-bold shadow-xs transition flex items-center gap-1.5';
            }
        }
    });

    const mobileLinks = document.querySelectorAll('.mobile-nav-item');
    mobileLinks.forEach(link => {
        const href = (link.getAttribute('href') || '').replace(/\/$/, '') || '/';
        const isActive = href === '/' ? currentPath === '/' : currentPath.startsWith(href);

        if (isActive) {
            link.classList.add('bg-indigo-50/70', 'border-l-4', 'border-indigo-600');
            const title = link.querySelector('.font-bold') || link.querySelector('.font-semibold');
            if (title) {
                title.classList.remove('text-slate-800');
                title.classList.add('text-indigo-700');
            }
        }
    });

    // 2. Mobile Menu Toggle Controller
    const menuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    const iconBars = document.getElementById('menu-icon-bars');
    const iconClose = document.getElementById('menu-icon-close');

    if (menuBtn && mobileMenu) {
        const toggleMenu = (forceClose = false) => {
            const isCurrentlyOpen = menuBtn.getAttribute('aria-expanded') === 'true';
            const shouldOpen = forceClose ? false : !isCurrentlyOpen;

            menuBtn.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
            if (shouldOpen) {
                mobileMenu.classList.remove('hidden');
                iconBars?.classList.add('hidden');
                iconClose?.classList.remove('hidden');
            } else {
                mobileMenu.classList.add('hidden');
                iconBars?.classList.remove('hidden');
                iconClose?.classList.add('hidden');
            }
        };

        menuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleMenu();
        });

        // Close when clicking outside of menu and toggle button
        document.addEventListener('click', (e) => {
            if (!mobileMenu.classList.contains('hidden')) {
                if (!mobileMenu.contains(e.target) && !menuBtn.contains(e.target)) {
                    toggleMenu(true);
                }
            }
        });

        // Close on Escape key press
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !mobileMenu.classList.contains('hidden')) {
                toggleMenu(true);
                menuBtn.focus();
            }
        });

        // Close when any mobile nav item is clicked
        mobileLinks.forEach(item => {
            item.addEventListener('click', () => {
                toggleMenu(true);
            });
        });
    }
});
