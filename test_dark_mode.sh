#!/bin/bash
# Quick test script for dark mode verification

echo "🌓 Starting Dark Mode Test..."
echo ""
echo "This will open a test page to verify dropdown visibility"
echo "and all form elements in dark mode."
echo ""
echo "Testing checklist:"
echo "  ✓ Dropdown menus are visible"
echo "  ✓ Option text is readable"
echo "  ✓ Hover states work correctly"
echo "  ✓ Form labels are visible (e.g., 'Your Email Address')"
echo "  ✓ All interactive elements have proper contrast"
echo ""
echo "Press Ctrl+C to stop the test"
echo ""

streamlit run test_dark_mode.py --server.port 8502
