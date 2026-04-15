# ⚡ SEO Technical Audit Tool

A professional-grade SEO crawler with a full web UI. Performs 30+ on-page and technical SEO checks on any URL with exact fixes and Google documentation references.

## 🚀 Deploy Online (Railway — Free)

1. Upload all 5 files to your GitHub repo
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Select your repo → Railway auto-detects Python and deploys
4. Your live URL appears in ~2 minutes ✅

## 💻 Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
python app.py

# 3. Open in browser
http://localhost:5000
```

## 📁 Files

| File | Purpose |
|------|---------|
| `app.py` | Flask web server + full frontend UI |
| `crawler.py` | SEO audit engine (30+ checks) |
| `requirements.txt` | Python dependencies |
| `Procfile` | Tells Railway/Render how to start the app |
| `README.md` | This file |

## 📊 What It Checks (30+ Checks)

### Technical SEO
- HTTPS enforcement
- SSL certificate validity + days to expiry
- Redirect chain (count, type, full chain)
- Real page load time measurement
- HTTP status code (200, 301, 302, 404, 5xx)
- robots.txt — presence + URL-level block detection
- XML Sitemap detection
- Response headers — Cache-Control, Content-Type, X-Robots-Tag, Charset
- GZIP/Brotli compression
- Render-blocking scripts in `<head>`

### On-Page SEO
- Title tag — presence, length (30–60 chars), duplicates
- Meta description — presence, length (120–160 chars), duplicates
- H1 — presence, multiple H1s, heading hierarchy
- Canonical tag — presence, empty href, self-referential check
- Meta robots — noindex, nofollow, `none` detection
- Open Graph tags (5 required tags)
- Twitter Card tags
- Image alt text — missing, empty, count
- Image dimensions (CLS prevention)
- Internal/external links + empty anchor text
- URL structure (length, underscores, uppercase)
- Content word count (thin content)
- Structured data / Schema.org (JSON-LD + Microdata)
- Viewport meta tag
- HTML lang attribute
- Hreflang + x-default
- Favicon
- Inline scripts/styles
- Text-to-HTML ratio

## SEO Score
Each issue deducts points: Critical (−15), High (−8), Medium (−4), Low (−1). Maximum score: 100.
