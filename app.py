"""
SEO Audit Flask Application - Deployment Ready
Run locally:  python app.py
Deploy on Railway/Render: push to GitHub and connect repo
"""

import os
import json
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from crawler import SEOCrawler

app = Flask(__name__)
CORS(app)

# ─── HTML FRONTEND ────────────────────────────────────────────────────────────

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SEO Technical Auditor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #050810;
    --surface: #0c1220;
    --surface2: #111827;
    --border: #1e2d45;
    --accent: #00e5ff;
    --accent2: #7c3aed;
    --critical: #ef4444;
    --high: #f97316;
    --medium: #eab308;
    --low: #64748b;
    --pass: #10b981;
    --text: #e2e8f0;
    --muted: #64748b;
    --grid: rgba(0,229,255,0.03);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    min-height: 100vh;
    background-image:
      linear-gradient(var(--grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--grid) 1px, transparent 1px);
    background-size: 40px 40px;
  }
  nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 32px;
    border-bottom: 1px solid var(--border);
    background: rgba(5,8,16,0.92);
    backdrop-filter: blur(12px);
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .logo { font-weight: 800; font-size: 1.2rem; letter-spacing: -0.5px; color: var(--accent); display: flex; align-items: center; gap: 8px; }
  .logo span { color: var(--text); }
  .badge { font-family: 'Space Mono', monospace; font-size: 0.65rem; background: var(--accent2); color: white; padding: 2px 8px; border-radius: 4px; letter-spacing: 1px; }
  .hero { text-align: center; padding: 80px 20px 60px; max-width: 900px; margin: 0 auto; }
  .hero h1 { font-size: clamp(2.5rem, 6vw, 4.5rem); font-weight: 800; line-height: 1.05; letter-spacing: -2px; background: linear-gradient(135deg, #fff 0%, var(--accent) 60%, var(--accent2) 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 16px; }
  .hero p { color: var(--muted); font-size: 1.1rem; max-width: 600px; margin: 0 auto 40px; line-height: 1.7; }
  .search-wrap { display: flex; max-width: 680px; margin: 0 auto; border: 1.5px solid var(--border); border-radius: 12px; overflow: hidden; background: var(--surface); transition: border-color 0.2s; }
  .search-wrap:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0,229,255,0.1); }
  #url-input { flex: 1; background: transparent; border: none; outline: none; padding: 18px 20px; font-size: 1rem; color: var(--text); font-family: 'Space Mono', monospace; }
  #url-input::placeholder { color: var(--muted); }
  #audit-btn { background: var(--accent); color: #050810; border: none; padding: 0 32px; font-family: 'Syne', sans-serif; font-weight: 700; font-size: 0.95rem; cursor: pointer; letter-spacing: 0.5px; transition: all 0.2s; white-space: nowrap; }
  #audit-btn:hover { background: #33eaff; }
  #audit-btn:disabled { background: var(--muted); cursor: not-allowed; }
  #loader { display: none; text-align: center; padding: 60px 20px; }
  .spinner { width: 48px; height: 48px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 20px; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loader-text { font-family: 'Space Mono', monospace; color: var(--accent); font-size: 0.85rem; letter-spacing: 1px; animation: pulse 1.5s ease-in-out infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  #results { display: none; max-width: 1100px; margin: 0 auto; padding: 0 20px 80px; }
  .score-section { display: grid; grid-template-columns: auto 1fr; gap: 32px; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 32px; margin-bottom: 28px; }
  .score-circle { position: relative; width: 140px; height: 140px; flex-shrink: 0; }
  .score-circle svg { transform: rotate(-90deg); }
  .score-num { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); font-size: 2.4rem; font-weight: 800; letter-spacing: -2px; }
  .score-label { position: absolute; bottom: 28px; left: 50%; transform: translateX(-50%); font-size: 0.6rem; font-family: 'Space Mono', monospace; color: var(--muted); letter-spacing: 1px; white-space: nowrap; }
  .score-info h2 { font-size: 1.4rem; font-weight: 700; margin-bottom: 6px; }
  .score-url { font-family: 'Space Mono', monospace; font-size: 0.8rem; color: var(--accent); word-break: break-all; margin-bottom: 16px; }
  .pill-row { display: flex; flex-wrap: wrap; gap: 8px; }
  .pill { padding: 4px 14px; border-radius: 100px; font-size: 0.78rem; font-weight: 700; display: flex; align-items: center; gap: 5px; }
  .pill.critical { background: rgba(239,68,68,0.15); color: var(--critical); border: 1px solid rgba(239,68,68,0.3); }
  .pill.high { background: rgba(249,115,22,0.15); color: var(--high); border: 1px solid rgba(249,115,22,0.3); }
  .pill.medium { background: rgba(234,179,8,0.15); color: var(--medium); border: 1px solid rgba(234,179,8,0.3); }
  .pill.low { background: rgba(100,116,139,0.15); color: var(--low); border: 1px solid rgba(100,116,139,0.3); }
  .pill.pass { background: rgba(16,185,129,0.15); color: var(--pass); border: 1px solid rgba(16,185,129,0.3); }
  .section-title { font-size: 0.7rem; font-family: 'Space Mono', monospace; color: var(--muted); letter-spacing: 2px; text-transform: uppercase; margin: 32px 0 14px; display: flex; align-items: center; gap: 10px; }
  .section-title::after { content: ''; flex: 1; height: 1px; background: var(--border); }
  .metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; }
  .metric-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }
  .metric-card .label { font-size: 0.68rem; font-family: 'Space Mono', monospace; color: var(--muted); letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 6px; }
  .metric-card .value { font-size: 1.4rem; font-weight: 700; line-height: 1; }
  .metric-card .value.good { color: var(--pass); }
  .metric-card .value.bad { color: var(--critical); }
  .metric-card .value.warn { color: var(--medium); }
  .metric-card .sub { font-size: 0.72rem; color: var(--muted); margin-top: 4px; }
  .filter-tabs { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
  .filter-tab { padding: 6px 16px; border-radius: 8px; border: 1px solid var(--border); background: transparent; color: var(--muted); font-family: 'Syne', sans-serif; font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.15s; }
  .filter-tab.active, .filter-tab:hover { background: var(--surface2); color: var(--text); border-color: var(--accent); }
  .filter-tab.active { color: var(--accent); }
  .issue-list { display: flex; flex-direction: column; gap: 10px; }
  .issue-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; border-left: 4px solid var(--border); transition: transform 0.15s; }
  .issue-card:hover { transform: translateX(3px); }
  .issue-card.critical { border-left-color: var(--critical); }
  .issue-card.high { border-left-color: var(--high); }
  .issue-card.medium { border-left-color: var(--medium); }
  .issue-card.low { border-left-color: var(--low); }
  .issue-card.pass { border-left-color: var(--pass); opacity: 0.75; }
  .issue-header { display: flex; align-items: center; gap: 12px; padding: 14px 18px; cursor: pointer; user-select: none; }
  .issue-sev { font-size: 0.65rem; font-family: 'Space Mono', monospace; font-weight: 700; letter-spacing: 1px; padding: 3px 9px; border-radius: 5px; white-space: nowrap; flex-shrink: 0; }
  .critical .issue-sev { background: rgba(239,68,68,0.2); color: var(--critical); }
  .high .issue-sev { background: rgba(249,115,22,0.2); color: var(--high); }
  .medium .issue-sev { background: rgba(234,179,8,0.2); color: var(--medium); }
  .low .issue-sev { background: rgba(100,116,139,0.2); color: var(--low); }
  .pass .issue-sev { background: rgba(16,185,129,0.2); color: var(--pass); }
  .issue-cat { font-size: 0.68rem; font-family: 'Space Mono', monospace; color: var(--muted); flex-shrink: 0; }
  .issue-check { font-weight: 700; font-size: 0.95rem; flex: 1; }
  .issue-toggle { color: var(--muted); font-size: 0.8rem; margin-left: auto; }
  .issue-body { display: none; padding: 0 18px 16px; border-top: 1px solid var(--border); }
  .issue-body.open { display: block; }
  .issue-msg { font-size: 0.88rem; color: var(--text); margin: 12px 0 10px; line-height: 1.6; }
  .detail-block { border-radius: 8px; padding: 12px 16px; margin-top: 10px; font-size: 0.82rem; line-height: 1.7; }
  .detail-block.ref { background: rgba(124,58,237,0.1); border: 1px solid rgba(124,58,237,0.2); }
  .detail-block.sol { background: rgba(0,229,255,0.05); border: 1px solid rgba(0,229,255,0.15); }
  .detail-block.found { background: rgba(0,0,0,0.3); border: 1px solid var(--border); font-family: 'Space Mono', monospace; font-size: 0.75rem; white-space: pre-wrap; word-break: break-all; }
  .detail-label { font-size: 0.65rem; font-family: 'Space Mono', monospace; letter-spacing: 1.5px; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; font-weight: 700; }
  .ref-link { color: var(--accent2); text-decoration: none; word-break: break-all; }
  .ref-link:hover { text-decoration: underline; }
  .empty { text-align: center; padding: 60px 20px; color: var(--muted); }
  .passes-toggle { display: flex; align-items: center; gap: 10px; padding: 14px 18px; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; cursor: pointer; font-weight: 600; color: var(--pass); transition: all 0.15s; }
  .passes-toggle:hover { border-color: var(--pass); }
  .error-box { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-radius: 12px; padding: 24px; color: var(--critical); text-align: center; margin: 40px auto; max-width: 600px; }
  .error-box h3 { margin-bottom: 8px; }
  .error-box p { font-size: 0.9rem; color: var(--muted); }
  @media (max-width: 640px) {
    .score-section { grid-template-columns: 1fr; text-align: center; }
    .pill-row { justify-content: center; }
    nav { padding: 14px 16px; }
    .hero { padding: 50px 16px 40px; }
  }
</style>
</head>
<body>
<nav>
  <div class="logo">⚡ <span>SEO</span>Audit <div class="badge">TECHNICAL</div></div>
  <div style="font-family:'Space Mono',monospace;font-size:0.7rem;color:var(--muted)">v2.0 · 30+ Checks</div>
</nav>

<div class="hero">
  <h1>Technical SEO<br>Audit Engine</h1>
  <p>Deep crawl any URL — on-page, technical, Core Web Vitals indicators, structured data, and 30+ checks with exact fixes and Google references.</p>
  <div class="search-wrap">
    <input type="text" id="url-input" placeholder="https://yourwebsite.com" />
    <button id="audit-btn" onclick="runAudit()">RUN AUDIT →</button>
  </div>
</div>

<div id="loader">
  <div class="spinner"></div>
  <div class="loader-text" id="loader-text">FETCHING PAGE...</div>
</div>

<div id="results"></div>

<script>
const loaderMsgs = ["FETCHING PAGE...","CHECKING SSL & HTTPS...","ANALYZING HEADERS...","PARSING HTML STRUCTURE...","AUDITING META TAGS...","CHECKING CANONICAL & ROBOTS...","SCANNING IMAGES & LINKS...","VALIDATING STRUCTURED DATA...","RUNNING TECHNICAL CHECKS...","COMPUTING SEO SCORE..."];
let loaderInterval, allIssues = [], allPasses = [], activeFilter = 'all', activeCat = 'all';

function startLoader() {
  let i = 0;
  document.getElementById('loader-text').textContent = loaderMsgs[0];
  loaderInterval = setInterval(() => { i = (i+1)%loaderMsgs.length; document.getElementById('loader-text').textContent = loaderMsgs[i]; }, 1800);
}
function stopLoader() { clearInterval(loaderInterval); }

function scoreColor(s) { return s>=80?'#10b981':s>=50?'#eab308':'#ef4444'; }
function esc(str) { if(str==null)return''; return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function mClass(k,v) {
  if(k==='load_time_ms') return v<1000?'good':v<3000?'warn':'bad';
  if(k==='status_code') return v===200?'good':'bad';
  if(k==='ssl_expiry_days') return v>30?'good':v>7?'warn':'bad';
  if(k==='word_count') return v>=300?'good':'warn';
  if(k==='redirect_count') return v===0?'good':v<=2?'warn':'bad';
  if(k==='images_missing_alt') return v===0?'good':v<3?'warn':'bad';
  if(k==='render_blocking_scripts') return v===0?'good':'warn';
  return '';
}

function renderMetrics(m) {
  const items = [
    {key:'status_code',label:'HTTP Status',fmt:v=>v,sub:''},
    {key:'load_time_ms',label:'Load Time',fmt:v=>v+'ms',sub:'< 3000ms target'},
    {key:'redirect_count',label:'Redirects',fmt:v=>v,sub:'0 is optimal'},
    {key:'word_count',label:'Word Count',fmt:v=>v.toLocaleString(),sub:'300+ recommended'},
    {key:'title_length',label:'Title Length',fmt:v=>v+' chars',sub:'30–60 optimal'},
    {key:'meta_description_length',label:'Meta Desc Len',fmt:v=>v+' chars',sub:'120–160 optimal'},
    {key:'h1_count',label:'H1 Tags',fmt:v=>v,sub:'Exactly 1 required'},
    {key:'image_count',label:'Images',fmt:v=>v,sub:''},
    {key:'images_missing_alt',label:'Missing Alt',fmt:v=>v,sub:'0 is target'},
    {key:'internal_links',label:'Internal Links',fmt:v=>v,sub:'3+ recommended'},
    {key:'external_links',label:'External Links',fmt:v=>v,sub:''},
    {key:'ssl_expiry_days',label:'SSL Days Left',fmt:v=>v+'d',sub:'> 30 days safe'},
    {key:'text_to_html_ratio',label:'Text/HTML Ratio',fmt:v=>v+'%',sub:'> 10% good'},
    {key:'render_blocking_scripts',label:'Blocking Scripts',fmt:v=>v,sub:'0 is target'},
  ];
  return `<div class="metrics-grid">${items.map(item=>{
    const val = m[item.key];
    if(val==null) return '';
    const cls = mClass(item.key, val);
    return `<div class="metric-card"><div class="label">${item.label}</div><div class="value ${cls}">${item.fmt(val)}</div>${item.sub?`<div class="sub">${item.sub}</div>`:''}</div>`;
  }).join('')}</div>`;
}

function renderCard(issue, idx) {
  const sev = issue.severity;
  const found = issue.found ? JSON.stringify(issue.found, null, 2) : null;
  return `<div class="issue-card ${sev}">
    <div class="issue-header" onclick="toggle(${idx})">
      <span class="issue-sev">${sev.toUpperCase()}</span>
      <span class="issue-cat">${esc(issue.category)}</span>
      <span class="issue-check">${esc(issue.check)}</span>
      <span class="issue-toggle" id="tog-${idx}">▼</span>
    </div>
    <div class="issue-body" id="body-${idx}">
      <div class="issue-msg">${esc(issue.message)}</div>
      ${issue.solution&&issue.solution!=='N/A'?`<div class="detail-block sol"><div class="detail-label">🔧 Solution</div>${esc(issue.solution)}</div>`:''}
      ${issue.reference?`<div class="detail-block ref"><div class="detail-label">📖 Google Reference</div><a href="${esc(issue.reference)}" target="_blank" rel="noopener" class="ref-link">${esc(issue.reference)}</a></div>`:''}
      ${found?`<div class="detail-block found"><div class="detail-label">🔍 Found Data</div>${esc(found)}</div>`:''}
    </div>
  </div>`;
}

function toggle(idx) {
  const b = document.getElementById(`body-${idx}`);
  const t = document.getElementById(`tog-${idx}`);
  b.classList.toggle('open');
  t.textContent = b.classList.contains('open') ? '▲' : '▼';
}

function getFiltered() {
  let f = allIssues;
  if(activeFilter !== 'all') f = f.filter(i => i.severity === activeFilter);
  if(activeCat !== 'all') f = f.filter(i => i.category === activeCat);
  return f;
}

function rerenderIssues() {
  const c = document.getElementById('issue-container');
  if(!c) return;
  const filtered = getFiltered();
  if(filtered.length===0) { c.innerHTML='<div class="empty">✅ No issues for this filter.</div>'; return; }
  c.innerHTML = `<div class="issue-list">${filtered.map((iss,i)=>renderCard(iss, i+10000)).join('')}</div>`;
}

function setFilter(sev) { activeFilter=sev; activeCat='all'; rerenderIssues(); }
function setCat(cat) { activeCat=cat; activeFilter='all'; rerenderIssues(); }
function togglePasses() {
  const pl = document.getElementById('pass-list');
  const tog = document.getElementById('pass-tog');
  if(pl) { pl.style.display = pl.style.display==='none'?'block':'none'; tog.textContent=pl.style.display==='none'?'▼':'▲'; }
}

function renderResults(data) {
  const el = document.getElementById('results');
  if(data.error) {
    el.innerHTML=`<div class="error-box"><h3>⚠ Audit Failed</h3><p>${esc(data.error)}</p><p style="margin-top:8px">Make sure the URL is publicly accessible and try again.</p></div>`;
    el.style.display='block'; return;
  }
  allIssues = data.issues||[];
  allPasses = data.passes||[];
  activeFilter='all'; activeCat='all';
  const s=data.summary, m=data.metrics, sc=s.seo_score, col=scoreColor(sc);
  const r=56, circ=2*Math.PI*r, offset=circ-(sc/100)*circ;
  const cats=[...new Set(allIssues.map(i=>i.category))];

  el.innerHTML = `
    <div class="score-section">
      <div class="score-circle">
        <svg width="140" height="140" viewBox="0 0 140 140">
          <circle cx="70" cy="70" r="${r}" fill="none" stroke="var(--border)" stroke-width="10"/>
          <circle cx="70" cy="70" r="${r}" fill="none" stroke="${col}" stroke-width="10"
            stroke-dasharray="${circ}" stroke-dashoffset="${offset}" stroke-linecap="round"
            style="transition:stroke-dashoffset 1s ease"/>
        </svg>
        <div class="score-num" style="color:${col}">${sc}</div>
        <div class="score-label">SEO SCORE</div>
      </div>
      <div class="score-info">
        <h2>Audit Complete</h2>
        <div class="score-url">${esc(data.url)}</div>
        <div class="pill-row">
          ${s.critical?`<div class="pill critical">● ${s.critical} Critical</div>`:''}
          ${s.high?`<div class="pill high">● ${s.high} High</div>`:''}
          ${s.medium?`<div class="pill medium">● ${s.medium} Medium</div>`:''}
          ${s.low?`<div class="pill low">● ${s.low} Low</div>`:''}
          <div class="pill pass">✓ ${s.passes} Passed</div>
          <div class="pill" style="border-color:var(--border);color:var(--muted)">⏱ ${data.audit_duration_s}s</div>
        </div>
      </div>
    </div>

    <div class="section-title">Page Metrics</div>
    ${renderMetrics(m)}
    ${m.title?`<div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 18px;margin-top:12px;font-size:0.85rem"><span style="color:var(--muted);font-family:'Space Mono',monospace;font-size:0.65rem;text-transform:uppercase;letter-spacing:1px">Title: </span><span style="color:var(--accent)">${esc(m.title)}</span></div>`:''}

    <div class="section-title" style="margin-top:36px">Issues Found (${allIssues.length})</div>
    <div class="filter-tabs">
      <button class="filter-tab active" onclick="setFilter('all')">All (${allIssues.length})</button>
      ${s.critical?`<button class="filter-tab" onclick="setFilter('critical')" style="color:var(--critical)">Critical (${s.critical})</button>`:''}
      ${s.high?`<button class="filter-tab" onclick="setFilter('high')" style="color:var(--high)">High (${s.high})</button>`:''}
      ${s.medium?`<button class="filter-tab" onclick="setFilter('medium')" style="color:var(--medium)">Medium (${s.medium})</button>`:''}
      ${s.low?`<button class="filter-tab" onclick="setFilter('low')" style="color:var(--low)">Low (${s.low})</button>`:''}
      ${cats.map(c=>`<button class="filter-tab" onclick="setCat('${c}')">${c}</button>`).join('')}
    </div>
    <div id="issue-container"></div>

    ${allPasses.length>0?`
    <div class="section-title" style="margin-top:28px">Passed Checks (${allPasses.length})</div>
    <div class="passes-toggle" onclick="togglePasses()">
      <span>✓</span><span>${allPasses.length} checks passed — click to expand</span>
      <span style="margin-left:auto;font-size:0.75rem" id="pass-tog">▼</span>
    </div>
    <div id="pass-list" style="display:none;margin-top:10px">
      <div class="issue-list">${allPasses.map((p,i)=>renderCard({...p,severity:'pass'},99000+i)).join('')}</div>
    </div>`:''}
  `;

  rerenderIssues();
  el.style.display='block';
  el.scrollIntoView({behavior:'smooth', block:'start'});
}

async function runAudit() {
  const urlInput = document.getElementById('url-input');
  const btn = document.getElementById('audit-btn');
  const url = urlInput.value.trim();
  if(!url) { urlInput.style.border='1.5px solid var(--critical)'; return; }
  urlInput.style.border='';
  btn.disabled=true; btn.textContent='AUDITING...';
  document.getElementById('loader').style.display='block';
  document.getElementById('results').style.display='none';
  startLoader();
  try {
    const res = await fetch('/audit', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url}) });
    const data = await res.json();
    stopLoader();
    document.getElementById('loader').style.display='none';
    renderResults(data);
  } catch(e) {
    stopLoader();
    document.getElementById('loader').style.display='none';
    document.getElementById('results').innerHTML=`<div class="error-box"><h3>⚠ Connection Error</h3><p>Could not reach the audit server. Ensure the backend is running.</p></div>`;
    document.getElementById('results').style.display='block';
  } finally {
    btn.disabled=false; btn.textContent='RUN AUDIT →';
  }
}

document.getElementById('url-input').addEventListener('keydown', e => { if(e.key==='Enter') runAudit(); });
</script>
</body>
</html>"""


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/audit", methods=["POST"])
def audit():
    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    crawler = SEOCrawler(url)
    result = crawler.run()
    return jsonify(result)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ─── ENTRYPOINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀 SEO Audit Tool running at: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
