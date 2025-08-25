#!/bin/bash

echo "🔧 FIXING FRONTEND TO USE LOCAL BACKEND"
echo "========================================"
echo ""

# Ensure .env file exists with correct URL
echo "✅ Setting API URL to localhost:8000..."
echo "VITE_API_BASE_URL=http://localhost:8000" > .env

# Clear browser cache instructions
echo ""
echo "📱 NOW IN YOUR BROWSER:"
echo "  1. Go to: http://localhost:5173"
echo "  2. Open DevTools (F12)"
echo "  3. Right-click the refresh button"
echo "  4. Select 'Empty Cache and Hard Reload'"
echo "     OR press Cmd+Shift+R (Mac) / Ctrl+Shift+F5 (Windows)"
echo ""
echo "✅ The frontend should now connect to localhost:8000"
echo "✅ No more 422 errors from 34.29.29.170"
echo ""
echo "If you still see old URLs:"
echo "  - Try an incognito/private window"
echo "  - Clear all site data for localhost"
