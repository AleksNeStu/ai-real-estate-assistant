/**
 * Professional Theme Toggle System
 * Supports light and dark modes with smooth transitions
 */

(function() {
    'use strict';

    const STORAGE_KEY = 'ai-real-estate-theme';
    const THEME_ATTR = 'data-theme';

    /**
     * Get current theme preference
     */
    function getThemePreference() {
        // Check localStorage first
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored && (stored === 'light' || stored === 'dark')) {
            return stored;
        }

        // Default to light theme
        return 'light';
    }

    /**
     * Apply theme to document
     */
    function applyTheme(theme) {
        console.log('Applying theme:', theme);

        // Set on html element
        document.documentElement.setAttribute(THEME_ATTR, theme);

        // Set on body
        document.body.setAttribute(THEME_ATTR, theme);

        // Find and set on stApp
        const stApp = document.querySelector('.stApp');
        if (stApp) {
            stApp.setAttribute(THEME_ATTR, theme);
        }

        // Find and set on main
        const main = document.querySelector('.main');
        if (main) {
            main.setAttribute(THEME_ATTR, theme);
        }

        // Store preference
        localStorage.setItem(STORAGE_KEY, theme);

        // Update toggle button
        updateToggleButton(theme);

        // Dispatch event
        window.dispatchEvent(new CustomEvent('themechange', {
            detail: { theme }
        }));

        console.log('Theme applied:', theme);
    }

    /**
     * Toggle theme
     */
    function toggleTheme() {
        const current = getThemePreference();
        const newTheme = current === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    }

    /**
     * Update toggle button appearance
     */
    function updateToggleButton(theme) {
        const btn = document.getElementById('theme-toggle');
        if (!btn) return;

        if (theme === 'dark') {
            btn.innerHTML = '☀️';
            btn.setAttribute('aria-label', 'Switch to light mode');
            btn.setAttribute('title', 'Switch to light mode');
        } else {
            btn.innerHTML = '🌙';
            btn.setAttribute('aria-label', 'Switch to dark mode');
            btn.setAttribute('title', 'Switch to dark mode');
        }
    }

    /**
     * Create toggle button
     */
    function createToggleButton() {
        // Remove existing button if any
        const existing = document.getElementById('theme-toggle-container');
        if (existing) {
            existing.remove();
        }

        // Create container
        const container = document.createElement('div');
        container.id = 'theme-toggle-container';

        // Create button
        const button = document.createElement('button');
        button.id = 'theme-toggle';
        button.className = 'theme-toggle-btn';
        button.setAttribute('aria-label', 'Toggle theme');
        button.style.cssText = `
            background-color: var(--background-secondary);
            border: 1px solid var(--border-color);
            border-radius: 50%;
            width: 3rem;
            height: 3rem;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: var(--shadow-md);
            font-size: 1.5rem;
        `;

        button.addEventListener('click', toggleTheme);

        container.appendChild(button);
        document.body.appendChild(container);

        // Initial state
        updateToggleButton(getThemePreference());
    }

    /**
     * Re-apply theme (for Streamlit re-runs)
     */
    function reapplyTheme() {
        const theme = getThemePreference();
        applyTheme(theme);

        // Recreate button if it doesn't exist
        if (!document.getElementById('theme-toggle')) {
            createToggleButton();
        }
    }

    /**
     * Initialize theme system
     */
    function init() {
        console.log('Initializing theme system...');

        // Apply initial theme
        const initialTheme = getThemePreference();
        applyTheme(initialTheme);

        // Create toggle button
        createToggleButton();

        // Watch for Streamlit re-runs
        const observer = new MutationObserver((mutations) => {
            // Check if stApp was re-rendered
            const stAppChanged = mutations.some(mutation =>
                Array.from(mutation.addedNodes).some(node =>
                    node.classList && (
                        node.classList.contains('stApp') ||
                        node.classList.contains('main')
                    )
                )
            );

            if (stAppChanged) {
                console.log('Streamlit re-render detected, re-applying theme');
                setTimeout(reapplyTheme, 100);
            }

            // Recreate button if needed
            if (!document.getElementById('theme-toggle')) {
                createToggleButton();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        console.log('Theme system initialized');
    }

    /**
     * Expose API
     */
    window.ThemeManager = {
        getTheme: getThemePreference,
        setTheme: applyTheme,
        toggleTheme: toggleTheme,
        init: init,
        reapply: reapplyTheme
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Also initialize after page load (for Streamlit)
    window.addEventListener('load', () => {
        setTimeout(init, 500);
    });

    // Re-apply theme periodically (for Streamlit hot reloads)
    setInterval(() => {
        const btn = document.getElementById('theme-toggle');
        if (!btn) {
            createToggleButton();
        }
        reapplyTheme();
    }, 2000);

})();
