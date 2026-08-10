(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const n of document.querySelectorAll('link[rel="modulepreload"]'))d(n);new MutationObserver(n=>{for(const r of n)if(r.type==="childList")for(const i of r.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&d(i)}).observe(document,{childList:!0,subtree:!0});function s(n){const r={};return n.integrity&&(r.integrity=n.integrity),n.referrerPolicy&&(r.referrerPolicy=n.referrerPolicy),n.crossOrigin==="use-credentials"?r.credentials="include":n.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function d(n){if(n.ep)return;n.ep=!0;const r=s(n);fetch(n.href,r)}})();async function m(a){const t=await fetch(a);if(!t.ok){const s=await t.text();throw new Error(`${t.status} ${a}: ${s}`)}return await t.json()}function _(a){const t=new URLSearchParams;a.profile&&t.set("profile",a.profile),a.status&&t.set("status",a.status);const s=t.toString();return m(`/api/runs${s?`?${s}`:""}`)}function S(a){return m(`/api/runs/${encodeURIComponent(a)}`)}function R(a,t){return m(`/api/runs/${encodeURIComponent(a)}/tests/${encodeURIComponent(t)}`)}function N(a=50){return m(`/api/trends?limit=${a}`)}function L(a){return`/api/artifacts/file?path=${encodeURIComponent(a)}`}function h(a){if(a==null||Number.isNaN(a))return"—";if(a<60)return`${a.toFixed(1)}s`;const t=Math.floor(a/60),s=a-t*60;return`${t}m ${s.toFixed(0)}s`}function e(a){return String(a??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function x(a){const t=await S(a),s=t.run,d=t.banner,n=t.tests.map(r=>`
    <tr data-testid="test-row" data-test-id="${e(r.id)}">
      <td class="wrap"><a href="#/runs/${e(a)}/tests/${e(r.id)}">${e(r.nodeid)}</a></td>
      <td><span class="badge ${e(r.status)}">${e(r.status)}</span></td>
      <td class="verdict-${e(r.verdict??"")}">${e(r.verdict??"—")}</td>
      <td>${e(h(r.duration_s))}</td>
      <td class="wrap">${e(r.death_step_name??"")}</td>
    </tr>`).join("");return`
    <p class="meta"><a href="#/">← Runs</a> · ${e(s.id)}</p>
    <h1>Run detail</h1>
    <div class="meta">
      profile=${e(s.profile)} · driver=${e(s.driver??"—")} ·
      device=${e(s.device??"—")} · status=${e(s.status)} ·
      duration=${e(h(s.duration_s))}
    </div>
    <div class="banner" data-testid="verdict-banner">
      <div class="stat ok"><span>passed</span><b>${s.passed}</b></div>
      <div class="stat"><span>failed</span><b>${s.failed}</b></div>
      <div class="stat infra"><span>infra</span><b>${d.infra_failures}</b></div>
      <div class="stat test"><span>test</span><b>${d.test_failures}</b></div>
      <div class="stat"><span>authoring</span><b>${d.authoring_failures}</b></div>
    </div>
    <h2>Tests</h2>
    <div class="table-wrap">
      <table data-testid="tests-table">
        <thead>
          <tr><th>Test</th><th>Status</th><th>Verdict</th><th>Duration</th><th>Death step</th></tr>
        </thead>
        <tbody>${n||'<tr><td colspan="5">No tests.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function T(a,t){const s=await R(a,t),d=s.test,n=s.steps.map(c=>{const l=String(c.status??"");return`<li data-testid="step-row">
        <span class="ts">${e(c.started_at??"")}</span>
        <span class="badge ${e(l)}">${e(l)}</span>
        <span>${e(c.name??"")}${c.error_message?` — ${e(c.error_message)}`:""}</span>
      </li>`}).join(""),r=(s.history||[]).map(c=>{const l=String(c.status??""),$=Number(c.duration_s??0)||1,p=Math.max(4,Math.min(28,$*4));return`<i class="${e(l)}" style="height:${p}px" title="${e(l)}"></i>`}).join(""),i=s.death_point||{},o=i.last_started_step||{},u=i.driver_health||{},f=d.verdict==="infra"?"infra":"",v=(s.artifacts||[]).map(c=>{const l=String(c.path??""),$=String(c.kind??""),p=String(c.name??l),b=L(l);return $==="screenshot"||/\.(png|jpe?g|webp|gif)$/i.test(p)?`<div><a href="${e(b)}" target="_blank" rel="noreferrer">
          <img src="${e(b)}" alt="${e(p)}"/><div>${e(p)}</div></a></div>`:`<div><a href="${e(b)}" target="_blank" rel="noreferrer">${e(p)}</a>
        <div class="meta">${e($)} · ${e(c.size_bytes??"")} B</div></div>`}).join("");return`
    <p class="meta">
      <a href="#/">Runs</a> /
      <a href="#/runs/${e(a)}">${e(a.slice(0,8))}…</a>
    </p>
    <h1 data-testid="test-title">${e(d.nodeid)}</h1>
    <div class="meta">
      status=<span class="badge ${e(d.status)}">${e(d.status)}</span> ·
      verdict=<span class="verdict-${e(d.verdict??"")}">${e(d.verdict??"—")}</span> ·
      duration=${e(h(d.duration_s))}
    </div>

    <div class="panel death ${f}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${e(o.name??"—")}</b>
        @ ${e(o.started_at??"")}</div>
      <div>error: ${e(d.error_type??"")} — ${e(d.error_message??"")}</div>
      <div>driver health: ${e(JSON.stringify(u||{}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${r||"<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${n||"<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${v||"<span class='meta'>none</span>"}</div>
  `}async function k(){const a=await N(50),t=a.series||[],s=Math.max(1,...t.map(i=>Number(i.duration_s??0)||0)),d=t.map(i=>{const o=i.pass_rate==null?0:Number(i.pass_rate),u=Math.max(4,Math.round(o*100)),f=Number(i.duration_s??0);return`<div class="bar ${Number(i.failed??0)>0?"fail":""}" style="height:${u}%">
        <span>${e(i.run_id)} · ${(o*100).toFixed(0)}% · ${e(h(f))}</span>
      </div>`}).join(""),n=t.map(i=>{const o=Number(i.duration_s??0);return`<div class="bar" style="height:${Math.max(4,Math.round(o/s*100))}%">
        <span>${e(i.run_id)} · ${e(h(o))}</span>
      </div>`}).join(""),r=(a.flaky_tests||[]).map(i=>`<tr>
        <td class="wrap">${e(i.nodeid)}</td>
        <td>${e(i.runs)}</td>
        <td>${e(i.passed)}/${e(i.failed)}</td>
        <td>${(Number(i.pass_rate)*100).toFixed(0)}%</td>
        <td>${(Number(i.flake_score)*100).toFixed(0)}%</td>
      </tr>`).join("");return`
    <h1>Trends</h1>
    <h2>Pass rate (recent runs)</h2>
    <div class="chart" data-testid="pass-chart">${d||"<span class='meta'>no data</span>"}</div>
    <h2>Duration</h2>
    <div class="chart" data-testid="dur-chart">${n||"<span class='meta'>no data</span>"}</div>
    <h2>Flakiness board</h2>
    <div class="table-wrap">
      <table data-testid="flaky-table">
        <thead>
          <tr><th>Test</th><th>Runs</th><th>P/F</th><th>Pass%</th><th>Flake</th></tr>
        </thead>
        <tbody>${r||'<tr><td colspan="5">No flaky tests detected.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function I(){return`
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `}function E(a){const t=document.getElementById("live-status"),s=document.getElementById("live-clear");s==null||s.addEventListener("click",()=>{a.innerHTML=""});const n=`${location.protocol==="https:"?"wss":"ws"}://${location.host}/live`;let r;try{r=new WebSocket(n)}catch(i){t&&(t.textContent="failed"),a.innerHTML=`<div>WebSocket error: ${e(String(i))}</div>`;return}r.onopen=()=>{t&&(t.textContent="live",t.className="badge passed")},r.onclose=()=>{t&&(t.textContent="closed",t.className="badge failed")},r.onerror=()=>{t&&(t.textContent="error",t.className="badge failed")},r.onmessage=i=>{try{const o=JSON.parse(String(i.data)),u=String(o.type??"?"),f=String(o.timestamp??""),v=o.nodeid||o.name||o.test_id||o.status||o.profile||"",c=document.createElement("div");c.innerHTML=`<span class="t">${e(f)}</span><b>${e(u)}</b> ${e(v)}`,a.prepend(c)}catch{const o=document.createElement("div");o.textContent=String(i.data),a.prepend(o)}}}const g=document.querySelector("#app");function y(a,t){const s=(d,n)=>`<a href="${d}" class="${a===n?"active":""}">${n}</a>`;return`
    <header class="topbar">
      <a class="brand" href="#/">Questline <span>HUD</span></a>
      <nav class="nav">
        ${s("#/","Runs")}
        ${s("#/trends","Trends")}
        ${s("#/live","Live")}
      </nav>
    </header>
    <main class="main">${t}</main>
  `}function M(){const t=(location.hash.replace(/^#\/?/,"")||"").split("/").filter(Boolean);return t[0]==="runs"&&t[1]&&t[2]==="tests"&&t[3]?{name:"test",params:{runId:t[1],testId:t[3]}}:t[0]==="runs"&&t[1]?{name:"run",params:{runId:t[1]}}:t[0]==="trends"?{name:"trends",params:{}}:t[0]==="live"?{name:"live",params:{}}:{name:"runs",params:{}}}function P(a){return a.length?`
    <div class="table-wrap">
      <table data-testid="runs-table">
        <thead>
          <tr>
            <th>Run</th><th>Profile</th><th>Driver</th><th>Device</th>
            <th>Status</th><th>Pass</th><th>Infra</th><th>Test</th>
            <th>Duration</th><th>Started</th>
          </tr>
        </thead>
        <tbody>${a.map(s=>`
    <tr data-testid="run-row" data-run-id="${e(s.id)}">
      <td class="wrap"><a href="#/runs/${e(s.id)}">${e(s.id.slice(0,8))}…</a></td>
      <td>${e(s.profile)}</td>
      <td>${e(s.driver??"—")}</td>
      <td>${e(s.device??"—")}</td>
      <td><span class="badge ${e(s.status)}">${e(s.status)}</span></td>
      <td>${s.passed}/${s.total}</td>
      <td class="verdict-infra">${s.infra_failures}</td>
      <td class="verdict-test">${s.test_failures}</td>
      <td>${e(h(s.duration_s))}</td>
      <td>${e(s.started_at??"")}</td>
    </tr>`).join("")}</tbody>
      </table>
    </div>`:`<div class="empty" data-testid="empty-store">
      No runs in the store yet.<br/>
      Run a suite with the questline plugin, then refresh.
    </div>`}async function j(){const a=new URLSearchParams(location.hash.split("?")[1]||""),t=a.get("profile")||"",s=a.get("status")||"",d=await _({profile:t||void 0,status:s||void 0});return`
    <h1>Runs</h1>
    <div class="toolbar">
      <label>profile <input id="f-profile" value="${e(t)}" placeholder="any"/></label>
      <label>status
        <select id="f-status">
          <option value="">any</option>
          ${["passed","failed","running","error"].map(n=>`<option value="${n}" ${s===n?"selected":""}>${n}</option>`).join("")}
        </select>
      </label>
      <button type="button" id="f-apply">Filter</button>
    </div>
    ${P(d.runs)}
  `}async function w(){const a=M();try{let t="",s="Runs";a.name==="run"?(t=await x(a.params.runId),s="Runs"):a.name==="test"?(t=await T(a.params.runId,a.params.testId),s="Runs"):a.name==="trends"?(t=await k(),s="Trends"):a.name==="live"?(t=await I(),s="Live"):(t=await j(),s="Runs"),g.innerHTML=y(s,t),C(a.name)}catch(t){g.innerHTML=y("Runs",`<div class="empty">Failed to load HUD: ${e(String(t))}</div>`)}}function C(a){var t;if(a==="runs"&&((t=document.getElementById("f-apply"))==null||t.addEventListener("click",()=>{const s=document.getElementById("f-profile").value.trim(),d=document.getElementById("f-status").value,n=new URLSearchParams;s&&n.set("profile",s),d&&n.set("status",d);const r=n.toString();location.hash=r?`/?${r}`:"/"})),a==="live"){const s=document.getElementById("live-root");s&&E(s)}}window.addEventListener("hashchange",()=>{w()});w();
