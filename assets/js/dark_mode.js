/**
 * Dark Mode Toggle with System Preference Detection
 * Provides automatic theme detection and manual override functionality
 * Ensures accessibility and smooth transitions
 */

(function() {
    'use strict';

    // Configuration
    const STORAGE_KEY = 'theme-preference';
    const THEME_ATTRIBUTE = 'data-theme';
    const SYSTEM_PREFERENCE = window.matchMedia('(prefers-color-scheme: dark)');

    /**
     * Get the current theme preference
     * Priority: Manual override > System preference > Default (light)
     */
    function getThemePreference() {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            return stored;
        }
        return SYSTEM_PREFERENCE.matches ? 'dark' : 'light';
    }

    /**
     * Set theme preference and apply to DOM
     */
    function setTheme(theme) {
        // Store preference
        localStorage.setItem(STORAGE_KEY, theme);

        // Apply to document
        document.documentElement.setAttribute(THEME_ATTRIBUTE, theme);

        // Also apply to Streamlit app container if it exists
        const stApp = document.querySelector('.stApp');
        if (stApp) {
            stApp.setAttribute(THEME_ATTRIBUTE, theme);
        }

        // Update toggle button if it exists
        updateToggleButton(theme);

        // Dispatch custom event for other components
        window.dispatchEvent(new CustomEvent('themechange', {
            detail: { theme }
        }));

        console.log(`Theme changed to: ${theme}`);
    }

    /**
     * Toggle between light and dark themes
     */
    function toggleTheme() {
        const currentTheme = getThemePreference();
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
    }

    /**
     * Update toggle button appearance
     */
    function updateToggleButton(theme) {
        const toggleBtn = document.getElementById('theme-toggle');
        if (!toggleBtn) return;

        const icon = toggleBtn.querySelector('.theme-icon');
        if (!icon) return;

        if (theme === 'dark') {
            icon.textContent = '☀️';
            toggleBtn.setAttribute('aria-label', 'Switch to light mode');
            toggleBtn.setAttribute('title', 'Switch to light mode');
        } else {
            icon.textContent = '🌙';
            toggleBtn.setAttribute('aria-label', 'Switch to dark mode');
            toggleBtn.setAttribute('title', 'Switch to dark mode');
        }
    }

    /**
     * Create and inject toggle button
     */
    function createToggleButton() {
        // Check if button already exists
        if (document.getElementById('theme-toggle')) {
            return;
        }

        const button = document.createElement('button');
        button.id = 'theme-toggle';
        button.className = 'theme-toggle-btn';
        button.setAttribute('aria-label', 'Toggle theme');
        button.style.cssText = `
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 9999;
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

        const icon = document.createElement('span');
        icon.className = 'theme-icon';
        button.appendChild(icon);

        button.addEventListener('click', toggleTheme);

        // Add hover effect
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
        });

        button.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });

        document.body.appendChild(button);

        // Initial button state
        updateToggleButton(getThemePreference());
    }

    /**
     * Listen for system theme changes
     */
    function watchSystemTheme() {
        SYSTEM_PREFERENCE.addEventListener('change', (e) => {
            // Only auto-update if user hasn't manually set a preference
            if (!localStorage.getItem(STORAGE_KEY)) {
                const newTheme = e.matches ? 'dark' : 'light';
                setTheme(newTheme);
            }
        });
    }

    /**
     * Apply theme to chart elements (Plotly, etc.)
     */
    function applyThemeToCharts(theme) {
        // This will be called by Streamlit components
        const plotlyElements = document.querySelectorAll('.js-plotly-plot');
        plotlyElements.forEach(plot => {
            if (window.Plotly && plot.data) {
                const layout = plot.layout || {};
                if (theme === 'dark') {
                    layout.paper_bgcolor = '#1a1d24';
                    layout.plot_bgcolor = '#1a1d24';
                    layout.font = { color: '#fafafa' };
                } else {
                    layout.paper_bgcolor = '#ffffff';
                    layout.plot_bgcolor = '#ffffff';
                    layout.font = { color: '#262730' };
                }
                window.Plotly.relayout(plot, layout);
            }
        });
    }

    /**
     * Initialize theme system
     */
    function initTheme() {
        // Apply initial theme
        const initialTheme = getThemePreference();
        setTheme(initialTheme);

        // Watch for system preference changes
        watchSystemTheme();

        // Create toggle button after DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', createToggleButton);
        } else {
            createToggleButton();
        }

        // Listen for theme changes to update charts
        window.addEventListener('themechange', (e) => {
            applyThemeToCharts(e.detail.theme);
        });

        // Re-inject button when Streamlit reruns (use MutationObserver)
        const observer = new MutationObserver((mutations) => {
            const hasToggle = document.getElementById('theme-toggle');
            if (!hasToggle) {
                createToggleButton();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    /**
     * Expose API for Streamlit components
     */
    window.ThemeManager = {
        getTheme: getThemePreference,
        setTheme: setTheme,
        toggleTheme: toggleTheme,
        applyToCharts: applyThemeToCharts
    };

    // Initialize on load
    initTheme();

    // Also initialize when Streamlit finishes loading
    window.addEventListener('load', () => {
        setTimeout(initTheme, 100); // Small delay to ensure Streamlit is ready
    });

    console.log('Dark mode system initialized');
})();
