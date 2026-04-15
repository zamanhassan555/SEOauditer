"""
SEO Technical Audit Crawler
Performs deep on-page + technical SEO analysis
"""

import re
import ssl
import json
import time
import socket
import urllib3
import urllib.parse
from datetime import datetime
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SEO_STANDARDS = {
    "title_min": 30,
    "title_max": 60,
    "meta_desc_min": 120,
    "meta_desc_max": 160,
    "content_min_words": 300,
    "max_load_time_ms": 3000,
    "max_url_length": 100,
    "max_redirects": 3,
}

SEVERITY = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "PASS": "pass",
}


class SEOIssue:
    def __init__(self, category, check, severity, message, reference, solution, found=None):
        self.category = category
        self.check = check
        self.severity = severity
        self.message = message
        self.reference = reference
        self.solution = solution
        self.found = found

    def to_dict(self):
        return {
            "category": self.category,
            "check": self.check,
            "severity": self.severity,
            "message": self.message,
            "reference": self.reference,
            "solution": self.solution,
            "found": self.found,
        }


class SEOCrawler:
    def __init__(self, url):
        self.url = self._normalize_url(url)
        self.issues = []
        self.passes = []
        self.metrics = {}
        self.soup = None
        self.response = None
        self.html = ""
        self.text_content = ""
        self.parsed_url = urllib.parse.urlparse(self.url)
        self.base_domain = self.parsed_url.netloc
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; SEOAuditBot/1.0; +https://seocrawler.dev)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
        })

    def _normalize_url(self, url):
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    def _add_issue(self, category, check, severity, message, reference, solution, found=None):
        issue = SEOIssue(category, check, severity, message, reference, solution, found)
        if severity == SEVERITY["PASS"]:
            self.passes.append(issue.to_dict())
        else:
            self.issues.append(issue.to_dict())

    def fetch_page(self):
        try:
            start = time.time()
            resp = self.session.get(self.url, timeout=20, allow_redirects=True, verify=False)
            end = time.time()
            self.metrics["load_time_ms"] = round((end - start) * 1000, 2)
            self.metrics["status_code"] = resp.status_code
            self.metrics["final_url"] = resp.url
            self.metrics["redirect_count"] = len(resp.history)
            self.metrics["redirect_chain"] = [r.url for r in resp.history] + [resp.url]
            self.metrics["content_type"] = resp.headers.get("Content-Type", "")
            self.metrics["content_length"] = len(resp.content)
            self.metrics["server"] = resp.headers.get("Server", "Unknown")
            self.metrics["response_headers"] = dict(resp.headers)
            self.response = resp
            self.html = resp.text
            self.soup = BeautifulSoup(self.html, "lxml")
            return True
        except Exception as e:
            self.metrics["fetch_error"] = str(e)
            return False

    # ─── TECHNICAL CHECKS ─────────────────────

    def check_https(self):
        if self.parsed_url.scheme == "https":
            self._add_issue("Technical", "HTTPS", SEVERITY["PASS"], "Site uses HTTPS", "", "N/A")
        else:
            self._add_issue("Technical", "HTTPS", SEVERITY["CRITICAL"],
                "Site is NOT using HTTPS",
                "https://developers.google.com/search/docs/crawling-indexing/https",
                "Migrate to HTTPS. Get a free SSL certificate via Let's Encrypt. "
                "Set up 301 redirects from HTTP to HTTPS. Update all internal links and canonical tags.",
                {"current_scheme": self.parsed_url.scheme})

    def check_ssl_certificate(self):
        try:
            ctx = ssl.create_default_context()
            conn = ctx.wrap_socket(socket.socket(), server_hostname=self.base_domain)
            conn.settimeout(10)
            conn.connect((self.base_domain, 443))
            cert = conn.getpeercert()
            conn.close()
            expiry = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
            days_left = (expiry - datetime.utcnow()).days
            self.metrics["ssl_expiry_days"] = days_left
            self.metrics["ssl_expiry_date"] = expiry.strftime("%Y-%m-%d")
            if days_left < 14:
                self._add_issue("Technical", "SSL Certificate", SEVERITY["CRITICAL"],
                    f"SSL certificate expires in {days_left} days — URGENT",
                    "https://developers.google.com/search/docs/crawling-indexing/https",
                    "Renew SSL certificate immediately. Enable auto-renewal via Let's Encrypt/Certbot.",
                    {"expires": expiry.strftime("%Y-%m-%d"), "days_remaining": days_left})
            elif days_left < 30:
                self._add_issue("Technical", "SSL Certificate", SEVERITY["HIGH"],
                    f"SSL certificate expires in {days_left} days",
                    "https://developers.google.com/search/docs/crawling-indexing/https",
                    "Renew SSL certificate soon. Enable auto-renewal to prevent future expiry.",
                    {"expires": expiry.strftime("%Y-%m-%d"), "days_remaining": days_left})
            else:
                self._add_issue("Technical", "SSL Certificate", SEVERITY["PASS"],
                    f"SSL certificate valid for {days_left} more days", "", "N/A",
                    {"expires": expiry.strftime("%Y-%m-%d")})
        except Exception as e:
            if self.parsed_url.scheme == "https":
                self._add_issue("Technical", "SSL Certificate", SEVERITY["HIGH"],
                    f"Could not verify SSL certificate: {str(e)[:80]}",
                    "https://developers.google.com/search/docs/crawling-indexing/https",
                    "Verify SSL certificate is valid and properly installed. Test at: https://www.ssllabs.com/ssltest/",
                    {"error": str(e)[:100]})

    def check_redirects(self):
        count = self.metrics.get("redirect_count", 0)
        chain = self.metrics.get("redirect_chain", [])
        if count == 0:
            self._add_issue("Technical", "Redirects", SEVERITY["PASS"], "No redirects detected", "", "N/A")
        elif count <= SEO_STANDARDS["max_redirects"]:
            self._add_issue("Technical", "Redirects", SEVERITY["LOW"],
                f"{count} redirect(s) detected",
                "https://developers.google.com/search/docs/crawling-indexing/301-redirects",
                "Minimize redirect chains. Update internal links to point directly to final URLs.",
                {"count": count, "chain": chain})
        else:
            self._add_issue("Technical", "Redirects", SEVERITY["HIGH"],
                f"Excessive redirect chain: {count} redirects detected",
                "https://developers.google.com/search/docs/crawling-indexing/301-redirects",
                "Reduce to max 1-2 redirects. Each redirect adds ~100-300ms latency and dilutes link equity.",
                {"count": count, "chain": chain})

    def check_load_time(self):
        ms = self.metrics.get("load_time_ms", 0)
        if ms == 0:
            return
        if ms < 1000:
            self._add_issue("Technical", "Page Load Time", SEVERITY["PASS"],
                f"Excellent load time: {ms}ms", "", "N/A", {"ms": ms})
        elif ms < SEO_STANDARDS["max_load_time_ms"]:
            self._add_issue("Technical", "Page Load Time", SEVERITY["LOW"],
                f"Moderate load time: {ms}ms",
                "https://developers.google.com/speed/docs/insights/v5/about",
                "Optimize images, enable caching, use a CDN, minify CSS/JS. Target under 1000ms.",
                {"ms": ms})
        else:
            self._add_issue("Technical", "Page Load Time", SEVERITY["HIGH"],
                f"Slow load time: {ms}ms (threshold: {SEO_STANDARDS['max_load_time_ms']}ms)",
                "https://web.dev/performance/",
                "Compress images to WebP, enable GZIP/Brotli, leverage browser caching, use CDN, "
                "defer non-critical JS, minimize render-blocking resources.",
                {"ms": ms, "threshold": SEO_STANDARDS["max_load_time_ms"]})

    def check_status_code(self):
        code = self.metrics.get("status_code", 0)
        if code == 200:
            self._add_issue("Technical", "HTTP Status Code", SEVERITY["PASS"],
                "Page returns 200 OK", "", "N/A", {"code": code})
        elif code in (301, 302):
            self._add_issue("Technical", "HTTP Status Code", SEVERITY["MEDIUM"],
                f"Page returns {code} redirect — crawl equity may be diluted",
                "https://developers.google.com/search/docs/crawling-indexing/301-redirects",
                "Use 301 (permanent) redirect instead of 302 (temporary) for SEO-safe redirects.",
                {"code": code})
        elif code == 404:
            self._add_issue("Technical", "HTTP Status Code", SEVERITY["CRITICAL"],
                "Page returns 404 Not Found — cannot be indexed",
                "https://developers.google.com/search/docs/crawling-indexing/http-network-errors",
                "Fix the broken URL or implement a 301 redirect to the correct page.",
                {"code": code})
        elif code >= 500:
            self._add_issue("Technical", "HTTP Status Code", SEVERITY["CRITICAL"],
                f"Server error {code} — page cannot be crawled or indexed",
                "https://developers.google.com/search/docs/crawling-indexing/http-network-errors",
                "Investigate server logs immediately. Server errors prevent Googlebot from indexing the page.",
                {"code": code})
        else:
            self._add_issue("Technical", "HTTP Status Code", SEVERITY["MEDIUM"],
                f"Unexpected status code: {code}",
                "https://developers.google.com/search/docs/crawling-indexing/http-network-errors",
                "Ensure the page returns a proper 200 OK response.", {"code": code})

    def check_robots_txt(self):
        robots_url = f"{self.parsed_url.scheme}://{self.base_domain}/robots.txt"
        try:
            r = self.session.get(robots_url, timeout=10, verify=False)
            if r.status_code == 200:
                self.metrics["robots_txt"] = r.text[:500]
                path = self.parsed_url.path or "/"
                blocked = False
                for line in r.text.splitlines():
                    line = line.strip().lower()
                    if line.startswith("disallow:"):
                        rule = line.replace("disallow:", "").strip()
                        if rule and (rule == "/" or path.startswith(rule)):
                            blocked = True
                if blocked:
                    self._add_issue("Technical", "Robots.txt", SEVERITY["CRITICAL"],
                        "This URL is blocked by robots.txt — Googlebot cannot crawl it",
                        "https://developers.google.com/search/docs/crawling-indexing/robots/intro",
                        "Review your robots.txt Disallow rules. Use Google Search Console robots.txt tester. "
                        "Remove the blocking rule if this page should be indexed.",
                        {"robots_url": robots_url, "blocked_path": path})
                else:
                    self._add_issue("Technical", "Robots.txt", SEVERITY["PASS"],
                        "robots.txt found and page is not blocked", "", "N/A",
                        {"robots_url": robots_url})
            else:
                self._add_issue("Technical", "Robots.txt", SEVERITY["MEDIUM"],
                    f"robots.txt not found (HTTP {r.status_code})",
                    "https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt",
                    "Create a robots.txt at your domain root. Include a Sitemap: directive.",
                    {"robots_url": robots_url})
        except Exception as e:
            self._add_issue("Technical", "Robots.txt", SEVERITY["MEDIUM"],
                f"Could not fetch robots.txt: {str(e)[:60]}",
                "https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt",
                "Ensure robots.txt is accessible at your domain root.",
                {"robots_url": robots_url})

    def check_sitemap(self):
        sitemap_urls = [
            f"{self.parsed_url.scheme}://{self.base_domain}/sitemap.xml",
            f"{self.parsed_url.scheme}://{self.base_domain}/sitemap_index.xml",
        ]
        found = False
        for surl in sitemap_urls:
            try:
                r = self.session.get(surl, timeout=10, verify=False)
                if r.status_code == 200 and ("<urlset" in r.text or "<sitemapindex" in r.text):
                    self.metrics["sitemap_url"] = surl
                    found = True
                    break
            except Exception:
                pass
        if found:
            self._add_issue("Technical", "XML Sitemap", SEVERITY["PASS"],
                f"Sitemap found at {self.metrics['sitemap_url']}", "", "N/A")
        else:
            self._add_issue("Technical", "XML Sitemap", SEVERITY["HIGH"],
                "No XML sitemap found at standard locations",
                "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview",
                "Create an XML sitemap and submit it via Google Search Console. "
                "Add 'Sitemap:' directive in robots.txt.",
                {"checked_urls": sitemap_urls})

    def check_response_headers(self):
        headers = self.metrics.get("response_headers", {})

        x_robots = headers.get("X-Robots-Tag", "").lower()
        if "noindex" in x_robots:
            self._add_issue("Technical", "X-Robots-Tag Header", SEVERITY["CRITICAL"],
                "X-Robots-Tag header contains 'noindex' — page is blocked from indexing",
                "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                "Remove 'noindex' from X-Robots-Tag header if this page should be indexed.",
                {"header_value": x_robots})

        ct = headers.get("Content-Type", "")
        if "text/html" not in ct:
            self._add_issue("Technical", "Content-Type Header", SEVERITY["MEDIUM"],
                f"Unexpected Content-Type: {ct}",
                "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type",
                "Serve HTML pages with 'text/html; charset=utf-8'",
                {"content_type": ct})

        if "utf-8" not in ct.lower() and "utf8" not in ct.lower():
            self._add_issue("Technical", "Charset Encoding", SEVERITY["MEDIUM"],
                "UTF-8 charset not declared in Content-Type header",
                "https://developers.google.com/search/docs/appearance/site-structure",
                "Set Content-Type: text/html; charset=utf-8 in server response headers.",
                {"content_type": ct})
        else:
            self._add_issue("Technical", "Charset Encoding", SEVERITY["PASS"],
                "UTF-8 charset declared correctly", "", "N/A")

        cache = headers.get("Cache-Control", "")
        if not cache:
            self._add_issue("Technical", "Cache-Control Header", SEVERITY["LOW"],
                "No Cache-Control header set",
                "https://web.dev/http-cache/",
                "Add Cache-Control headers. Use 'public, max-age=31536000' for static assets, "
                "'no-cache' for HTML pages.")
        else:
            self._add_issue("Technical", "Cache-Control Header", SEVERITY["PASS"],
                f"Cache-Control set: {cache}", "", "N/A")

        ce = headers.get("Content-Encoding", "")
        if ce in ("gzip", "br", "deflate"):
            self._add_issue("Technical", "Compression (GZIP/Brotli)", SEVERITY["PASS"],
                f"Response is compressed: {ce}", "", "N/A")
        else:
            self._add_issue("Technical", "Compression (GZIP/Brotli)", SEVERITY["MEDIUM"],
                "Response is NOT compressed",
                "https://web.dev/uses-text-compression/",
                "Enable GZIP or Brotli on your server. Reduces page size by 60-80%.",
                {"content_encoding": ce or "none"})

    def check_page_speed_indicators(self):
        head = self.soup.find("head")
        if not head:
            return
        css_links = self.soup.find_all("link", rel="stylesheet")
        head_scripts = head.find_all("script", src=True)
        blocking = [s for s in head_scripts
                    if not s.get("async") and not s.get("defer")
                    and s.get("type") != "module"]
        self.metrics["css_files"] = len(css_links)
        self.metrics["render_blocking_scripts"] = len(blocking)

        if blocking:
            self._add_issue("Technical", "Render-Blocking Scripts", SEVERITY["MEDIUM"],
                f"{len(blocking)} render-blocking <script> tag(s) in <head>",
                "https://web.dev/render-blocking-resources/",
                "Add 'defer' or 'async' to scripts in <head>. Example: <script src='app.js' defer>",
                {"count": len(blocking),
                 "examples": [s.get("src", "")[:60] for s in blocking[:3]]})
        else:
            self._add_issue("Technical", "Render-Blocking Scripts", SEVERITY["PASS"],
                "No render-blocking scripts in <head>", "", "N/A")

    # ─── ON-PAGE CHECKS ────────────────────────

    def check_title_tag(self):
        title_tag = self.soup.find("title")
        if not title_tag:
            self._add_issue("On-Page", "Title Tag", SEVERITY["CRITICAL"],
                "No <title> tag found on this page",
                "https://developers.google.com/search/docs/appearance/title-link",
                "Add a unique <title> tag (30-60 chars) inside <head> with your primary keyword first.")
            return
        title = title_tag.get_text(strip=True)
        length = len(title)
        self.metrics["title"] = title
        self.metrics["title_length"] = length

        if length == 0:
            self._add_issue("On-Page", "Title Tag", SEVERITY["CRITICAL"],
                "Title tag exists but is empty",
                "https://developers.google.com/search/docs/appearance/title-link",
                "Write a descriptive title 30-60 characters long with your primary keyword.",
                {"length": 0})
        elif length < SEO_STANDARDS["title_min"]:
            self._add_issue("On-Page", "Title Tag", SEVERITY["HIGH"],
                f"Title too short: {length} chars (minimum {SEO_STANDARDS['title_min']})",
                "https://developers.google.com/search/docs/appearance/title-link",
                f"Expand title to 30-60 characters. Include primary keyword + brand name. Found: '{title}'",
                {"title": title, "length": length})
        elif length > SEO_STANDARDS["title_max"]:
            self._add_issue("On-Page", "Title Tag", SEVERITY["HIGH"],
                f"Title too long: {length} chars (max {SEO_STANDARDS['title_max']}) — truncated in SERPs",
                "https://developers.google.com/search/docs/appearance/title-link",
                f"Shorten title to under 60 characters. Google truncates at ~600px width. Found: '{title}'",
                {"title": title, "length": length})
        else:
            self._add_issue("On-Page", "Title Tag", SEVERITY["PASS"],
                f"Title tag optimal: {length} chars", "", "N/A",
                {"title": title, "length": length})

    def check_meta_description(self):
        meta = self.soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
        if not meta:
            self._add_issue("On-Page", "Meta Description", SEVERITY["HIGH"],
                "No meta description tag found",
                "https://developers.google.com/search/docs/appearance/snippet",
                "Add <meta name='description' content='...'> with 120-160 chars. "
                "Include primary keyword and a clear CTA to improve CTR.")
            return
        desc = meta.get("content", "").strip()
        length = len(desc)
        self.metrics["meta_description"] = desc
        self.metrics["meta_description_length"] = length

        if length == 0:
            self._add_issue("On-Page", "Meta Description", SEVERITY["HIGH"],
                "Meta description tag is empty",
                "https://developers.google.com/search/docs/appearance/snippet",
                "Write a 120-160 character description with your primary keyword and a call-to-action.")
        elif length < SEO_STANDARDS["meta_desc_min"]:
            self._add_issue("On-Page", "Meta Description", SEVERITY["MEDIUM"],
                f"Meta description too short: {length} chars (min {SEO_STANDARDS['meta_desc_min']})",
                "https://developers.google.com/search/docs/appearance/snippet",
                "Expand description to 120-160 chars. Include keyword and CTA.",
                {"description": desc, "length": length})
        elif length > SEO_STANDARDS["meta_desc_max"]:
            self._add_issue("On-Page", "Meta Description", SEVERITY["MEDIUM"],
                f"Meta description too long: {length} chars (max {SEO_STANDARDS['meta_desc_max']}) — truncated",
                "https://developers.google.com/search/docs/appearance/snippet",
                "Shorten description to under 160 characters.",
                {"description": desc, "length": length})
        else:
            self._add_issue("On-Page", "Meta Description", SEVERITY["PASS"],
                f"Meta description optimal: {length} chars", "", "N/A",
                {"description": desc, "length": length})

    def check_headings(self):
        h1s = self.soup.find_all("h1")
        h2s = self.soup.find_all("h2")
        h3s = self.soup.find_all("h3")
        h4s = self.soup.find_all("h4")
        h1_texts = [h.get_text(strip=True) for h in h1s]
        self.metrics["h1_count"] = len(h1s)
        self.metrics["h1_texts"] = h1_texts
        self.metrics["h2_count"] = len(h2s)
        self.metrics["h3_count"] = len(h3s)

        if len(h1s) == 0:
            self._add_issue("On-Page", "H1 Tag", SEVERITY["CRITICAL"],
                "No H1 tag found on this page",
                "https://developers.google.com/search/docs/appearance/title-link",
                "Add exactly one <h1> with your primary keyword. It describes the main topic of the page.")
        elif len(h1s) > 1:
            self._add_issue("On-Page", "H1 Tag", SEVERITY["HIGH"],
                f"Multiple H1 tags found: {len(h1s)}",
                "https://developers.google.com/search/docs/appearance/title-link",
                "Keep exactly one H1. Use H2-H6 for all subheadings.",
                {"count": len(h1s), "h1_texts": h1_texts})
        else:
            h1_text = h1_texts[0] if h1_texts else ""
            if len(h1_text) < 5:
                self._add_issue("On-Page", "H1 Tag", SEVERITY["HIGH"],
                    f"H1 tag is too short: '{h1_text}'",
                    "https://developers.google.com/search/docs/appearance/title-link",
                    "H1 should clearly describe the page topic and include the primary keyword.",
                    {"h1": h1_text})
            else:
                self._add_issue("On-Page", "H1 Tag", SEVERITY["PASS"],
                    f"Single H1 found: '{h1_text[:60]}'", "", "N/A")

        if len(h2s) == 0 and len(h3s) > 0:
            self._add_issue("On-Page", "Heading Hierarchy", SEVERITY["MEDIUM"],
                "H3 tags used without any H2 — heading hierarchy is broken",
                "https://web.dev/use-landmarks/",
                "Use headings in order: H1 -> H2 -> H3. Never skip levels.",
                {"h2_count": 0, "h3_count": len(h3s)})
        elif len(h2s) > 0:
            self._add_issue("On-Page", "Heading Hierarchy", SEVERITY["PASS"],
                f"Heading structure: {len(h2s)} H2s, {len(h3s)} H3s, {len(h4s)} H4s", "", "N/A")

    def check_canonical(self):
        canonical = self.soup.find("link", rel="canonical")
        if not canonical:
            self._add_issue("On-Page", "Canonical Tag", SEVERITY["HIGH"],
                "No canonical tag found",
                "https://developers.google.com/search/docs/crawling-indexing/canonicalization",
                "Add <link rel='canonical' href='https://yourdomain.com/page/'> in <head>. "
                "Prevents duplicate content and consolidates link equity.")
            return
        href = canonical.get("href", "").strip()
        self.metrics["canonical_url"] = href
        if not href:
            self._add_issue("On-Page", "Canonical Tag", SEVERITY["HIGH"],
                "Canonical tag found but href is empty",
                "https://developers.google.com/search/docs/crawling-indexing/canonicalization",
                "Set canonical href to the full absolute URL of this page.",
                {"canonical_href": ""})
        elif href != self.metrics.get("final_url", self.url):
            self._add_issue("On-Page", "Canonical Tag", SEVERITY["MEDIUM"],
                "Canonical points to a different URL than the current page",
                "https://developers.google.com/search/docs/crawling-indexing/canonicalization",
                "Verify this is intentional. If this is the main URL, canonical should match.",
                {"canonical_url": href, "current_url": self.metrics.get("final_url")})
        else:
            self._add_issue("On-Page", "Canonical Tag", SEVERITY["PASS"],
                "Canonical correctly set to current URL", "", "N/A", {"canonical_url": href})

    def check_meta_robots(self):
        robots = self.soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
        if not robots:
            self._add_issue("On-Page", "Meta Robots", SEVERITY["LOW"],
                "No meta robots tag (defaults to index, follow)",
                "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                "Add <meta name='robots' content='index, follow'> explicitly for clarity.")
            return
        content = robots.get("content", "").lower()
        self.metrics["meta_robots"] = content
        if "noindex" in content:
            self._add_issue("On-Page", "Meta Robots", SEVERITY["CRITICAL"],
                f"Page has 'noindex' — will NOT appear in Google search results",
                "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                "Remove 'noindex' from meta robots if this page should be indexed.",
                {"content": content})
        elif "nofollow" in content:
            self._add_issue("On-Page", "Meta Robots", SEVERITY["MEDIUM"],
                "Page has 'nofollow' — links won't pass PageRank",
                "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                "Remove 'nofollow' if you want link equity to flow from this page.",
                {"content": content})
        else:
            self._add_issue("On-Page", "Meta Robots", SEVERITY["PASS"],
                f"Meta robots: '{content}' — indexing allowed", "", "N/A")

    def check_noindex_nofollow(self):
        all_robots = self.soup.find_all("meta", attrs={"name": re.compile("^robots$", re.I)})
        for r in all_robots:
            content = r.get("content", "").lower()
            if "none" in content:
                self._add_issue("On-Page", "Robots Meta: 'none'", SEVERITY["CRITICAL"],
                    "Meta robots='none' blocks BOTH indexing AND link following",
                    "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                    "Replace 'none' with 'index, follow' unless intentionally blocking this page.",
                    {"content": content})

    def check_duplicate_meta(self):
        titles = self.soup.find_all("title")
        descs = self.soup.find_all("meta", attrs={"name": re.compile("^description$", re.I)})
        if len(titles) > 1:
            self._add_issue("On-Page", "Duplicate Title Tags", SEVERITY["HIGH"],
                f"Multiple <title> tags found: {len(titles)}",
                "https://developers.google.com/search/docs/appearance/title-link",
                "Remove all duplicate title tags. Only one should exist in <head>.",
                {"count": len(titles)})
        if len(descs) > 1:
            self._add_issue("On-Page", "Duplicate Meta Description", SEVERITY["HIGH"],
                f"Multiple meta description tags found: {len(descs)}",
                "https://developers.google.com/search/docs/appearance/snippet",
                "Remove all duplicate meta description tags. Only one per page.",
                {"count": len(descs)})

    def check_open_graph(self):
        og_title = self.soup.find("meta", property="og:title")
        og_desc = self.soup.find("meta", property="og:description")
        og_image = self.soup.find("meta", property="og:image")
        og_url = self.soup.find("meta", property="og:url")
        og_type = self.soup.find("meta", property="og:type")

        missing = []
        if not og_title: missing.append("og:title")
        if not og_desc: missing.append("og:description")
        if not og_image: missing.append("og:image")
        if not og_url: missing.append("og:url")
        if not og_type: missing.append("og:type")

        self.metrics["og_tags"] = {
            "og:title": og_title.get("content", "") if og_title else None,
            "og:description": og_desc.get("content", "") if og_desc else None,
            "og:image": og_image.get("content", "") if og_image else None,
            "og:url": og_url.get("content", "") if og_url else None,
            "og:type": og_type.get("content", "") if og_type else None,
        }

        if missing:
            self._add_issue("On-Page", "Open Graph Tags", SEVERITY["MEDIUM"],
                f"Missing Open Graph tags: {', '.join(missing)}",
                "https://ogp.me/",
                f"Add missing OG tags in <head>. Controls how page appears when shared on "
                f"Facebook, LinkedIn, etc. Missing: {', '.join(missing)}",
                {"missing": missing})
        else:
            self._add_issue("On-Page", "Open Graph Tags", SEVERITY["PASS"],
                "All essential Open Graph tags present", "", "N/A")

    def check_twitter_cards(self):
        tc = self.soup.find("meta", attrs={"name": re.compile("^twitter:card$", re.I)})
        if not tc:
            self._add_issue("On-Page", "Twitter Card Tags", SEVERITY["LOW"],
                "No Twitter Card meta tags found",
                "https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards",
                "Add <meta name='twitter:card' content='summary_large_image'>. "
                "Controls appearance on Twitter/X.")
        else:
            self._add_issue("On-Page", "Twitter Card Tags", SEVERITY["PASS"],
                f"Twitter card found: {tc.get('content', '')}", "", "N/A")

    def check_images(self):
        images = self.soup.find_all("img")
        missing_alt = []
        empty_alt = []
        missing_dimensions = []
        total = len(images)

        for img in images:
            src = img.get("src", "") or img.get("data-src", "")
            alt = img.get("alt")
            if alt is None:
                missing_alt.append(src[:80] if src else "[no src]")
            elif alt.strip() == "":
                empty_alt.append(src[:80] if src else "[no src]")
            if not img.get("width") or not img.get("height"):
                missing_dimensions.append(src[:80] if src else "[no src]")

        self.metrics["image_count"] = total
        self.metrics["images_missing_alt"] = len(missing_alt)
        self.metrics["images_empty_alt"] = len(empty_alt)

        if total == 0:
            self._add_issue("On-Page", "Images", SEVERITY["LOW"],
                "No images found on this page",
                "https://developers.google.com/search/docs/appearance/google-images",
                "Add relevant images with descriptive alt text to improve engagement and image search visibility.")
            return

        if missing_alt:
            self._add_issue("On-Page", "Image Alt Text (Missing)", SEVERITY["HIGH"],
                f"{len(missing_alt)} image(s) are missing alt attribute entirely",
                "https://developers.google.com/search/docs/appearance/google-images#use-descriptive-alt-text",
                "Add descriptive alt text to all images. Required for accessibility (WCAG 2.1) and image SEO.",
                {"count": len(missing_alt), "examples": missing_alt[:5]})

        if empty_alt:
            self._add_issue("On-Page", "Image Alt Text (Empty)", SEVERITY["MEDIUM"],
                f"{len(empty_alt)} image(s) have empty alt='' attributes",
                "https://developers.google.com/search/docs/appearance/google-images#use-descriptive-alt-text",
                "Use empty alt only for decorative images. Write descriptive alt for content images.",
                {"count": len(empty_alt), "examples": empty_alt[:5]})

        if missing_dimensions:
            self._add_issue("On-Page", "Image Dimensions", SEVERITY["LOW"],
                f"{len(missing_dimensions)} image(s) missing width/height attributes",
                "https://web.dev/optimize-cls/",
                "Add width and height to all images to prevent Cumulative Layout Shift (CLS).",
                {"count": len(missing_dimensions)})

        if not missing_alt and not empty_alt:
            self._add_issue("On-Page", "Image Alt Text", SEVERITY["PASS"],
                f"All {total} images have alt attributes", "", "N/A")

    def check_links(self):
        links = self.soup.find_all("a", href=True)
        internal = []
        external = []
        nofollow_external = []
        empty_anchor_text = []

        for link in links:
            href = link.get("href", "").strip()
            text = link.get_text(strip=True)
            rel = link.get("rel", [])
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            if href.startswith("/") or self.base_domain in href:
                internal.append({"href": href, "text": text[:60]})
            elif href.startswith("http"):
                external.append({"href": href, "text": text[:60], "rel": rel})
                if "nofollow" in rel:
                    nofollow_external.append(href)
            if not text and not link.find("img"):
                empty_anchor_text.append(href[:60])

        self.metrics["internal_links"] = len(internal)
        self.metrics["external_links"] = len(external)
        self.metrics["total_links"] = len(links)

        if len(internal) == 0:
            self._add_issue("On-Page", "Internal Links", SEVERITY["HIGH"],
                "No internal links found on this page",
                "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
                "Add internal links to related pages to distribute PageRank and help Googlebot discover content.")
        elif len(internal) < 3:
            self._add_issue("On-Page", "Internal Links", SEVERITY["MEDIUM"],
                f"Very few internal links: {len(internal)}",
                "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
                "Add more internal links to improve crawlability and spread link equity.",
                {"count": len(internal)})
        else:
            self._add_issue("On-Page", "Internal Links", SEVERITY["PASS"],
                f"{len(internal)} internal links found", "", "N/A")

        if empty_anchor_text:
            self._add_issue("On-Page", "Anchor Text", SEVERITY["MEDIUM"],
                f"{len(empty_anchor_text)} link(s) have empty anchor text",
                "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
                "Add descriptive anchor text to all links. Empty anchors miss keyword relevance signals.",
                {"examples": empty_anchor_text[:5]})

        do_follow_ext = len(external) - len(nofollow_external)
        if do_follow_ext > 10:
            self._add_issue("On-Page", "External Dofollow Links", SEVERITY["LOW"],
                f"{do_follow_ext} dofollow external links — review for link equity leakage",
                "https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links",
                "Add rel='nofollow' or rel='sponsored' to untrusted or commercial external links.",
                {"dofollow": do_follow_ext, "nofollow": len(nofollow_external)})

    def check_url_structure(self):
        url = self.url
        path = self.parsed_url.path
        length = len(url)
        self.metrics["url_length"] = length

        issues = []
        if length > SEO_STANDARDS["max_url_length"]:
            issues.append(f"URL too long: {length} chars (max {SEO_STANDARDS['max_url_length']})")
        if "_" in path:
            issues.append("URL uses underscores — use hyphens instead")
        if path != path.lower():
            issues.append("URL has uppercase letters — use lowercase only")
        if re.search(r"\?(.*&.*|.*=.*)", url) and len(re.findall(r"&", url)) > 2:
            issues.append("URL has complex query parameters")
        if re.search(r"\d{4,}", path):
            if not re.search(r"(blog|post|article|news)", path, re.I):
                issues.append("Long numeric ID in URL — use descriptive slugs instead")

        if issues:
            self._add_issue("On-Page", "URL Structure", SEVERITY["MEDIUM"],
                f"URL structure issues: {'; '.join(issues)}",
                "https://developers.google.com/search/docs/crawling-indexing/url-structure",
                "Use lowercase, hyphens, short descriptive slugs, max 3 folder levels. "
                "Keep URLs clean and readable.",
                {"url": url, "issues": issues})
        else:
            self._add_issue("On-Page", "URL Structure", SEVERITY["PASS"],
                "URL structure follows SEO best practices", "", "N/A", {"url": url})

    def check_content(self):
        soup_copy = BeautifulSoup(self.html, "lxml")
        for tag in soup_copy(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = soup_copy.get_text(separator=" ")
        words = [w for w in text.split() if w.strip() and len(w) > 1]
        word_count = len(words)
        self.metrics["word_count"] = word_count
        self.text_content = " ".join(words)

        if word_count < SEO_STANDARDS["content_min_words"]:
            self._add_issue("On-Page", "Content Length", SEVERITY["HIGH"],
                f"Thin content: {word_count} words (minimum {SEO_STANDARDS['content_min_words']})",
                "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
                f"Expand content to at least {SEO_STANDARDS['content_min_words']} words. "
                "Add FAQs, examples, data, and expert insights to satisfy Google's Helpful Content guidelines.",
                {"word_count": word_count})
        elif word_count < 600:
            self._add_issue("On-Page", "Content Length", SEVERITY["MEDIUM"],
                f"Content could be deeper: {word_count} words",
                "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
                "For competitive topics, aim for 1000-2000+ words. Analyze top competitors for depth benchmarks.",
                {"word_count": word_count})
        else:
            self._add_issue("On-Page", "Content Length", SEVERITY["PASS"],
                f"Good content length: {word_count} words", "", "N/A")

    def check_structured_data(self):
        ld_json = self.soup.find_all("script", type="application/ld+json")
        microdata = self.soup.find_all(attrs={"itemtype": True})
        schema_types = []

        for script in ld_json:
            try:
                data = json.loads(script.string or "{}")
                stype = data.get("@type", "Unknown")
                schema_types.extend(stype if isinstance(stype, list) else [stype])
            except Exception:
                self._add_issue("On-Page", "Structured Data (JSON-LD)", SEVERITY["HIGH"],
                    "Invalid JSON in ld+json script — Google cannot parse this structured data",
                    "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data",
                    "Fix JSON syntax errors. Validate at: https://search.google.com/test/rich-results")

        self.metrics["schema_types"] = schema_types

        if not ld_json and not microdata:
            self._add_issue("On-Page", "Structured Data", SEVERITY["MEDIUM"],
                "No structured data (Schema.org) found",
                "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data",
                "Add JSON-LD structured data: Article, Product, FAQ, BreadcrumbList, LocalBusiness, etc. "
                "Enables rich results in SERPs and improves CTR.")
        else:
            self._add_issue("On-Page", "Structured Data", SEVERITY["PASS"],
                f"Structured data found: {', '.join(schema_types) or 'Microdata'}", "", "N/A",
                {"schema_types": schema_types})

    def check_viewport(self):
        viewport = self.soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
        if not viewport:
            self._add_issue("On-Page", "Viewport Meta Tag", SEVERITY["HIGH"],
                "No viewport meta tag — mobile experience will be broken",
                "https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing",
                "Add <meta name='viewport' content='width=device-width, initial-scale=1'> in <head>. "
                "Critical for Google's mobile-first indexing.")
        else:
            content = viewport.get("content", "")
            self.metrics["viewport"] = content
            self._add_issue("On-Page", "Viewport Meta Tag", SEVERITY["PASS"],
                f"Viewport tag present: {content}", "", "N/A")

    def check_lang_attribute(self):
        html_tag = self.soup.find("html")
        if not html_tag:
            return
        lang = html_tag.get("lang", "")
        self.metrics["html_lang"] = lang
        if not lang:
            self._add_issue("On-Page", "HTML Lang Attribute", SEVERITY["MEDIUM"],
                "No lang attribute on <html> tag",
                "https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites",
                "Add lang='en' (or your language code) to <html>. Required for accessibility and international SEO.")
        else:
            self._add_issue("On-Page", "HTML Lang Attribute", SEVERITY["PASS"],
                f"HTML lang='{lang}' set correctly", "", "N/A")

    def check_hreflang(self):
        hreflang = self.soup.find_all("link", rel="alternate", hreflang=True)
        if hreflang:
            langs = [l.get("hreflang") for l in hreflang]
            self.metrics["hreflang_tags"] = langs
            if "x-default" not in langs:
                self._add_issue("On-Page", "Hreflang x-default", SEVERITY["LOW"],
                    "Hreflang tags present but missing x-default",
                    "https://developers.google.com/search/docs/specialty/international/localization",
                    "Add <link rel='alternate' hreflang='x-default' href='...'> for the default language fallback.",
                    {"langs": langs})
            else:
                self._add_issue("On-Page", "Hreflang Tags", SEVERITY["PASS"],
                    f"Hreflang tags found: {', '.join(langs[:5])}", "", "N/A")

    def check_favicon(self):
        favicon = (self.soup.find("link", rel=lambda r: r and "icon" in r) or
                   self.soup.find("link", attrs={"rel": "shortcut icon"}))
        if not favicon:
            self._add_issue("On-Page", "Favicon", SEVERITY["LOW"],
                "No favicon link tag found in HTML",
                "https://developers.google.com/search/docs/appearance/favicon-in-search",
                "Add <link rel='icon' href='/favicon.ico'>. Appears in browser tabs and Google search results.")
        else:
            self._add_issue("On-Page", "Favicon", SEVERITY["PASS"],
                "Favicon link tag found", "", "N/A")

    def check_inline_styles_scripts(self):
        inline_scripts = [s for s in self.soup.find_all("script", src=False)
                          if s.get_text(strip=True) and s.get("type") != "application/ld+json"]
        inline_style_attrs = self.soup.find_all(style=True)

        if len(inline_scripts) > 5:
            self._add_issue("On-Page", "Inline Scripts", SEVERITY["LOW"],
                f"{len(inline_scripts)} inline <script> blocks found",
                "https://web.dev/render-blocking-resources/",
                "Move inline scripts to external .js files for better caching and CSP compatibility.",
                {"count": len(inline_scripts)})

        if len(inline_style_attrs) > 10:
            self._add_issue("On-Page", "Inline Styles", SEVERITY["LOW"],
                f"{len(inline_style_attrs)} elements with inline style attributes",
                "https://web.dev/extract-critical-css/",
                "Move inline styles to external CSS classes for better caching and maintainability.",
                {"count": len(inline_style_attrs)})

    def check_word_to_code_ratio(self):
        html_size = len(self.html)
        text_size = len(self.text_content)
        if html_size > 0:
            ratio = round((text_size / html_size) * 100, 1)
            self.metrics["text_to_html_ratio"] = ratio
            if ratio < 10:
                self._add_issue("On-Page", "Text-to-HTML Ratio", SEVERITY["MEDIUM"],
                    f"Low text-to-HTML ratio: {ratio}% — page is code-heavy",
                    "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
                    "Clean up bloated HTML. Remove excessive comments, whitespace, dead code. "
                    "More text vs code signals a content-rich page.",
                    {"ratio": ratio, "html_size_kb": round(html_size / 1024, 1)})
            else:
                self._add_issue("On-Page", "Text-to-HTML Ratio", SEVERITY["PASS"],
                    f"Text-to-HTML ratio: {ratio}%", "", "N/A", {"ratio": ratio})

    # ─── MASTER RUN ────────────────────────────

    def run(self):
        start = time.time()
        ok = self.fetch_page()
        if not ok:
            return {
                "url": self.url,
                "error": self.metrics.get("fetch_error", "Failed to fetch page"),
                "metrics": self.metrics,
                "issues": [],
                "passes": [],
                "summary": {},
            }

        # Technical
        self.check_https()
        self.check_ssl_certificate()
        self.check_redirects()
        self.check_load_time()
        self.check_status_code()
        self.check_robots_txt()
        self.check_sitemap()
        self.check_response_headers()
        self.check_page_speed_indicators()

        # On-Page
        self.check_title_tag()
        self.check_meta_description()
        self.check_headings()
        self.check_canonical()
        self.check_meta_robots()
        self.check_noindex_nofollow()
        self.check_duplicate_meta()
        self.check_open_graph()
        self.check_twitter_cards()
        self.check_images()
        self.check_links()
        self.check_url_structure()
        self.check_content()
        self.check_structured_data()
        self.check_viewport()
        self.check_lang_attribute()
        self.check_hreflang()
        self.check_favicon()
        self.check_inline_styles_scripts()
        self.check_word_to_code_ratio()

        duration = round(time.time() - start, 2)
        sev = defaultdict(int)
        for issue in self.issues:
            sev[issue["severity"]] += 1

        score = max(0, 100
                    - sev.get("critical", 0) * 15
                    - sev.get("high", 0) * 8
                    - sev.get("medium", 0) * 4
                    - sev.get("low", 0) * 1)

        return {
            "url": self.url,
            "audit_time": datetime.utcnow().isoformat(),
            "audit_duration_s": duration,
            "metrics": self.metrics,
            "issues": self.issues,
            "passes": self.passes,
            "summary": {
                "seo_score": score,
                "total_checks": len(self.issues) + len(self.passes),
                "issues_found": len(self.issues),
                "passes": len(self.passes),
                "critical": sev.get("critical", 0),
                "high": sev.get("high", 0),
                "medium": sev.get("medium", 0),
                "low": sev.get("low", 0),
            }
        }


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    result = SEOCrawler(url).run()
    print(json.dumps(result, indent=2))
