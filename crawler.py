"""
Expert SEO Audit Crawler v3.0 — by Zaman Hassan
Covers every technical + on-page SEO standard with keyword analysis
"""

import re
import ssl
import json
import time
import socket
import hashlib
import urllib3
import urllib.parse
from datetime import datetime
from collections import defaultdict, Counter

import requests
from bs4 import BeautifulSoup, Comment

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SEO_STANDARDS = {
    "title_min": 30, "title_max": 60,
    "meta_desc_min": 120, "meta_desc_max": 160,
    "content_min_words": 300,
    "max_load_time_ms": 3000,
    "max_url_length": 100,
    "max_redirects": 2,
    "max_page_size_kb": 3000,
    "ideal_keyword_density_min": 0.5,
    "ideal_keyword_density_max": 2.5,
}

STOP_WORDS = set("""a about above after again against all am an and any are aren't as at be because
been before being below between both but by can't cannot could couldn't did didn't do does doesn't
doing don't down during each few for from further get got had hadn't has hasn't have haven't having
he he'd he'll he's her here here's hers herself him himself his how how's i i'd i'll i'm i've if in
into is isn't it it's its itself let's me more most mustn't my myself no nor not of off on once only
or other ought our ours ourselves out over own same shan't she she'd she'll she's should shouldn't
so some such than that that's the their theirs them themselves then there there's these they they'd
they'll they're they've this those through to too under until up very was wasn't we we'd we'll we're
we've were weren't what what's when when's where where's which while who who's whom why why's will
with won't would wouldn't you you'd you'll you're you've your yours yourself yourselves
also just like make made use used using one two three get got want need know go
""".split())

SEVERITY = {
    "CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium",
    "LOW": "low", "INFO": "info", "PASS": "pass",
}


class SEOIssue:
    def __init__(self, category, check, severity, message, reference, solution, found=None, impact=""):
        self.category = category
        self.check = check
        self.severity = severity
        self.message = message
        self.reference = reference
        self.solution = solution
        self.found = found
        self.impact = impact

    def to_dict(self):
        return {
            "category": self.category,
            "check": self.check,
            "severity": self.severity,
            "message": self.message,
            "reference": self.reference,
            "solution": self.solution,
            "found": self.found,
            "impact": self.impact,
        }


def extract_keywords(text, top_n=20):
    words = re.findall(r'\b[a-zA-Z][a-zA-Z\-]{2,}\b', text.lower())
    words = [w for w in words if w not in STOP_WORDS and len(w) > 3]
    freq = Counter(words)
    total = len(words) or 1
    scored = {w: (c / total * 100, c) for w, c in freq.items() if c >= 2}
    bigrams = []
    for i in range(len(words) - 1):
        bg = f"{words[i]} {words[i+1]}"
        bigrams.append(bg)
    bigram_freq = Counter(bigrams)
    trigrams = []
    for i in range(len(words) - 2):
        tg = f"{words[i]} {words[i+1]} {words[i+2]}"
        trigrams.append(tg)
    trigram_freq = Counter(trigrams)
    primary_keywords = sorted(scored.items(), key=lambda x: -x[1][0])[:top_n]
    top_bigrams = [(bg, cnt) for bg, cnt in bigram_freq.most_common(15) if cnt >= 2
                   and not all(w in STOP_WORDS for w in bg.split())]
    top_trigrams = [(tg, cnt) for tg, cnt in trigram_freq.most_common(10) if cnt >= 2]
    return {
        "primary_keywords": [{"keyword": k, "density": round(v[0], 2), "count": v[1]}
                              for k, v in primary_keywords[:10]],
        "bigrams": [{"phrase": bg, "count": cnt} for bg, cnt in top_bigrams[:8]],
        "trigrams": [{"phrase": tg, "count": cnt} for tg, cnt in top_trigrams[:5]],
        "total_words": total,
    }


def generate_keyword_ideas(primary_kws, title, meta_desc):
    ideas = []
    found = [k["keyword"] for k in primary_kws[:4]]
    for kw in found[:3]:
        ideas.extend([
            f"best {kw}", f"{kw} guide", f"how to use {kw}",
            f"{kw} tips", f"{kw} for beginners", f"{kw} tutorial",
            f"top {kw} tools", f"{kw} examples", f"{kw} 2025",
            f"what is {kw}", f"{kw} strategy", f"free {kw}",
        ])
    seen = set()
    clean = []
    for idea in ideas:
        if idea not in seen and not all(w in STOP_WORDS for w in idea.split()):
            seen.add(idea)
            clean.append(idea)
    return clean[:20]


class SEOCrawler:
    def __init__(self, url, mode="single"):
        self.url = self._normalize_url(url)
        self.mode = mode
        self.issues = []
        self.passes = []
        self.metrics = {}
        self.soup = None
        self.response = None
        self.html = ""
        self.text_content = ""
        self.parsed_url = urllib.parse.urlparse(self.url)
        self.base_domain = self.parsed_url.netloc
        self.scheme = self.parsed_url.scheme
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
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

    def _add(self, category, check, severity, message, reference, solution, found=None, impact=""):
        issue = SEOIssue(category, check, severity, message, reference, solution, found, impact)
        if severity == SEVERITY["PASS"]:
            self.passes.append(issue.to_dict())
        else:
            self.issues.append(issue.to_dict())

    def fetch_page(self):
        try:
            start = time.time()
            resp = self.session.get(self.url, timeout=25, allow_redirects=True, verify=False)
            ttfb = round((time.time() - start) * 1000, 2)
            self.metrics.update({
                "load_time_ms": ttfb,
                "status_code": resp.status_code,
                "final_url": resp.url,
                "redirect_count": len(resp.history),
                "redirect_chain": [r.url for r in resp.history] + [resp.url],
                "content_type": resp.headers.get("Content-Type", ""),
                "content_length_bytes": len(resp.content),
                "content_length_kb": round(len(resp.content) / 1024, 1),
                "server": resp.headers.get("Server", "Unknown"),
                "response_headers": dict(resp.headers),
                "x_powered_by": resp.headers.get("X-Powered-By", ""),
            })
            self.response = resp
            self.html = resp.text
            self.soup = BeautifulSoup(self.html, "lxml")
            return True
        except Exception as e:
            self.metrics["fetch_error"] = str(e)
            return False

    # ── TECHNICAL ─────────────────────────────────────────────────────────────

    def check_https(self):
        if self.scheme == "https":
            try:
                http_url = self.url.replace("https://", "http://", 1)
                r = self.session.get(http_url, timeout=8, allow_redirects=True, verify=False)
                if r.url.startswith("https://"):
                    self._add("Technical", "HTTP→HTTPS Redirect", SEVERITY["PASS"],
                        "HTTP correctly redirects to HTTPS", "", "N/A")
                else:
                    self._add("Technical", "HTTP→HTTPS Redirect", SEVERITY["HIGH"],
                        "HTTP version does NOT redirect to HTTPS — duplicate content risk",
                        "https://developers.google.com/search/docs/crawling-indexing/https",
                        "Add 301 redirect from http:// to https:// in your server config.\n"
                        "Apache (.htaccess):\nRewriteEngine On\nRewriteCond %{HTTPS} off\n"
                        "RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]\n"
                        "Nginx: return 301 https://$host$request_uri;",
                        impact="Duplicate content + split link equity + trust issues")
            except Exception:
                pass
            self._add("Technical", "HTTPS", SEVERITY["PASS"], "Site uses HTTPS", "", "N/A")
        else:
            self._add("Technical", "HTTPS", SEVERITY["CRITICAL"],
                "Site NOT using HTTPS — major Google ranking signal missing",
                "https://developers.google.com/search/docs/crawling-indexing/https",
                "1. Install free SSL via Let's Encrypt (certbot)\n"
                "2. Configure server to force HTTPS\n"
                "3. Update all internal links to https://\n"
                "4. Update canonical tags to https://\n"
                "5. Resubmit XML sitemap in Google Search Console",
                {"scheme": self.scheme},
                impact="HTTPS is a confirmed Google ranking signal since 2014")

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
            issuer = dict(x[0] for x in cert.get("issuer", []))
            self.metrics.update({
                "ssl_expiry_days": days_left,
                "ssl_expiry_date": expiry.strftime("%Y-%m-%d"),
                "ssl_issuer": issuer.get("organizationName", "Unknown"),
            })
            if days_left < 7:
                self._add("Technical", "SSL Certificate", SEVERITY["CRITICAL"],
                    f"SSL expires in {days_left} days — browsers will show security warnings",
                    "https://developers.google.com/search/docs/crawling-indexing/https",
                    "Renew immediately: sudo certbot renew\nSetup cron: 0 0 1 * * certbot renew",
                    {"expires": expiry.strftime("%Y-%m-%d"), "days_left": days_left},
                    impact="Users see 'Not Secure' — CTR drops dramatically")
            elif days_left < 30:
                self._add("Technical", "SSL Certificate", SEVERITY["HIGH"],
                    f"SSL expires in {days_left} days — renew soon",
                    "https://developers.google.com/search/docs/crawling-indexing/https",
                    "Renew now: certbot renew. Enable auto-renewal: certbot renew --dry-run",
                    {"expires": expiry.strftime("%Y-%m-%d"), "days_left": days_left})
            else:
                self._add("Technical", "SSL Certificate", SEVERITY["PASS"],
                    f"SSL valid {days_left} days — issued by {issuer.get('organizationName','CA')}",
                    "", "N/A", {"expires": expiry.strftime("%Y-%m-%d")})
        except Exception as e:
            if self.scheme == "https":
                self._add("Technical", "SSL Certificate", SEVERITY["HIGH"],
                    f"SSL certificate could not be verified: {str(e)[:80]}",
                    "https://www.ssllabs.com/ssltest/",
                    "Test at ssllabs.com/ssltest/. Check for chain issues, mixed content.",
                    {"error": str(e)[:100]})

    def check_robots_txt(self):
        robots_url = f"{self.scheme}://{self.base_domain}/robots.txt"
        try:
            r = self.session.get(robots_url, timeout=10, verify=False)
            if r.status_code == 200:
                content = r.text
                self.metrics["robots_txt_content"] = content[:800]
                path = self.parsed_url.path or "/"
                current_agent = None
                blocked = False
                has_sitemap = "Sitemap:" in content
                has_crawl_delay = "crawl-delay" in content.lower()
                disallow_all = False
                for line in content.splitlines():
                    line = line.strip()
                    if line.lower().startswith("user-agent:"):
                        current_agent = line.split(":", 1)[1].strip()
                    elif line.lower().startswith("disallow:") and current_agent in ("*", "Googlebot"):
                        rule = line.split(":", 1)[1].strip()
                        if rule == "/":
                            disallow_all = True
                        elif rule and path.startswith(rule):
                            blocked = True
                if disallow_all:
                    self._add("Technical", "Robots.txt — Blocks Entire Site", SEVERITY["CRITICAL"],
                        "robots.txt has 'Disallow: /' — entire site blocked from Google",
                        "https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt",
                        "Change to 'Disallow:' (empty = allow all crawling).\n"
                        "Verify fix using Google Search Console > robots.txt Tester.",
                        impact="Nothing on the site can be indexed by Google")
                elif blocked:
                    self._add("Technical", "Robots.txt — URL Blocked", SEVERITY["CRITICAL"],
                        f"This URL is blocked by robots.txt Disallow rule",
                        "https://developers.google.com/search/docs/crawling-indexing/robots/intro",
                        "Review and fix Disallow rules in robots.txt. Remove rule blocking this path.",
                        {"path": path, "robots_url": robots_url})
                else:
                    self._add("Technical", "Robots.txt", SEVERITY["PASS"],
                        "robots.txt present and page is not blocked", "", "N/A",
                        {"has_sitemap_directive": has_sitemap})
                if not has_sitemap:
                    self._add("Technical", "Robots.txt — Sitemap Directive", SEVERITY["LOW"],
                        "robots.txt missing Sitemap: directive",
                        "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview",
                        "Add to robots.txt:\nSitemap: https://yourdomain.com/sitemap.xml",
                        impact="Slower sitemap discovery by search engine crawlers")
                if has_crawl_delay:
                    self._add("Technical", "Robots.txt — Crawl-Delay", SEVERITY["LOW"],
                        "Crawl-delay in robots.txt — Google ignores this directive",
                        "https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt",
                        "Remove Crawl-delay. Use Google Search Console > Crawl Rate Settings instead.")
            else:
                self._add("Technical", "Robots.txt — Missing", SEVERITY["MEDIUM"],
                    f"robots.txt not found (HTTP {r.status_code})",
                    "https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt",
                    "Create /robots.txt:\nUser-agent: *\nDisallow:\nSitemap: https://yourdomain.com/sitemap.xml",
                    {"robots_url": robots_url})
        except Exception as e:
            self._add("Technical", "Robots.txt", SEVERITY["MEDIUM"],
                f"Could not fetch robots.txt: {str(e)[:60]}",
                "https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt",
                "Ensure robots.txt is accessible at domain root.",
                {"url": robots_url})

    def check_sitemap(self):
        candidates = [
            f"{self.scheme}://{self.base_domain}/sitemap.xml",
            f"{self.scheme}://{self.base_domain}/sitemap_index.xml",
            f"{self.scheme}://{self.base_domain}/sitemap-index.xml",
        ]
        try:
            r = self.session.get(f"{self.scheme}://{self.base_domain}/robots.txt", timeout=8, verify=False)
            for line in r.text.splitlines():
                if line.strip().lower().startswith("sitemap:"):
                    sm = line.split(":", 1)[1].strip()
                    if sm not in candidates:
                        candidates.insert(0, sm)
        except Exception:
            pass

        found_url = None
        url_count = 0
        has_lastmod = False
        for surl in candidates:
            try:
                r = self.session.get(surl, timeout=10, verify=False)
                if r.status_code == 200 and ("<urlset" in r.text or "<sitemapindex" in r.text):
                    found_url = surl
                    url_count = r.text.count("<url>") + r.text.count("<sitemap>")
                    has_lastmod = "<lastmod>" in r.text
                    self.metrics["sitemap_url"] = surl
                    self.metrics["sitemap_url_count"] = url_count
                    break
            except Exception:
                pass

        if found_url:
            q_issues = []
            if not has_lastmod:
                q_issues.append("missing <lastmod> dates")
            if url_count == 0:
                q_issues.append("sitemap appears empty")
            if q_issues:
                self._add("Technical", "XML Sitemap — Quality Issues", SEVERITY["MEDIUM"],
                    f"Sitemap found but: {', '.join(q_issues)}",
                    "https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap",
                    "Add <lastmod> to every URL. Keep sitemap under 50,000 URLs/50MB.\n"
                    "Submit in Google Search Console > Sitemaps.",
                    {"sitemap_url": found_url, "url_count": url_count})
            else:
                self._add("Technical", "XML Sitemap", SEVERITY["PASS"],
                    f"Sitemap found: {url_count} URLs with lastmod dates", "", "N/A",
                    {"sitemap_url": found_url})
        else:
            self._add("Technical", "XML Sitemap — Missing", SEVERITY["HIGH"],
                "No XML sitemap found",
                "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview",
                "Create sitemap.xml listing all indexable URLs.\n"
                "- WordPress: Yoast SEO or RankMath plugins\n"
                "- Other: xml-sitemaps.com generator\n"
                "Submit in Google Search Console > Sitemaps",
                {"checked": candidates},
                impact="Slower page discovery — deep pages may never be indexed")

    def check_redirects(self):
        count = self.metrics.get("redirect_count", 0)
        chain = self.metrics.get("redirect_chain", [])
        if count == 0:
            self._add("Technical", "Redirects", SEVERITY["PASS"], "No redirects detected", "", "N/A")
        elif count == 1:
            self._add("Technical", "Redirects", SEVERITY["LOW"],
                "1 redirect (acceptable if using 301)",
                "https://developers.google.com/search/docs/crawling-indexing/301-redirects",
                "Ensure redirect type is 301 (permanent), not 302 (temporary).\n"
                "Update internal links to point directly to final URL.",
                {"chain": chain})
        else:
            self._add("Technical", "Redirects — Chain", SEVERITY["HIGH"],
                f"Redirect chain: {count} hops — link equity diluted each hop",
                "https://developers.google.com/search/docs/crawling-indexing/301-redirects",
                f"Collapse to a single 301 redirect. Update all internal links to final URL.\n"
                f"Chain: {' → '.join([str(u)[:60] for u in chain[:5]])}",
                {"count": count, "chain": chain},
                impact="Each redirect hop loses ~15% link equity and adds latency")

    def check_status_code(self):
        code = self.metrics.get("status_code", 0)
        if code == 200:
            self._add("Technical", "HTTP Status Code", SEVERITY["PASS"],
                "200 OK", "", "N/A", {"code": code})
        elif code == 301:
            self._add("Technical", "HTTP Status Code", SEVERITY["LOW"],
                "301 Permanent Redirect",
                "https://developers.google.com/search/docs/crawling-indexing/301-redirects",
                "Update internal links to point directly to the destination URL.",
                {"code": code})
        elif code == 302:
            self._add("Technical", "HTTP Status Code — 302", SEVERITY["MEDIUM"],
                "302 Temporary Redirect — link equity may not pass",
                "https://developers.google.com/search/docs/crawling-indexing/301-redirects",
                "If this is a permanent redirect, change 302 to 301 immediately.",
                {"code": code},
                impact="302 redirects may not pass PageRank — use 301 for permanent redirects")
        elif code == 403:
            self._add("Technical", "HTTP Status Code — 403", SEVERITY["CRITICAL"],
                "403 Forbidden — Googlebot may be blocked",
                "https://developers.google.com/search/docs/crawling-indexing/http-network-errors",
                "Check server config. Ensure Googlebot IP range is not blocked.\n"
                "Test: Google Search Console > URL Inspection.",
                {"code": code})
        elif code == 404:
            self._add("Technical", "HTTP Status Code — 404", SEVERITY["CRITICAL"],
                "404 Not Found — page cannot be indexed",
                "https://developers.google.com/search/docs/crawling-indexing/http-network-errors",
                "Fix URL to return 200 OR 301 redirect to closest relevant page.\n"
                "Check Search Console > Coverage for crawl errors.",
                {"code": code})
        elif code >= 500:
            self._add("Technical", "HTTP Status Code — 5xx", SEVERITY["CRITICAL"],
                f"Server error {code} — page cannot be crawled",
                "https://developers.google.com/search/docs/crawling-indexing/http-network-errors",
                "Check server error logs immediately. Persistent 5xx errors cause deindexing.",
                {"code": code},
                impact="Repeated 5xx errors cause Google to drop pages from index")

    def check_page_size(self):
        size_kb = self.metrics.get("content_length_kb", 0)
        if size_kb > SEO_STANDARDS["max_page_size_kb"]:
            self._add("Technical", "Page Size — Critical", SEVERITY["HIGH"],
                f"Page too large: {size_kb}KB (max recommended 3000KB)",
                "https://web.dev/performance/",
                "Minify HTML/CSS/JS, compress images, remove inline SVGs, defer non-critical resources.",
                {"size_kb": size_kb},
                impact="Large pages cause slow TTFB and hurt Core Web Vitals")
        elif size_kb > 300:
            self._add("Technical", "Page Size", SEVERITY["LOW"],
                f"Page size: {size_kb}KB — consider optimization",
                "https://web.dev/performance/",
                "Target HTML under 100KB. Move inline styles/scripts to external files.",
                {"size_kb": size_kb})
        else:
            self._add("Technical", "Page Size", SEVERITY["PASS"],
                f"Page size: {size_kb}KB", "", "N/A")

    def check_load_time(self):
        ms = self.metrics.get("load_time_ms", 0)
        if ms == 0:
            return
        if ms < 800:
            self._add("Technical", "Server Response Time (TTFB)", SEVERITY["PASS"],
                f"Excellent TTFB: {ms}ms (Google target: <800ms)", "", "N/A", {"ms": ms})
        elif ms < SEO_STANDARDS["max_load_time_ms"]:
            self._add("Technical", "Server Response Time (TTFB)", SEVERITY["MEDIUM"],
                f"TTFB: {ms}ms — above Google's 800ms recommendation",
                "https://web.dev/ttfb/",
                "Enable server caching, use Cloudflare CDN (free), optimize DB queries.",
                {"ms": ms, "target": "< 800ms"})
        else:
            self._add("Technical", "Server Response Time (TTFB)", SEVERITY["HIGH"],
                f"Slow TTFB: {ms}ms — directly impacts LCP Core Web Vital",
                "https://web.dev/ttfb/",
                "1. Enable Redis/Varnish caching\n"
                "2. Use Cloudflare CDN\n"
                "3. Enable GZIP/Brotli compression\n"
                "4. Optimize database queries\n"
                "5. Upgrade to better hosting",
                {"ms": ms},
                impact="Slow TTFB delays LCP — a Core Web Vital ranking factor")

    def check_response_headers(self):
        headers = self.metrics.get("response_headers", {})

        x_robots = headers.get("X-Robots-Tag", "").lower()
        if "noindex" in x_robots:
            self._add("Technical", "X-Robots-Tag: noindex", SEVERITY["CRITICAL"],
                "HTTP header X-Robots-Tag contains 'noindex' — page will be deindexed",
                "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                "Remove 'noindex' from X-Robots-Tag server header. This overrides all other indexing signals.",
                {"header": x_robots},
                impact="Page will be removed from Google index — overrides meta robots too")

        ct = headers.get("Content-Type", "")
        if "text/html" not in ct:
            self._add("Technical", "Content-Type Header", SEVERITY["MEDIUM"],
                f"Unexpected Content-Type: '{ct}'",
                "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type",
                "Set: Content-Type: text/html; charset=utf-8",
                {"content_type": ct})

        if "utf-8" not in ct.lower() and "utf8" not in ct.lower():
            self._add("Technical", "Charset (UTF-8)", SEVERITY["MEDIUM"],
                "UTF-8 charset not declared in Content-Type header",
                "https://developers.google.com/search/docs/appearance/site-structure",
                "Set Content-Type: text/html; charset=utf-8 AND add <meta charset='UTF-8'> in <head>.",
                {"content_type": ct})
        else:
            self._add("Technical", "Charset (UTF-8)", SEVERITY["PASS"],
                "UTF-8 charset correctly declared", "", "N/A")

        meta_charset = self.soup.find("meta", charset=True) if self.soup else None
        if not meta_charset:
            self._add("Technical", "HTML Charset Meta Tag", SEVERITY["MEDIUM"],
                "Missing <meta charset='UTF-8'> in HTML head",
                "https://html.spec.whatwg.org/multipage/semantics.html#charset",
                "Add as FIRST tag in <head>: <meta charset='UTF-8'>")
        else:
            if "utf-8" not in meta_charset.get("charset", "").lower():
                self._add("Technical", "HTML Charset Meta Tag", SEVERITY["MEDIUM"],
                    f"Meta charset is not UTF-8: '{meta_charset.get('charset')}'",
                    "https://html.spec.whatwg.org/multipage/semantics.html#charset",
                    "Change to: <meta charset='UTF-8'>")
            else:
                self._add("Technical", "HTML Charset Meta Tag", SEVERITY["PASS"],
                    "Meta charset='UTF-8' present", "", "N/A")

        cache = headers.get("Cache-Control", "")
        if not cache:
            self._add("Technical", "Cache-Control Header", SEVERITY["MEDIUM"],
                "No Cache-Control header — browsers won't cache page",
                "https://web.dev/http-cache/",
                "Add caching headers:\n"
                "- HTML: Cache-Control: no-cache\n"
                "- CSS/JS: Cache-Control: public, max-age=31536000, immutable\n"
                "- Images: Cache-Control: public, max-age=604800",
                impact="Every visit redownloads the page — hurts performance for repeat visitors")
        else:
            self._add("Technical", "Cache-Control Header", SEVERITY["PASS"],
                f"Cache-Control: {cache}", "", "N/A")

        ce = headers.get("Content-Encoding", "")
        if ce in ("gzip", "br", "deflate"):
            self._add("Technical", "Compression (GZIP/Brotli)", SEVERITY["PASS"],
                f"Response compressed: {ce}", "", "N/A")
        else:
            self._add("Technical", "Compression", SEVERITY["MEDIUM"],
                "Response NOT compressed — serving full-size HTML",
                "https://web.dev/uses-text-compression/",
                "Enable Brotli (preferred) or GZIP:\n"
                "Nginx: gzip on; gzip_types text/html text/css application/javascript;\n"
                "Apache: AddOutputFilterByType DEFLATE text/html text/css\n"
                "Cloudflare: Auto-compression enabled by default",
                impact="Uncompressed pages are 60-80% larger — hurts Core Web Vitals")

        hsts = headers.get("Strict-Transport-Security", "")
        if not hsts and self.scheme == "https":
            self._add("Technical", "HSTS Header", SEVERITY["LOW"],
                "Strict-Transport-Security (HSTS) header missing",
                "https://web.dev/strict-transport-security/",
                "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload\n"
                "Forces HTTPS and prevents protocol downgrade attacks.",
                impact="Without HSTS, browsers may attempt HTTP — adds latency")

        xpb = self.metrics.get("x_powered_by", "")
        if xpb:
            self._add("Technical", "Technology Stack Exposed", SEVERITY["LOW"],
                f"X-Powered-By header reveals: '{xpb}' — security risk",
                "https://owasp.org/www-project-secure-headers/",
                "Remove X-Powered-By header. PHP: set expose_php=Off in php.ini.\n"
                "Express.js: app.disable('x-powered-by')")

    def check_render_blocking(self):
        head = self.soup.find("head")
        if not head:
            return
        blocking_scripts = [s for s in head.find_all("script", src=True)
                            if not s.get("async") and not s.get("defer")
                            and s.get("type") != "module"]
        css_links = self.soup.find_all("link", rel="stylesheet")
        self.metrics["render_blocking_scripts"] = len(blocking_scripts)
        self.metrics["css_files"] = len(css_links)

        if blocking_scripts:
            self._add("Technical", "Render-Blocking Scripts", SEVERITY["MEDIUM"],
                f"{len(blocking_scripts)} render-blocking scripts in <head>",
                "https://web.dev/render-blocking-resources/",
                "Add 'defer' to non-critical scripts: <script src='app.js' defer>\n"
                "Add 'async' for independent scripts (analytics, ads).\n"
                "Move scripts to bottom of <body> as last resort.",
                {"count": len(blocking_scripts),
                 "scripts": [s.get("src", "")[:80] for s in blocking_scripts[:5]]},
                impact="Each blocking script pauses page rendering — delays LCP metric")
        else:
            self._add("Technical", "Render-Blocking Scripts", SEVERITY["PASS"],
                "No render-blocking scripts in <head>", "", "N/A")

        ext_scripts = self.soup.find_all("script", src=True)
        self.metrics["external_scripts"] = len(ext_scripts)
        if len(ext_scripts) > 15:
            self._add("Technical", "Excessive JavaScript Files", SEVERITY["MEDIUM"],
                f"{len(ext_scripts)} external JS files loaded",
                "https://web.dev/efficiently-load-third-party-javascript/",
                "Bundle JS with webpack/rollup. Remove unused scripts.\n"
                "Audit with Chrome DevTools > Coverage tab.",
                {"count": len(ext_scripts)})

    def check_mobile_friendly(self):
        viewport = self.soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
        if not viewport:
            self._add("Technical", "Mobile Viewport — Missing", SEVERITY["CRITICAL"],
                "No viewport meta tag — page NOT mobile-friendly",
                "https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing",
                "Add immediately to <head>:\n<meta name='viewport' content='width=device-width, initial-scale=1'>",
                impact="Google uses mobile-first indexing — poor mobile experience = poor rankings")
        else:
            content = viewport.get("content", "")
            self.metrics["viewport"] = content
            problems = []
            if "width=device-width" not in content:
                problems.append("missing width=device-width")
            if "initial-scale" not in content:
                problems.append("missing initial-scale=1")
            if "user-scalable=no" in content or "maximum-scale=1" in content:
                problems.append("user zoom disabled — accessibility violation (WCAG 1.4.4)")
            if problems:
                self._add("Technical", "Viewport Configuration", SEVERITY["MEDIUM"],
                    f"Viewport issues: {', '.join(problems)}",
                    "https://web.dev/viewport/",
                    "Use: <meta name='viewport' content='width=device-width, initial-scale=1'>\n"
                    "Never disable user zoom — it's an accessibility violation.",
                    {"content": content})
            else:
                self._add("Technical", "Mobile Viewport", SEVERITY["PASS"],
                    f"Viewport correctly configured", "", "N/A")

        theme_color = self.soup.find("meta", attrs={"name": "theme-color"})
        if not theme_color:
            self._add("Technical", "Theme Color Meta", SEVERITY["LOW"],
                "Missing theme-color meta — no branded browser chrome on mobile",
                "https://web.dev/add-manifest/",
                "Add: <meta name='theme-color' content='#your-brand-color'>")

    def check_page_speed_indicators(self):
        imgs = self.soup.find_all("img")
        lazy_loaded = [i for i in imgs if i.get("loading") == "lazy"]
        not_lazy = [i for i in imgs if not i.get("loading")]

        if len(not_lazy) > 3:
            self._add("Technical", "Image Lazy Loading", SEVERITY["MEDIUM"],
                f"{len(not_lazy)} images missing loading='lazy'",
                "https://web.dev/lazy-loading-images/",
                "Add loading='lazy' to all below-fold images:\n"
                "<img src='...' alt='...' loading='lazy' width='800' height='600'>\n"
                "Keep loading='eager' only for above-fold/LCP images.",
                {"total": len(imgs), "not_lazy": len(not_lazy)},
                impact="Non-lazy images download immediately — increases page weight")
        elif imgs:
            self._add("Technical", "Image Lazy Loading", SEVERITY["PASS"],
                f"Lazy loading: {len(lazy_loaded)}/{len(imgs)} images", "", "N/A")

        img_srcs = [i.get("src", "") for i in imgs]
        old_fmts = [s for s in img_srcs if re.search(r'\.(jpg|jpeg|png|gif)(\?|$)', s, re.I)]
        webp_avif = [s for s in img_srcs if re.search(r'\.(webp|avif)(\?|$)', s, re.I)]
        if old_fmts and not webp_avif:
            self._add("Technical", "Next-Gen Image Formats", SEVERITY["MEDIUM"],
                f"{len(old_fmts)} images in JPEG/PNG — no WebP/AVIF detected",
                "https://web.dev/uses-webp-images/",
                "Convert to WebP (30-50% smaller than JPEG):\n"
                "<picture>\n"
                "  <source srcset='img.webp' type='image/webp'>\n"
                "  <img src='img.jpg' alt='...'>\n"
                "</picture>\n"
                "Tools: Squoosh.app, sharp (Node.js), ImageMagick",
                {"jpeg_png_count": len(old_fmts)},
                impact="Large images directly hurt LCP Core Web Vital score")

        inline_style_elems = self.soup.find_all(style=True)
        if len(inline_style_elems) > 10:
            self._add("Technical", "Excessive Inline Styles", SEVERITY["LOW"],
                f"{len(inline_style_elems)} elements with inline style attributes",
                "https://web.dev/extract-critical-css/",
                "Move inline styles to external CSS classes for better caching.",
                {"count": len(inline_style_elems)})

    def check_page_experience(self):
        preloads = self.soup.find_all("link", rel="preload")
        preconnects = self.soup.find_all("link", rel="preconnect")
        self.metrics["preload_hints"] = len(preloads)
        self.metrics["preconnect_hints"] = len(preconnects)

        if not preloads and not preconnects:
            self._add("Technical", "Resource Hints Missing", SEVERITY["LOW"],
                "No preload or preconnect hints found",
                "https://web.dev/preconnect-and-dns-prefetch/",
                "Add for critical resources:\n"
                "<link rel='preconnect' href='https://fonts.googleapis.com'>\n"
                "<link rel='preload' href='hero.jpg' as='image'>\n"
                "<link rel='preload' href='font.woff2' as='font' crossorigin>",
                impact="Without preloading, critical resources are discovered late — delays LCP")

        manifest = self.soup.find("link", rel="manifest")
        if not manifest:
            self._add("Technical", "Web App Manifest", SEVERITY["LOW"],
                "No web app manifest linked",
                "https://web.dev/add-manifest/",
                "Add: <link rel='manifest' href='/manifest.json'>\n"
                "Enables PWA features and 'Add to Home Screen' on mobile.")

    def check_javascript_rendering(self):
        body = self.soup.find("body")
        if not body:
            return
        body_text = body.get_text(strip=True)
        spa_frameworks = ["__NEXT_DATA__", "ng-app", "data-reactroot", "data-vue-app",
                          "__nuxt", "__gatsby", "ember-application"]
        spa_detected = any(f in self.html for f in spa_frameworks)
        if spa_detected and len(body_text) < 300:
            self._add("Technical", "JavaScript Rendering (SPA)", SEVERITY["HIGH"],
                "SPA detected with minimal server-side HTML — Googlebot may miss content",
                "https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics",
                "Implement SSR (Server-Side Rendering) or SSG (Static Site Generation):\n"
                "- Next.js: getServerSideProps() or getStaticProps()\n"
                "- Nuxt.js: SSR mode enabled\n"
                "- Test: curl -A Googlebot <url> to see raw crawl output",
                impact="JS-only content may not be indexed — critical SEO risk")

    def check_page_freshness(self):
        last_mod = self.metrics.get("response_headers", {}).get("Last-Modified", "")
        if last_mod:
            self.metrics["last_modified"] = last_mod
            self._add("Technical", "Last-Modified Header", SEVERITY["PASS"],
                f"Last-Modified: {last_mod}", "", "N/A")
        else:
            self._add("Technical", "Last-Modified Header", SEVERITY["LOW"],
                "No Last-Modified header in server response",
                "https://developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget",
                "Configure server to send Last-Modified header. Helps Googlebot optimize crawl frequency.")

    # ── ON-PAGE ───────────────────────────────────────────────────────────────

    def check_title_tag(self):
        titles = self.soup.find_all("title")
        if len(titles) == 0:
            self._add("On-Page", "Title Tag — Missing", SEVERITY["CRITICAL"],
                "No <title> tag found",
                "https://developers.google.com/search/docs/appearance/title-link",
                "Add: <title>Primary Keyword — Secondary Keyword | Brand Name</title>\n"
                "30-60 characters. Put target keyword first. One per page.",
                impact="Title tag is #1 on-page ranking factor — Google uses it as SERP headline")
            return

        if len(titles) > 1:
            self._add("On-Page", "Title Tag — Duplicates", SEVERITY["HIGH"],
                f"{len(titles)} title tags found — only first is used",
                "https://developers.google.com/search/docs/appearance/title-link",
                "Remove all duplicate <title> tags. Exactly ONE per page.",
                {"titles": [t.get_text()[:60] for t in titles]})

        title = titles[0].get_text(strip=True)
        length = len(title)
        self.metrics["title"] = title
        self.metrics["title_length"] = length

        if length == 0:
            self._add("On-Page", "Title Tag — Empty", SEVERITY["CRITICAL"],
                "Title tag is empty",
                "https://developers.google.com/search/docs/appearance/title-link",
                "Write descriptive title 30-60 chars with primary keyword.")
            return

        issues = []
        if length < SEO_STANDARDS["title_min"]:
            issues.append(f"too short: {length} chars (minimum 30)")
        if length > SEO_STANDARDS["title_max"]:
            issues.append(f"too long: {length} chars (max 60) — truncated in SERPs")

        words = title.lower().split()
        repeats = {w: c for w, c in Counter(words).items() if c > 2 and w not in STOP_WORDS}
        if repeats:
            issues.append(f"keyword repetition: {repeats}")

        if title.lower().startswith(("home", "welcome", "index", "untitled")):
            issues.append("starts with generic word — put target keyword first")

        if issues:
            self._add("On-Page", "Title Tag", SEVERITY["HIGH"],
                f"Title issues: {'; '.join(issues)}",
                "https://developers.google.com/search/docs/appearance/title-link",
                f"Format: [Primary Keyword] - [Secondary Keyword] | [Brand]\n"
                f"30-60 chars. One separator (dash or pipe). No repetition.\n"
                f"Current ({length} chars): '{title}'",
                {"title": title, "length": length},
                impact="Title is your SERP headline — directly affects click-through rate")
        else:
            self._add("On-Page", "Title Tag", SEVERITY["PASS"],
                f"Title optimal ({length} chars): '{title[:50]}'", "", "N/A",
                {"title": title, "length": length})

    def check_meta_description(self):
        descs = self.soup.find_all("meta", attrs={"name": re.compile("^description$", re.I)})
        if len(descs) == 0:
            self._add("On-Page", "Meta Description — Missing", SEVERITY["HIGH"],
                "No meta description found",
                "https://developers.google.com/search/docs/appearance/snippet",
                "Add: <meta name='description' content='...'>\n"
                "120-160 chars. Include: primary keyword + value prop + call-to-action.\n"
                "Example: 'Discover the best [topic] with our expert guide. Learn [benefit]. Start [CTA] today.'",
                impact="Meta description is your organic ad copy — poor copy = lower CTR")
            return

        if len(descs) > 1:
            self._add("On-Page", "Meta Description — Duplicates", SEVERITY["HIGH"],
                f"Multiple meta description tags: {len(descs)}",
                "https://developers.google.com/search/docs/appearance/snippet",
                "Remove all duplicates. Keep exactly ONE meta description per page.",
                {"count": len(descs)})

        desc = descs[0].get("content", "").strip()
        length = len(desc)
        self.metrics["meta_description"] = desc
        self.metrics["meta_description_length"] = length

        if length == 0:
            self._add("On-Page", "Meta Description — Empty", SEVERITY["HIGH"],
                "Meta description tag is empty",
                "https://developers.google.com/search/docs/appearance/snippet",
                "Write 120-160 char description with keyword + CTA.")
            return

        issues = []
        if length < SEO_STANDARDS["meta_desc_min"]:
            issues.append(f"too short ({length} chars, min 120)")
        if length > SEO_STANDARDS["meta_desc_max"]:
            issues.append(f"too long ({length} chars, max 160) — truncated in SERPs")

        cta_words = ["learn", "discover", "get", "find", "start", "try", "explore",
                     "see", "read", "shop", "buy", "download", "join", "contact", "book"]
        if not any(w in desc.lower() for w in cta_words):
            issues.append("no call-to-action — add action verb to improve CTR")

        if issues:
            self._add("On-Page", "Meta Description", SEVERITY["MEDIUM"],
                f"Issues: {'; '.join(issues)}",
                "https://developers.google.com/search/docs/appearance/snippet",
                f"Target 120-160 chars with keyword + value prop + CTA.\n"
                f"Current ({length} chars): '{desc[:100]}'",
                {"length": length},
                impact="Meta description is your organic SERP ad — bad copy = lower CTR")
        else:
            self._add("On-Page", "Meta Description", SEVERITY["PASS"],
                f"Meta description optimal ({length} chars)", "", "N/A",
                {"length": length})

    def check_headings(self):
        h1s = self.soup.find_all("h1")
        h2s = self.soup.find_all("h2")
        h3s = self.soup.find_all("h3")
        h4s = self.soup.find_all("h4")

        h1_texts = [h.get_text(strip=True) for h in h1s]
        self.metrics.update({
            "h1_count": len(h1s), "h1_texts": h1_texts,
            "h2_count": len(h2s), "h3_count": len(h3s),
        })

        if len(h1s) == 0:
            self._add("On-Page", "H1 Tag — Missing", SEVERITY["CRITICAL"],
                "No H1 tag — primary topic signal completely missing",
                "https://moz.com/learn/seo/on-page-factors",
                "Add exactly ONE <h1> with your primary keyword:\n"
                "<h1>Your Primary Keyword Phrase Here</h1>\n"
                "Place as the main visible headline of the page content.",
                impact="H1 is a strong on-page ranking signal for the page's primary topic")
        elif len(h1s) > 1:
            self._add("On-Page", "H1 Tag — Multiple", SEVERITY["HIGH"],
                f"{len(h1s)} H1 tags found — dilutes keyword focus",
                "https://moz.com/learn/seo/on-page-factors",
                "Keep exactly ONE H1. Change additional H1s to H2 or H3.",
                {"count": len(h1s), "h1_texts": h1_texts},
                impact="Multiple H1s dilute keyword signal and confuse search engines")
        else:
            h1 = h1_texts[0]
            if len(h1) < 5:
                self._add("On-Page", "H1 Tag — Too Short", SEVERITY["HIGH"],
                    f"H1 too short: '{h1}'",
                    "https://moz.com/learn/seo/on-page-factors",
                    "H1 should clearly state the page topic with the primary keyword.", {"h1": h1})
            elif len(h1) > 70:
                self._add("On-Page", "H1 Tag — Too Long", SEVERITY["LOW"],
                    f"H1 is {len(h1)} chars — aim for under 70",
                    "https://moz.com/learn/seo/on-page-factors",
                    "Keep H1 concise. Put primary keyword at the beginning.", {"h1": h1})
            else:
                self._add("On-Page", "H1 Tag", SEVERITY["PASS"],
                    f"H1 present: '{h1[:60]}'", "", "N/A")

        if len(h2s) == 0 and len(h3s) > 0:
            self._add("On-Page", "Heading Hierarchy — Broken", SEVERITY["MEDIUM"],
                "H3 used without H2 — heading structure is broken",
                "https://web.dev/use-landmarks/",
                "Use heading order: H1 → H2 → H3 → H4. Never skip levels.",
                {"h1": len(h1s), "h2": 0, "h3": len(h3s)})
        elif len(h2s) == 0:
            self._add("On-Page", "H2 Subheadings — Missing", SEVERITY["MEDIUM"],
                "No H2 subheadings — content has no structure",
                "https://moz.com/learn/seo/on-page-factors",
                "Add H2 tags for each major section. Include secondary/LSI keywords in H2s.\n"
                "H2s help Google understand page sections and power featured snippets.",
                impact="Unstructured content is harder to rank for multiple keywords")
        else:
            h2_samples = [h.get_text(strip=True)[:60] for h in h2s[:5]]
            self._add("On-Page", "Heading Structure", SEVERITY["PASS"],
                f"Structure: 1 H1, {len(h2s)} H2s, {len(h3s)} H3s, {len(h4s)} H4s", "", "N/A",
                {"h2_sample": h2_samples})

        empty = []
        for tag in ["h1", "h2", "h3", "h4"]:
            for h in self.soup.find_all(tag):
                if not h.get_text(strip=True):
                    empty.append(tag.upper())
        if empty:
            self._add("On-Page", "Empty Heading Tags", SEVERITY["MEDIUM"],
                f"Empty heading tags found: {', '.join(empty)}",
                "https://moz.com/learn/seo/on-page-factors",
                "Remove all empty heading tags or add meaningful content to them.",
                {"empty_tags": empty})

    def check_canonical(self):
        canonicals = self.soup.find_all("link", rel="canonical")
        if len(canonicals) == 0:
            self._add("On-Page", "Canonical Tag — Missing", SEVERITY["HIGH"],
                "No canonical tag — duplicate content risk",
                "https://developers.google.com/search/docs/crawling-indexing/canonicalization",
                "Add to <head>:\n<link rel='canonical' href='https://yourdomain.com/this-exact-page/'>\n"
                "Use absolute URL. Always self-reference unless you intentionally want a different canonical.",
                impact="Without canonical, Google may rank the wrong URL variant")
            return
        if len(canonicals) > 1:
            self._add("On-Page", "Canonical Tag — Multiple", SEVERITY["HIGH"],
                f"Multiple canonical tags: {len(canonicals)} — Google ignores all",
                "https://developers.google.com/search/docs/crawling-indexing/canonicalization",
                "Multiple canonicals are treated as invalid. Keep exactly one.",
                {"canonicals": [c.get("href", "") for c in canonicals]})
            return

        href = canonicals[0].get("href", "").strip()
        self.metrics["canonical_url"] = href

        if not href:
            self._add("On-Page", "Canonical Tag — Empty", SEVERITY["HIGH"],
                "Canonical tag present but href is empty",
                "https://developers.google.com/search/docs/crawling-indexing/canonicalization",
                "Set href to full absolute URL: <link rel='canonical' href='https://yourdomain.com/page/'>")
        elif not href.startswith("http"):
            self._add("On-Page", "Canonical Tag — Relative URL", SEVERITY["MEDIUM"],
                "Canonical uses relative URL — should be absolute",
                "https://developers.google.com/search/docs/crawling-indexing/canonicalization",
                "Always use absolute URLs in canonical: https://yourdomain.com/page/",
                {"href": href})
        elif href.rstrip("/") != self.metrics.get("final_url", self.url).rstrip("/"):
            self._add("On-Page", "Canonical Tag — Cross-Page", SEVERITY["MEDIUM"],
                "Canonical points to different URL (cross-page canonical)",
                "https://developers.google.com/search/docs/crawling-indexing/canonicalization",
                "Verify this is intentional. If not, update canonical to self-reference current URL.",
                {"canonical": href, "current": self.metrics.get("final_url")})
        else:
            self._add("On-Page", "Canonical Tag", SEVERITY["PASS"],
                "Canonical correctly self-references this URL", "", "N/A", {"canonical": href})

    def check_meta_robots(self):
        all_robots = self.soup.find_all("meta", attrs={"name": re.compile("^robots$", re.I)})
        if not all_robots:
            self._add("On-Page", "Meta Robots", SEVERITY["LOW"],
                "No meta robots tag (defaults to 'index, follow' — acceptable)",
                "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                "For clarity, add: <meta name='robots' content='index, follow'>\n"
                "For pages to hide: <meta name='robots' content='noindex, nofollow'>")
            return
        for robots_tag in all_robots:
            content = robots_tag.get("content", "").lower()
            self.metrics["meta_robots"] = content
            if "none" in content:
                self._add("On-Page", "Meta Robots: 'none'", SEVERITY["CRITICAL"],
                    "robots='none' blocks BOTH indexing AND link following",
                    "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                    "Change to 'index, follow' if page should appear in search results.",
                    {"content": content}, impact="Page completely invisible to search engines")
            elif "noindex" in content:
                self._add("On-Page", "Meta Robots: noindex", SEVERITY["CRITICAL"],
                    "noindex detected — page will be removed from Google index",
                    "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                    "Remove 'noindex' if this page should appear in search results.",
                    {"content": content})
            elif "nofollow" in content:
                self._add("On-Page", "Meta Robots: nofollow", SEVERITY["MEDIUM"],
                    "nofollow — links on this page won't pass PageRank",
                    "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag",
                    "Remove 'nofollow' from page-level robots unless intentional.\n"
                    "Use link-level rel='nofollow' for specific links instead.",
                    {"content": content})
            else:
                self._add("On-Page", "Meta Robots", SEVERITY["PASS"],
                    f"Meta robots: '{content}' — indexing allowed", "", "N/A")

    def check_open_graph(self):
        required = ["og:title", "og:description", "og:image", "og:url", "og:type"]
        found_tags = {}
        for meta in self.soup.find_all("meta", property=True):
            prop = meta.get("property", "")
            if prop.startswith("og:"):
                found_tags[prop] = meta.get("content", "")
        self.metrics["og_tags"] = found_tags
        missing = [t for t in required if t not in found_tags]

        if missing:
            self._add("On-Page", "Open Graph Tags — Missing", SEVERITY["MEDIUM"],
                f"Missing required OG tags: {', '.join(missing)}",
                "https://ogp.me/",
                "Add to <head>:\n"
                "<meta property='og:title' content='Your Page Title'>\n"
                "<meta property='og:description' content='Description 120-160 chars'>\n"
                "<meta property='og:image' content='https://domain.com/img.jpg'> (1200×630px)\n"
                "<meta property='og:url' content='https://domain.com/page/'>\n"
                "<meta property='og:type' content='website'>\n"
                "<meta property='og:site_name' content='Your Brand'>",
                {"missing": missing},
                impact="Poor social sharing preview reduces CTR from Facebook, LinkedIn, WhatsApp")
        else:
            og_image = found_tags.get("og:image", "")
            if og_image and "og:image:width" not in found_tags:
                self._add("On-Page", "OG Image Dimensions Missing", SEVERITY["LOW"],
                    "og:image missing width/height — may display incorrectly",
                    "https://ogp.me/",
                    "Add: <meta property='og:image:width' content='1200'>\n"
                    "<meta property='og:image:height' content='630'>\n"
                    "Recommended: 1200×630px (1.91:1 ratio)")
            self._add("On-Page", "Open Graph Tags", SEVERITY["PASS"],
                "All required Open Graph tags present", "", "N/A", {"tags": found_tags})

    def check_twitter_cards(self):
        tw_tags = {}
        for meta in self.soup.find_all("meta"):
            name = meta.get("name", "")
            if name.startswith("twitter:"):
                tw_tags[name] = meta.get("content", "")
        self.metrics["twitter_tags"] = tw_tags
        required = ["twitter:card", "twitter:title", "twitter:description"]
        missing = [t for t in required if t not in tw_tags]
        if missing:
            self._add("On-Page", "Twitter Card Tags", SEVERITY["LOW"],
                f"Missing Twitter Card tags: {', '.join(missing)}",
                "https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards",
                "Add to <head>:\n"
                "<meta name='twitter:card' content='summary_large_image'>\n"
                "<meta name='twitter:title' content='Page Title'>\n"
                "<meta name='twitter:description' content='Description'>\n"
                "<meta name='twitter:image' content='https://domain.com/img.jpg'>\n"
                "<meta name='twitter:site' content='@yourtwitterhandle'>")
        else:
            self._add("On-Page", "Twitter Card Tags", SEVERITY["PASS"],
                f"Twitter cards configured: {tw_tags.get('twitter:card', '')}", "", "N/A")

    def check_images(self):
        images = self.soup.find_all("img")
        total = len(images)
        missing_alt, empty_alt, missing_dims, generic_alt, bad_filenames = [], [], [], [], []
        generic_names = {"image", "img", "photo", "picture", "banner", "logo", "icon",
                         "screenshot", "image1", "image2", "untitled", "thumb", "thumbnail"}

        for img in images:
            src = img.get("src", "") or img.get("data-src", "") or img.get("data-lazy-src", "")
            alt = img.get("alt")
            if alt is None:
                missing_alt.append(src[:80] or "[no src]")
            elif alt.strip() == "":
                empty_alt.append(src[:80] or "[no src]")
            elif alt.strip().lower() in generic_names:
                generic_alt.append({"src": src[:60], "alt": alt.strip()})
            if not img.get("width") or not img.get("height"):
                missing_dims.append(src[:60] or "[no src]")
            if src:
                fname = src.split("/")[-1].split("?")[0].lower()
                if re.match(r'^(img|image|photo|dsc|screenshot|untitled|p\d+|img\d+)[\d_-]*\.(jpg|png|jpeg|gif|webp)$', fname):
                    bad_filenames.append(fname)

        self.metrics.update({
            "image_count": total,
            "images_missing_alt": len(missing_alt),
            "images_empty_alt": len(empty_alt),
        })

        if total == 0:
            self._add("On-Page", "Images — None Found", SEVERITY["LOW"],
                "No images on page",
                "https://developers.google.com/search/docs/appearance/google-images",
                "Add relevant images with descriptive alt text. Improves engagement and image search visibility.")
            return

        if missing_alt:
            self._add("On-Page", "Images — Missing Alt", SEVERITY["HIGH"],
                f"{len(missing_alt)}/{total} images missing alt attribute entirely",
                "https://developers.google.com/search/docs/appearance/google-images#use-descriptive-alt-text",
                "Add alt text to ALL images:\n"
                "<img src='product.jpg' alt='Blue wireless earbuds with noise cancellation'>\n"
                "Include target keywords naturally. Required for WCAG accessibility compliance.",
                {"count": len(missing_alt), "examples": missing_alt[:4]},
                impact="Missing alt = zero image SEO value + accessibility failure + possible ADA violation")
        if empty_alt:
            self._add("On-Page", "Images — Empty Alt", SEVERITY["MEDIUM"],
                f"{len(empty_alt)} images have empty alt=''",
                "https://developers.google.com/search/docs/appearance/google-images#use-descriptive-alt-text",
                "Use alt='' ONLY for purely decorative images (spacers, backgrounds).\n"
                "For all content images, write descriptive keyword-rich alt text.",
                {"count": len(empty_alt), "examples": empty_alt[:4]})
        if generic_alt:
            self._add("On-Page", "Images — Generic Alt Text", SEVERITY["MEDIUM"],
                f"{len(generic_alt)} images have generic/useless alt text",
                "https://developers.google.com/search/docs/appearance/google-images#use-descriptive-alt-text",
                "Replace generic alt with specific descriptions:\n"
                "❌ alt='image' → ✅ alt='handmade leather wallet for men'\n"
                "❌ alt='photo' → ✅ alt='CEO Jane Smith at the 2024 product launch'",
                {"examples": generic_alt[:4]})
        if missing_dims:
            self._add("On-Page", "Images — Missing Dimensions", SEVERITY["MEDIUM"],
                f"{len(missing_dims)} images missing width/height — causes layout shift",
                "https://web.dev/optimize-cls/",
                "Add explicit dimensions to prevent CLS (Core Web Vital):\n"
                "<img src='img.jpg' alt='...' width='1200' height='630' loading='lazy'>",
                {"count": len(missing_dims)},
                impact="Layout shift is a CLS Core Web Vital — directly affects ranking")
        if bad_filenames:
            self._add("On-Page", "Images — Generic Filenames", SEVERITY["LOW"],
                f"{len(bad_filenames)} images have non-descriptive filenames",
                "https://developers.google.com/search/docs/appearance/google-images",
                "Rename with descriptive, hyphenated slugs:\n"
                "❌ img001.jpg → ✅ blue-wireless-earbuds-review.jpg\n"
                "❌ DSC1234.png → ✅ team-photo-london-office-2024.jpg",
                {"examples": bad_filenames[:4]},
                impact="Descriptive filenames are an image search ranking signal")
        if not missing_alt and not empty_alt and not generic_alt:
            self._add("On-Page", "Image Alt Text", SEVERITY["PASS"],
                f"All {total} images have alt attributes", "", "N/A")

    def check_links(self):
        all_links = self.soup.find_all("a", href=True)
        internal, external, nofollow_ext, empty_text, http_internal = [], [], [], [], []

        for link in all_links:
            href = link.get("href", "").strip()
            text = link.get_text(strip=True)
            rel = link.get("rel", [])
            if isinstance(rel, str):
                rel = [rel]
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
                continue
            if href.startswith("http"):
                if self.base_domain in href:
                    internal.append({"href": href, "text": text[:60], "rel": rel})
                    if href.startswith("http://"):
                        http_internal.append(href)
                else:
                    external.append({"href": href, "text": text[:60], "rel": rel})
                    if any(r in rel for r in ["nofollow", "ugc", "sponsored"]):
                        nofollow_ext.append(href)
            elif href.startswith("/"):
                internal.append({"href": href, "text": text[:60], "rel": rel})
            if not text and not link.find("img"):
                empty_text.append(href[:60])

        dofollow_ext = [e for e in external if not any(r in e["rel"] for r in ["nofollow", "ugc", "sponsored"])]
        self.metrics.update({
            "internal_links": len(internal),
            "external_links": len(external),
            "total_links": len(all_links),
            "dofollow_external": len(dofollow_ext),
        })

        if len(internal) == 0:
            self._add("On-Page", "Internal Links — None", SEVERITY["HIGH"],
                "No internal links — Google cannot discover other pages",
                "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
                "Add 3-5+ internal links to relevant pages.\n"
                "Use keyword-rich anchor text. Link to cornerstone content, categories, related posts.",
                impact="No internal linking = no PageRank flow, poor crawlability")
        elif len(internal) < 3:
            self._add("On-Page", "Internal Links — Too Few", SEVERITY["MEDIUM"],
                f"Only {len(internal)} internal links — add more",
                "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
                "Add links to related content, parent categories, and related articles.",
                {"count": len(internal)})
        else:
            self._add("On-Page", "Internal Links", SEVERITY["PASS"],
                f"{len(internal)} internal links found", "", "N/A")

        if empty_text:
            self._add("On-Page", "Empty Anchor Text", SEVERITY["MEDIUM"],
                f"{len(empty_text)} links with no anchor text",
                "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
                "Add descriptive keyword-rich anchor text:\n"
                "❌ <a href='/products'>click here</a>\n"
                "✅ <a href='/products'>View our product catalog</a>",
                {"examples": empty_text[:5]},
                impact="Anchor text is a keyword relevance signal — empty = wasted SEO opportunity")

        if http_internal:
            self._add("On-Page", "Internal HTTP Links", SEVERITY["MEDIUM"],
                f"{len(http_internal)} internal links using http:// instead of https://",
                "https://developers.google.com/search/docs/crawling-indexing/https",
                "Update all internal links from http:// to https://. Prevents redirect chains.",
                {"examples": http_internal[:4]})

        if len(dofollow_ext) > 20:
            self._add("On-Page", "External Dofollow Links — Excessive", SEVERITY["MEDIUM"],
                f"{len(dofollow_ext)} dofollow external links — review for link equity leakage",
                "https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links",
                "Add rel='nofollow' to commercial/untrusted links.\n"
                "rel='sponsored' for paid links. rel='ugc' for user content.\n"
                "Only dofollow editorially endorsed resources.",
                {"dofollow": len(dofollow_ext), "nofollow": len(nofollow_ext)})

    def check_url_structure(self):
        url = self.url
        path = self.parsed_url.path
        length = len(url)
        self.metrics["url_length"] = length
        depth = len([p for p in path.split("/") if p])
        self.metrics["url_depth"] = depth
        issues, fixes = [], []

        if length > SEO_STANDARDS["max_url_length"]:
            issues.append(f"too long ({length} chars, max 100)")
            fixes.append("Shorten slug, remove stop words from URL")
        if "_" in path:
            issues.append("underscores detected (Google treats _ as word-joiner)")
            fixes.append("Replace underscores with hyphens: my_page → my-page")
        if path != path.lower():
            issues.append("uppercase letters detected")
            fixes.append("Force all URLs to lowercase at server level")
        if depth > 4:
            issues.append(f"{depth} folder levels deep (max 4 recommended)")
            fixes.append("Flatten URL structure for better crawl priority")
        stop_in_url = [w for w in re.findall(r'[a-z]+', path.lower())
                       if w in {"the", "a", "an", "and", "or", "but", "in", "on", "at"}]
        if len(stop_in_url) > 2:
            issues.append(f"stop words in URL: {', '.join(stop_in_url)}")
            fixes.append("Remove common stop words from URL slugs")

        if issues:
            self._add("On-Page", "URL Structure", SEVERITY["MEDIUM"],
                f"URL issues: {'; '.join(issues)}",
                "https://developers.google.com/search/docs/crawling-indexing/url-structure",
                "SEO URL format: https://domain.com/category/primary-keyword/\n"
                "Rules: lowercase, hyphens, max 4 folders, no stop words, descriptive slugs.\n"
                f"Fixes needed: {'; '.join(fixes)}",
                {"url": url, "depth": depth, "length": length},
                impact="Clean URLs improve CTR in SERPs and make link-sharing easier")
        else:
            self._add("On-Page", "URL Structure", SEVERITY["PASS"],
                f"URL is clean and SEO-friendly (depth: {depth} levels)", "", "N/A",
                {"url": url})

    def check_content(self):
        soup_copy = BeautifulSoup(self.html, "lxml")
        for tag in soup_copy(["script", "style", "noscript", "iframe"]):
            tag.decompose()
        for comment in soup_copy.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        text = re.sub(r'\s+', ' ', soup_copy.get_text(separator=" ", strip=True)).strip()
        words = [w for w in text.split() if len(w) > 1]
        word_count = len(words)
        self.metrics["word_count"] = word_count
        self.text_content = text

        if word_count < SEO_STANDARDS["content_min_words"]:
            self._add("On-Page", "Content — Thin", SEVERITY["HIGH"],
                f"Thin content: {word_count} words (minimum {SEO_STANDARDS['content_min_words']})",
                "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
                "Google's Helpful Content Update penalizes thin content.\n"
                "Target minimums: Blog posts: 800+ words. Landing pages: 500+ words. Pillar pages: 2000+ words.\n"
                "Add: FAQs, how-to sections, examples, data, expert insights, case studies.",
                {"word_count": word_count},
                impact="Thin content is a primary reason pages are not ranked or penalized")
        elif word_count < 600:
            self._add("On-Page", "Content — Shallow", SEVERITY["MEDIUM"],
                f"Content is shallow: {word_count} words",
                "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
                "For competitive keywords, aim for 1000-2000+ words.\n"
                "Analyze top-10 competitor pages and aim to be more comprehensive.",
                {"word_count": word_count})
        else:
            self._add("On-Page", "Content Length", SEVERITY["PASS"],
                f"Good content: {word_count} words", "", "N/A")

        # Keyword density check
        title = self.metrics.get("title", "")
        if title and word_count > 100:
            title_kws = [w.lower() for w in title.split() if w.lower() not in STOP_WORDS and len(w) > 3]
            text_lower = text.lower()
            for kw in title_kws[:2]:
                count = text_lower.count(kw)
                density = round((count / word_count) * 100, 2)
                if count < 2 and density < SEO_STANDARDS["ideal_keyword_density_min"]:
                    self._add("On-Page", "Keyword Density — Too Low", SEVERITY["MEDIUM"],
                        f"'{kw}' appears only {count}x ({density}%) — too sparse",
                        "https://moz.com/learn/seo/on-page-factors",
                        f"Include '{kw}' in: first paragraph, H2 subheadings, conclusion, alt text.\n"
                        f"Target 0.5-2.5% density. Current: {density}%",
                        {"keyword": kw, "count": count, "density": density})
                elif density > SEO_STANDARDS["ideal_keyword_density_max"]:
                    self._add("On-Page", "Keyword Stuffing Detected", SEVERITY["HIGH"],
                        f"'{kw}' appears {count}x ({density}%) — possible keyword stuffing",
                        "https://developers.google.com/search/docs/essentials/spam-policies",
                        f"Reduce '{kw}' usage. Use synonyms and LSI keywords instead.\n"
                        f"Target 0.5-2.5% density. Google penalizes keyword stuffing.",
                        {"keyword": kw, "count": count, "density": density},
                        impact="Keyword stuffing is a Google spam violation — can cause penalty")

        # First paragraph keyword check
        paragraphs = soup_copy.find_all("p")
        if paragraphs and title:
            first_para = paragraphs[0].get_text(strip=True).lower()
            title_kws = [w.lower() for w in title.split() if w.lower() not in STOP_WORDS and len(w) > 3]
            if title_kws and not any(kw in first_para for kw in title_kws[:2]):
                self._add("On-Page", "Keyword in Introduction", SEVERITY["MEDIUM"],
                    "Primary keyword not in first paragraph",
                    "https://moz.com/learn/seo/on-page-factors",
                    f"Include '{title_kws[0] if title_kws else ''}' in the first 100 words.\n"
                    "First-paragraph keyword placement is a strong on-page relevance signal.",
                    impact="Keyword in intro is a key on-page ranking factor")

        if len(paragraphs) < 3 and word_count > 200:
            self._add("On-Page", "Content Structure", SEVERITY["LOW"],
                f"Only {len(paragraphs)} paragraphs for {word_count} words",
                "https://web.dev/content-structure/",
                "Break content into short paragraphs (2-4 sentences). Add bullet points and numbered lists.")

    def check_structured_data(self):
        ld_scripts = self.soup.find_all("script", type="application/ld+json")
        microdata = self.soup.find_all(attrs={"itemtype": True})
        schema_types = []
        schema_errors = []

        for script in ld_scripts:
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for d in items:
                    stype = d.get("@type", "Unknown")
                    schema_types.extend(stype if isinstance(stype, list) else [stype])
            except json.JSONDecodeError as e:
                schema_errors.append(str(e)[:80])

        self.metrics["schema_types"] = schema_types

        if schema_errors:
            self._add("On-Page", "Structured Data — JSON Error", SEVERITY["HIGH"],
                f"Invalid JSON-LD: {'; '.join(schema_errors[:2])}",
                "https://search.google.com/test/rich-results",
                "Fix JSON syntax errors. Validate at: https://search.google.com/test/rich-results\n"
                "Common: missing quotes, trailing commas, unescaped characters.",
                {"errors": schema_errors[:3]},
                impact="Invalid JSON = zero rich result eligibility in SERPs")

        if not ld_scripts and not microdata:
            self._add("On-Page", "Structured Data — Missing", SEVERITY["MEDIUM"],
                "No structured data (Schema.org) found",
                "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data",
                "Add JSON-LD schema for your page type:\n"
                "- Blog/Article: Article or BlogPosting\n"
                "- Products: Product + AggregateRating\n"
                "- Local Business: LocalBusiness\n"
                "- FAQ section: FAQPage (enables FAQ rich results)\n"
                "- How-To: HowTo schema\n"
                "- Any page: BreadcrumbList\n"
                "Generator: https://technicalseo.com/tools/schema-markup-generator/",
                impact="Structured data enables rich results (stars, FAQ, images) — major CTR boost")
        else:
            text_lower = self.text_content.lower()
            recommendations = []
            if ("faq" in text_lower or "frequently asked" in text_lower) and "FAQPage" not in schema_types:
                recommendations.append("FAQPage (FAQ content detected)")
            if any(w in text_lower for w in ["price", "buy", "cart", "product"]) and "Product" not in schema_types:
                recommendations.append("Product schema (e-commerce content detected)")
            if recommendations:
                self._add("On-Page", "Structured Data — Enhancement", SEVERITY["LOW"],
                    f"Current schema: {', '.join(schema_types)}. Recommended additions: {', '.join(recommendations)}",
                    "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data",
                    f"Add these schemas to unlock additional rich results: {', '.join(recommendations)}",
                    {"current": schema_types, "recommended": recommendations})
            else:
                self._add("On-Page", "Structured Data", SEVERITY["PASS"],
                    f"Schema found: {', '.join(schema_types[:5])}", "", "N/A",
                    {"types": schema_types})

    def check_lang_and_locale(self):
        html_tag = self.soup.find("html")
        lang = html_tag.get("lang", "") if html_tag else ""
        self.metrics["html_lang"] = lang

        if not lang:
            self._add("On-Page", "HTML Lang — Missing", SEVERITY["MEDIUM"],
                "No lang attribute on <html> tag",
                "https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites",
                "Add: <html lang='en'> (or your language code)\n"
                "Common: en, en-US, fr, de, ar, ur, zh, es, it, pt\n"
                "Full list: https://www.w3schools.com/tags/ref_language_codes.asp",
                impact="Missing lang = wrong language detection, incorrect region targeting")
        else:
            if not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', lang):
                self._add("On-Page", "HTML Lang — Format", SEVERITY["LOW"],
                    f"Lang format may be incorrect: '{lang}'",
                    "https://www.ietf.org/rfc/rfc5646.txt",
                    "Use BCP 47 format: 'en', 'en-US', 'fr-FR', 'ar', 'ur'")
            else:
                self._add("On-Page", "HTML Lang", SEVERITY["PASS"],
                    f"HTML lang='{lang}'", "", "N/A")

        hreflang_tags = self.soup.find_all("link", rel="alternate", hreflang=True)
        if hreflang_tags:
            langs = [l.get("hreflang") for l in hreflang_tags]
            if "x-default" not in langs:
                self._add("On-Page", "Hreflang — x-default Missing", SEVERITY["MEDIUM"],
                    "Hreflang tags missing x-default fallback",
                    "https://developers.google.com/search/docs/specialty/international/localization",
                    "Add: <link rel='alternate' hreflang='x-default' href='https://domain.com/page/'>\n"
                    "Specifies fallback page for users not matching any specific language.",
                    {"langs": langs})
            else:
                self._add("On-Page", "Hreflang Tags", SEVERITY["PASS"],
                    f"Hreflang correct with x-default: {', '.join(langs[:5])}", "", "N/A")

    def check_social_and_misc(self):
        favicon = (self.soup.find("link", rel=lambda r: r and "icon" in (r if isinstance(r, list) else [r])) or
                   self.soup.find("link", attrs={"rel": "shortcut icon"}))
        if not favicon:
            self._add("On-Page", "Favicon — Missing", SEVERITY["LOW"],
                "No favicon found",
                "https://developers.google.com/search/docs/appearance/favicon-in-search",
                "Add to <head>:\n"
                "<link rel='icon' type='image/png' href='/favicon-32x32.png' sizes='32x32'>\n"
                "<link rel='apple-touch-icon' href='/apple-touch-icon.png' sizes='180x180'>")
        else:
            self._add("On-Page", "Favicon", SEVERITY["PASS"], "Favicon present", "", "N/A")

        bc_schema = any("BreadcrumbList" in str(t) for t in self.metrics.get("schema_types", []))
        bc_html = self.soup.find(class_=re.compile("breadcrumb", re.I))
        if not bc_schema and not bc_html:
            self._add("On-Page", "Breadcrumbs — Missing", SEVERITY["LOW"],
                "No breadcrumb navigation found",
                "https://developers.google.com/search/docs/appearance/structured-data/breadcrumb",
                "Add breadcrumbs: Home > Category > Page\n"
                "Plus BreadcrumbList JSON-LD schema for SERP display.\n"
                "Breadcrumbs appear in Google results and boost CTR.",
                impact="Breadcrumbs in SERPs increase visibility and CTR")

    def check_duplicate_content_signals(self):
        title = self.metrics.get("title", "")
        h1_texts = self.metrics.get("h1_texts", [])
        if title and h1_texts:
            h1 = h1_texts[0].strip().lower()
            if h1 == title.strip().lower():
                self._add("On-Page", "Title = H1 (Missed Opportunity)", SEVERITY["LOW"],
                    "Title and H1 are identical — missed keyword optimization",
                    "https://moz.com/learn/seo/on-page-factors",
                    "Use different but complementary copy:\n"
                    "Title: 'Best Running Shoes 2025 — SportBrand' (SERP-focused + brand)\n"
                    "H1: 'The Best Running Shoes for Every Runner' (user-focused headline)",
                    {"title": title, "h1": h1_texts[0]})

        paragraphs = [p.get_text(strip=True) for p in self.soup.find_all("p") if len(p.get_text(strip=True)) > 50]
        if paragraphs:
            hashes = [hashlib.md5(p.encode()).hexdigest() for p in paragraphs]
            dupes = len(hashes) - len(set(hashes))
            if dupes > 0:
                self._add("On-Page", "Duplicate Content Blocks", SEVERITY["MEDIUM"],
                    f"{dupes} duplicate paragraphs detected on this page",
                    "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
                    "Remove or rewrite repeated content blocks. Each section should be unique.",
                    {"duplicate_count": dupes})

    def check_word_to_code_ratio(self):
        html_size = len(self.html)
        text_size = len(self.text_content)
        if html_size > 0:
            ratio = round((text_size / html_size) * 100, 1)
            self.metrics["text_to_html_ratio"] = ratio
            if ratio < 5:
                self._add("On-Page", "Text-to-HTML Ratio — Critical", SEVERITY["HIGH"],
                    f"Critically low ratio: {ratio}% — almost no visible content detected",
                    "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
                    "Possible causes: JS-rendered content, excessive inline SVG/code, nearly empty page.\n"
                    "Fix: Add text content, reduce code bloat, implement SSR if using JavaScript framework.",
                    {"ratio": ratio, "html_kb": round(html_size/1024, 1)})
            elif ratio < 15:
                self._add("On-Page", "Text-to-HTML Ratio", SEVERITY["MEDIUM"],
                    f"Low text-to-HTML ratio: {ratio}%",
                    "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
                    "Reduce HTML bloat or add more textual content.",
                    {"ratio": ratio})
            else:
                self._add("On-Page", "Text-to-HTML Ratio", SEVERITY["PASS"],
                    f"Text-to-HTML ratio: {ratio}%", "", "N/A", {"ratio": ratio})

    # ── KEYWORD ANALYSIS ──────────────────────────────────────────────────────

    def analyze_keywords(self):
        if not self.text_content:
            return {}
        kw_data = extract_keywords(self.text_content)
        title = self.metrics.get("title", "")
        meta_desc = self.metrics.get("meta_description", "")
        keyword_ideas = generate_keyword_ideas(kw_data["primary_keywords"], title, meta_desc)
        primary_kws = kw_data["primary_keywords"][:5]
        h1_texts = self.metrics.get("h1_texts", [])
        h1_text = h1_texts[0].lower() if h1_texts else ""
        title_lower = title.lower()
        alignment = []
        for kw_info in primary_kws[:5]:
            kw = kw_info["keyword"]
            alignment.append({
                "keyword": kw,
                "density": kw_info["density"],
                "count": kw_info["count"],
                "in_title": kw in title_lower,
                "in_h1": kw in h1_text,
                "in_meta_desc": kw in meta_desc.lower(),
            })
        return {
            "primary_keywords": kw_data["primary_keywords"],
            "phrase_keywords": kw_data["bigrams"],
            "long_tail_phrases": kw_data["trigrams"],
            "keyword_ideas": keyword_ideas,
            "keyword_alignment": alignment,
            "total_words": kw_data["total_words"],
        }

    # ── SITE CRAWL ────────────────────────────────────────────────────────────

    def crawl_site(self, max_pages=20):
        visited = set()
        to_visit = [self.url]
        pages_data = []
        base = f"{self.scheme}://{self.base_domain}"

        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)
            try:
                start = time.time()
                resp = self.session.get(current_url, timeout=15, allow_redirects=True, verify=False)
                load_ms = round((time.time() - start) * 1000, 2)
                if "text/html" not in resp.headers.get("Content-Type", ""):
                    continue
                soup = BeautifulSoup(resp.text, "lxml")
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""
                meta_desc_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
                meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else ""
                h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
                canonical = soup.find("link", rel="canonical")
                canonical_href = canonical.get("href", "") if canonical else ""
                imgs = soup.find_all("img")
                missing_alt = sum(1 for i in imgs if i.get("alt") is None)
                robots_meta = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
                robots_content = robots_meta.get("content", "").lower() if robots_meta else "index, follow"

                page_issues = []
                if not title:
                    page_issues.append({"severity": "critical", "issue": "Missing title tag"})
                elif len(title) < 30:
                    page_issues.append({"severity": "high", "issue": f"Title too short ({len(title)} chars)"})
                elif len(title) > 60:
                    page_issues.append({"severity": "high", "issue": f"Title too long ({len(title)} chars)"})

                if not meta_desc:
                    page_issues.append({"severity": "high", "issue": "Missing meta description"})
                elif len(meta_desc) > 160:
                    page_issues.append({"severity": "medium", "issue": f"Meta desc too long ({len(meta_desc)} chars)"})

                if len(h1s) == 0:
                    page_issues.append({"severity": "critical", "issue": "No H1 tag"})
                elif len(h1s) > 1:
                    page_issues.append({"severity": "high", "issue": f"Multiple H1s ({len(h1s)})"})

                if not canonical_href:
                    page_issues.append({"severity": "high", "issue": "No canonical tag"})

                if missing_alt > 0:
                    page_issues.append({"severity": "medium", "issue": f"{missing_alt} images missing alt"})

                if "noindex" in robots_content:
                    page_issues.append({"severity": "critical", "issue": "noindex meta robots"})

                if resp.status_code != 200:
                    page_issues.append({"severity": "critical", "issue": f"HTTP {resp.status_code}"})

                if load_ms > 3000:
                    page_issues.append({"severity": "high", "issue": f"Slow: {load_ms}ms"})

                pages_data.append({
                    "url": current_url,
                    "status_code": resp.status_code,
                    "title": title,
                    "title_length": len(title),
                    "meta_description": meta_desc[:100],
                    "meta_description_length": len(meta_desc),
                    "h1_count": len(h1s),
                    "h1_text": h1s[0][:60] if h1s else "",
                    "canonical": canonical_href,
                    "load_time_ms": load_ms,
                    "images_total": len(imgs),
                    "images_missing_alt": missing_alt,
                    "robots": robots_content,
                    "issues": page_issues,
                    "issue_count": len(page_issues),
                })

                if len(visited) < max_pages:
                    for link in soup.find_all("a", href=True):
                        href = link.get("href", "").strip()
                        if href.startswith("/"):
                            full = base + href.split("?")[0].split("#")[0]
                            if full not in visited and full not in to_visit:
                                to_visit.append(full)
                        elif href.startswith(base):
                            clean = href.split("?")[0].split("#")[0]
                            if clean not in visited and clean not in to_visit:
                                to_visit.append(clean)
            except Exception as e:
                pages_data.append({
                    "url": current_url,
                    "error": str(e)[:100],
                    "issues": [{"severity": "critical", "issue": f"Crawl error: {str(e)[:80]}"}],
                    "issue_count": 1,
                })

        return pages_data

    # ── MASTER RUN ────────────────────────────────────────────────────────────

    def run(self):
        start_time = time.time()
        ok = self.fetch_page()

        if not ok:
            return {
                "url": self.url, "mode": self.mode,
                "error": self.metrics.get("fetch_error", "Failed to fetch page. Check URL and try again."),
                "metrics": self.metrics, "issues": [], "passes": [],
                "summary": {}, "keyword_analysis": {}, "site_pages": [],
            }

        # Technical checks
        self.check_https()
        self.check_ssl_certificate()
        self.check_redirects()
        self.check_status_code()
        self.check_page_size()
        self.check_load_time()
        self.check_robots_txt()
        self.check_sitemap()
        self.check_response_headers()
        self.check_render_blocking()
        self.check_mobile_friendly()
        self.check_page_speed_indicators()
        self.check_page_experience()
        self.check_javascript_rendering()
        self.check_page_freshness()

        # On-Page checks
        self.check_title_tag()
        self.check_meta_description()
        self.check_headings()
        self.check_canonical()
        self.check_meta_robots()
        self.check_open_graph()
        self.check_twitter_cards()
        self.check_images()
        self.check_links()
        self.check_url_structure()
        self.check_content()
        self.check_structured_data()
        self.check_lang_and_locale()
        self.check_social_and_misc()
        self.check_duplicate_content_signals()
        self.check_word_to_code_ratio()

        # Keyword analysis (single page)
        keyword_analysis = {}
        if self.mode == "single":
            keyword_analysis = self.analyze_keywords()

        # Site crawl
        site_pages = []
        if self.mode == "site":
            site_pages = self.crawl_site(max_pages=20)

        duration = round(time.time() - start_time, 2)

        sev_counts = defaultdict(int)
        for issue in self.issues:
            sev_counts[issue["severity"]] += 1

        score = max(0, 100
                    - sev_counts.get("critical", 0) * 15
                    - sev_counts.get("high", 0) * 7
                    - sev_counts.get("medium", 0) * 3
                    - sev_counts.get("low", 0) * 1)

        grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 45 else "F"

        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

        return {
            "url": self.url,
            "mode": self.mode,
            "audit_time": datetime.utcnow().isoformat(),
            "audit_duration_s": duration,
            "metrics": self.metrics,
            "issues": sorted(self.issues, key=lambda x: sev_order.get(x["severity"], 5)),
            "passes": self.passes,
            "keyword_analysis": keyword_analysis,
            "site_pages": site_pages,
            "summary": {
                "seo_score": score,
                "grade": grade,
                "total_checks": len(self.issues) + len(self.passes),
                "issues_found": len(self.issues),
                "passes": len(self.passes),
                "critical": sev_counts.get("critical", 0),
                "high": sev_counts.get("high", 0),
                "medium": sev_counts.get("medium", 0),
                "low": sev_counts.get("low", 0),
                "info": sev_counts.get("info", 0),
            }
        }


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    mode = sys.argv[2] if len(sys.argv) > 2 else "single"
    result = SEOCrawler(url, mode).run()
    print(json.dumps(result, indent=2))
