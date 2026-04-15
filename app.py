import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from crawler import SEOCrawler

app = Flask(__name__)
CORS(app)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Expert SEO Audit Tool — Zaman Hassan</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#080c10;--surface:#0d1117;--card:#111820;--border:#1e2d3d;--border2:#243447;
  --accent:#00d4aa;--accent2:#0088ff;--accent3:#ff6b35;--accent4:#a855f7;
  --red:#ff3b5c;--yellow:#fbbf24;--green:#00d4aa;--blue:#0088ff;
  --text:#e6edf3;--muted:#7d8fa0;--faint:#3d5068;
  --crit:#ff3b5c;--high:#ff6b35;--med:#fbbf24;--low:#0088ff;--pass:#00d4aa;
  --r:10px;--r2:6px;
}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:'Outfit',sans-serif;min-height:100vh;line-height:1.6;overflow-x:hidden}

/* ── GRID BG ── */
body::before{
  content:'';position:fixed;inset:0;
  background-image:linear-gradient(rgba(0,212,170,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,170,.03) 1px,transparent 1px);
  background-size:40px 40px;pointer-events:none;z-index:0;
}

/* ── HEADER ── */
header{
  position:relative;z-index:10;
  background:linear-gradient(180deg,rgba(0,212,170,.06) 0%,transparent 100%);
  border-bottom:1px solid var(--border);padding:0 32px;
}
.header-inner{max-width:1280px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:68px;gap:16px}
.logo{display:flex;align-items:center;gap:12px;text-decoration:none}
.logo-icon{width:36px;height:36px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.logo-text{display:flex;flex-direction:column;line-height:1.1}
.logo-title{font-size:15px;font-weight:700;color:var(--text);letter-spacing:-.3px}
.logo-sub{font-size:11px;color:var(--accent);font-weight:500;letter-spacing:.5px;text-transform:uppercase}
.header-contact{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted);background:var(--card);border:1px solid var(--border);border-radius:6px;padding:6px 14px;text-decoration:none;transition:.2s}
.header-contact:hover{border-color:var(--accent);color:var(--accent)}
.header-contact svg{width:14px;height:14px;flex-shrink:0}

/* ── MAIN ── */
main{position:relative;z-index:1;max-width:1280px;margin:0 auto;padding:40px 32px 80px}

/* ── HERO ── */
.hero{text-align:center;padding:48px 0 40px}
.hero-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(0,212,170,.08);border:1px solid rgba(0,212,170,.25);color:var(--accent);font-size:12px;font-weight:600;letter-spacing:.8px;text-transform:uppercase;padding:6px 16px;border-radius:100px;margin-bottom:24px}
.hero-badge span{width:6px;height:6px;border-radius:50%;background:var(--accent);display:inline-block;animation:pulse 2s infinite}
.hero h1{font-size:clamp(28px,4vw,48px);font-weight:800;line-height:1.15;letter-spacing:-1px;margin-bottom:16px}
.hero h1 em{font-style:normal;background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero p{font-size:16px;color:var(--muted);max-width:580px;margin:0 auto 36px}

/* ── MODE TOGGLE ── */
.mode-toggle{display:flex;background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:5px;gap:5px;width:fit-content;margin:0 auto 28px}
.mode-btn{padding:10px 28px;border-radius:7px;border:none;cursor:pointer;font-family:'Outfit',sans-serif;font-size:14px;font-weight:600;transition:.2s;display:flex;align-items:center;gap:8px;color:var(--muted);background:transparent}
.mode-btn.active{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;box-shadow:0 4px 16px rgba(0,212,170,.3)}
.mode-btn:hover:not(.active){color:var(--text);background:var(--border)}

/* ── INPUT BOX ── */
.input-area{background:var(--card);border:1px solid var(--border2);border-radius:var(--r);padding:6px 6px 6px 20px;display:flex;align-items:center;gap:10px;max-width:780px;margin:0 auto;transition:.3s}
.input-area:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px rgba(0,212,170,.12)}
.input-area input{flex:1;background:transparent;border:none;outline:none;font-size:16px;font-family:'Outfit',sans-serif;color:var(--text);min-width:0}
.input-area input::placeholder{color:var(--faint)}
.audit-btn{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#000;border:none;border-radius:7px;padding:12px 28px;font-size:14px;font-weight:700;font-family:'Outfit',sans-serif;cursor:pointer;transition:.2s;white-space:nowrap;display:flex;align-items:center;gap:8px}
.audit-btn:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(0,212,170,.4)}
.audit-btn:disabled{opacity:.5;cursor:not-allowed;transform:none}

/* ── LOADING ── */
#loading{display:none;text-align:center;padding:80px 20px}
.spinner{width:48px;height:48px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 24px}
.loading-text{font-size:15px;color:var(--muted);animation:fade 1.5s ease-in-out infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
@keyframes fade{0%,100%{opacity:.5}50%{opacity:1}}
@keyframes slideUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
@keyframes countUp{from{opacity:0;transform:scale(.8)}to{opacity:1;transform:scale(1)}}

/* ── RESULTS ── */
#results{display:none;animation:slideUp .4s ease}

/* ── SCORE SECTION ── */
.score-section{display:grid;grid-template-columns:220px 1fr;gap:24px;margin-bottom:28px;align-items:center}
.score-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:28px;text-align:center;position:relative;overflow:hidden}
.score-card::before{content:'';position:absolute;inset:0;background:radial-gradient(circle at 50% 0%,rgba(0,212,170,.07),transparent 70%);pointer-events:none}
.score-ring{position:relative;width:130px;height:130px;margin:0 auto 12px}
.score-ring svg{transform:rotate(-90deg)}
.score-ring .track{stroke:var(--border);fill:none;stroke-width:10}
.score-ring .fill{fill:none;stroke-width:10;stroke-linecap:round;transition:stroke-dashoffset 1.2s cubic-bezier(.22,1,.36,1)}
.score-num{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}
.score-num .num{font-size:34px;font-weight:800;font-family:'DM Mono',monospace;line-height:1}
.score-num .grade{font-size:13px;color:var(--muted);font-weight:600;margin-top:2px}
.score-label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;font-weight:600}

.meta-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px}
.meta-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:16px;display:flex;flex-direction:column;gap:4px}
.meta-card .label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;font-weight:600}
.meta-card .value{font-size:18px;font-weight:700;font-family:'DM Mono',monospace;line-height:1.2}
.meta-card .sub{font-size:11px;color:var(--muted)}

/* ── SEVERITY PILLS ── */
.severity-pills{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:28px}
.pill{display:flex;align-items:center;gap:8px;padding:10px 18px;border-radius:100px;cursor:pointer;border:1.5px solid transparent;transition:.2s;font-weight:600;font-size:13px}
.pill:hover{transform:translateY(-2px)}
.pill.active{border-color:currentColor}
.pill-crit{background:rgba(255,59,92,.1);color:var(--crit)}
.pill-high{background:rgba(255,107,53,.1);color:var(--high)}
.pill-med{background:rgba(251,191,36,.1);color:var(--med)}
.pill-low{background:rgba(0,136,255,.1);color:var(--low)}
.pill-pass{background:rgba(0,212,170,.1);color:var(--pass)}
.pill-count{background:rgba(255,255,255,.1);border-radius:100px;padding:1px 8px;font-size:12px;font-family:'DM Mono',monospace}

/* ── FILTER BAR ── */
.filter-bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px;align-items:center}
.filter-label{font-size:12px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-right:4px}
.cat-btn{padding:6px 16px;border-radius:100px;border:1px solid var(--border);background:transparent;color:var(--muted);font-size:12px;font-weight:600;cursor:pointer;transition:.2s;font-family:'Outfit',sans-serif}
.cat-btn.active,.cat-btn:hover{background:var(--border);color:var(--text)}
.cat-btn.active{border-color:var(--accent2);color:var(--accent2)}

/* ── ISSUE CARDS ── */
.issues-list{display:flex;flex-direction:column;gap:10px;margin-bottom:32px}
.issue-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);overflow:hidden;transition:.2s}
.issue-card:hover{border-color:var(--border2);transform:translateY(-1px)}
.issue-header{display:flex;align-items:flex-start;gap:14px;padding:16px 18px;cursor:pointer}
.sev-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:5px}
.sev-crit{background:var(--crit);box-shadow:0 0 8px rgba(255,59,92,.5)}
.sev-high{background:var(--high);box-shadow:0 0 8px rgba(255,107,53,.4)}
.sev-med{background:var(--med);box-shadow:0 0 8px rgba(251,191,36,.4)}
.sev-low{background:var(--low);box-shadow:0 0 8px rgba(0,136,255,.4)}
.sev-pass{background:var(--pass);box-shadow:0 0 8px rgba(0,212,170,.4)}
.issue-main{flex:1;min-width:0}
.issue-top{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px}
.issue-check{font-size:13px;font-weight:700;color:var(--text)}
.issue-cat{font-size:11px;padding:2px 9px;border-radius:4px;font-weight:600;background:var(--border);color:var(--muted)}
.issue-sev-badge{font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.badge-critical{background:rgba(255,59,92,.15);color:var(--crit)}
.badge-high{background:rgba(255,107,53,.15);color:var(--high)}
.badge-medium{background:rgba(251,191,36,.15);color:var(--med)}
.badge-low{background:rgba(0,136,255,.15);color:var(--low)}
.badge-pass{background:rgba(0,212,170,.15);color:var(--pass)}
.issue-msg{font-size:13px;color:var(--muted);line-height:1.5}
.issue-chevron{width:18px;height:18px;color:var(--faint);flex-shrink:0;margin-top:3px;transition:transform .25s}
.issue-card.open .issue-chevron{transform:rotate(180deg)}
.issue-body{display:none;padding:0 18px 18px 42px;border-top:1px solid var(--border);padding-top:16px}
.issue-card.open .issue-body{display:block}
.detail-row{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.detail-row:last-child{margin-bottom:0}
.detail-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--faint)}
.detail-content{font-size:13px;line-height:1.7;color:var(--muted);white-space:pre-wrap;font-family:'DM Mono',monospace;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:10px 14px}
.detail-solution{font-size:13px;line-height:1.7;color:var(--text)}
.detail-impact{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--high);background:rgba(255,107,53,.08);border:1px solid rgba(255,107,53,.2);border-radius:6px;padding:6px 12px}
.detail-link{display:inline-flex;align-items:center;gap:6px;color:var(--accent2);text-decoration:none;font-size:12px;font-weight:600;margin-top:8px}
.detail-link:hover{text-decoration:underline}

/* ── PASS SECTION ── */
.pass-section{margin-top:24px}
.pass-toggle{display:flex;align-items:center;gap:10px;cursor:pointer;padding:12px 18px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);color:var(--pass);font-size:14px;font-weight:600;transition:.2s;user-select:none}
.pass-toggle:hover{border-color:var(--pass);background:rgba(0,212,170,.04)}
.pass-list{display:none;padding:16px 0 0;display:flex;flex-direction:column;gap:8px}
.pass-list.visible{display:flex}
.pass-item{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;background:rgba(0,212,170,.04);border:1px solid rgba(0,212,170,.1);border-radius:var(--r2)}
.pass-item-text{font-size:13px;color:var(--muted)}
.pass-item-check{font-size:12px;font-weight:700;color:var(--pass)}

/* ── KEYWORD PANEL ── */
.kw-panel{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:24px;margin-bottom:28px}
.kw-panel h3{font-size:16px;font-weight:700;margin-bottom:20px;display:flex;align-items:center;gap:10px}
.kw-panel h3 span{font-size:11px;font-weight:600;padding:3px 10px;border-radius:4px;background:rgba(168,85,247,.12);color:var(--accent4);letter-spacing:.4px;text-transform:uppercase}
.kw-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.kw-col h4{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--faint);margin-bottom:12px}
.kw-table{width:100%;border-collapse:collapse}
.kw-table th{font-size:11px;font-weight:600;color:var(--faint);text-transform:uppercase;letter-spacing:.5px;padding:6px 8px;text-align:left;border-bottom:1px solid var(--border)}
.kw-table td{font-size:13px;padding:8px 8px;border-bottom:1px solid rgba(30,45,61,.5);font-family:'DM Mono',monospace}
.kw-table tr:last-child td{border-bottom:none}
.kw-density{font-size:11px;color:var(--muted)}
.kw-check{display:inline-block;width:18px;height:18px;border-radius:4px;text-align:center;line-height:18px;font-size:10px;font-weight:700}
.kw-yes{background:rgba(0,212,170,.15);color:var(--green)}
.kw-no{background:rgba(255,59,92,.1);color:var(--red)}
.kw-align{margin-top:20px}
.kw-align h4{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--faint);margin-bottom:12px}
.phrase-list{display:flex;flex-direction:column;gap:6px}
.phrase-item{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--surface);border:1px solid var(--border);border-radius:6px}
.phrase-text{font-size:13px;font-family:'DM Mono',monospace}
.phrase-count{font-size:11px;color:var(--muted);background:var(--border);border-radius:4px;padding:2px 7px}
.ideas-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin-top:16px}
.idea-chip{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:8px 12px;font-size:12px;color:var(--muted);font-family:'DM Mono',monospace;cursor:pointer;transition:.2s}
.idea-chip:hover{border-color:var(--accent4);color:var(--accent4)}

/* ── SITE CRAWL TABLE ── */
.site-panel{margin-bottom:28px}
.site-panel h3{font-size:16px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:10px}
.site-panel h3 em{font-size:12px;font-weight:600;font-style:normal;padding:3px 10px;border-radius:4px;background:rgba(0,136,255,.1);color:var(--blue)}
.site-table-wrap{overflow-x:auto;border-radius:var(--r);border:1px solid var(--border)}
.site-table{width:100%;border-collapse:collapse;font-size:12px}
.site-table th{background:var(--surface);padding:10px 14px;text-align:left;font-size:11px;font-weight:700;color:var(--faint);text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;border-bottom:1px solid var(--border)}
.site-table td{padding:10px 14px;border-bottom:1px solid rgba(30,45,61,.5);vertical-align:middle}
.site-table tr:last-child td{border-bottom:none}
.site-table tr:hover td{background:rgba(255,255,255,.02)}
.site-url{max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:'DM Mono',monospace;font-size:11px;color:var(--accent2)}
.site-status{font-family:'DM Mono',monospace;font-weight:700;font-size:12px}
.ok{color:var(--green)}.err{color:var(--red)}.warn{color:var(--yellow)}
.site-issues-cell{display:flex;flex-wrap:wrap;gap:4px}
.site-issue-chip{font-size:10px;padding:2px 7px;border-radius:4px;font-weight:600;white-space:nowrap}
.sc-crit{background:rgba(255,59,92,.12);color:var(--crit)}
.sc-high{background:rgba(255,107,53,.12);color:var(--high)}
.sc-med{background:rgba(251,191,36,.12);color:var(--med)}
.sc-pass{background:rgba(0,212,170,.1);color:var(--pass)}
.issue-count-badge{display:inline-block;min-width:22px;height:22px;border-radius:100px;text-align:center;line-height:22px;font-size:11px;font-weight:700;padding:0 6px}
.count-crit{background:rgba(255,59,92,.15);color:var(--crit)}
.count-high{background:rgba(255,107,53,.15);color:var(--high)}
.count-ok{background:rgba(0,212,170,.1);color:var(--pass)}

/* ── DASHBOARD METRICS ── */
.dashboard{display:grid;grid-template-columns:repeat(auto-fill,minmax(165px,1fr));gap:12px;margin-bottom:28px}
.dash-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:16px 18px}
.dash-card .d-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--faint);margin-bottom:6px}
.dash-card .d-val{font-size:20px;font-weight:800;font-family:'DM Mono',monospace;line-height:1}
.dash-card .d-sub{font-size:11px;color:var(--muted);margin-top:4px}

/* ── ERROR ── */
.error-box{background:rgba(255,59,92,.06);border:1px solid rgba(255,59,92,.25);border-radius:var(--r);padding:24px;text-align:center;color:var(--crit);margin-top:40px}
.error-box h3{font-size:18px;margin-bottom:8px}
.error-box p{font-size:14px;color:var(--muted)}

/* ── FOOTER ── */
footer{position:relative;z-index:1;border-top:1px solid var(--border);padding:24px 32px;text-align:center}
.footer-inner{max-width:1280px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.footer-brand{font-size:13px;color:var(--muted)}
.footer-brand strong{color:var(--text)}
.footer-contact{display:flex;align-items:center;gap:16px}
.footer-link{font-size:13px;color:var(--muted);text-decoration:none;display:flex;align-items:center;gap:6px;transition:.2s}
.footer-link:hover{color:var(--accent)}

/* ── SECTION LABELS ── */
.section-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px}
.section-title{font-size:15px;font-weight:700;color:var(--text)}
.section-count{font-size:12px;color:var(--muted);font-family:'DM Mono',monospace}

/* ── RESPONSIVE ── */
@media(max-width:768px){
  main{padding:24px 16px 60px}
  header{padding:0 16px}
  .hero{padding:32px 0 28px}
  .score-section{grid-template-columns:1fr;justify-items:center}
  .kw-grid{grid-template-columns:1fr}
  .input-area{padding:6px 6px 6px 14px}
  .input-area input{font-size:14px}
  .footer-inner{flex-direction:column;text-align:center}
  .mode-btn{padding:9px 18px;font-size:13px}
}
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <a href="#" class="logo">
      <div class="logo-icon">🔍</div>
      <div class="logo-text">
        <span class="logo-title">Expert SEO Audit Tool</span>
        <span class="logo-sub">by Zaman Hassan</span>
      </div>
    </a>
    <a href="#contact" class="header-contact">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.01 1.18 2 2 0 012 0h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 14.92v2z"/></svg>
      +92 308 2696942
    </a>
  </div>
</header>

<main>
  <section class="hero">
    <div class="hero-badge">
      <span></span>
      Full-Spectrum SEO Audit Engine
    </div>
    <h1>Audit Any URL for <em>Every</em><br>SEO Issue That Matters</h1>
    <p>50+ technical + on-page checks, keyword analysis, schema validation, Core Web Vitals signals — with exact fixes for every problem found.</p>

    <div class="mode-toggle">
      <button class="mode-btn active" id="btn-single" onclick="setMode('single')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
        Single Page Audit
      </button>
      <button class="mode-btn" id="btn-site" onclick="setMode('site')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
        Crawl Full Website
      </button>
    </div>

    <div class="input-area">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3d5068" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="url" id="urlInput" placeholder="https://yourwebsite.com" autocomplete="off" onkeypress="if(event.key==='Enter')runAudit()">
      <button class="audit-btn" id="auditBtn" onclick="runAudit()">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/></svg>
        Run Audit
      </button>
    </div>
    <div id="mode-hint" style="font-size:12px;color:var(--muted);margin-top:10px">Single page — audits one URL with keyword analysis</div>
  </section>

  <div id="loading">
    <div class="spinner"></div>
    <p class="loading-text" id="loadingMsg">Initializing audit engine…</p>
  </div>

  <div id="results"></div>
</main>

<footer id="contact">
  <div class="footer-inner">
    <div class="footer-brand">
      <strong>Expert SEO Audit Tool</strong> — by Zaman Hassan
    </div>
    <div class="footer-contact">
      <a href="tel:+923082696942" class="footer-link">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.01 1.18 2 2 0 012 0h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 14.92v2z"/></svg>
        +92 308 2696942
      </a>
      <a href="https://github.com/zamanhassan555/SEOauditer" class="footer-link" target="_blank">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.44 9.8 8.2 11.39.6.11.82-.26.82-.58v-2.03c-3.34.73-4.04-1.61-4.04-1.61-.54-1.37-1.33-1.74-1.33-1.74-1.09-.74.08-.73.08-.73 1.2.08 1.84 1.23 1.84 1.23 1.07 1.83 2.8 1.3 3.49 1 .1-.78.42-1.3.76-1.6-2.67-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.12-.3-.54-1.52.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 013-.4c1.02.005 2.04.14 3 .4 2.28-1.55 3.29-1.23 3.29-1.23.66 1.66.24 2.88.12 3.18.77.84 1.23 1.91 1.23 3.22 0 4.61-2.8 5.63-5.48 5.92.43.37.81 1.1.81 2.22v3.29c0 .32.22.7.83.58C20.56 21.8 24 17.3 24 12c0-6.63-5.37-12-12-12z"/></svg>
        GitHub
      </a>
    </div>
  </div>
</footer>

<script>
let currentMode = 'single';
const loadingMsgs = [
  'Fetching page headers and SSL certificate…',
  'Analysing robots.txt and sitemap…',
  'Checking title, meta description, headings…',
  'Scanning images, links, and structured data…',
  'Running keyword density analysis…',
  'Validating canonical, hreflang, Open Graph…',
  'Scoring 50+ SEO checks…',
  'Building your full audit report…',
];

function setMode(mode) {
  currentMode = mode;
  document.getElementById('btn-single').classList.toggle('active', mode === 'single');
  document.getElementById('btn-site').classList.toggle('active', mode === 'site');
  const hint = document.getElementById('mode-hint');
  hint.textContent = mode === 'single'
    ? 'Single page — audits one URL with full keyword analysis'
    : 'Site crawl — discovers and audits up to 20 pages of your website';
}

async function runAudit() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) { alert('Please enter a URL to audit.'); return; }

  const btn = document.getElementById('auditBtn');
  btn.disabled = true;
  btn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation:spin 1s linear infinite"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.73-8.06"/></svg> Auditing…';

  document.getElementById('loading').style.display = 'block';
  document.getElementById('results').style.display = 'none';
  document.getElementById('results').innerHTML = '';

  let msgIdx = 0;
  const msgEl = document.getElementById('loadingMsg');
  const msgTimer = setInterval(() => {
    msgEl.textContent = loadingMsgs[msgIdx % loadingMsgs.length];
    msgIdx++;
  }, 1800);

  try {
    const resp = await fetch('/audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, mode: currentMode }),
    });
    const data = await resp.json();
    clearInterval(msgTimer);
    renderResults(data);
  } catch (e) {
    clearInterval(msgTimer);
    document.getElementById('results').innerHTML = `
      <div class="error-box">
        <h3>⚠️ Audit Failed</h3>
        <p>${e.message || 'Network error. Please try again.'}</p>
      </div>`;
    document.getElementById('results').style.display = 'block';
  }

  document.getElementById('loading').style.display = 'none';
  btn.disabled = false;
  btn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="13 17 18 12 13 7"/><polyline points="6 17 11 12 6 7"/></svg> Run Audit';
}

/* ─── SEVERITY FILTER STATE ─── */
let activeSev = null;
let activeCat = 'All';

function renderResults(data) {
  const r = document.getElementById('results');
  r.style.display = 'block';

  if (data.error) {
    r.innerHTML = `<div class="error-box"><h3>⚠️ Could Not Fetch URL</h3><p>${data.error}</p></div>`;
    return;
  }

  const s = data.summary || {};
  const m = data.metrics || {};
  const issues = data.issues || [];
  const passes = data.passes || [];
  const kw = data.keyword_analysis || {};
  const pages = data.site_pages || [];
  const score = s.seo_score || 0;
  const grade = s.grade || 'F';

  // Score color
  const scoreColor = score >= 75 ? '#00d4aa' : score >= 50 ? '#fbbf24' : '#ff3b5c';
  const circumference = 2 * Math.PI * 54;
  const dashOffset = circumference - (score / 100) * circumference;

  // Grade label
  const gradeLabel = { A: 'Excellent', B: 'Good', C: 'Needs Work', D: 'Poor', F: 'Critical' }[grade] || '';

  let html = '';

  // ── SCORE + META ──
  html += `
  <div class="score-section">
    <div class="score-card">
      <div class="score-ring">
        <svg width="130" height="130" viewBox="0 0 130 130">
          <circle class="track" cx="65" cy="65" r="54"/>
          <circle class="fill" cx="65" cy="65" r="54"
            stroke="${scoreColor}"
            stroke-dasharray="${circumference}"
            stroke-dashoffset="${dashOffset}"
            id="scoreCircle"/>
        </svg>
        <div class="score-num">
          <div class="num" style="color:${scoreColor}">${score}</div>
          <div class="grade">${grade} — ${gradeLabel}</div>
        </div>
      </div>
      <div class="score-label">SEO Health Score</div>
    </div>
    <div class="meta-grid">
      <div class="meta-card">
        <div class="label">Load Time</div>
        <div class="value" style="color:${m.load_time_ms < 800 ? '#00d4aa' : m.load_time_ms < 3000 ? '#fbbf24' : '#ff3b5c'}">${m.load_time_ms ? m.load_time_ms + 'ms' : 'N/A'}</div>
        <div class="sub">TTFB</div>
      </div>
      <div class="meta-card">
        <div class="label">Status</div>
        <div class="value" style="color:${m.status_code === 200 ? '#00d4aa' : '#ff3b5c'}">${m.status_code || 'N/A'}</div>
        <div class="sub">HTTP status</div>
      </div>
      <div class="meta-card">
        <div class="label">Word Count</div>
        <div class="value">${m.word_count || 0}</div>
        <div class="sub">min 300</div>
      </div>
      <div class="meta-card">
        <div class="label">Page Size</div>
        <div class="value">${m.content_length_kb || 0}<span style="font-size:12px;font-weight:400"> KB</span></div>
        <div class="sub">HTML weight</div>
      </div>
      <div class="meta-card">
        <div class="label">Title</div>
        <div class="value" style="color:${m.title_length >= 30 && m.title_length <= 60 ? '#00d4aa' : '#fbbf24'}">${m.title_length || 0}<span style="font-size:12px;font-weight:400"> chr</span></div>
        <div class="sub">30–60 ideal</div>
      </div>
      <div class="meta-card">
        <div class="label">Images</div>
        <div class="value">${m.image_count || 0}</div>
        <div class="sub">${m.images_missing_alt || 0} missing alt</div>
      </div>
      <div class="meta-card">
        <div class="label">Int. Links</div>
        <div class="value">${m.internal_links || 0}</div>
        <div class="sub">${m.external_links || 0} external</div>
      </div>
      <div class="meta-card">
        <div class="label">Redirects</div>
        <div class="value" style="color:${m.redirect_count === 0 ? '#00d4aa' : '#fbbf24'}">${m.redirect_count || 0}</div>
        <div class="sub">hop${m.redirect_count !== 1 ? 's' : ''}</div>
      </div>
      ${m.ssl_expiry_days !== undefined ? `
      <div class="meta-card">
        <div class="label">SSL Expiry</div>
        <div class="value" style="color:${m.ssl_expiry_days > 30 ? '#00d4aa' : '#ff3b5c'}">${m.ssl_expiry_days}d</div>
        <div class="sub">${m.ssl_expiry_date || ''}</div>
      </div>` : ''}
      ${m.schema_types && m.schema_types.length ? `
      <div class="meta-card">
        <div class="label">Schema</div>
        <div class="value" style="font-size:13px;line-height:1.3">${m.schema_types.slice(0,2).join(', ')}</div>
        <div class="sub">${m.schema_types.length} type${m.schema_types.length !== 1 ? 's' : ''}</div>
      </div>` : ''}
      ${m.html_lang ? `
      <div class="meta-card">
        <div class="label">Lang</div>
        <div class="value">${m.html_lang}</div>
        <div class="sub">HTML lang attr</div>
      </div>` : ''}
    </div>
  </div>`;

  // ── SEVERITY PILLS ──
  html += `
  <div class="severity-pills">
    ${buildPill('critical', s.critical || 0, 'pill-crit', '🔴 Critical')}
    ${buildPill('high', s.high || 0, 'pill-high', '🟠 High')}
    ${buildPill('medium', s.medium || 0, 'pill-med', '🟡 Medium')}
    ${buildPill('low', s.low || 0, 'pill-low', '🔵 Low')}
    ${buildPill('pass', s.passes || 0, 'pill-pass', '✅ Passed')}
  </div>`;

  // ── FILTER BAR ──
  const cats = ['All', ...new Set(issues.map(i => i.category))];
  html += `<div class="filter-bar">
    <span class="filter-label">Filter:</span>
    ${cats.map(c => `<button class="cat-btn${c === 'All' ? ' active' : ''}" onclick="filterCat('${c}',this)">${c}</button>`).join('')}
  </div>`;

  // ── ISSUES LIST ──
  html += `<div class="section-head">
    <span class="section-title">Issues Found</span>
    <span class="section-count">${issues.length} issue${issues.length !== 1 ? 's' : ''} · ${passes.length} passed</span>
  </div>`;
  html += `<div class="issues-list" id="issuesList">`;
  issues.forEach((issue, idx) => {
    html += buildIssueCard(issue, idx);
  });
  html += `</div>`;

  // ── KEYWORD ANALYSIS ──
  if (data.mode === 'single' && kw.primary_keywords && kw.primary_keywords.length) {
    html += buildKeywordPanel(kw);
  }

  // ── SITE CRAWL ──
  if (data.mode === 'site' && pages.length) {
    html += buildSiteTable(pages);
  }

  // ── PASSES ──
  if (passes.length) {
    html += `
    <div class="pass-section">
      <div class="pass-toggle" onclick="togglePasses(this)">
        <span>✅</span>
        <span>${passes.length} checks passed — click to expand</span>
        <span style="margin-left:auto;font-size:12px;color:var(--faint)">▼</span>
      </div>
      <div class="pass-list" id="passList">
        ${passes.map(p => `
          <div class="pass-item">
            <span class="pass-item-check">✓</span>
            <div>
              <div style="font-size:12px;font-weight:700;color:var(--text)">${p.check}</div>
              <div class="pass-item-text">${p.message}</div>
              ${p.found ? `<div style="font-size:11px;color:var(--faint);font-family:'DM Mono',monospace;margin-top:4px">${JSON.stringify(p.found).slice(0,120)}</div>` : ''}
            </div>
          </div>`).join('')}
      </div>
    </div>`;
  }

  // Page meta
  html += `<div style="margin-top:32px;padding-top:20px;border-top:1px solid var(--border);display:flex;flex-wrap:wrap;gap:16px;font-size:12px;color:var(--faint)">
    <span>URL: <span style="color:var(--muted)">${data.url}</span></span>
    <span>Mode: <span style="color:var(--muted)">${data.mode}</span></span>
    <span>Audited: <span style="color:var(--muted)">${new Date(data.audit_time).toLocaleString()}</span></span>
    <span>Duration: <span style="color:var(--muted)">${data.audit_duration_s}s</span></span>
    <span>Total checks: <span style="color:var(--muted)">${s.total_checks}</span></span>
  </div>`;

  r.innerHTML = html;
  r.style.display = 'block';

  // Animate score ring
  const circle = document.getElementById('scoreCircle');
  if (circle) {
    circle.style.strokeDashoffset = circumference;
    setTimeout(() => { circle.style.strokeDashoffset = dashOffset; }, 100);
  }
}

function buildPill(sev, count, cls, label) {
  return `<div class="pill ${cls}" onclick="filterSev('${sev}',this)" id="pill-${sev}">
    <span>${label}</span>
    <span class="pill-count">${count}</span>
  </div>`;
}

function buildIssueCard(issue, idx) {
  const sevClass = { critical:'sev-crit', high:'sev-high', medium:'sev-med', low:'sev-low', pass:'sev-pass' }[issue.severity] || 'sev-low';
  const badgeClass = 'badge-' + issue.severity;
  const solutionLines = (issue.solution || '').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const foundStr = issue.found ? JSON.stringify(issue.found, null, 2).slice(0, 400) : '';

  return `<div class="issue-card" data-sev="${issue.severity}" data-cat="${issue.category}" id="card-${idx}">
    <div class="issue-header" onclick="toggleCard(${idx})">
      <div class="sev-dot ${sevClass}"></div>
      <div class="issue-main">
        <div class="issue-top">
          <span class="issue-check">${escHtml(issue.check)}</span>
          <span class="issue-cat">${escHtml(issue.category)}</span>
          <span class="issue-sev-badge ${badgeClass}">${issue.severity}</span>
        </div>
        <div class="issue-msg">${escHtml(issue.message)}</div>
      </div>
      <svg class="issue-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
    </div>
    <div class="issue-body">
      ${issue.impact ? `<div style="margin-bottom:14px"><div class="detail-label" style="margin-bottom:6px">Impact</div><div class="detail-impact">⚡ ${escHtml(issue.impact)}</div></div>` : ''}
      <div class="detail-row">
        <div class="detail-label">🔧 Solution</div>
        <div class="detail-solution">${solutionLines.replace(/\n/g,'<br>')}</div>
      </div>
      ${foundStr ? `<div class="detail-row"><div class="detail-label">🔍 Found Data</div><div class="detail-content">${escHtml(foundStr)}</div></div>` : ''}
      ${issue.reference ? `<a href="${issue.reference}" class="detail-link" target="_blank">📖 Google Documentation ↗</a>` : ''}
    </div>
  </div>`;
}

function buildKeywordPanel(kw) {
  const primary = kw.primary_keywords || [];
  const bigrams = kw.phrase_keywords || [];
  const trigrams = kw.long_tail_phrases || [];
  const ideas = kw.keyword_ideas || [];
  const alignment = kw.keyword_alignment || [];

  let html = `<div class="kw-panel">
    <h3>Keyword Analysis <span>Single Page</span></h3>
    <div class="kw-grid">
      <div>
        <div class="kw-col"><h4>Primary Keywords — Top 10 by Density</h4>
          <table class="kw-table">
            <thead><tr><th>Keyword</th><th>Count</th><th>Density</th><th>Title</th><th>H1</th><th>Meta</th></tr></thead>
            <tbody>`;

  alignment.forEach(a => {
    html += `<tr>
      <td style="color:var(--text)">${escHtml(a.keyword)}</td>
      <td>${a.count}</td>
      <td><span class="kw-density">${a.density}%</span></td>
      <td><span class="kw-check ${a.in_title ? 'kw-yes' : 'kw-no'}">${a.in_title ? '✓' : '✗'}</span></td>
      <td><span class="kw-check ${a.in_h1 ? 'kw-yes' : 'kw-no'}">${a.in_h1 ? '✓' : '✗'}</span></td>
      <td><span class="kw-check ${a.in_meta_desc ? 'kw-yes' : 'kw-no'}">${a.in_meta_desc ? '✓' : '✗'}</span></td>
    </tr>`;
  });
  // fill remaining primaries without alignment
  primary.slice(alignment.length).forEach(k => {
    html += `<tr>
      <td style="color:var(--text)">${escHtml(k.keyword)}</td>
      <td>${k.count}</td>
      <td><span class="kw-density">${k.density}%</span></td>
      <td>—</td><td>—</td><td>—</td>
    </tr>`;
  });

  html += `</tbody></table></div></div>
      <div>
        <div class="kw-col"><h4>Phrase Keywords (Bigrams)</h4>
          <div class="phrase-list">
            ${bigrams.map(b => `<div class="phrase-item"><span class="phrase-text">${escHtml(b.phrase)}</span><span class="phrase-count">${b.count}×</span></div>`).join('')}
          </div>
        </div>
        <div class="kw-col" style="margin-top:20px"><h4>Long-Tail Phrases (Trigrams)</h4>
          <div class="phrase-list">
            ${trigrams.map(t => `<div class="phrase-item"><span class="phrase-text">${escHtml(t.phrase)}</span><span class="phrase-count">${t.count}×</span></div>`).join('')}
          </div>
        </div>
      </div>
    </div>`;

  if (ideas.length) {
    html += `<div style="margin-top:24px;border-top:1px solid var(--border);padding-top:20px">
      <h4 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--faint);margin-bottom:12px">
        💡 ${ideas.length} Keyword Ideas for Better SEO
      </h4>
      <div class="ideas-grid">
        ${ideas.map(i => `<div class="idea-chip">${escHtml(i)}</div>`).join('')}
      </div>
    </div>`;
  }

  html += `</div>`;
  return html;
}

function buildSiteTable(pages) {
  let html = `<div class="site-panel">
    <h3>Site Crawl Results <em>${pages.length} pages crawled</em></h3>
    <div class="site-table-wrap"><table class="site-table">
      <thead><tr>
        <th>#</th><th>URL</th><th>Status</th><th>Title</th><th>H1</th>
        <th>Meta Desc</th><th>Load</th><th>Images</th><th>Issues</th>
      </tr></thead><tbody>`;

  pages.forEach((p, i) => {
    const statusColor = p.status_code === 200 ? 'ok' : p.status_code >= 400 ? 'err' : 'warn';
    const loadColor = !p.load_time_ms ? '' : p.load_time_ms < 1000 ? 'ok' : p.load_time_ms < 3000 ? 'warn' : 'err';
    const titleLen = p.title_length || 0;
    const tlColor = titleLen >= 30 && titleLen <= 60 ? 'ok' : titleLen === 0 ? 'err' : 'warn';
    const mdLen = p.meta_description_length || 0;
    const mdColor = mdLen >= 120 && mdLen <= 160 ? 'ok' : mdLen === 0 ? 'err' : 'warn';
    const critCount = (p.issues || []).filter(x => x.severity === 'critical').length;
    const highCount = (p.issues || []).filter(x => x.severity === 'high').length;
    const badgeCls = critCount > 0 ? 'count-crit' : highCount > 0 ? 'count-high' : 'count-ok';

    html += `<tr>
      <td style="color:var(--faint)">${i + 1}</td>
      <td><span class="site-url" title="${escHtml(p.url || '')}">${escHtml((p.url || '').replace(/^https?:\/\//, '').slice(0, 45))}</span></td>
      <td><span class="site-status ${statusColor}">${p.status_code || '—'}</span></td>
      <td><span class="${tlColor}">${titleLen ? titleLen + 'c' : '❌ Missing'}</span></td>
      <td><span class="${p.h1_count === 1 ? 'ok' : p.h1_count === 0 ? 'err' : 'warn'}">${p.h1_count === 0 ? '❌ None' : p.h1_count + ' H1'}</span></td>
      <td><span class="${mdColor}">${mdLen ? mdLen + 'c' : '❌ Missing'}</span></td>
      <td><span class="${loadColor}">${p.load_time_ms ? p.load_time_ms + 'ms' : '—'}</span></td>
      <td>${p.images_missing_alt > 0 ? `<span class="warn">${p.images_missing_alt}/${p.images_total} no alt</span>` : `<span class="ok">${p.images_total || 0} imgs ✓</span>`}</td>
      <td>
        <span class="issue-count-badge ${badgeCls}">${p.issue_count || 0}</span>
        ${(p.issues || []).slice(0, 3).map(iss => `<div class="site-issue-chip sc-${iss.severity}">${escHtml(iss.issue.slice(0,30))}</div>`).join('')}
      </td>
    </tr>`;
  });

  html += `</tbody></table></div></div>`;
  return html;
}

/* ─── INTERACTIVITY ─── */
function toggleCard(idx) {
  const card = document.getElementById('card-' + idx);
  card.classList.toggle('open');
}

function togglePasses(el) {
  const list = document.getElementById('passList');
  list.classList.toggle('visible');
}

function filterSev(sev, el) {
  if (activeSev === sev) {
    activeSev = null;
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
  } else {
    activeSev = sev;
    document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
    el.classList.add('active');
  }
  applyFilters();
}

function filterCat(cat, el) {
  activeCat = cat;
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  applyFilters();
}

function applyFilters() {
  document.querySelectorAll('.issue-card').forEach(card => {
    const sev = card.dataset.sev;
    const cat = card.dataset.cat;
    const sevOk = !activeSev || sev === activeSev;
    const catOk = activeCat === 'All' || cat === activeCat;
    card.style.display = (sevOk && catOk) ? 'block' : 'none';
  });
}

function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Enter key
document.getElementById('urlInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') runAudit();
});
</script>
</body>
</html>"""


@app.route("/")
def index():
    return HTML


@app.route("/audit", methods=["POST"])
def audit():
    data = request.get_json(force=True)
    url = data.get("url", "").strip()
    mode = data.get("mode", "single")

    if not url:
        return jsonify({"error": "URL is required"}), 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        result = SEOCrawler(url, mode).run()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "url": url, "mode": mode,
                        "issues": [], "passes": [], "summary": {}}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n🚀 SEO Audit Tool running at: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
