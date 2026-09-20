(function(){const n=document.createElement("link").relList;if(n&&n.supports&&n.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))s(i);new MutationObserver(i=>{for(const r of i)if(r.type==="childList")for(const d of r.addedNodes)d.tagName==="LINK"&&d.rel==="modulepreload"&&s(d)}).observe(document,{childList:!0,subtree:!0});function e(i){const r={};return i.integrity&&(r.integrity=i.integrity),i.referrerPolicy&&(r.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?r.credentials="include":i.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function s(i){if(i.ep)return;i.ep=!0;const r=e(i);fetch(i.href,r)}})();let C=null;async function y(t){const n=await fetch(t),e=await n.text();if(/^\s*</.test(e)||(n.headers.get("content-type")||"").includes("text/html"))throw new Error(`${n.status} ${t}: got HTML instead of JSON. Restart questline hud (old process missing new /api routes).`);if(!n.ok)throw new Error(`${n.status} ${t}: ${e}`);try{return JSON.parse(e)}catch(i){throw new Error(`${t}: invalid JSON (${String(i)})`)}}async function q(){return C||(C=(await y("/api/csrf")).csrf_token,C)}async function S(t,n,e){const s=await q(),i=await fetch(n,{method:t,headers:{"Content-Type":"application/json","X-CSRF-Token":s},body:e===void 0?void 0:JSON.stringify(e)});if(!i.ok){const r=await i.text();throw new Error(`${i.status} ${n}: ${r}`)}if(i.status!==204)return await i.json()}function x(){return y("/api/meta")}function D(t){const n=new URLSearchParams;t.profile&&n.set("profile",t.profile),t.status&&n.set("status",t.status);const e=n.toString();return y(`/api/runs${e?`?${e}`:""}`)}function tt(t){return y(`/api/runs/${encodeURIComponent(t)}`)}function et(t,n){const e=new URLSearchParams({id:n});return y(`/api/runs/${encodeURIComponent(t)}/test?${e.toString()}`)}function nt(t=50){return y(`/api/trends?limit=${t}`)}function N(t){const n=t?`?config=${encodeURIComponent(t)}`:"";return y(`/api/profiles${n}`)}function at(){return y("/api/configs")}function J(){return y("/api/devices")}function F(t){return y(`/api/profiles/${encodeURIComponent(t)}`)}function st(t,n){return S("POST",`/api/profiles/${encodeURIComponent(t)}/validate`,{fields:n,apply:!1})}function R(t,n,e){return S("POST",`/api/profiles/${encodeURIComponent(t)}`,{fields:n,apply:e})}function it(){return y("/api/reporters")}function H(){return y("/api/launcher")}function rt(t){return S("POST","/api/launcher/start",t)}function ot(){return S("POST","/api/launcher/stop")}function dt(){return y("/api/quarantine")}function lt(t){return S("POST","/api/quarantine",t)}function ct(t){return S("DELETE",`/api/quarantine?test_id=${encodeURIComponent(t)}`)}function ut(t){return S("POST","/api/quarantine/audit",t||{})}function W(t){return y(`/api/perf/${encodeURIComponent(t)}`)}function pt(t,n){return y(`/api/perf/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(n)}`)}function ft(t=50){return y(`/api/perf/correlation?limit=${t}`)}function mt(t){return`/api/artifacts/file?path=${encodeURIComponent(t)}`}function G(){return y("/api/lens/snapshots")}function ht(t,n){const e=new URLSearchParams({a:t,b:n});return y(`/api/lens/diff?${e.toString()}`)}function vt(){return y("/api/telemetry/sessions")}function gt(t){return y(`/api/telemetry/sessions/${encodeURIComponent(t)}`)}function $t(){return y("/api/lens/agent/turns")}function yt(t){return y(`/api/lens/agent/turns/${encodeURIComponent(t)}`)}function bt(t){return S("POST","/api/lens/agent/run",t)}function Q(t){return y(`/api/runs/${encodeURIComponent(t)}/agent-tasks`)}function wt(t){return S("POST","/api/agents/triage",t)}function St(t){return S("POST","/api/agents/diagnose",t)}function _t(t){return S("POST","/api/agents/heal",t)}function k(t){if(t==null||Number.isNaN(t))return"—";if(t<60)return`${t.toFixed(1)}s`;const n=Math.floor(t/60),e=t-n*60;return`${n}m ${e.toFixed(0)}s`}function a(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function kt(t){const n=await tt(t),e=n.run,s=n.banner,i=n.tests.map(p=>`
    <tr data-testid="test-row" data-test-id="${a(p.id)}">
      <td class="wrap"><a href="#/runs/${encodeURIComponent(t)}/tests/${encodeURIComponent(p.id)}">${a(p.nodeid)}</a></td>
      <td><span class="badge ${a(p.status)}">${a(p.status)}</span></td>
      <td class="verdict-${a(p.verdict??"")}">${a(p.verdict??"—")}</td>
      <td>${a(k(p.duration_s))}</td>
      <td class="wrap">${a(p.death_step_name??"")}</td>
    </tr>`).join(""),d=(n.ai_calls||[]).map(p=>`
    <tr data-testid="ai-call-row">
      <td>${a(p.provider??"—")}</td>
      <td class="wrap">${a(p.model??"—")}</td>
      <td>${a(p.tokens_in??0)}</td>
      <td>${a(p.tokens_out??0)}</td>
      <td>${a(A(p.cost))}</td>
      <td>${a(p.outcome??"—")}</td>
      <td class="wrap">${a(p.purpose??"")}</td>
    </tr>`).join("")||'<tr><td colspan="7">No AI calls for this run.</td></tr>',c=n.tests.some(p=>p.status==="failed"||p.status==="error");let o=!0;try{o=!(await x()).read_only}catch{o=!0}let l=[];try{l=(await Q(t)).tasks||[]}catch{l=[]}return`
    <p class="meta"><a href="#/">← Runs</a> · ${a(e.id)}</p>
    <h1>Run detail</h1>
    <div class="meta">
      profile=${a(e.profile)} · driver=${a(e.driver??"—")} ·
      device=${a(e.device??"—")} · status=${a(e.status)} ·
      duration=${a(k(e.duration_s))}
    </div>
    <div class="banner" data-testid="verdict-banner">
      <div class="stat ok"><span>passed</span><b>${e.passed}</b></div>
      <div class="stat"><span>failed</span><b>${e.failed}</b></div>
      <div class="stat infra"><span>infra</span><b>${s.infra_failures}</b></div>
      <div class="stat test"><span>test</span><b>${s.test_failures}</b></div>
      <div class="stat"><span>authoring</span><b>${s.authoring_failures}</b></div>
    </div>
    ${c&&o?`<div class="toolbar" data-testid="agent-run-actions">
      <button type="button" id="triage-run" data-testid="triage-run">Triage this run</button>
      <span id="triage-msg" class="meta" data-testid="triage-msg"></span>
    </div>
    <div id="triage-result" data-testid="triage-result">${xt(l)}</div>
    <script type="application/json" id="run-agent-ctx">${JSON.stringify({runId:t})}<\/script>`:""}
    <h2>AI calls</h2>
    <div class="meta">total_usd=${a(A(n.ai_cost_total))}</div>
    <div class="table-wrap">
      <table data-testid="ai-calls-table">
        <thead>
          <tr>
            <th>Provider</th><th>Model</th><th>In</th><th>Out</th>
            <th>Cost</th><th>Outcome</th><th>Purpose</th>
          </tr>
        </thead>
        <tbody>${d}</tbody>
      </table>
    </div>
    <h2>Tests</h2>
    <div class="table-wrap">
      <table data-testid="tests-table">
        <thead>
          <tr><th>Test</th><th>Status</th><th>Verdict</th><th>Duration</th><th>Death step</th></tr>
        </thead>
        <tbody>${i||`<tr><td colspan="5">${e.status==="failed"||e.status==="error"?'No tests recorded — session setup failed before any test ran (often adb device lock or Wire connect). Open <a href="#/launch">Launch</a> Status → <code>error</code> / <code>log_tail</code>.':"No tests."}</td></tr>`}</tbody>
      </table>
    </div>
  `}function Et(){const t=document.getElementById("triage-run");t==null||t.addEventListener("click",()=>{(async()=>{var r;const n=document.getElementById("triage-msg"),e=document.getElementById("triage-result"),s=(r=document.getElementById("run-agent-ctx"))==null?void 0:r.textContent;let i="";try{i=String(JSON.parse(s||"{}").runId||"")}catch{}if(i){n&&(n.textContent="running…");try{const d=await wt({run_id:i});n&&(n.textContent=`status=${d.task.status} verdict=${d.task.verdict}`),e&&(e.innerHTML=K(d.task))}catch(d){n&&(n.textContent=String(d))}}})()})}function xt(t){return t.length?t.map(K).join(""):'<p class="meta">No agent tasks yet.</p>'}function K(t){const n=(t.clusters||[]).map(e=>{const s=String(e.bucket??e.key??""),i=String(e.error_type??""),r=Array.isArray(e.test_ids)?e.test_ids.length:"",d=String(e.hypothesis??e.signature??"");return`<li>${a(s)} · ${a(i)} x${a(r)} — ${a(d)}</li>`}).join("");return`
    <div class="panel" data-testid="agent-task" data-task-kind="${a(t.kind??"")}">
      <div class="meta">kind=${a(t.kind??"")} · verdict=${a(t.verdict??"")}
        · cause=${a(t.cause??"")} · status=${a(t.status??"")}</div>
      <p>${a(t.summary??"")}</p>
      ${n?`<ul data-testid="triage-clusters">${n}</ul>`:""}
    </div>`}function A(t){return t==null||Number.isNaN(t)?"0.000000":t.toFixed(6)}async function It(t,n){const e=await et(t,n),s=e.test,i=e.steps.map(u=>{const g=String(u.status??"");return`<li data-testid="step-row">
        <span class="ts">${a(u.started_at??"")}</span>
        <span class="badge ${a(g)}">${a(g)}</span>
        <span>${a(u.name??"")}${u.error_message?` — ${a(u.error_message)}`:""}</span>
      </li>`}).join(""),r=(e.history||[]).map(u=>{const g=String(u.status??""),b=Number(u.duration_s??0)||1,w=Math.max(4,Math.min(28,b*4));return`<i class="${a(g)}" style="height:${w}px" title="${a(g)}"></i>`}).join(""),d=e.death_point||{},c=d.last_started_step||{},o=d.driver_health||{},l=s.verdict==="infra"?"infra":"",p=(e.artifacts||[]).map(u=>{const g=String(u.path??""),b=String(u.kind??""),w=String(u.name??g),h=mt(g);return b==="screenshot"||/\.(png|jpe?g|webp|gif)$/i.test(w)?`<div><a href="${a(h)}" target="_blank" rel="noreferrer">
          <img src="${a(h)}" alt="${a(w)}"/><div>${a(w)}</div></a></div>`:`<div><a href="${a(h)}" target="_blank" rel="noreferrer">${a(w)}</a>
        <div class="meta">${a(b)} · ${a(u.size_bytes??"")} B</div></div>`}).join(""),$=s.status==="failed"||s.status==="error";let v=!0;try{v=!(await x()).read_only}catch{v=!0}const f=String(s.error_type??"").includes("ElementNotFound");let m=[];try{m=((await Q(t)).tasks||[]).filter(g=>!g.test_id||g.test_id===n)}catch{m=[]}return`
    <p class="meta">
      <a href="#/">Runs</a> /
      <a href="#/runs/${a(t)}">${a(t.slice(0,8))}…</a>
    </p>
    <h1 data-testid="test-title">${a(s.nodeid)}</h1>
    <div class="meta">
      status=<span class="badge ${a(s.status)}">${a(s.status)}</span> ·
      verdict=<span class="verdict-${a(s.verdict??"")}">${a(s.verdict??"—")}</span> ·
      duration=${a(k(s.duration_s))}
    </div>

    ${$&&v?`<div class="toolbar" data-testid="agent-test-actions">
      <button type="button" id="diagnose-test" data-testid="diagnose-test">Diagnose this test</button>
      <button type="button" id="fix-test" data-testid="fix-test">Fix this test</button>
      ${f?'<button type="button" id="heal-test" data-testid="heal-test">Suggest locator</button>':""}
      <span id="diagnose-msg" class="meta" data-testid="diagnose-msg"></span>
    </div>
    <div id="diagnose-result" data-testid="diagnose-result">${qt(m)}</div>
    <script type="application/json" id="test-agent-ctx">${JSON.stringify({runId:t,testId:n,locatorMiss:f})}<\/script>`:""}

    <div class="panel death ${l}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${a(c.name??"—")}</b>
        @ ${a(c.started_at??"")}</div>
      <div>error: ${a(s.error_type??"")} — ${a(s.error_message??"")}</div>
      <div>driver health: ${a(JSON.stringify(o||{}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${r||"<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${i||"<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${p||"<span class='meta'>none</span>"}</div>
  `}function Lt(){var r,d,c;const t=document.getElementById("test-agent-ctx");let n="",e="";try{const o=JSON.parse((t==null?void 0:t.textContent)||"{}");n=o.runId||"",e=o.testId||""}catch{return}const s=()=>document.getElementById("diagnose-msg"),i=()=>document.getElementById("diagnose-result");(r=document.getElementById("diagnose-test"))==null||r.addEventListener("click",()=>{T("diagnose",n,e,s(),i())}),(d=document.getElementById("fix-test"))==null||d.addEventListener("click",()=>{window.confirm("Fix mode writes files under the project jail and re-runs the test. Continue?")&&T("fix",n,e,s(),i())}),(c=document.getElementById("heal-test"))==null||c.addEventListener("click",()=>{T("heal",n,e,s(),i())})}async function T(t,n,e,s,i){if(!(!n||!e)){s&&(s.textContent="running…");try{const r=t==="heal"?await _t({run_id:n,test_id:e}):await St({run_id:n,test_id:e,fix:t==="fix"});s&&(s.textContent=`status=${r.task.status} verdict=${r.task.verdict}`),i&&(i.innerHTML=V(r.task))}catch(r){s&&(s.textContent=String(r))}}}function qt(t){return t.length?t.map(V).join(""):""}function V(t){const n=t.suggestion||{},e=typeof n.yaml_diff=="string"?n.yaml_diff:"",s=t.gate?`gate accepted=${a(String(t.gate.accepted??""))}`:"";return`
    <div class="panel" data-testid="agent-task" data-task-kind="${a(t.kind??"")}">
      <div class="meta">kind=${a(t.kind??"")} · verdict=${a(t.verdict??"")}
        · cause=${a(t.cause??"")} ${s}</div>
      <p>${a(t.summary??"")}</p>
      ${e?`<pre data-testid="heal-diff">${a(e)}</pre>`:""}
    </div>`}async function Ct(){const[t,n]=await Promise.all([nt(50),ft(50)]),e=t.series||[],s=Math.max(1,...e.map(o=>Number(o.duration_s??0)||0)),i=e.map(o=>{const l=o.pass_rate==null?0:Number(o.pass_rate),p=Math.max(4,Math.round(l*100)),$=Number(o.duration_s??0);return`<div class="bar ${Number(o.failed??0)>0?"fail":""}" style="height:${p}%">
        <span>${a(o.run_id)} · ${(l*100).toFixed(0)}% · ${a(k($))}</span>
      </div>`}).join(""),r=e.map(o=>{const l=Number(o.duration_s??0);return`<div class="bar" style="height:${Math.max(4,Math.round(l/s*100))}%">
        <span>${a(o.run_id)} · ${a(k(l))}</span>
      </div>`}).join(""),d=(t.flaky_tests||[]).map(o=>`<tr>
        <td class="wrap">${a(o.nodeid)}</td>
        <td>${a(o.runs)}</td>
        <td>${a(o.passed)}/${a(o.failed)}</td>
        <td>${(Number(o.pass_rate)*100).toFixed(0)}%</td>
        <td>${(Number(o.flake_score)*100).toFixed(0)}%</td>
      </tr>`).join(""),c=(n.tests||[]).map(o=>{const l=(o.points||[]).map(p=>{const $=p.duration_s==null?0:Number(p.duration_s);return`<span class="dot ${p.passed?"ok":"bad"}" title="${a(p.run_id)} · ${a(k($))}"></span>`}).join("");return`<tr>
        <td class="wrap">${a(o.nodeid)}</td>
        <td>${o.passed}/${o.failed}</td>
        <td class="corr-dots">${l}</td>
      </tr>`}).join("");return`
    <h1>Trends</h1>
    <h2>Pass rate (recent runs)</h2>
    <div class="chart" data-testid="pass-chart">${i||"<span class='meta'>no data</span>"}</div>
    <h2>Duration</h2>
    <div class="chart" data-testid="dur-chart">${r||"<span class='meta'>no data</span>"}</div>
    <h2>Flakiness board</h2>
    <div class="table-wrap">
      <table data-testid="flaky-table">
        <thead>
          <tr><th>Test</th><th>Runs</th><th>P/F</th><th>Pass%</th><th>Flake</th></tr>
        </thead>
        <tbody>${d||'<tr><td colspan="5">No flaky tests detected.</td></tr>'}</tbody>
      </table>
    </div>
    <h2>Duration vs pass (correlation)</h2>
    <p class="meta">Green = pass, red = fail per run (same flaky nodeids).</p>
    <div class="table-wrap">
      <table data-testid="corr-table">
        <thead><tr><th>Test</th><th>P/F</th><th>Runs</th></tr></thead>
        <tbody>${c||'<tr><td colspan="3">No mixed pass/fail series yet.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function Bt(){return`
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `}function Pt(t){const n=document.getElementById("live-status"),e=document.getElementById("live-clear");e==null||e.addEventListener("click",()=>{t.innerHTML=""});const i=`${location.protocol==="https:"?"wss":"ws"}://${location.host}/live`;let r;try{r=new WebSocket(i)}catch(d){n&&(n.textContent="failed"),t.innerHTML=`<div>WebSocket error: ${a(String(d))}</div>`;return}r.onopen=()=>{n&&(n.textContent="live",n.className="badge passed")},r.onclose=()=>{n&&(n.textContent="closed",n.className="badge failed")},r.onerror=()=>{n&&(n.textContent="error",n.className="badge failed")},r.onmessage=d=>{try{const c=JSON.parse(String(d.data)),o=String(c.type??"?"),l=String(c.timestamp??""),p=c.nodeid||c.name||c.test_id||c.status||c.profile||"",$=document.createElement("div");$.innerHTML=`<span class="t">${a(l)}</span><b>${a(o)}</b> ${a(p)}`,t.prepend($)}catch{const c=document.createElement("div");c.textContent=String(d.data),t.prepend(c)}}}const X=[{id:"mock",label:"Mock demo",config:"questline.toml",profile:"mock",tests:"examples/demo-tests",live_target:!1,note:"No Unity. CI-style mock driver."},{id:"wire-editor",label:"Wire Editor",config:"examples/wire-smoke/questline.toml",profile:"editor",tests:"examples/wire-smoke",live_target:!0,note:"Unity Play + Wire on :13000. Device picker stays empty (OK)."},{id:"wire-android",label:"Wire Android",config:"examples/wire-smoke/questline.toml",profile:"android_local",tests:"examples/wire-smoke",live_target:!0,note:"Dev APK + adb. Pick a serial if more than one device."}];async function Nt(){var g,b,w;await q();let t,n,e,s;try{[t,n,e,s]=await Promise.all([x(),at().catch(()=>({project_root:"",active:"",configs:[{path:"questline.toml",absolute:"questline.toml"}]})),it().catch(()=>({reporters:["console"]})),H().catch(()=>({launcher:{state:"idle"}}))])}catch(h){return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-error">
        Failed to load launcher APIs: ${a(String(h))}<br/>
        Stop the old <code>questline hud</code> process and start it again from
        <code>D:\\dev\\questline</code>.
      </div>`}if(t.read_only)return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;const i=((g=n.configs.find(h=>h.path.replace(/\\/g,"/")==="questline.toml"))==null?void 0:g.path)||((b=n.configs[0])==null?void 0:b.path)||"questline.toml",r=await N(i),d=await J(),c=(n.configs||[]).map(h=>{const I=h.path===i?"selected":"";return`<option value="${a(h.path)}" ${I}>${a(h.path)}</option>`}).join(""),o=(r.profiles||[]).map(h=>{const I=r.profiles.includes("editor")?"editor":r.profiles.includes("mock")?"mock":r.profiles[0]||"";return`<option value="${a(h)}" ${h===I?"selected":""}>${a(h)}</option>`}).join(""),l=['<option value="">(no adb pin — OK for Editor)</option>',...(d.devices||[]).map(h=>`<option value="${a(h.id)}">${a(h.id)} · ${a(h.platform)}</option>`)].join(""),p=(e.reporters||[]).map(h=>`<label class="check"><input type="checkbox" name="reporter" value="${a(h)}" ${h==="console"?"checked":""}/> ${a(h)}</label>`).join(""),$=X.map(h=>`<button type="button" class="preset" data-preset="${a(h.id)}" title="${a(h.note)}">${a(h.label)}</button>`).join(""),v=s.launcher,f=["starting","running","stopping"].includes(v.state||""),m=d.hint||((w=d.devices)!=null&&w.length?`${d.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire.");return`
    <h1>Run launcher</h1>
    ${f?`<div class="empty" data-testid="launch-busy">
        A managed run is <strong>${a(v.state||"")}</strong>
        (job <code>${a(v.job_id||"")}</code>, profile
        <code>${a(v.profile||"")}</code>).
        <a href="#/live">Open Live</a> to watch it, or <strong>Stop</strong> below
        before launching another.
      </div>`:""}
    <p class="meta">Profiles come from <code>questline.toml</code> (not from Unity being open).
      Unity Play + Wire = use preset <strong>Wire Editor</strong> or profile <code>editor</code>.
      Device list is <em>adb only</em> — Editor does not appear there.</p>
    <div class="toolbar" data-testid="launch-presets">
      <span class="meta">Presets:</span> ${$}
    </div>
    <div class="panel" data-testid="launch-form">
      <div class="toolbar">
        <label>config
          <select id="launch-config" data-testid="launch-config">${c}</select>
        </label>
        <label>profile
          <select id="launch-profile" data-testid="launch-profile">${o}</select>
        </label>
        <label>device
          <select id="launch-device" data-testid="launch-device">${l}</select>
        </label>
        <button type="button" id="launch-refresh-devices" data-testid="launch-refresh-devices">Refresh devices</button>
      </div>
      <p class="meta" id="launch-device-hint" data-testid="launch-device-hint">${a(m)}</p>
      ${d.error?`<p class="meta">adb error: ${a(d.error)}</p>`:""}
      <label class="block">markers <input id="launch-markers" placeholder="optional -m expression" data-testid="launch-markers"/></label>
      <label class="block">tests (one path/nodeid per line)
        <textarea id="launch-tests" rows="4" data-testid="launch-tests" placeholder="examples/wire-smoke">examples/demo-tests</textarea>
      </label>
      <div class="toolbar wrap">${p||"<span class='meta'>no reporters</span>"}</div>
      <label class="check"><input type="checkbox" id="launch-quarantine"/> include quarantined</label>
      <label class="check"><input type="checkbox" id="launch-live" data-testid="launch-live"/> QUESTLINE_LIVE_TARGET=1 (required for wire-smoke)</label>
      <div class="toolbar">
        <button type="button" id="launch-start" data-testid="launch-start" ${f?"disabled":""}>Launch</button>
        <button type="button" id="launch-stop" data-testid="launch-stop" ${f?"":"disabled"}>Stop</button>
        ${f?'<a class="button" href="#/live" data-testid="launch-open-live">Open Live</a>':""}
      </div>
      <p class="meta">Active project: <code>${a(n.project_root)}</code></p>
    </div>
    <h2>Status</h2>
    <pre class="log" id="launch-status" data-testid="launch-status">${a(JSON.stringify(v,null,2))}</pre>
  `}function Ot(){var p,$,v;const t=document.getElementById("launch-status"),n=document.getElementById("launch-config"),e=document.getElementById("launch-profile"),s=document.getElementById("launch-device"),i=document.getElementById("launch-tests"),r=document.getElementById("launch-live"),d=document.getElementById("launch-device-hint"),c=async()=>{if(!(!n||!e))try{const f=await N(n.value),m=f.profiles.includes("editor")?"editor":f.profiles[0]||"";e.innerHTML=f.profiles.map(u=>`<option value="${a(u)}" ${u===m?"selected":""}>${a(u)}</option>`).join("")}catch(f){t&&(t.textContent=String(f))}},o=async()=>{var f;if(s)try{const m=await J();s.innerHTML=['<option value="">(no adb pin — OK for Editor)</option>',...(m.devices||[]).map(u=>`<option value="${a(u.id)}">${a(u.id)} · ${a(u.platform)}</option>`)].join(""),d&&(d.textContent=m.hint||((f=m.devices)!=null&&f.length?`${m.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire."))}catch(m){d&&(d.textContent=String(m))}};n==null||n.addEventListener("change",()=>{c()}),(p=document.getElementById("launch-refresh-devices"))==null||p.addEventListener("click",()=>{o()}),document.querySelectorAll(".preset").forEach(f=>{f.addEventListener("click",()=>{const m=f.dataset.preset||"",u=X.find(g=>g.id===m);if(u){if(n){if(!Array.from(n.options).some(b=>b.value===u.config)){const b=document.createElement("option");b.value=u.config,b.textContent=u.config,n.appendChild(b)}n.value=u.config}i&&(i.value=u.tests),r&&(r.checked=u.live_target),(async()=>(await c(),e&&(e.value=u.profile)))()}})});const l=async()=>{try{const{launcher:f}=await H();t&&(t.textContent=JSON.stringify(f,null,2));const m=["starting","running","stopping"].includes(f.state||""),u=document.getElementById("launch-start"),g=document.getElementById("launch-stop");u&&(u.disabled=m),g&&(g.disabled=!m)}catch(f){t&&(t.textContent=String(f))}};($=document.getElementById("launch-start"))==null||$.addEventListener("click",()=>{(async()=>{var I;const f=(e==null?void 0:e.value)||"",m=(s==null?void 0:s.value)||"",u=document.getElementById("launch-markers").value.trim(),b=((i==null?void 0:i.value)||"").split(/\r?\n/).map(_=>_.trim()).filter(Boolean),w=Array.from(document.querySelectorAll('input[name="reporter"]:checked')).map(_=>_.value),h=(I=document.getElementById("launch-quarantine"))==null?void 0:I.checked;try{const{launcher:_}=await rt({profile:f,tests:b,markers:u||void 0,device_serial:m||void 0,reporters:w.length?w:void 0,include_quarantined:!!h,config:(n==null?void 0:n.value)||void 0,live_target:!!(r!=null&&r.checked)});t&&(t.textContent=JSON.stringify(_,null,2)),location.hash="/live"}catch(_){const O=String(_);t&&(t.textContent=O),/\b409\b/.test(O)&&/already/i.test(O)&&(location.hash="/live")}})()}),(v=document.getElementById("launch-stop"))==null||v.addEventListener("click",()=>{(async()=>{try{const{launcher:f}=await ot();t&&(t.textContent=JSON.stringify(f,null,2))}catch(f){t&&(t.textContent=String(f))}})()}),l(),window.setInterval(()=>{location.hash.replace(/^#\/?/,"").startsWith("launch")&&l()},2e3)}async function Tt(){if(await q(),(await x()).read_only)return`<h1>Quarantine</h1>
      <div class="empty">Read-only mode — quarantine management disabled.</div>`;const n=await dt(),e=(n.entries||[]).map(s=>`<tr data-testid="quarantine-row">
        <td class="wrap">${a(s.test_id)}</td>
        <td class="wrap">${a(s.reason)}</td>
        <td>${a(s.owner)}</td>
        <td>${a(s.date)}</td>
        <td class="wrap">${a(s.exit_criteria)}</td>
        <td>${a(s.issue??"—")}</td>
        <td><button type="button" class="q-remove" data-id="${a(s.test_id)}">Remove</button></td>
      </tr>`).join("");return`
    <h1>Quarantine</h1>
    <p class="meta">Ledger: <code>${a(n.path)}</code> — same <code>QuarantineLedger</code> as CLI.</p>
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
  `}function jt(){var n,e;const t=document.getElementById("q-msg");(n=document.getElementById("q-add"))==null||n.addEventListener("click",()=>{(async()=>{try{await lt({test_id:document.getElementById("q-id").value.trim(),owner:document.getElementById("q-owner").value.trim(),reason:document.getElementById("q-reason").value.trim(),exit_criteria:document.getElementById("q-exit").value.trim(),issue:document.getElementById("q-issue").value.trim()||void 0}),location.reload()}catch(s){t&&(t.textContent=String(s))}})()}),(e=document.getElementById("q-audit"))==null||e.addEventListener("click",()=>{(async()=>{try{const s=await ut({});t&&(t.textContent=s.summary)}catch(s){t&&(t.textContent=String(s))}})()}),document.querySelectorAll(".q-remove").forEach(s=>{s.addEventListener("click",()=>{(async()=>{const i=s.dataset.id||"";try{await ct(i),location.reload()}catch(r){t&&(t.textContent=String(r))}})()})})}async function Rt(){if(await q(),(await x()).read_only)return`<h1>Profiles</h1>
      <div class="empty">Read-only mode — profile editor disabled.</div>`;const{profiles:n,path:e}=await N(),s=n.map(c=>`<option value="${a(c)}">${a(c)}</option>`).join(""),i=n[0]||"";let r="{}",d="";if(i){const c=await F(i);r=JSON.stringify(c.fields,null,2),d=(c.secret_env_names||[]).map(o=>`<code>${a(o)}</code>`).join(" ")}return`
    <h1>Profile editor</h1>
    <p class="meta">Config: <code>${a(e)}</code>. Secrets are env names only — never values.</p>
    <div class="toolbar">
      <label>profile
        <select id="prof-name" data-testid="prof-name">${s}</select>
      </label>
      <button type="button" id="prof-load" data-testid="prof-load">Load</button>
      <button type="button" id="prof-validate" data-testid="prof-validate">Validate</button>
      <button type="button" id="prof-preview" data-testid="prof-preview">Diff preview</button>
      <button type="button" id="prof-save" data-testid="prof-save">Save</button>
    </div>
    <p class="meta">Secret env slots: ${d||"—"}</p>
    <textarea id="prof-fields" data-testid="prof-fields" rows="18" class="code">${a(r)}</textarea>
    <pre class="log" id="prof-msg" data-testid="prof-msg"></pre>
  `}function At(){var i,r,d,c;const t=document.getElementById("prof-msg"),n=document.getElementById("prof-fields"),e=document.getElementById("prof-name"),s=()=>n?JSON.parse(n.value):{};(i=document.getElementById("prof-load"))==null||i.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",l=await F(o);n&&(n.value=JSON.stringify(l.fields,null,2)),t&&(t.textContent=`loaded ${o}`)}catch(o){t&&(t.textContent=String(o))}})()}),(r=document.getElementById("prof-validate"))==null||r.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",l=await st(o,s());t&&(t.textContent=l.ok?`OK
${JSON.stringify(l.settings_summary,null,2)}`:l.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()}),(d=document.getElementById("prof-preview"))==null||d.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",l=await R(o,s(),!1);t&&(t.textContent=l.diff||"(no diff)")}catch(o){t&&(t.textContent=String(o))}})()}),(c=document.getElementById("prof-save"))==null||c.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",l=await R(o,s(),!0);t&&(t.textContent=l.saved?`saved
${l.diff}`:l.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()})}function j(t,n="var(--accent)"){const e=t.map(l=>Number(l.v??0));if(!e.length)return'<span class="meta">no samples</span>';const s=Math.min(...e),i=Math.max(...e),r=Math.max(1e-9,i-s),d=320,c=64,o=e.map((l,p)=>{const $=p/Math.max(1,e.length-1)*d,v=c-(l-s)/r*(c-4)-2;return`${$.toFixed(1)},${v.toFixed(1)}`}).join(" ");return`<svg class="spark" viewBox="0 0 ${d} ${c}" width="${d}" height="${c}">
    <polyline fill="none" stroke="${n}" stroke-width="1.5" points="${o}"/>
  </svg>`}async function Ut(){var i;const t=await D({}),n=t.runs.map(r=>`<option value="${a(r.id)}">${a(r.id.slice(0,8))}… · ${a(r.profile)}</option>`).join(""),e=((i=t.runs[0])==null?void 0:i.id)||"";let s='<div class="empty">Pick a run to load perf series.</div>';if(e){const r=await W(e);s=z(e,r.series,r.summary)}return`
    <h1>Perf graphs</h1>
    <p class="meta">Same data as <code>questline perf report</code>, with overlays and compare.</p>
    <div class="toolbar">
      <label>run
        <select id="perf-run" data-testid="perf-run">${n}</select>
      </label>
      <button type="button" id="perf-load" data-testid="perf-load">Load series</button>
    </div>
    <div id="perf-series" data-testid="perf-series">${s}</div>
    <h2>Build-over-build compare</h2>
    <div class="toolbar">
      <label>A (baseline)
        <select id="perf-a" data-testid="perf-a">${n}</select>
      </label>
      <label>B
        <select id="perf-b" data-testid="perf-b">${n}</select>
      </label>
      <button type="button" id="perf-compare" data-testid="perf-compare">Compare</button>
    </div>
    <div id="perf-compare-out" data-testid="perf-compare-out"></div>
    <script>
      // defaults selected via DOM after paint
    <\/script>
  `}function z(t,n,e){const s=Object.keys(n);return s.length?s.map(i=>{var d,c;const r=e[i]||{};return`<div class="panel" data-testid="perf-metric">
        <h2>${a(i)} <span class="meta">avg ${a(((c=(d=r.avg)==null?void 0:d.toFixed)==null?void 0:c.call(d,2))??"—")} · n ${a(r.count??0)}</span></h2>
        ${j(n[i]||[])}
      </div>`}).join(""):`<div class="empty">No perf samples for ${a(t)}.</div>`}function Mt(){var r,d;const t=document.getElementById("perf-series"),n=document.getElementById("perf-compare-out"),e=document.getElementById("perf-run"),s=document.getElementById("perf-a"),i=document.getElementById("perf-b");s&&i&&i.options.length>1&&(i.selectedIndex=1),(r=document.getElementById("perf-load"))==null||r.addEventListener("click",()=>{(async()=>{const c=(e==null?void 0:e.value)||"";if(!(!c||!t))try{const o=await W(c);t.innerHTML=z(c,o.series,o.summary)}catch(o){t.textContent=String(o)}})()}),(d=document.getElementById("perf-compare"))==null||d.addEventListener("click",()=>{(async()=>{const c=(s==null?void 0:s.value)||"",o=(i==null?void 0:i.value)||"";if(n)try{const l=await pt(c,o),p=l.deltas.map(v=>{var f,m,u,g,b,w;return`<tr>
              <td>${a(v.metric)}</td>
              <td>${a(((u=(m=(f=v.a)==null?void 0:f.avg)==null?void 0:m.toFixed)==null?void 0:u.call(m,2))??"—")}</td>
              <td>${a(((w=(b=(g=v.b)==null?void 0:g.avg)==null?void 0:b.toFixed)==null?void 0:w.call(b,2))??"—")}</td>
              <td>${v.delta_avg==null?"—":a(v.delta_avg.toFixed(2))}</td>
            </tr>`}).join(""),$=Object.keys(l.series_a).map(v=>{const f=l.series_a[v]||[],m=l.series_b[v]||[];return`<div class="panel">
              <h2>${a(v)} overlay</h2>
              <div class="toolbar">
                <span class="meta">A</span>${j(f,"var(--accent)")}
                <span class="meta">B</span>${j(m,"var(--ok)")}
              </div>
            </div>`}).join("");n.innerHTML=`
          <div class="table-wrap">
            <table data-testid="perf-delta-table">
              <thead><tr><th>Metric</th><th>A avg</th><th>B avg</th><th>Δ avg</th></tr></thead>
              <tbody>${p||'<tr><td colspan="4">No metrics</td></tr>'}</tbody>
            </table>
          </div>
          ${$}`}catch(l){n.textContent=String(l)}})()})}function E(t){const n=(e,s)=>`<a href="${e}" class="${t===s?"active":""}">${s}</a>`;return`<div class="subnav" data-testid="lens-nav">
    ${n("#/lens","Snapshots")}
    ${n("#/lens/diff","Diff")}
    ${n("#/lens/sessions","Sessions")}
    ${n("#/lens/turns","Agent")}
  </div>`}async function Dt(){var d,c,o;const n=(await G()).snapshots||[],e=n.map(l=>`<option value="${a(l.id)}">${a(l.id)} · ${a(l.game_version)}</option>`).join(""),s=((d=n[1])==null?void 0:d.id)||((c=n[0])==null?void 0:c.id)||"",i=((o=n[0])==null?void 0:o.id)||"",r=n.map(l=>`
    <tr data-testid="lens-snap-row" data-snap-id="${a(l.id)}">
      <td class="wrap"><code>${a(l.id)}</code></td>
      <td>${a(l.game_version)}</td>
      <td>${a(l.feature_id??"—")}</td>
      <td>${a(l.created_at??"")}</td>
    </tr>`).join("");return`
    <h1>GameLens</h1>
    ${E("Snapshots")}
    <p class="meta">Config truth from <code>balance_snapshots</code>. AI never invents green/red.</p>
    <div class="toolbar">
      <label>A <select id="lens-a" data-testid="lens-a">${e}</select></label>
      <label>B <select id="lens-b" data-testid="lens-b">${e}</select></label>
      <button type="button" id="lens-open-diff" data-testid="lens-open-diff">Open typed diff</button>
    </div>
    <div class="table-wrap">
      <table data-testid="lens-snapshots">
        <thead><tr><th>Id</th><th>Version</th><th>Feature</th><th>Created</th></tr></thead>
        <tbody>${r||'<tr><td colspan="4">No snapshots in this store.</td></tr>'}</tbody>
      </table>
    </div>
    <script type="application/json" id="lens-defaults">${JSON.stringify({a:s,b:i})}<\/script>
  `}async function Jt(){var v,f,m;const t=(await G()).snapshots||[],n=new URLSearchParams(location.hash.split("?")[1]||""),e=n.get("a")||((v=t[1])==null?void 0:v.id)||((f=t[0])==null?void 0:f.id)||"",s=n.get("b")||((m=t[0])==null?void 0:m.id)||"";if(!e||!s)return`
      <h1>Typed diff</h1>
      ${E("Diff")}
      <div class="empty" data-testid="lens-diff-empty">Pick two snapshots on GameLens.</div>`;const i=await ht(e,s),r=i.diff.entries||[],d=i.diff.by_system||{},o=Object.keys(d).sort().map(u=>{const g=(d[u]||[]).map(b=>`<li data-testid="lens-diff-entry">${a(zt(b))}</li>`).join("");return`<div class="panel"><h3>[${a(u)}]</h3><ul>${g}</ul></div>`}).join(""),l=i.implications;let p=[];try{(await x()).read_only||(p=(await N()).profiles||[])}catch{p=[]}const $=p.filter(u=>u.startsWith("ai_")).concat(p.filter(u=>!u.startsWith("ai_"))).map(u=>{const g=u==="ai_groq"?"selected":"";return`<option value="${a(u)}" ${g}>${a(u)}</option>`}).join("");return`
    <h1>Typed diff</h1>
    ${E("Diff")}
    <p class="meta" data-testid="lens-diff-meta">
      ${a(i.diff.snapshot_id_a||e)} → ${a(i.diff.snapshot_id_b||s)}
      · ${r.length} entries · framing vs measured stay separate
    </p>
    ${o||'<div class="empty">(no differences)</div>'}
    ${Vt(l)}
    <h2>Ask balance agent</h2>
    <p class="meta">Retune <em>priorities</em> only — model reasoning, never SO writes or green/red.</p>
    <div class="panel" data-testid="lens-agent-form">
      <label class="block">profile
        <select id="agent-profile" data-testid="agent-profile">${$||'<option value="ai_groq">ai_groq</option>'}</select>
      </label>
      <label class="block">question
        <textarea id="agent-q" data-testid="agent-q" rows="3">What should a human look at for a retune?</textarea>
      </label>
      <button type="button" id="agent-run" data-testid="agent-run">Ask</button>
      <div id="agent-msg" class="meta" data-testid="agent-msg"></div>
    </div>
    <div id="agent-result"></div>
    <script type="application/json" id="lens-pair">${JSON.stringify({a:e,b:s})}<\/script>
  `}async function Ft(){const n=((await vt()).sessions||[]).map(e=>`
    <tr data-testid="tel-session-row" data-session-id="${a(e.id)}">
      <td class="wrap"><a href="#/lens/sessions/${encodeURIComponent(e.id)}">${a(e.id)}</a></td>
      <td>${a(e.outcome??"—")}</td>
      <td class="wrap">${a(e.config_snapshot_id??"—")}</td>
      <td>${a(e.policy_id??"—")}</td>
      <td>${a(e.seed??"—")}</td>
      <td class="wrap">${a((e.notes||[]).join("; "))}</td>
    </tr>`).join("");return`
    <h1>Telemetry sessions</h1>
    ${E("Sessions")}
    <p class="meta"><code>outcome=lose</code> is measured play, not a bot/framework fail. <code>snap-unset</code> is a join gap.</p>
    <div class="table-wrap">
      <table data-testid="tel-sessions">
        <thead>
          <tr><th>Id</th><th>Outcome</th><th>Snapshot</th><th>Policy</th><th>Seed</th><th>Notes</th></tr>
        </thead>
        <tbody>${n||'<tr><td colspan="6">No telemetry sessions.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function Ht(t){const e=(await gt(t)).session;return`
    <p class="meta"><a href="#/lens/sessions">← Sessions</a> · ${a(e.id)}</p>
    <h1>Session</h1>
    ${E("Sessions")}
    ${Xt(e)}
  `}async function Wt(){const n=((await $t()).turns||[]).map(e=>`
    <tr data-testid="agent-turn-row" data-turn-id="${a(e.id)}">
      <td class="wrap"><a href="#/lens/turns/${encodeURIComponent(e.id)}">${a(e.id)}</a></td>
      <td>${a(e.status??"")}</td>
      <td>${a(e.framing??"")}</td>
      <td class="wrap">${a(e.question??"")}</td>
      <td>${a(e.created_at??"")}</td>
    </tr>`).join("");return`
    <h1>Balance agent</h1>
    ${E("Agent")}
    <p class="meta">Persisted turns. Numbers in citations are measured; priorities are model reasoning.</p>
    <div class="table-wrap">
      <table data-testid="agent-turns">
        <thead><tr><th>Id</th><th>Status</th><th>Framing</th><th>Question</th><th>Created</th></tr></thead>
        <tbody>${n||'<tr><td colspan="5">No agent turns yet. Ask from a typed diff.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function Gt(t){const n=await yt(t);return`
    <p class="meta"><a href="#/lens/turns">← Agent</a> · ${a(t)}</p>
    <h1>Agent turn</h1>
    ${E("Agent")}
    ${Y(n.turn)}
  `}function Qt(){var e;const t=document.getElementById("lens-open-diff");t==null||t.addEventListener("click",()=>{var r,d;const s=(r=document.getElementById("lens-a"))==null?void 0:r.value,i=(d=document.getElementById("lens-b"))==null?void 0:d.value;!s||!i||(location.hash=`/lens/diff?a=${encodeURIComponent(s)}&b=${encodeURIComponent(i)}`)});const n=(e=document.getElementById("lens-defaults"))==null?void 0:e.textContent;if(n)try{const s=JSON.parse(n),i=document.getElementById("lens-a"),r=document.getElementById("lens-b");i&&s.a&&(i.value=s.a),r&&s.b&&(r.value=s.b)}catch{}}function Kt(){const t=document.getElementById("agent-run");t==null||t.addEventListener("click",()=>{(async()=>{var o,l,p;const n=document.getElementById("agent-msg"),e=document.getElementById("agent-result"),s=(o=document.getElementById("lens-pair"))==null?void 0:o.textContent;let i="",r="";try{const $=JSON.parse(s||"{}");i=$.a||"",r=$.b||""}catch{}const d=(l=document.getElementById("agent-q"))==null?void 0:l.value,c=(p=document.getElementById("agent-profile"))==null?void 0:p.value;n&&(n.textContent="running…");try{const $=await bt({snapshot_a:i,snapshot_b:r,question:d||void 0,profile:c||void 0});n&&(n.textContent=`status=${$.turn.status}`),e&&(e.innerHTML=Y($.turn))}catch($){n&&(n.textContent=String($))}})()})}function Vt(t){if(!t)return'<div class="empty" data-testid="lens-impl-empty">No persisted implications for this pair.</div>';const n=(t.gaps||[]).map(e=>`<li>${a(e)}</li>`).join("");return`
    <h2>Implications</h2>
    <div class="panel" data-testid="lens-implications">
      <div class="meta">status=${a(t.status??"")} · framing=${a(t.framing??"")}
        ${t.pending?` · pending=${a(t.pending)}`:""}</div>
      <h3>Gaps</h3>
      <ul class="gap-list" data-testid="lens-gaps">${n||"<li>(none)</li>"}</ul>
      <h3>Model reasoning</h3>
      <div data-testid="lens-impl-summary">${a(t.summary??"")}</div>
      <h3>Measured</h3>
      <pre class="pre-json" data-testid="lens-measured">${a(JSON.stringify(t.measured??{},null,2))}</pre>
    </div>`}function Xt(t){const n=(t.notes||[]).map(e=>`<li>${a(e)}</li>`).join("");return`
    <div class="panel" data-testid="tel-session-detail">
      <div class="meta">outcome=${a(t.outcome??"—")} · snapshot=${a(t.config_snapshot_id??"—")}
        · policy=${a(t.policy_id??"—")} · seed=${a(t.seed??"—")}</div>
      <h3>Notes</h3>
      <ul data-testid="tel-session-notes">${n||"<li>(none)</li>"}</ul>
      <h3>Summary (measured)</h3>
      <pre class="pre-json">${a(JSON.stringify(t.summary??{},null,2))}</pre>
    </div>`}function Y(t){const n=(t.priorities||[]).map(i=>`<li>${a(i)}</li>`).join(""),e=(t.gaps||[]).map(i=>`<li>${a(i)}</li>`).join(""),s=t.ai_cost_total!=null?String(t.ai_cost_total):"—";return`
    <div class="panel" data-testid="agent-turn">
      <div class="meta">status=${a(t.status??"")} · framing=${a(t.framing??"")}
        · cost_usd=${a(s)}${t.pending?` · pending=${a(t.pending)}`:""}</div>
      <h3>Priorities (model reasoning)</h3>
      <ul data-testid="agent-priorities">${n||"<li>(none)</li>"}</ul>
      <h3>Gaps</h3>
      <ul class="gap-list" data-testid="agent-gaps">${e||"<li>(none)</li>"}</ul>
      <h3>Measured citations</h3>
      <pre class="pre-json" data-testid="agent-measured">${a(JSON.stringify(t.citations??{},null,2))}</pre>
    </div>`}function zt(t){if(t.kind==="added_entity")return`+ entity ${t.entity_id}`;if(t.kind==="removed_entity")return`- entity ${t.entity_id}`;const n=t.path||"?";return t.delta!=null?`~ ${t.entity_id}.${n}: ${t.before} -> ${t.after} (delta ${t.delta})`:`~ ${t.entity_id}.${n}: ${JSON.stringify(t.before)} -> ${JSON.stringify(t.after)}`}const U=document.querySelector("#app");let L=!1,B=!1,P=!1;function M(t,n){const e=(c,o)=>`<a href="${c}" class="${t===o?"active":""}">${o}</a>`,s=L?"":`${e("#/launch","Launch")}
        ${e("#/quarantine","Quarantine")}
        ${e("#/profiles","Profiles")}`,i=[L?'<span class="badge warn" title="--read-only">RO</span>':"",B?'<span class="badge warn" title="Playwright smoke fixture — not real runs">SMOKE</span>':"",P?'<span class="badge warn" title="Restart questline hud">STALE API</span>':""].filter(Boolean).join(" "),r=B?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)">
        <strong>SMOKE FIXTURE SERVER</strong> — fake launcher + seeded runs.
        For real Wire/mock runs stop this process and use
        <code>uv run questline hud --open</code> (port 8741).
      </div>`:"",d=P?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)" data-testid="stale-api">
        <strong>STALE HUD PROCESS</strong> — SPA is newer than the Python API
        (missing <code>/api/runs/…/test?id=</code> or GameLens <code>/api/lens</code>). Stop the old
        <code>questline hud</code> and run <code>uv run questline hud --open</code>
        again from the repo root, then hard-refresh.
      </div>`:"";return`
    <header class="topbar">
      <a class="brand" href="#/">Questline <span>HUD</span></a>
      <nav class="nav">
        ${e("#/","Runs")}
        ${s}
        ${e("#/perf","Perf")}
        ${e("#/lens","GameLens")}
        ${e("#/trends","Trends")}
        ${e("#/live","Live")}
      </nav>
      ${i}
    </header>
    <main class="main">${r}${d}${n}</main>
  `}function Yt(){const e=((location.hash.replace(/^#\/?/,"")||"").split("?")[0]||"").split("/").filter(Boolean);if(e[0]==="runs"&&e[1]&&e[2]==="tests"&&e.length>=4){const s=e.slice(3).join("/");let i=s;try{i=decodeURIComponent(s)}catch{}return{name:"test",params:{runId:e[1],testId:i}}}return e[0]==="runs"&&e[1]?{name:"run",params:{runId:e[1]}}:e[0]==="trends"?{name:"trends",params:{}}:e[0]==="live"?{name:"live",params:{}}:e[0]==="launch"?{name:"launch",params:{}}:e[0]==="quarantine"?{name:"quarantine",params:{}}:e[0]==="profiles"?{name:"profiles",params:{}}:e[0]==="perf"?{name:"perf",params:{}}:e[0]==="lens"?e[1]==="diff"?{name:"lens-diff",params:{}}:e[1]==="sessions"&&e[2]?{name:"lens-session",params:{id:e[2]}}:e[1]==="sessions"?{name:"lens-sessions",params:{}}:e[1]==="turns"&&e[2]?{name:"lens-turn",params:{id:e[2]}}:e[1]==="turns"?{name:"lens-turns",params:{}}:{name:"lens",params:{}}:{name:"runs",params:{}}}function Zt(t){return t.length?`
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
    <tr data-testid="run-row" data-run-id="${a(e.id)}">
      <td class="wrap"><a href="#/runs/${a(e.id)}">${a(e.id.slice(0,8))}…</a></td>
      <td>${a(e.profile)}</td>
      <td>${a(e.driver??"—")}</td>
      <td>${a(e.device??"—")}</td>
      <td><span class="badge ${a(e.status)}">${a(e.status)}</span></td>
      <td>${e.passed}/${e.total}</td>
      <td class="verdict-infra">${e.infra_failures}</td>
      <td class="verdict-test">${e.test_failures}</td>
      <td>${a(k(e.duration_s))}</td>
      <td>${a(e.started_at??"")}</td>
    </tr>`).join("")}</tbody>
      </table>
    </div>`:`<div class="empty" data-testid="empty-store">
      No runs in the store yet.<br/>
      Use <a href="#/launch">Launch</a> or run a suite with the questline plugin, then refresh.
    </div>`}async function te(){const t=new URLSearchParams(location.hash.split("?")[1]||""),n=t.get("profile")||"",e=t.get("status")||"",s=await D({profile:n||void 0,status:e||void 0});return`
    <h1>Runs</h1>
    <div class="toolbar">
      <label>profile <input id="f-profile" value="${a(n)}" placeholder="any"/></label>
      <label>status
        <select id="f-status">
          <option value="">any</option>
          ${["passed","failed","running","error"].map(i=>`<option value="${i}" ${e===i?"selected":""}>${i}</option>`).join("")}
        </select>
      </label>
      <button type="button" id="f-apply">Filter</button>
      ${L?"":'<a class="btn" href="#/launch">Launch run</a>'}
    </div>
    ${Zt(s.runs)}
  `}async function Z(){const t=Yt();try{let n="",e="Runs";t.name==="run"?(n=await kt(t.params.runId),e="Runs"):t.name==="test"?(n=await It(t.params.runId,t.params.testId),e="Runs"):t.name==="trends"?(n=await Ct(),e="Trends"):t.name==="live"?(n=await Bt(),e="Live"):t.name==="launch"?(n=await Nt(),e="Launch"):t.name==="quarantine"?(n=await Tt(),e="Quarantine"):t.name==="profiles"?(n=await Rt(),e="Profiles"):t.name==="perf"?(n=await Ut(),e="Perf"):t.name==="lens"?(n=await Dt(),e="GameLens"):t.name==="lens-diff"?(n=await Jt(),e="GameLens"):t.name==="lens-sessions"?(n=await Ft(),e="GameLens"):t.name==="lens-session"?(n=await Ht(t.params.id),e="GameLens"):t.name==="lens-turns"?(n=await Wt(),e="GameLens"):t.name==="lens-turn"?(n=await Gt(t.params.id),e="GameLens"):(n=await te(),e="Runs"),U.innerHTML=M(e,n),ee(t.name)}catch(n){U.innerHTML=M("Runs",`<div class="empty">Failed to load HUD: ${a(String(n))}</div>`)}}function ee(t){var n;if(t==="runs"&&((n=document.getElementById("f-apply"))==null||n.addEventListener("click",()=>{const e=document.getElementById("f-profile").value.trim(),s=document.getElementById("f-status").value,i=new URLSearchParams;e&&i.set("profile",e),s&&i.set("status",s);const r=i.toString();location.hash=r?`/?${r}`:"/"})),t==="live"){const e=document.getElementById("live-root");e&&Pt(e)}t==="launch"&&Ot(),t==="quarantine"&&jt(),t==="profiles"&&At(),t==="perf"&&Mt(),t==="lens"&&Qt(),t==="lens-diff"&&Kt(),t==="run"&&Et(),t==="test"&&Lt()}async function ne(){var t,n,e;try{const s=await x();L=!!s.read_only,B=!!s.smoke,P=!((t=s.api)!=null&&t.test_by_query)||!((n=s.api)!=null&&n.lens)||!((e=s.api)!=null&&e.agents),L||await q()}catch{L=!1,B=!1,P=!0}await Z()}window.addEventListener("hashchange",()=>{Z()});ne();
