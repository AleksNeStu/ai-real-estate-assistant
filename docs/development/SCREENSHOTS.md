# Taking Screenshots for Documentation

This guide explains how to take proper screenshots of the AI Real Estate Assistant for documentation and marketing purposes.

## Prerequisites

- App running in Docker with demo mode enabled
- Dark theme enabled in UI
- Clean browser state (incognito mode recommended)
- Screenshot capture tool

## Setup Instructions

### 1. Start the Application

```bash
cd deploy/compose
docker compose up --build
```

### 2. Access the UI

Open your browser to: http://localhost:3082

### 3. Enable Demo Mode

The demo mode should be enabled by default (you'll see a banner at the top). If not, toggle it on using the switch in the banner.

### 4. Enable Dark Theme

The screenshots should use dark theme for consistency. Look for a theme toggle in the settings menu.

## Screenshot List

Take screenshots of the following pages (in order):

1. **01-home.png** - Home page with hero section
   - URL: http://localhost:3082/
   - Content: Hero section with search bar

2. **02-search.png** - Property search with sample results
   - URL: http://localhost:3082/search
   - Content: Search results showing sample properties

3. **03-chat.png** - AI chat interface with demo response
   - URL: http://localhost:3082/chat
   - Content: Chat interface with a sample conversation

4. **04-analytics.png** - Market trends visualization
   - URL: http://localhost:3082/market-trends
   - Content: Market charts and statistics

5. **05-favorites.png** - Saved properties list
   - URL: http://localhost:3082/favorites
   - Content: List of favorited properties

6. **06-city-overview.png** - City statistics page
   - URL: http://localhost:3082/cities
   - Content: City overview with market data

7. **07-agents.png** - AI agents configuration
   - URL: http://localhost:3082/agents
   - Content: Agent settings and configuration

8. **08-knowledge.png** - Knowledge base articles
   - URL: http://localhost:3082/knowledge
   - Content: Knowledge base interface

9. **09-documents.png** - Document management
   - URL: http://localhost:3082/documents
   - Content: Document list and management

10. **10-settings.png** - User settings with demo toggle
    - URL: http://localhost:3082/settings
    - Content: Settings page showing demo mode toggle

## Screenshot Tools

### macOS
- **Selection**: Cmd+Shift+4
- **Full UI capture**: Cmd+Shift+5
- **Specific window**: Cmd+Shift+4, then Space

### Windows
- **Snipping Tool**: Win+Shift+S (recommended)
- **Snip & Sketch**: Win+Shift+S
- **Full screenshot**: PrtScn (Print Screen)

### Linux
- **GNOME**: gnome-screenshot
- **KDE**: spectacle
- **Command line**: import -window root screenshot.png (ImageMagick)

## Best Practices

1. **Consistent dimensions**: Try to keep all screenshots the same size (recommended: 1280x800)
2. **Dark theme**: Use dark theme for all screenshots
3. **Clean browser**: Use incognito/private mode to avoid extensions cluttering the UI
4. **No personal data**: Ensure no personal information is visible
5. **High quality**: Use PNG format for best quality

## Image Optimization (Optional)

If you need to optimize file sizes:

```bash
# Using pngquant (recommended)
pngquant --quality=85-95 --ext .png --force assets/screenshots/*.png

# Using optipng
optipng -o7 assets/screenshots/*.png
```

## File Organization

Place screenshots in: `assets/screenshots/`

Naming convention:
- `01-page-name.png` (dark theme)
- `01-page-name-light.png` (light theme, if needed)

## Troubleshooting

### App won't start
```bash
# Check Docker logs
docker compose logs backend
docker compose logs frontend

# Verify services are running
docker compose ps
```

### Can't access UI
- Ensure backend is healthy: `curl http://localhost:8082/health`
- Check frontend is running: `curl http://localhost:3082/`
- Try clearing browser cache

### Screenshots look wrong
- Verify dark theme is enabled
- Check browser zoom is at 100%
- Ensure browser window is maximized
- Try a different browser

## Automated Screenshot Creation

For automated screenshot creation, Playwright scripts can be used. See `scripts/screenshots/` for examples (note: recent screenshot commits had issues, so manual capture is recommended for now).
