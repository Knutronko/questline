(function(){const a=document.createElement("link").relList;if(a&&a.supports&&a.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))r(s);new MutationObserver(s=>{for(const i of s)if(i.type==="childList")for(const c of i.addedNodes)c.tagName==="LINK"&&c.rel==="modulepreload"&&r(c)}).observe(document,{childList:!0,subtree:!0});function e(s){const i={};return s.integrity&&(i.integrity=s.integrity),s.referrerPolicy&&(i.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?i.credentials="include":s.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function r(s){if(s.ep)return;s.ep=!0;const i=e(s);fetch(s.href,i)}})();let S=null;async function h(t){const a=await fetch(t);if(!a.ok){const e=await a.text();throw new Error(`${a.status} ${t}: ${e}`)}return await a.json()}async function w(){return S||(S=(await h("/api/csrf")).csrf_token,S)}async function b(t,a,e){const r=await w(),s=await fetch(a,{method:t,headers:{"Content-Type":"application/json","X-CSRF-Token":r},body:e===void 0?void 0:JSON.stringify(e)});if(!s.ok){const i=await s.text();throw new Error(`${s.status} ${a}: ${i}`)}if(s.status!==204)return await s.json()}function _(){return h("/api/meta")}function B(t){const a=new URLSearchParams;t.profile&&a.set("profile",t.profile),t.status&&a.set("status",t.status);const e=a.toString();return h(`/api/runs${e?`?${e}`:""}`)}function M(t){return h(`/api/runs/${encodeURIComponent(t)}`)}function F(t,a){return h(`/api/runs/${encodeURIComponent(t)}/tests/${encodeURIComponent(a)}`)}function U(t=50){return h(`/api/trends?limit=${t}`)}function P(){return h("/api/profiles")}function R(t){return h(`/api/profiles/${encodeURIComponent(t)}`)}function D(t,a){return b("POST",`/api/profiles/${encodeURIComponent(t)}/validate`,{fields:a,apply:!1})}function E(t,a,e){return b("POST",`/api/profiles/${encodeURIComponent(t)}`,{fields:a,apply:e})}function J(){return h("/api/devices")}function H(){return h("/api/reporters")}function N(){return h("/api/launcher")}function Q(t){return b("POST","/api/launcher/start",t)}function A(){return b("POST","/api/launcher/stop")}function W(){return h("/api/quarantine")}function K(t){return b("POST","/api/quarantine",t)}function V(t){return b("DELETE",`/api/quarantine?test_id=${encodeURIComponent(t)}`)}function z(t){return b("POST","/api/quarantine/audit",t||{})}function O(t){return h(`/api/perf/${encodeURIComponent(t)}`)}function G(t,a){return h(`/api/perf/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(a)}`)}function X(t=50){return h(`/api/perf/correlation?limit=${t}`)}function Y(t){return`/api/artifacts/file?path=${encodeURIComponent(t)}`}function $(t){if(t==null||Number.isNaN(t))return"—";if(t<60)return`${t.toFixed(1)}s`;const a=Math.floor(t/60),e=t-a*60;return`${a}m ${e.toFixed(0)}s`}function n(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function Z(t){const a=await M(t),e=a.run,r=a.banner,s=a.tests.map(i=>`
    <tr data-testid="test-row" data-test-id="${n(i.id)}">
      <td class="wrap"><a href="#/runs/${n(t)}/tests/${n(i.id)}">${n(i.nodeid)}</a></td>
      <td><span class="badge ${n(i.status)}">${n(i.status)}</span></td>
      <td class="verdict-${n(i.verdict??"")}">${n(i.verdict??"—")}</td>
      <td>${n($(i.duration_s))}</td>
      <td class="wrap">${n(i.death_step_name??"")}</td>
    </tr>`).join("");return`
    <p class="meta"><a href="#/">← Runs</a> · ${n(e.id)}</p>
    <h1>Run detail</h1>
    <div class="meta">
      profile=${n(e.profile)} · driver=${n(e.driver??"—")} ·
      device=${n(e.device??"—")} · status=${n(e.status)} ·
      duration=${n($(e.duration_s))}
    </div>
    <div class="banner" data-testid="verdict-banner">
      <div class="stat ok"><span>passed</span><b>${e.passed}</b></div>
      <div class="stat"><span>failed</span><b>${e.failed}</b></div>
      <div class="stat infra"><span>infra</span><b>${r.infra_failures}</b></div>
      <div class="stat test"><span>test</span><b>${r.test_failures}</b></div>
      <div class="stat"><span>authoring</span><b>${r.authoring_failures}</b></div>
    </div>
    <h2>Tests</h2>
    <div class="table-wrap">
      <table data-testid="tests-table">
        <thead>
          <tr><th>Test</th><th>Status</th><th>Verdict</th><th>Duration</th><th>Death step</th></tr>
        </thead>
        <tbody>${s||'<tr><td colspan="5">No tests.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function tt(t,a){const e=await F(t,a),r=e.test,s=e.steps.map(p=>{const u=String(p.status??"");return`<li data-testid="step-row">
        <span class="ts">${n(p.started_at??"")}</span>
        <span class="badge ${n(u)}">${n(u)}</span>
        <span>${n(p.name??"")}${p.error_message?` — ${n(p.error_message)}`:""}</span>
      </li>`}).join(""),i=(e.history||[]).map(p=>{const u=String(p.status??""),v=Number(p.duration_s??0)||1,m=Math.max(4,Math.min(28,v*4));return`<i class="${n(u)}" style="height:${m}px" title="${n(u)}"></i>`}).join(""),c=e.death_point||{},l=c.last_started_step||{},o=c.driver_health||{},d=r.verdict==="infra"?"infra":"",f=(e.artifacts||[]).map(p=>{const u=String(p.path??""),v=String(p.kind??""),m=String(p.name??u),y=Y(u);return v==="screenshot"||/\.(png|jpe?g|webp|gif)$/i.test(m)?`<div><a href="${n(y)}" target="_blank" rel="noreferrer">
          <img src="${n(y)}" alt="${n(m)}"/><div>${n(m)}</div></a></div>`:`<div><a href="${n(y)}" target="_blank" rel="noreferrer">${n(m)}</a>
        <div class="meta">${n(v)} · ${n(p.size_bytes??"")} B</div></div>`}).join("");return`
    <p class="meta">
      <a href="#/">Runs</a> /
      <a href="#/runs/${n(t)}">${n(t.slice(0,8))}…</a>
    </p>
    <h1 data-testid="test-title">${n(r.nodeid)}</h1>
    <div class="meta">
      status=<span class="badge ${n(r.status)}">${n(r.status)}</span> ·
      verdict=<span class="verdict-${n(r.verdict??"")}">${n(r.verdict??"—")}</span> ·
      duration=${n($(r.duration_s))}
    </div>

    <div class="panel death ${d}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${n(l.name??"—")}</b>
        @ ${n(l.started_at??"")}</div>
      <div>error: ${n(r.error_type??"")} — ${n(r.error_message??"")}</div>
      <div>driver health: ${n(JSON.stringify(o||{}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${i||"<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${s||"<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${f||"<span class='meta'>none</span>"}</div>
  `}async function et(){const[t,a]=await Promise.all([U(50),X(50)]),e=t.series||[],r=Math.max(1,...e.map(o=>Number(o.duration_s??0)||0)),s=e.map(o=>{const d=o.pass_rate==null?0:Number(o.pass_rate),f=Math.max(4,Math.round(d*100)),p=Number(o.duration_s??0);return`<div class="bar ${Number(o.failed??0)>0?"fail":""}" style="height:${f}%">
        <span>${n(o.run_id)} · ${(d*100).toFixed(0)}% · ${n($(p))}</span>
      </div>`}).join(""),i=e.map(o=>{const d=Number(o.duration_s??0);return`<div class="bar" style="height:${Math.max(4,Math.round(d/r*100))}%">
        <span>${n(o.run_id)} · ${n($(d))}</span>
      </div>`}).join(""),c=(t.flaky_tests||[]).map(o=>`<tr>
        <td class="wrap">${n(o.nodeid)}</td>
        <td>${n(o.runs)}</td>
        <td>${n(o.passed)}/${n(o.failed)}</td>
        <td>${(Number(o.pass_rate)*100).toFixed(0)}%</td>
        <td>${(Number(o.flake_score)*100).toFixed(0)}%</td>
      </tr>`).join(""),l=(a.tests||[]).map(o=>{const d=(o.points||[]).map(f=>{const p=f.duration_s==null?0:Number(f.duration_s);return`<span class="dot ${f.passed?"ok":"bad"}" title="${n(f.run_id)} · ${n($(p))}"></span>`}).join("");return`<tr>
        <td class="wrap">${n(o.nodeid)}</td>
        <td>${o.passed}/${o.failed}</td>
        <td class="corr-dots">${d}</td>
      </tr>`}).join("");return`
    <h1>Trends</h1>
    <h2>Pass rate (recent runs)</h2>
    <div class="chart" data-testid="pass-chart">${s||"<span class='meta'>no data</span>"}</div>
    <h2>Duration</h2>
    <div class="chart" data-testid="dur-chart">${i||"<span class='meta'>no data</span>"}</div>
    <h2>Flakiness board</h2>
    <div class="table-wrap">
      <table data-testid="flaky-table">
        <thead>
          <tr><th>Test</th><th>Runs</th><th>P/F</th><th>Pass%</th><th>Flake</th></tr>
        </thead>
        <tbody>${c||'<tr><td colspan="5">No flaky tests detected.</td></tr>'}</tbody>
      </table>
    </div>
    <h2>Duration vs pass (correlation)</h2>
    <p class="meta">Green = pass, red = fail per run (same flaky nodeids).</p>
    <div class="table-wrap">
      <table data-testid="corr-table">
        <thead><tr><th>Test</th><th>P/F</th><th>Runs</th></tr></thead>
        <tbody>${l||'<tr><td colspan="3">No mixed pass/fail series yet.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function at(){return`
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `}function nt(t){const a=document.getElementById("live-status"),e=document.getElementById("live-clear");e==null||e.addEventListener("click",()=>{t.innerHTML=""});const s=`${location.protocol==="https:"?"wss":"ws"}://${location.host}/live`;let i;try{i=new WebSocket(s)}catch(c){a&&(a.textContent="failed"),t.innerHTML=`<div>WebSocket error: ${n(String(c))}</div>`;return}i.onopen=()=>{a&&(a.textContent="live",a.className="badge passed")},i.onclose=()=>{a&&(a.textContent="closed",a.className="badge failed")},i.onerror=()=>{a&&(a.textContent="error",a.className="badge failed")},i.onmessage=c=>{try{const l=JSON.parse(String(c.data)),o=String(l.type??"?"),d=String(l.timestamp??""),f=l.nodeid||l.name||l.test_id||l.status||l.profile||"",p=document.createElement("div");p.innerHTML=`<span class="t">${n(d)}</span><b>${n(o)}</b> ${n(f)}`,t.prepend(p)}catch{const l=document.createElement("div");l.textContent=String(c.data),t.prepend(l)}}}async function st(){await w();const[t,a,e,r,s]=await Promise.all([_(),P(),J(),H(),N().catch(()=>({launcher:{state:"idle"}}))]);if(t.read_only)return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;const i=(a.profiles||[]).map(d=>`<option value="${n(d)}">${n(d)}</option>`).join(""),c=['<option value="">(profile default)</option>',...(e.devices||[]).map(d=>`<option value="${n(d.id)}">${n(d.id)} · ${n(d.platform)}</option>`)].join(""),l=(r.reporters||[]).map(d=>`<label class="check"><input type="checkbox" name="reporter" value="${n(d)}"/> ${n(d)}</label>`).join(""),o=s.launcher;return`
    <h1>Run launcher</h1>
    <p class="meta">Composes the same pytest / questline session flags as the CLI.
      Live events attach automatically via event forward → <a href="#/live">Live</a>.</p>
    <div class="panel" data-testid="launch-form">
      <div class="toolbar">
        <label>profile
          <select id="launch-profile" data-testid="launch-profile">${i}</select>
        </label>
        <label>device
          <select id="launch-device" data-testid="launch-device">${c}</select>
        </label>
        <label>markers <input id="launch-markers" placeholder="quest_demo" data-testid="launch-markers"/></label>
      </div>
      <label class="block">tests (one path/nodeid per line)
        <textarea id="launch-tests" rows="4" data-testid="launch-tests" placeholder="examples/demo-tests"></textarea>
      </label>
      <div class="toolbar wrap">${l||"<span class='meta'>no reporters</span>"}</div>
      <label class="check"><input type="checkbox" id="launch-quarantine"/> include quarantined</label>
      <div class="toolbar">
        <button type="button" id="launch-start" data-testid="launch-start">Launch</button>
        <button type="button" id="launch-stop" data-testid="launch-stop">Stop</button>
      </div>
    </div>
    <h2>Status</h2>
    <pre class="log" id="launch-status" data-testid="launch-status">${n(JSON.stringify(o,null,2))}</pre>
    ${e.error?`<p class="meta">devices: ${n(e.error)}</p>`:""}
  `}function rt(){var e,r;const t=document.getElementById("launch-status"),a=async()=>{try{const{launcher:s}=await N();t&&(t.textContent=JSON.stringify(s,null,2))}catch(s){t&&(t.textContent=String(s))}};(e=document.getElementById("launch-start"))==null||e.addEventListener("click",()=>{(async()=>{var p;const s=document.getElementById("launch-profile").value,i=document.getElementById("launch-device").value,c=document.getElementById("launch-markers").value.trim(),o=document.getElementById("launch-tests").value.split(/\r?\n/).map(u=>u.trim()).filter(Boolean),d=Array.from(document.querySelectorAll('input[name="reporter"]:checked')).map(u=>u.value),f=(p=document.getElementById("launch-quarantine"))==null?void 0:p.checked;try{const{launcher:u}=await Q({profile:s,tests:o,markers:c||void 0,device_serial:i||void 0,reporters:d.length?d:void 0,include_quarantined:!!f});t&&(t.textContent=JSON.stringify(u,null,2)),location.hash="/live"}catch(u){t&&(t.textContent=String(u))}})()}),(r=document.getElementById("launch-stop"))==null||r.addEventListener("click",()=>{(async()=>{try{const{launcher:s}=await A();t&&(t.textContent=JSON.stringify(s,null,2))}catch(s){t&&(t.textContent=String(s))}})()}),a(),window.setInterval(()=>{location.hash.replace(/^#\/?/,"").startsWith("launch")&&a()},2e3)}async function it(){if(await w(),(await _()).read_only)return`<h1>Quarantine</h1>
      <div class="empty">Read-only mode — quarantine management disabled.</div>`;const a=await W(),e=(a.entries||[]).map(r=>`<tr data-testid="quarantine-row">
        <td class="wrap">${n(r.test_id)}</td>
        <td class="wrap">${n(r.reason)}</td>
        <td>${n(r.owner)}</td>
        <td>${n(r.date)}</td>
        <td class="wrap">${n(r.exit_criteria)}</td>
        <td>${n(r.issue??"—")}</td>
        <td><button type="button" class="q-remove" data-id="${n(r.test_id)}">Remove</button></td>
      </tr>`).join("");return`
    <h1>Quarantine</h1>
    <p class="meta">Ledger: <code>${n(a.path)}</code> — same <code>QuarantineLedger</code> as CLI.</p>
    <div class="panel" data-testid="quarantine-add">
      <h2>Add</h2>
      <div class="toolbar">
        <label>test_id <input id="q-id" data-testid="q-id" placeholder="path::test" style="min-width:18rem"/></label>
        <label>owner <input id="q-owner" data-testid="q-owner"/></label>
      </div>
      <div class="toolbar">
        <label>reason <input id="q-reason" data-testid="q-reason" style="min-width:16rem"/></label>
        <label>exit <input id="q-exit" data-testid="q-exit" style="min-width:16rem"/></label>
        <label>issue <input id="q-issue"/></label>
      </div>
      <button type="button" id="q-add" data-testid="q-add">Add to ledger</button>
      <button type="button" id="q-audit" data-testid="q-audit">Limbo audit</button>
    </div>
    <pre class="log" id="q-msg" data-testid="q-msg"></pre>
    <div class="table-wrap">
      <table data-testid="quarantine-table">
        <thead>
          <tr><th>Test</th><th>Reason</th><th>Owner</th><th>Date</th><th>Exit</th><th>Issue</th><th></th></tr>
        </thead>
        <tbody>${e||'<tr><td colspan="7">No quarantine entries.</td></tr>'}</tbody>
      </table>
    </div>
  `}function ot(){var a,e;const t=document.getElementById("q-msg");(a=document.getElementById("q-add"))==null||a.addEventListener("click",()=>{(async()=>{try{await K({test_id:document.getElementById("q-id").value.trim(),owner:document.getElementById("q-owner").value.trim(),reason:document.getElementById("q-reason").value.trim(),exit_criteria:document.getElementById("q-exit").value.trim(),issue:document.getElementById("q-issue").value.trim()||void 0}),location.reload()}catch(r){t&&(t.textContent=String(r))}})()}),(e=document.getElementById("q-audit"))==null||e.addEventListener("click",()=>{(async()=>{try{const r=await z({});t&&(t.textContent=r.summary)}catch(r){t&&(t.textContent=String(r))}})()}),document.querySelectorAll(".q-remove").forEach(r=>{r.addEventListener("click",()=>{(async()=>{const s=r.dataset.id||"";try{await V(s),location.reload()}catch(i){t&&(t.textContent=String(i))}})()})})}async function dt(){if(await w(),(await _()).read_only)return`<h1>Profiles</h1>
      <div class="empty">Read-only mode — profile editor disabled.</div>`;const{profiles:a,path:e}=await P(),r=a.map(l=>`<option value="${n(l)}">${n(l)}</option>`).join(""),s=a[0]||"";let i="{}",c="";if(s){const l=await R(s);i=JSON.stringify(l.fields,null,2),c=(l.secret_env_names||[]).map(o=>`<code>${n(o)}</code>`).join(" ")}return`
    <h1>Profile editor</h1>
    <p class="meta">Config: <code>${n(e)}</code>. Secrets are env names only — never values.</p>
    <div class="toolbar">
      <label>profile
        <select id="prof-name" data-testid="prof-name">${r}</select>
      </label>
      <button type="button" id="prof-load" data-testid="prof-load">Load</button>
      <button type="button" id="prof-validate" data-testid="prof-validate">Validate</button>
      <button type="button" id="prof-preview" data-testid="prof-preview">Diff preview</button>
      <button type="button" id="prof-save" data-testid="prof-save">Save</button>
    </div>
    <p class="meta">Secret env slots: ${c||"—"}</p>
    <textarea id="prof-fields" data-testid="prof-fields" rows="18" class="code">${n(i)}</textarea>
    <pre class="log" id="prof-msg" data-testid="prof-msg"></pre>
  `}function lt(){var s,i,c,l;const t=document.getElementById("prof-msg"),a=document.getElementById("prof-fields"),e=document.getElementById("prof-name"),r=()=>a?JSON.parse(a.value):{};(s=document.getElementById("prof-load"))==null||s.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",d=await R(o);a&&(a.value=JSON.stringify(d.fields,null,2)),t&&(t.textContent=`loaded ${o}`)}catch(o){t&&(t.textContent=String(o))}})()}),(i=document.getElementById("prof-validate"))==null||i.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",d=await D(o,r());t&&(t.textContent=d.ok?`OK
${JSON.stringify(d.settings_summary,null,2)}`:d.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()}),(c=document.getElementById("prof-preview"))==null||c.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",d=await E(o,r(),!1);t&&(t.textContent=d.diff||"(no diff)")}catch(o){t&&(t.textContent=String(o))}})()}),(l=document.getElementById("prof-save"))==null||l.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",d=await E(o,r(),!0);t&&(t.textContent=d.saved?`saved
${d.diff}`:d.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()})}function I(t,a="var(--accent)"){const e=t.map(d=>Number(d.v??0));if(!e.length)return'<span class="meta">no samples</span>';const r=Math.min(...e),s=Math.max(...e),i=Math.max(1e-9,s-r),c=320,l=64,o=e.map((d,f)=>{const p=f/Math.max(1,e.length-1)*c,u=l-(d-r)/i*(l-4)-2;return`${p.toFixed(1)},${u.toFixed(1)}`}).join(" ");return`<svg class="spark" viewBox="0 0 ${c} ${l}" width="${c}" height="${l}">
    <polyline fill="none" stroke="${a}" stroke-width="1.5" points="${o}"/>
  </svg>`}async function ct(){var s;const t=await B({}),a=t.runs.map(i=>`<option value="${n(i.id)}">${n(i.id.slice(0,8))}… · ${n(i.profile)}</option>`).join(""),e=((s=t.runs[0])==null?void 0:s.id)||"";let r='<div class="empty">Pick a run to load perf series.</div>';if(e){const i=await O(e);r=T(e,i.series,i.summary)}return`
    <h1>Perf graphs</h1>
    <p class="meta">Same data as <code>questline perf report</code>, with overlays and compare.</p>
    <div class="toolbar">
      <label>run
        <select id="perf-run" data-testid="perf-run">${a}</select>
      </label>
      <button type="button" id="perf-load" data-testid="perf-load">Load series</button>
    </div>
    <div id="perf-series" data-testid="perf-series">${r}</div>
    <h2>Build-over-build compare</h2>
    <div class="toolbar">
      <label>A (baseline)
        <select id="perf-a" data-testid="perf-a">${a}</select>
      </label>
      <label>B
        <select id="perf-b" data-testid="perf-b">${a}</select>
      </label>
      <button type="button" id="perf-compare" data-testid="perf-compare">Compare</button>
    </div>
    <div id="perf-compare-out" data-testid="perf-compare-out"></div>
    <script>
      // defaults selected via DOM after paint
    <\/script>
  `}function T(t,a,e){const r=Object.keys(a);return r.length?r.map(s=>{var c,l;const i=e[s]||{};return`<div class="panel" data-testid="perf-metric">
        <h2>${n(s)} <span class="meta">avg ${n(((l=(c=i.avg)==null?void 0:c.toFixed)==null?void 0:l.call(c,2))??"—")} · n ${n(i.count??0)}</span></h2>
        ${I(a[s]||[])}
      </div>`}).join(""):`<div class="empty">No perf samples for ${n(t)}.</div>`}function ut(){var i,c;const t=document.getElementById("perf-series"),a=document.getElementById("perf-compare-out"),e=document.getElementById("perf-run"),r=document.getElementById("perf-a"),s=document.getElementById("perf-b");r&&s&&s.options.length>1&&(s.selectedIndex=1),(i=document.getElementById("perf-load"))==null||i.addEventListener("click",()=>{(async()=>{const l=(e==null?void 0:e.value)||"";if(!(!l||!t))try{const o=await O(l);t.innerHTML=T(l,o.series,o.summary)}catch(o){t.textContent=String(o)}})()}),(c=document.getElementById("perf-compare"))==null||c.addEventListener("click",()=>{(async()=>{const l=(r==null?void 0:r.value)||"",o=(s==null?void 0:s.value)||"";if(a)try{const d=await G(l,o),f=d.deltas.map(u=>{var v,m,y,k,x,q;return`<tr>
              <td>${n(u.metric)}</td>
              <td>${n(((y=(m=(v=u.a)==null?void 0:v.avg)==null?void 0:m.toFixed)==null?void 0:y.call(m,2))??"—")}</td>
              <td>${n(((q=(x=(k=u.b)==null?void 0:k.avg)==null?void 0:x.toFixed)==null?void 0:q.call(x,2))??"—")}</td>
              <td>${u.delta_avg==null?"—":n(u.delta_avg.toFixed(2))}</td>
            </tr>`}).join(""),p=Object.keys(d.series_a).map(u=>{const v=d.series_a[u]||[],m=d.series_b[u]||[];return`<div class="panel">
              <h2>${n(u)} overlay</h2>
              <div class="toolbar">
                <span class="meta">A</span>${I(v,"var(--accent)")}
                <span class="meta">B</span>${I(m,"var(--ok)")}
              </div>
            </div>`}).join("");a.innerHTML=`
          <div class="table-wrap">
            <table data-testid="perf-delta-table">
              <thead><tr><th>Metric</th><th>A avg</th><th>B avg</th><th>Δ avg</th></tr></thead>
              <tbody>${f||'<tr><td colspan="4">No metrics</td></tr>'}</tbody>
            </table>
          </div>
          ${p}`}catch(d){a.textContent=String(d)}})()})}const L=document.querySelector("#app");let g=!1;function C(t,a){const e=(s,i)=>`<a href="${s}" class="${t===i?"active":""}">${i}</a>`,r=g?"":`${e("#/launch","Launch")}
        ${e("#/quarantine","Quarantine")}
        ${e("#/profiles","Profiles")}`;return`
    <header class="topbar">
      <a class="brand" href="#/">Questline <span>HUD</span></a>
      <nav class="nav">
        ${e("#/","Runs")}
        ${r}
        ${e("#/perf","Perf")}
        ${e("#/trends","Trends")}
        ${e("#/live","Live")}
      </nav>
      ${g?'<span class="badge warn" title="--read-only">RO</span>':""}
    </header>
    <main class="main">${a}</main>
  `}function pt(){const a=(location.hash.replace(/^#\/?/,"")||"").split("/").filter(Boolean);return a[0]==="runs"&&a[1]&&a[2]==="tests"&&a[3]?{name:"test",params:{runId:a[1],testId:a[3]}}:a[0]==="runs"&&a[1]?{name:"run",params:{runId:a[1]}}:a[0]==="trends"?{name:"trends",params:{}}:a[0]==="live"?{name:"live",params:{}}:a[0]==="launch"?{name:"launch",params:{}}:a[0]==="quarantine"?{name:"quarantine",params:{}}:a[0]==="profiles"?{name:"profiles",params:{}}:a[0]==="perf"?{name:"perf",params:{}}:{name:"runs",params:{}}}function ft(t){return t.length?`
    <div class="table-wrap">
      <table data-testid="runs-table">
        <thead>
          <tr>
            <th>Run</th><th>Profile</th><th>Driver</th><th>Device</th>
            <th>Status</th><th>Pass</th><th>Infra</th><th>Test</th>
            <th>Duration</th><th>Started</th>
          </tr>
        </thead>
        <tbody>${t.map(e=>`
    <tr data-testid="run-row" data-run-id="${n(e.id)}">
      <td class="wrap"><a href="#/runs/${n(e.id)}">${n(e.id.slice(0,8))}…</a></td>
      <td>${n(e.profile)}</td>
      <td>${n(e.driver??"—")}</td>
      <td>${n(e.device??"—")}</td>
      <td><span class="badge ${n(e.status)}">${n(e.status)}</span></td>
      <td>${e.passed}/${e.total}</td>
      <td class="verdict-infra">${e.infra_failures}</td>
      <td class="verdict-test">${e.test_failures}</td>
      <td>${n($(e.duration_s))}</td>
      <td>${n(e.started_at??"")}</td>
    </tr>`).join("")}</tbody>
      </table>
    </div>`:`<div class="empty" data-testid="empty-store">
      No runs in the store yet.<br/>
      Use <a href="#/launch">Launch</a> or run a suite with the questline plugin, then refresh.
    </div>`}async function ht(){const t=new URLSearchParams(location.hash.split("?")[1]||""),a=t.get("profile")||"",e=t.get("status")||"",r=await B({profile:a||void 0,status:e||void 0});return`
    <h1>Runs</h1>
    <div class="toolbar">
      <label>profile <input id="f-profile" value="${n(a)}" placeholder="any"/></label>
      <label>status
        <select id="f-status">
          <option value="">any</option>
          ${["passed","failed","running","error"].map(s=>`<option value="${s}" ${e===s?"selected":""}>${s}</option>`).join("")}
        </select>
      </label>
      <button type="button" id="f-apply">Filter</button>
      ${g?"":'<a class="btn" href="#/launch">Launch run</a>'}
    </div>
    ${ft(r.runs)}
  `}async function j(){const t=pt();try{let a="",e="Runs";t.name==="run"?(a=await Z(t.params.runId),e="Runs"):t.name==="test"?(a=await tt(t.params.runId,t.params.testId),e="Runs"):t.name==="trends"?(a=await et(),e="Trends"):t.name==="live"?(a=await at(),e="Live"):t.name==="launch"?(a=await st(),e="Launch"):t.name==="quarantine"?(a=await it(),e="Quarantine"):t.name==="profiles"?(a=await dt(),e="Profiles"):t.name==="perf"?(a=await ct(),e="Perf"):(a=await ht(),e="Runs"),L.innerHTML=C(e,a),mt(t.name)}catch(a){L.innerHTML=C("Runs",`<div class="empty">Failed to load HUD: ${n(String(a))}</div>`)}}function mt(t){var a;if(t==="runs"&&((a=document.getElementById("f-apply"))==null||a.addEventListener("click",()=>{const e=document.getElementById("f-profile").value.trim(),r=document.getElementById("f-status").value,s=new URLSearchParams;e&&s.set("profile",e),r&&s.set("status",r);const i=s.toString();location.hash=i?`/?${i}`:"/"})),t==="live"){const e=document.getElementById("live-root");e&&nt(e)}t==="launch"&&rt(),t==="quarantine"&&ot(),t==="profiles"&&lt(),t==="perf"&&ut()}async function vt(){try{g=!!(await _()).read_only,g||await w()}catch{g=!1}await j()}window.addEventListener("hashchange",()=>{j()});vt();
