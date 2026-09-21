(function(){const n=document.createElement("link").relList;if(n&&n.supports&&n.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))s(i);new MutationObserver(i=>{for(const r of i)if(r.type==="childList")for(const o of r.addedNodes)o.tagName==="LINK"&&o.rel==="modulepreload"&&s(o)}).observe(document,{childList:!0,subtree:!0});function e(i){const r={};return i.integrity&&(r.integrity=i.integrity),i.referrerPolicy&&(r.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?r.credentials="include":i.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function s(i){if(i.ep)return;i.ep=!0;const r=e(i);fetch(i.href,r)}})();let P=null;async function b(t){const n=await fetch(t),e=await n.text();if(/^\s*</.test(e)||(n.headers.get("content-type")||"").includes("text/html"))throw new Error(`${n.status} ${t}: got HTML instead of JSON. Restart questline hud (old process missing new /api routes).`);if(!n.ok)throw new Error(`${n.status} ${t}: ${e}`);try{return JSON.parse(e)}catch(i){throw new Error(`${t}: invalid JSON (${String(i)})`)}}async function q(){return P||(P=(await b("/api/csrf")).csrf_token,P)}async function E(t,n,e){const s=await q(),i=await fetch(n,{method:t,headers:{"Content-Type":"application/json","X-CSRF-Token":s},body:e===void 0?void 0:JSON.stringify(e)});if(!i.ok){const r=await i.text();throw new Error(`${i.status} ${n}: ${r}`)}if(i.status!==204)return await i.json()}function k(){return b("/api/meta")}function Y(t){const n=new URLSearchParams;t.profile&&n.set("profile",t.profile),t.status&&n.set("status",t.status);const e=n.toString();return b(`/api/runs${e?`?${e}`:""}`)}function ct(t){return b(`/api/runs/${encodeURIComponent(t)}`)}function ut(t,n){const e=new URLSearchParams({id:n});return b(`/api/runs/${encodeURIComponent(t)}/test?${e.toString()}`)}function pt(t=50){return b(`/api/trends?limit=${t}`)}function j(t){const n=t?`?config=${encodeURIComponent(t)}`:"";return b(`/api/profiles${n}`)}function mt(){return b("/api/configs")}function D(){return b("/api/devices")}function X(t){return b(`/api/profiles/${encodeURIComponent(t)}`)}function ft(t,n){return E("POST",`/api/profiles/${encodeURIComponent(t)}/validate`,{fields:n,apply:!1})}function G(t,n,e){return E("POST",`/api/profiles/${encodeURIComponent(t)}`,{fields:n,apply:e})}function ht(){return b("/api/reporters")}function z(){return b("/api/launcher")}function Z(t){return E("POST","/api/launcher/start",t)}function vt(){return E("POST","/api/launcher/stop")}function gt(){return b("/api/quarantine")}function yt(t){return E("POST","/api/quarantine",t)}function $t(t){return E("DELETE",`/api/quarantine?test_id=${encodeURIComponent(t)}`)}function bt(t){return E("POST","/api/quarantine/audit",t||{})}function tt(t){return b(`/api/perf/${encodeURIComponent(t)}`)}function wt(t,n){return b(`/api/perf/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(n)}`)}function _t(t=50){return b(`/api/perf/correlation?limit=${t}`)}function St(t){return`/api/artifacts/file?path=${encodeURIComponent(t)}`}function et(){return b("/api/lens/snapshots")}function Et(t,n){const e=new URLSearchParams({a:t,b:n});return b(`/api/lens/diff?${e.toString()}`)}function kt(){return b("/api/telemetry/sessions")}function It(t){return b(`/api/telemetry/sessions/${encodeURIComponent(t)}`)}function xt(){return b("/api/lens/agent/turns")}function Lt(t){return b(`/api/lens/agent/turns/${encodeURIComponent(t)}`)}function Ct(t){return E("POST","/api/lens/agent/run",t)}function nt(t){return b(`/api/runs/${encodeURIComponent(t)}/agent-tasks`)}function Bt(t){return E("POST","/api/agents/triage",t)}function qt(t){return E("POST","/api/agents/diagnose",t)}function Pt(t){return E("POST","/api/agents/heal",t)}function Tt(){return b("/api/eval/runs")}function Ot(t,n){return b(`/api/eval/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(n)}`)}function Nt(t){return E("POST","/api/eval/run",t)}function Rt(t){return E("POST","/api/agents/generate",t)}function jt(){return b("/api/agent-tasks?kind=generate")}function Ut(t,n){const e=new URLSearchParams;t&&e.set("profile",t),n&&e.set("config",n);const s=e.toString();return b(`/api/unity/status${s?`?${s}`:""}`)}function Mt(t){return E("POST","/api/unity/ensure-editor",t)}function x(t){if(t==null||Number.isNaN(t))return"—";if(t<60)return`${t.toFixed(1)}s`;const n=Math.floor(t/60),e=t-n*60;return`${n}m ${e.toFixed(0)}s`}function a(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function At(t){const n=await ct(t),e=n.run,s=n.banner,i=n.tests.map(c=>`
    <tr data-testid="test-row" data-test-id="${a(c.id)}">
      <td class="wrap"><a href="#/runs/${encodeURIComponent(t)}/tests/${encodeURIComponent(c.id)}">${a(c.nodeid)}</a></td>
      <td><span class="badge ${a(c.status)}">${a(c.status)}</span></td>
      <td class="verdict-${a(c.verdict??"")}">${a(c.verdict??"—")}</td>
      <td>${a(x(c.duration_s))}</td>
      <td class="wrap">${a(c.death_step_name??"")}</td>
    </tr>`).join(""),o=(n.ai_calls||[]).map(c=>`
    <tr data-testid="ai-call-row">
      <td>${a(c.provider??"—")}</td>
      <td class="wrap">${a(c.model??"—")}</td>
      <td>${a(c.tokens_in??0)}</td>
      <td>${a(c.tokens_out??0)}</td>
      <td>${a(F(c.cost))}</td>
      <td>${a(c.outcome??"—")}</td>
      <td class="wrap">${a(c.purpose??"")}</td>
    </tr>`).join("")||'<tr><td colspan="7">No AI calls for this run.</td></tr>',l=n.tests.some(c=>c.status==="failed"||c.status==="error");let d=!0;try{d=!(await k()).read_only}catch{d=!0}let u=[];try{u=(await nt(t)).tasks||[]}catch{u=[]}return`
    <p class="meta"><a href="#/">← Runs</a> · ${a(e.id)}</p>
    <h1>Run detail</h1>
    <div class="meta">
      profile=${a(e.profile)} · driver=${a(e.driver??"—")} ·
      device=${a(e.device??"—")} · status=${a(e.status)} ·
      duration=${a(x(e.duration_s))}
    </div>
    <div class="banner" data-testid="verdict-banner">
      <div class="stat ok"><span>passed</span><b>${e.passed}</b></div>
      <div class="stat"><span>failed</span><b>${e.failed}</b></div>
      <div class="stat infra"><span>infra</span><b>${s.infra_failures}</b></div>
      <div class="stat test"><span>test</span><b>${s.test_failures}</b></div>
      <div class="stat"><span>authoring</span><b>${s.authoring_failures}</b></div>
    </div>
    ${l&&d?`<div class="toolbar" data-testid="agent-run-actions">
      <button type="button" id="triage-run" data-testid="triage-run">Triage this run</button>
      <span id="triage-msg" class="meta" data-testid="triage-msg"></span>
    </div>
    <div id="triage-result" data-testid="triage-result">${Ht(u)}</div>
    <script type="application/json" id="run-agent-ctx">${JSON.stringify({runId:t})}<\/script>`:""}
    <h2>AI calls</h2>
    <div class="meta">total_usd=${a(F(n.ai_cost_total))}</div>
    <div class="table-wrap">
      <table data-testid="ai-calls-table">
        <thead>
          <tr>
            <th>Provider</th><th>Model</th><th>In</th><th>Out</th>
            <th>Cost</th><th>Outcome</th><th>Purpose</th>
          </tr>
        </thead>
        <tbody>${o}</tbody>
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
  `}function Dt(){const t=document.getElementById("triage-run");t==null||t.addEventListener("click",()=>{(async()=>{var r;const n=document.getElementById("triage-msg"),e=document.getElementById("triage-result"),s=(r=document.getElementById("run-agent-ctx"))==null?void 0:r.textContent;let i="";try{i=String(JSON.parse(s||"{}").runId||"")}catch{}if(i){n&&(n.textContent="running…");try{const o=await Bt({run_id:i});n&&(n.textContent=`status=${o.task.status} verdict=${o.task.verdict}`),e&&(e.innerHTML=at(o.task))}catch(o){n&&(n.textContent=String(o))}}})()})}function Ht(t){return t.length?t.map(at).join(""):'<p class="meta">No agent tasks yet.</p>'}function at(t){const n=(t.clusters||[]).map(e=>{const s=String(e.bucket??e.key??""),i=String(e.error_type??""),r=Array.isArray(e.test_ids)?e.test_ids.length:"",o=String(e.hypothesis??e.signature??"");return`<li>${a(s)} · ${a(i)} x${a(r)} — ${a(o)}</li>`}).join("");return`
    <div class="panel" data-testid="agent-task" data-task-kind="${a(t.kind??"")}">
      <div class="meta">kind=${a(t.kind??"")} · verdict=${a(t.verdict??"")}
        · cause=${a(t.cause??"")} · status=${a(t.status??"")}</div>
      <p>${a(t.summary??"")}</p>
      ${n?`<ul data-testid="triage-clusters">${n}</ul>`:""}
    </div>`}function F(t){return t==null||Number.isNaN(t)?"0.000000":t.toFixed(6)}async function Gt(t,n){const e=await ut(t,n),s=e.test,i=e.steps.map(f=>{const w=String(f.status??"");return`<li data-testid="step-row">
        <span class="ts">${a(f.started_at??"")}</span>
        <span class="badge ${a(w)}">${a(w)}</span>
        <span>${a(f.name??"")}${f.error_message?` — ${a(f.error_message)}`:""}</span>
      </li>`}).join(""),r=(e.history||[]).map(f=>{const w=String(f.status??""),p=Number(f.duration_s??0)||1,m=Math.max(4,Math.min(28,p*4));return`<i class="${a(w)}" style="height:${m}px" title="${a(w)}"></i>`}).join(""),o=e.death_point||{},l=o.last_started_step||{},d=o.driver_health||{},u=s.verdict==="infra"?"infra":"",c=(e.artifacts||[]).map(f=>{const w=String(f.path??""),p=String(f.kind??""),m=String(f.name??w),h=St(w);return p==="screenshot"||/\.(png|jpe?g|webp|gif)$/i.test(m)?`<div><a href="${a(h)}" target="_blank" rel="noreferrer">
          <img src="${a(h)}" alt="${a(m)}"/><div>${a(m)}</div></a></div>`:`<div><a href="${a(h)}" target="_blank" rel="noreferrer">${a(m)}</a>
        <div class="meta">${a(p)} · ${a(f.size_bytes??"")} B</div></div>`}).join(""),v=s.status==="failed"||s.status==="error";let g=!0;try{g=!(await k()).read_only}catch{g=!0}const _=String(s.error_type??"").includes("ElementNotFound");let $=[];try{$=((await nt(t)).tasks||[]).filter(w=>!w.test_id||w.test_id===n)}catch{$=[]}return`
    <p class="meta">
      <a href="#/">Runs</a> /
      <a href="#/runs/${a(t)}">${a(t.slice(0,8))}…</a>
    </p>
    <h1 data-testid="test-title">${a(s.nodeid)}</h1>
    <div class="meta">
      status=<span class="badge ${a(s.status)}">${a(s.status)}</span> ·
      verdict=<span class="verdict-${a(s.verdict??"")}">${a(s.verdict??"—")}</span> ·
      duration=${a(x(s.duration_s))}
    </div>

    ${v&&g?`<div class="toolbar" data-testid="agent-test-actions">
      <button type="button" id="diagnose-test" data-testid="diagnose-test">Diagnose this test</button>
      <button type="button" id="fix-test" data-testid="fix-test">Fix this test</button>
      ${_?'<button type="button" id="heal-test" data-testid="heal-test">Suggest locator</button>':""}
      <span id="diagnose-msg" class="meta" data-testid="diagnose-msg"></span>
    </div>
    <div id="diagnose-result" data-testid="diagnose-result">${Jt($)}</div>
    <script type="application/json" id="test-agent-ctx">${JSON.stringify({runId:t,testId:n,locatorMiss:_})}<\/script>`:""}

    <div class="panel death ${u}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${a(l.name??"—")}</b>
        @ ${a(l.started_at??"")}</div>
      <div>error: ${a(s.error_type??"")} — ${a(s.error_message??"")}</div>
      <div>driver health: ${a(JSON.stringify(d||{}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${r||"<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${i||"<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${c||"<span class='meta'>none</span>"}</div>
  `}function Ft(){var r,o,l;const t=document.getElementById("test-agent-ctx");let n="",e="";try{const d=JSON.parse((t==null?void 0:t.textContent)||"{}");n=d.runId||"",e=d.testId||""}catch{return}const s=()=>document.getElementById("diagnose-msg"),i=()=>document.getElementById("diagnose-result");(r=document.getElementById("diagnose-test"))==null||r.addEventListener("click",()=>{M("diagnose",n,e,s(),i())}),(o=document.getElementById("fix-test"))==null||o.addEventListener("click",()=>{window.confirm("Fix mode writes files under the project jail and re-runs the test. Continue?")&&M("fix",n,e,s(),i())}),(l=document.getElementById("heal-test"))==null||l.addEventListener("click",()=>{M("heal",n,e,s(),i())})}async function M(t,n,e,s,i){if(!(!n||!e)){s&&(s.textContent="running…");try{const r=t==="heal"?await Pt({run_id:n,test_id:e}):await qt({run_id:n,test_id:e,fix:t==="fix"});s&&(s.textContent=`status=${r.task.status} verdict=${r.task.verdict}`),i&&(i.innerHTML=st(r.task))}catch(r){s&&(s.textContent=String(r))}}}function Jt(t){return t.length?t.map(st).join(""):""}function st(t){const n=t.suggestion||{},e=typeof n.yaml_diff=="string"?n.yaml_diff:"",s=t.gate?`gate accepted=${a(String(t.gate.accepted??""))}`:"";return`
    <div class="panel" data-testid="agent-task" data-task-kind="${a(t.kind??"")}">
      <div class="meta">kind=${a(t.kind??"")} · verdict=${a(t.verdict??"")}
        · cause=${a(t.cause??"")} ${s}</div>
      <p>${a(t.summary??"")}</p>
      ${e?`<pre data-testid="heal-diff">${a(e)}</pre>`:""}
    </div>`}async function Wt(){const[t,n]=await Promise.all([pt(50),_t(50)]),e=t.series||[],s=Math.max(1,...e.map(d=>Number(d.duration_s??0)||0)),i=e.map(d=>{const u=d.pass_rate==null?0:Number(d.pass_rate),c=Math.max(4,Math.round(u*100)),v=Number(d.duration_s??0);return`<div class="bar ${Number(d.failed??0)>0?"fail":""}" style="height:${c}%">
        <span>${a(d.run_id)} · ${(u*100).toFixed(0)}% · ${a(x(v))}</span>
      </div>`}).join(""),r=e.map(d=>{const u=Number(d.duration_s??0);return`<div class="bar" style="height:${Math.max(4,Math.round(u/s*100))}%">
        <span>${a(d.run_id)} · ${a(x(u))}</span>
      </div>`}).join(""),o=(t.flaky_tests||[]).map(d=>`<tr>
        <td class="wrap">${a(d.nodeid)}</td>
        <td>${a(d.runs)}</td>
        <td>${a(d.passed)}/${a(d.failed)}</td>
        <td>${(Number(d.pass_rate)*100).toFixed(0)}%</td>
        <td>${(Number(d.flake_score)*100).toFixed(0)}%</td>
      </tr>`).join(""),l=(n.tests||[]).map(d=>{const u=(d.points||[]).map(c=>{const v=c.duration_s==null?0:Number(c.duration_s);return`<span class="dot ${c.passed?"ok":"bad"}" title="${a(c.run_id)} · ${a(x(v))}"></span>`}).join("");return`<tr>
        <td class="wrap">${a(d.nodeid)}</td>
        <td>${d.passed}/${d.failed}</td>
        <td class="corr-dots">${u}</td>
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
        <tbody>${o||'<tr><td colspan="5">No flaky tests detected.</td></tr>'}</tbody>
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
  `}async function Kt(){return`
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `}function Qt(t){const n=document.getElementById("live-status"),e=document.getElementById("live-clear");e==null||e.addEventListener("click",()=>{t.innerHTML=""});const i=`${location.protocol==="https:"?"wss":"ws"}://${location.host}/live`;let r;try{r=new WebSocket(i)}catch(o){n&&(n.textContent="failed"),t.innerHTML=`<div>WebSocket error: ${a(String(o))}</div>`;return}r.onopen=()=>{n&&(n.textContent="live",n.className="badge passed")},r.onclose=()=>{n&&(n.textContent="closed",n.className="badge failed")},r.onerror=()=>{n&&(n.textContent="error",n.className="badge failed")},r.onmessage=o=>{try{const l=JSON.parse(String(o.data)),d=String(l.type??"?"),u=String(l.timestamp??""),c=l.nodeid||l.name||l.test_id||l.status||l.profile||"",v=document.createElement("div");v.innerHTML=`<span class="t">${a(u)}</span><b>${a(d)}</b> ${a(c)}`,t.prepend(v)}catch{const l=document.createElement("div");l.textContent=String(o.data),t.prepend(l)}}}const Vt="ql-last-generated",Yt=[{id:"mock",label:"Mock demo",config:"questline.toml",profile:"mock",tests:"examples/demo-tests",live_target:!1,note:"No Unity. CI-style mock driver."},{id:"wire-editor",label:"Wire Editor",config:"examples/wire-smoke/questline.toml",profile:"editor",tests:"examples/wire-smoke",live_target:!0,note:"Unity Play + Wire on :13000. Device picker stays empty (OK)."},{id:"wire-android",label:"Wire Android",config:"examples/wire-smoke/questline.toml",profile:"android_local",tests:"examples/wire-smoke",live_target:!0,note:"Dev APK + adb. Pick a serial if more than one device."}];function J(t,n,e){return t==null?"?":t?n:e}function W(t){return`
    <div class="panel" data-testid="unity-chip" data-state="loading">
      <div class="toolbar wrap">
        <strong>Unity Editor</strong>
        <span class="badge" data-testid="unity-cli">CLI …</span>
        <span class="badge" data-testid="unity-editor">Editor …</span>
        <span class="badge" data-testid="unity-play">Play …</span>
        <span class="badge" data-testid="unity-pipeline">Pipeline …</span>
        <button type="button" id="unity-ensure" data-testid="unity-ensure" ${t?"disabled":""}>Ensure Editor</button>
      </div>
      <p class="meta" data-testid="unity-detail">Checking Unity CLI…</p>
    </div>`}function K(t,n){const e=document.querySelector("[data-testid=unity-chip]"),s=document.querySelector("[data-testid=unity-cli]"),i=document.querySelector("[data-testid=unity-editor]"),r=document.querySelector("[data-testid=unity-play]"),o=document.querySelector("[data-testid=unity-pipeline]"),l=document.querySelector("[data-testid=unity-detail]");s&&(s.textContent=t.available?`CLI ${t.cli_version||"present"}`:"CLI missing"),i&&(i.textContent=`Editor ${J(t.editor_running,"running","stopped")}`),r&&(r.textContent=`Play ${J(t.play_mode,"on","off")}`),o&&(o.textContent=`Pipeline ${t.pipeline}`);const d=t.project_name?` (${t.project_name})`:"";l&&(l.textContent=`${n||t.detail||"Unity CLI status."}${d}`),e&&(e.dataset.state=t.available?"ready":"missing")}function Xt(t){try{return sessionStorage.getItem(Vt)||t}catch{return t}}function zt(t,n,e){if(t)return Yt;const s=[];return n.includes("mock")&&s.push({id:"mock",label:"Mock",config:"questline.toml",profile:"mock",tests:e,live_target:!1,note:"No Unity. Mock driver profile in this suite."}),n.includes("editor")&&s.push({id:"editor",label:"Wire Editor",config:"questline.toml",profile:"editor",tests:e,live_target:!0,note:"Unity Play + Wire on :13000. Device picker stays empty (OK)."}),n.includes("android_local")&&s.push({id:"android",label:"Wire Android",config:"questline.toml",profile:"android_local",tests:e,live_target:!0,note:"Dev APK + adb. Pick a serial if more than one device."}),s}async function Zt(){var m,h,S;await q();let t,n,e,s;try{[t,n,e,s]=await Promise.all([k(),mt().catch(()=>({project_root:"",active:"",configs:[{path:"questline.toml",absolute:"questline.toml"}]})),ht().catch(()=>({reporters:["console"]})),z().catch(()=>({launcher:{state:"idle"}}))])}catch(y){return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-error">
        Failed to load launcher APIs: ${a(String(y))}<br/>
        Stop the old <code>questline hud</code> process and start it again from
        <code>D:\\dev\\questline</code>.
      </div>`}if(t.read_only)return`<h1>Launch</h1>
      ${W(!0)}
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;const i=((m=n.configs.find(y=>y.path.replace(/\\/g,"/")==="questline.toml"))==null?void 0:m.path)||((h=n.configs[0])==null?void 0:h.path)||"questline.toml",r=Xt(t.has_suites?"suites":t.has_wire_smoke?"examples/demo-tests":"."),o=await j(i),l=await D(),d=zt(!!t.has_wire_smoke,o.profiles||[],r),u=(n.configs||[]).map(y=>{const C=y.path===i?"selected":"";return`<option value="${a(y.path)}" ${C}>${a(y.path)}</option>`}).join(""),c=(o.profiles||[]).map(y=>{const C=o.profiles.includes("editor")?"editor":o.profiles.includes("mock")?"mock":o.profiles[0]||"";return`<option value="${a(y)}" ${y===C?"selected":""}>${a(y)}</option>`}).join(""),v=['<option value="">(no adb pin — OK for Editor)</option>',...(l.devices||[]).map(y=>`<option value="${a(y.id)}">${a(y.id)} · ${a(y.platform)}</option>`)].join(""),g=(e.reporters||[]).map(y=>`<label class="check"><input type="checkbox" name="reporter" value="${a(y)}" ${y==="console"?"checked":""}/> ${a(y)}</label>`).join(""),_=d.map(y=>`<button type="button" class="preset" data-preset="${a(y.id)}" title="${a(y.note)}">${a(y.label)}</button>`).join(""),$=s.launcher,f=["starting","running","stopping"].includes($.state||""),w=l.hint||((S=l.devices)!=null&&S.length?`${l.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire."),p=f?`<div class="empty" data-testid="launch-busy">
        A managed run is <strong>${a($.state||"")}</strong>
        (job <code>${a($.job_id||"")}</code>, profile
        <code>${a($.profile||"")}</code>).
        <a href="#/live">Open Live</a> to watch it, or <strong>Stop</strong> below
        before launching another.
      </div>`:"";return`
    <h1>Run launcher</h1>
    ${W(!1)}
    ${p}
    <p class="meta">Profiles come from <code>questline.toml</code> (not from Unity being open).
      Unity Play + Wire = use preset <strong>Wire Editor</strong> or profile <code>editor</code>.
      Device list is <em>adb only</em> — Editor does not appear there.</p>
    <div class="toolbar" data-testid="launch-presets">
      <span class="meta">Presets:</span> ${_}
    </div>
    <div class="panel" data-testid="launch-form">
      <div class="toolbar">
        <label>config
          <select id="launch-config" data-testid="launch-config">${u}</select>
        </label>
        <label>profile
          <select id="launch-profile" data-testid="launch-profile">${c}</select>
        </label>
        <label>device
          <select id="launch-device" data-testid="launch-device">${v}</select>
        </label>
        <button type="button" id="launch-refresh-devices" data-testid="launch-refresh-devices">Refresh devices</button>
      </div>
      <p class="meta" id="launch-device-hint" data-testid="launch-device-hint">${a(w)}</p>
      ${l.error?`<p class="meta">adb error: ${a(l.error)}</p>`:""}
      <label class="block">markers <input id="launch-markers" placeholder="optional -m expression" data-testid="launch-markers"/></label>
      <label class="block">tests (one path/nodeid per line)
        <textarea id="launch-tests" rows="4" data-testid="launch-tests" placeholder="suites">${a(r)}</textarea>
      </label>
      <div class="toolbar wrap">${g||"<span class='meta'>no reporters</span>"}</div>
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
    <pre class="log" id="launch-status" data-testid="launch-status">${a(JSON.stringify($,null,2))}</pre>
    <script type="application/json" id="launch-preset-data">${JSON.stringify(d)}<\/script>
  `}function te(){var g,_,$,f,w;const t=document.getElementById("launch-status"),n=document.getElementById("launch-config"),e=document.getElementById("launch-profile"),s=document.getElementById("launch-device"),i=document.getElementById("launch-tests"),r=document.getElementById("launch-live"),o=document.getElementById("launch-device-hint"),l=JSON.parse(((g=document.getElementById("launch-preset-data"))==null?void 0:g.textContent)||"[]"),d=async()=>{if(!(!n||!e))try{const p=await j(n.value),m=p.profiles.includes("editor")?"editor":p.profiles[0]||"";e.innerHTML=p.profiles.map(h=>`<option value="${a(h)}" ${h===m?"selected":""}>${a(h)}</option>`).join("")}catch(p){t&&(t.textContent=String(p))}},u=async()=>{var p;if(s)try{const m=await D();s.innerHTML=['<option value="">(no adb pin — OK for Editor)</option>',...(m.devices||[]).map(h=>`<option value="${a(h.id)}">${a(h.id)} · ${a(h.platform)}</option>`)].join(""),o&&(o.textContent=m.hint||((p=m.devices)!=null&&p.length?`${m.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire."))}catch(m){o&&(o.textContent=String(m))}},c=async()=>{const p=document.querySelector("[data-testid=unity-detail]");try{const m=await Ut((e==null?void 0:e.value)||void 0,(n==null?void 0:n.value)||void 0);K(m.unity)}catch(m){p&&(p.textContent=String(m))}};n==null||n.addEventListener("change",()=>{d(),c()}),e==null||e.addEventListener("change",()=>{c()}),(_=document.getElementById("launch-refresh-devices"))==null||_.addEventListener("click",()=>{u()}),document.querySelectorAll(".preset").forEach(p=>{p.addEventListener("click",()=>{const m=p.dataset.preset||"",h=l.find(S=>S.id===m);if(h){if(n){if(!Array.from(n.options).some(y=>y.value===h.config)){const y=document.createElement("option");y.value=h.config,y.textContent=h.config,n.appendChild(y)}n.value=h.config}i&&(i.value=h.tests),r&&(r.checked=h.live_target),(async()=>(await d(),e&&(e.value=h.profile)))()}})});const v=async()=>{try{const{launcher:p}=await z();t&&(t.textContent=JSON.stringify(p,null,2));const m=["starting","running","stopping"].includes(p.state||""),h=document.getElementById("launch-start"),S=document.getElementById("launch-stop");h&&(h.disabled=m),S&&(S.disabled=!m)}catch(p){t&&(t.textContent=String(p))}};($=document.getElementById("unity-ensure"))==null||$.addEventListener("click",()=>{const p=document.getElementById("unity-ensure"),m=document.querySelector("[data-testid=unity-detail]");!p||p.disabled||(async()=>{p.disabled=!0,m&&(m.textContent="Ensuring Editor…");try{const h=await Mt({profile:(e==null?void 0:e.value)||void 0,config:(n==null?void 0:n.value)||void 0});K(h.unity,h.detail);const S=document.querySelector("[data-testid=unity-chip]");S&&(S.dataset.state=h.ok?"ready":h.skipped?"skipped":"error")}catch(h){m&&(m.textContent=String(h))}finally{p.disabled=!1}})()}),(f=document.getElementById("launch-start"))==null||f.addEventListener("click",()=>{(async()=>{var H;const p=(e==null?void 0:e.value)||"",m=(s==null?void 0:s.value)||"",h=document.getElementById("launch-markers").value.trim(),y=((i==null?void 0:i.value)||"").split(/\r?\n/).map(I=>I.trim()).filter(Boolean),C=Array.from(document.querySelectorAll('input[name="reporter"]:checked')).map(I=>I.value),lt=(H=document.getElementById("launch-quarantine"))==null?void 0:H.checked;try{const{launcher:I}=await Z({profile:p,tests:y,markers:h||void 0,device_serial:m||void 0,reporters:C.length?C:void 0,include_quarantined:!!lt,config:(n==null?void 0:n.value)||void 0,live_target:!!(r!=null&&r.checked)});t&&(t.textContent=JSON.stringify(I,null,2)),location.hash="/live"}catch(I){const U=String(I);t&&(t.textContent=U),/\b409\b/.test(U)&&/already/i.test(U)&&(location.hash="/live")}})()}),(w=document.getElementById("launch-stop"))==null||w.addEventListener("click",()=>{(async()=>{try{const{launcher:p}=await vt();t&&(t.textContent=JSON.stringify(p,null,2))}catch(p){t&&(t.textContent=String(p))}})()}),v(),c(),window.setInterval(()=>{location.hash.replace(/^#\/?/,"").startsWith("launch")&&v()},2e3)}async function ee(){if(await q(),(await k()).read_only)return`<h1>Quarantine</h1>
      <div class="empty">Read-only mode — quarantine management disabled.</div>`;const n=await gt(),e=(n.entries||[]).map(s=>`<tr data-testid="quarantine-row">
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
  `}function ne(){var n,e;const t=document.getElementById("q-msg");(n=document.getElementById("q-add"))==null||n.addEventListener("click",()=>{(async()=>{try{await yt({test_id:document.getElementById("q-id").value.trim(),owner:document.getElementById("q-owner").value.trim(),reason:document.getElementById("q-reason").value.trim(),exit_criteria:document.getElementById("q-exit").value.trim(),issue:document.getElementById("q-issue").value.trim()||void 0}),location.reload()}catch(s){t&&(t.textContent=String(s))}})()}),(e=document.getElementById("q-audit"))==null||e.addEventListener("click",()=>{(async()=>{try{const s=await bt({});t&&(t.textContent=s.summary)}catch(s){t&&(t.textContent=String(s))}})()}),document.querySelectorAll(".q-remove").forEach(s=>{s.addEventListener("click",()=>{(async()=>{const i=s.dataset.id||"";try{await $t(i),location.reload()}catch(r){t&&(t.textContent=String(r))}})()})})}async function ae(){if(await q(),(await k()).read_only)return`<h1>Profiles</h1>
      <div class="empty">Read-only mode — profile editor disabled.</div>`;const{profiles:n,path:e}=await j(),s=n.map(l=>`<option value="${a(l)}">${a(l)}</option>`).join(""),i=n[0]||"";let r="{}",o="";if(i){const l=await X(i);r=JSON.stringify(l.fields,null,2),o=(l.secret_env_names||[]).map(d=>`<code>${a(d)}</code>`).join(" ")}return`
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
    <p class="meta">Secret env slots: ${o||"—"}</p>
    <textarea id="prof-fields" data-testid="prof-fields" rows="18" class="code">${a(r)}</textarea>
    <pre class="log" id="prof-msg" data-testid="prof-msg"></pre>
  `}function se(){var i,r,o,l;const t=document.getElementById("prof-msg"),n=document.getElementById("prof-fields"),e=document.getElementById("prof-name"),s=()=>n?JSON.parse(n.value):{};(i=document.getElementById("prof-load"))==null||i.addEventListener("click",()=>{(async()=>{try{const d=(e==null?void 0:e.value)||"",u=await X(d);n&&(n.value=JSON.stringify(u.fields,null,2)),t&&(t.textContent=`loaded ${d}`)}catch(d){t&&(t.textContent=String(d))}})()}),(r=document.getElementById("prof-validate"))==null||r.addEventListener("click",()=>{(async()=>{try{const d=(e==null?void 0:e.value)||"",u=await ft(d,s());t&&(t.textContent=u.ok?`OK
${JSON.stringify(u.settings_summary,null,2)}`:u.errors.join(`
`))}catch(d){t&&(t.textContent=String(d))}})()}),(o=document.getElementById("prof-preview"))==null||o.addEventListener("click",()=>{(async()=>{try{const d=(e==null?void 0:e.value)||"",u=await G(d,s(),!1);t&&(t.textContent=u.diff||"(no diff)")}catch(d){t&&(t.textContent=String(d))}})()}),(l=document.getElementById("prof-save"))==null||l.addEventListener("click",()=>{(async()=>{try{const d=(e==null?void 0:e.value)||"",u=await G(d,s(),!0);t&&(t.textContent=u.saved?`saved
${u.diff}`:u.errors.join(`
`))}catch(d){t&&(t.textContent=String(d))}})()})}function A(t,n="var(--accent)"){const e=t.map(u=>Number(u.v??0));if(!e.length)return'<span class="meta">no samples</span>';const s=Math.min(...e),i=Math.max(...e),r=Math.max(1e-9,i-s),o=320,l=64,d=e.map((u,c)=>{const v=c/Math.max(1,e.length-1)*o,g=l-(u-s)/r*(l-4)-2;return`${v.toFixed(1)},${g.toFixed(1)}`}).join(" ");return`<svg class="spark" viewBox="0 0 ${o} ${l}" width="${o}" height="${l}">
    <polyline fill="none" stroke="${n}" stroke-width="1.5" points="${d}"/>
  </svg>`}async function ie(){var i;const t=await Y({}),n=t.runs.map(r=>`<option value="${a(r.id)}">${a(r.id.slice(0,8))}… · ${a(r.profile)}</option>`).join(""),e=((i=t.runs[0])==null?void 0:i.id)||"";let s='<div class="empty">Pick a run to load perf series.</div>';if(e){const r=await tt(e);s=it(e,r.series,r.summary)}return`
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
  `}function it(t,n,e){const s=Object.keys(n);return s.length?s.map(i=>{var o,l;const r=e[i]||{};return`<div class="panel" data-testid="perf-metric">
        <h2>${a(i)} <span class="meta">avg ${a(((l=(o=r.avg)==null?void 0:o.toFixed)==null?void 0:l.call(o,2))??"—")} · n ${a(r.count??0)}</span></h2>
        ${A(n[i]||[])}
      </div>`}).join(""):`<div class="empty">No perf samples for ${a(t)}.</div>`}function re(){var r,o;const t=document.getElementById("perf-series"),n=document.getElementById("perf-compare-out"),e=document.getElementById("perf-run"),s=document.getElementById("perf-a"),i=document.getElementById("perf-b");s&&i&&i.options.length>1&&(i.selectedIndex=1),(r=document.getElementById("perf-load"))==null||r.addEventListener("click",()=>{(async()=>{const l=(e==null?void 0:e.value)||"";if(!(!l||!t))try{const d=await tt(l);t.innerHTML=it(l,d.series,d.summary)}catch(d){t.textContent=String(d)}})()}),(o=document.getElementById("perf-compare"))==null||o.addEventListener("click",()=>{(async()=>{const l=(s==null?void 0:s.value)||"",d=(i==null?void 0:i.value)||"";if(n)try{const u=await wt(l,d),c=u.deltas.map(g=>{var _,$,f,w,p,m;return`<tr>
              <td>${a(g.metric)}</td>
              <td>${a(((f=($=(_=g.a)==null?void 0:_.avg)==null?void 0:$.toFixed)==null?void 0:f.call($,2))??"—")}</td>
              <td>${a(((m=(p=(w=g.b)==null?void 0:w.avg)==null?void 0:p.toFixed)==null?void 0:m.call(p,2))??"—")}</td>
              <td>${g.delta_avg==null?"—":a(g.delta_avg.toFixed(2))}</td>
            </tr>`}).join(""),v=Object.keys(u.series_a).map(g=>{const _=u.series_a[g]||[],$=u.series_b[g]||[];return`<div class="panel">
              <h2>${a(g)} overlay</h2>
              <div class="toolbar">
                <span class="meta">A</span>${A(_,"var(--accent)")}
                <span class="meta">B</span>${A($,"var(--ok)")}
              </div>
            </div>`}).join("");n.innerHTML=`
          <div class="table-wrap">
            <table data-testid="perf-delta-table">
              <thead><tr><th>Metric</th><th>A avg</th><th>B avg</th><th>Δ avg</th></tr></thead>
              <tbody>${c||'<tr><td colspan="4">No metrics</td></tr>'}</tbody>
            </table>
          </div>
          ${v}`}catch(u){n.textContent=String(u)}})()})}function L(t){const n=(e,s)=>`<a href="${e}" class="${t===s?"active":""}">${s}</a>`;return`<div class="subnav" data-testid="lens-nav">
    ${n("#/lens","Snapshots")}
    ${n("#/lens/diff","Diff")}
    ${n("#/lens/sessions","Sessions")}
    ${n("#/lens/turns","Agent")}
  </div>`}async function oe(){var o,l,d;const n=(await et()).snapshots||[],e=n.map(u=>`<option value="${a(u.id)}">${a(u.id)} · ${a(u.game_version)}</option>`).join(""),s=((o=n[1])==null?void 0:o.id)||((l=n[0])==null?void 0:l.id)||"",i=((d=n[0])==null?void 0:d.id)||"",r=n.map(u=>`
    <tr data-testid="lens-snap-row" data-snap-id="${a(u.id)}">
      <td class="wrap"><code>${a(u.id)}</code></td>
      <td>${a(u.game_version)}</td>
      <td>${a(u.feature_id??"—")}</td>
      <td>${a(u.created_at??"")}</td>
    </tr>`).join("");return`
    <h1>GameLens</h1>
    ${L("Snapshots")}
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
  `}async function de(){var g,_,$;const t=(await et()).snapshots||[],n=new URLSearchParams(location.hash.split("?")[1]||""),e=n.get("a")||((g=t[1])==null?void 0:g.id)||((_=t[0])==null?void 0:_.id)||"",s=n.get("b")||(($=t[0])==null?void 0:$.id)||"";if(!e||!s)return`
      <h1>Typed diff</h1>
      ${L("Diff")}
      <div class="empty" data-testid="lens-diff-empty">Pick two snapshots on GameLens.</div>`;const i=await Et(e,s),r=i.diff.entries||[],o=i.diff.by_system||{},d=Object.keys(o).sort().map(f=>{const w=(o[f]||[]).map(p=>`<li data-testid="lens-diff-entry">${a(ge(p))}</li>`).join("");return`<div class="panel"><h3>[${a(f)}]</h3><ul>${w}</ul></div>`}).join(""),u=i.implications;let c=[];try{(await k()).read_only||(c=(await j()).profiles||[])}catch{c=[]}const v=c.filter(f=>f.startsWith("ai_")).concat(c.filter(f=>!f.startsWith("ai_"))).map(f=>{const w=f==="ai_groq"?"selected":"";return`<option value="${a(f)}" ${w}>${a(f)}</option>`}).join("");return`
    <h1>Typed diff</h1>
    ${L("Diff")}
    <p class="meta" data-testid="lens-diff-meta">
      ${a(i.diff.snapshot_id_a||e)} → ${a(i.diff.snapshot_id_b||s)}
      · ${r.length} entries · framing vs measured stay separate
    </p>
    ${d||'<div class="empty">(no differences)</div>'}
    ${he(u)}
    <h2>Ask balance agent</h2>
    <p class="meta">Retune <em>priorities</em> only — model reasoning, never SO writes or green/red.</p>
    <div class="panel" data-testid="lens-agent-form">
      <label class="block">profile
        <select id="agent-profile" data-testid="agent-profile">${v||'<option value="ai_groq">ai_groq</option>'}</select>
      </label>
      <label class="block">question
        <textarea id="agent-q" data-testid="agent-q" rows="3">What should a human look at for a retune?</textarea>
      </label>
      <button type="button" id="agent-run" data-testid="agent-run">Ask</button>
      <div id="agent-msg" class="meta" data-testid="agent-msg"></div>
    </div>
    <div id="agent-result"></div>
    <script type="application/json" id="lens-pair">${JSON.stringify({a:e,b:s})}<\/script>
  `}async function le(){const n=((await kt()).sessions||[]).map(e=>`
    <tr data-testid="tel-session-row" data-session-id="${a(e.id)}">
      <td class="wrap"><a href="#/lens/sessions/${encodeURIComponent(e.id)}">${a(e.id)}</a></td>
      <td>${a(e.outcome??"—")}</td>
      <td class="wrap">${a(e.config_snapshot_id??"—")}</td>
      <td>${a(e.policy_id??"—")}</td>
      <td>${a(e.seed??"—")}</td>
      <td class="wrap">${a((e.notes||[]).join("; "))}</td>
    </tr>`).join("");return`
    <h1>Telemetry sessions</h1>
    ${L("Sessions")}
    <p class="meta"><code>outcome=lose</code> is measured play, not a bot/framework fail. <code>snap-unset</code> is a join gap.</p>
    <div class="table-wrap">
      <table data-testid="tel-sessions">
        <thead>
          <tr><th>Id</th><th>Outcome</th><th>Snapshot</th><th>Policy</th><th>Seed</th><th>Notes</th></tr>
        </thead>
        <tbody>${n||'<tr><td colspan="6">No telemetry sessions.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function ce(t){const e=(await It(t)).session;return`
    <p class="meta"><a href="#/lens/sessions">← Sessions</a> · ${a(e.id)}</p>
    <h1>Session</h1>
    ${L("Sessions")}
    ${ve(e)}
  `}async function ue(){const n=((await xt()).turns||[]).map(e=>`
    <tr data-testid="agent-turn-row" data-turn-id="${a(e.id)}">
      <td class="wrap"><a href="#/lens/turns/${encodeURIComponent(e.id)}">${a(e.id)}</a></td>
      <td>${a(e.status??"")}</td>
      <td>${a(e.framing??"")}</td>
      <td class="wrap">${a(e.question??"")}</td>
      <td>${a(e.created_at??"")}</td>
    </tr>`).join("");return`
    <h1>Balance agent</h1>
    ${L("Agent")}
    <p class="meta">Persisted turns. Numbers in citations are measured; priorities are model reasoning.</p>
    <div class="table-wrap">
      <table data-testid="agent-turns">
        <thead><tr><th>Id</th><th>Status</th><th>Framing</th><th>Question</th><th>Created</th></tr></thead>
        <tbody>${n||'<tr><td colspan="5">No agent turns yet. Ask from a typed diff.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function pe(t){const n=await Lt(t);return`
    <p class="meta"><a href="#/lens/turns">← Agent</a> · ${a(t)}</p>
    <h1>Agent turn</h1>
    ${L("Agent")}
    ${rt(n.turn)}
  `}function me(){var e;const t=document.getElementById("lens-open-diff");t==null||t.addEventListener("click",()=>{var r,o;const s=(r=document.getElementById("lens-a"))==null?void 0:r.value,i=(o=document.getElementById("lens-b"))==null?void 0:o.value;!s||!i||(location.hash=`/lens/diff?a=${encodeURIComponent(s)}&b=${encodeURIComponent(i)}`)});const n=(e=document.getElementById("lens-defaults"))==null?void 0:e.textContent;if(n)try{const s=JSON.parse(n),i=document.getElementById("lens-a"),r=document.getElementById("lens-b");i&&s.a&&(i.value=s.a),r&&s.b&&(r.value=s.b)}catch{}}function fe(){const t=document.getElementById("agent-run");t==null||t.addEventListener("click",()=>{(async()=>{var d,u,c;const n=document.getElementById("agent-msg"),e=document.getElementById("agent-result"),s=(d=document.getElementById("lens-pair"))==null?void 0:d.textContent;let i="",r="";try{const v=JSON.parse(s||"{}");i=v.a||"",r=v.b||""}catch{}const o=(u=document.getElementById("agent-q"))==null?void 0:u.value,l=(c=document.getElementById("agent-profile"))==null?void 0:c.value;n&&(n.textContent="running…");try{const v=await Ct({snapshot_a:i,snapshot_b:r,question:o||void 0,profile:l||void 0});n&&(n.textContent=`status=${v.turn.status}`),e&&(e.innerHTML=rt(v.turn))}catch(v){n&&(n.textContent=String(v))}})()})}function he(t){if(!t)return'<div class="empty" data-testid="lens-impl-empty">No persisted implications for this pair.</div>';const n=(t.gaps||[]).map(e=>`<li>${a(e)}</li>`).join("");return`
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
    </div>`}function ve(t){const n=(t.notes||[]).map(e=>`<li>${a(e)}</li>`).join("");return`
    <div class="panel" data-testid="tel-session-detail">
      <div class="meta">outcome=${a(t.outcome??"—")} · snapshot=${a(t.config_snapshot_id??"—")}
        · policy=${a(t.policy_id??"—")} · seed=${a(t.seed??"—")}</div>
      <h3>Notes</h3>
      <ul data-testid="tel-session-notes">${n||"<li>(none)</li>"}</ul>
      <h3>Summary (measured)</h3>
      <pre class="pre-json">${a(JSON.stringify(t.summary??{},null,2))}</pre>
    </div>`}function rt(t){const n=(t.priorities||[]).map(i=>`<li>${a(i)}</li>`).join(""),e=(t.gaps||[]).map(i=>`<li>${a(i)}</li>`).join(""),s=t.ai_cost_total!=null?String(t.ai_cost_total):"—";return`
    <div class="panel" data-testid="agent-turn">
      <div class="meta">status=${a(t.status??"")} · framing=${a(t.framing??"")}
        · cost_usd=${a(s)}${t.pending?` · pending=${a(t.pending)}`:""}</div>
      <h3>Priorities (model reasoning)</h3>
      <ul data-testid="agent-priorities">${n||"<li>(none)</li>"}</ul>
      <h3>Gaps</h3>
      <ul class="gap-list" data-testid="agent-gaps">${e||"<li>(none)</li>"}</ul>
      <h3>Measured citations</h3>
      <pre class="pre-json" data-testid="agent-measured">${a(JSON.stringify(t.citations??{},null,2))}</pre>
    </div>`}function ge(t){if(t.kind==="added_entity")return`+ entity ${t.entity_id}`;if(t.kind==="removed_entity")return`- entity ${t.entity_id}`;const n=t.path||"?";return t.delta!=null?`~ ${t.entity_id}.${n}: ${t.before} -> ${t.after} (delta ${t.delta})`:`~ ${t.entity_id}.${n}: ${JSON.stringify(t.before)} -> ${JSON.stringify(t.after)}`}function T(t){return t==null||Number.isNaN(t)?"—":`${(t*100).toFixed(1)}%`}function O(t){return t==null||Number.isNaN(t)?"—":t.toFixed(3)}async function ye(){var l,d,u;const n=(await Tt()).runs||[],e=n.map(c=>`<option value="${a(c.id)}">${a(c.id)} · ${a(c.provider||"—")}</option>`).join(""),s=((l=n[1])==null?void 0:l.id)||((d=n[0])==null?void 0:d.id)||"",i=((u=n[0])==null?void 0:u.id)||"",r=n.map(c=>`
    <tr data-testid="eval-row" data-eval-id="${a(c.id)}">
      <td class="wrap"><code>${a(c.id)}</code></td>
      <td>${a(c.provider??"—")}</td>
      <td>${a(c.prompt_version??"")}</td>
      <td>${a(T(c.diagnosis_accuracy))}</td>
      <td>${a(T(c.fix_correctness))}</td>
      <td>${a(T(c.false_green_rate))}</td>
      <td>${a(O(c.iterations_avg))}</td>
      <td>${c.case_count??0}</td>
      <td>${a(c.created_at??"")}</td>
    </tr>`).join("");let o=!0;try{o=!(await k()).read_only}catch{o=!0}return`
    <h1>Eval harness</h1>
    <p class="meta">Golden MockDriver cases. Metrics are gate-owned — models do not invent green/red.</p>
    <div class="table-wrap">
      <table data-testid="eval-table">
        <thead>
          <tr>
            <th>Id</th><th>Provider</th><th>Prompt</th>
            <th>Diagnosis</th><th>Fix</th><th>False-green</th>
            <th>Iters</th><th>n</th><th>When</th>
          </tr>
        </thead>
        <tbody>${r||'<tr><td colspan="9">No eval runs in this store.</td></tr>'}</tbody>
      </table>
    </div>
    <div class="toolbar">
      <label>A <select id="eval-a" data-testid="eval-a">${e}</select></label>
      <label>B <select id="eval-b" data-testid="eval-b">${e}</select></label>
      <button type="button" id="eval-compare" data-testid="eval-compare">Compare</button>
      ${o?'<button type="button" id="eval-run" data-testid="eval-run">Run fake eval</button>':""}
      <span id="eval-msg" class="meta" data-testid="eval-msg"></span>
    </div>
    <div id="eval-compare-out" data-testid="eval-compare-out"></div>
    <p class="meta">To write steps and generate a pytest file, open <a href="#/generate">Generate</a>.</p>
    <script type="application/json" id="eval-defaults">${JSON.stringify({a:s,b:i})}<\/script>
  `}function $e(){var s,i,r;const t=JSON.parse(((s=document.getElementById("eval-defaults"))==null?void 0:s.textContent)||"{}"),n=document.getElementById("eval-a"),e=document.getElementById("eval-b");n&&t.a&&(n.value=t.a),e&&t.b&&(e.value=t.b),(i=document.getElementById("eval-compare"))==null||i.addEventListener("click",()=>{(async()=>{const o=document.getElementById("eval-a").value,l=document.getElementById("eval-b").value,d=document.getElementById("eval-compare-out");if(!d||!o||!l)return;const c=(await Ot(o,l)).compare,g=["diagnosis_accuracy","fix_correctness","false_green_rate","iterations_avg","cost_usd"].map(_=>{var p,m,h,S,y;const $=(m=(p=c.a)==null?void 0:p.metrics)==null?void 0:m[_],f=(S=(h=c.b)==null?void 0:h.metrics)==null?void 0:S[_],w=(y=c.delta_b_minus_a)==null?void 0:y[_];return`<tr><td>${a(_)}</td><td>${a(O($??null))}</td>
            <td>${a(O(f??null))}</td><td>${a(O(w??null))}</td></tr>`}).join("");d.innerHTML=`
        <div class="table-wrap">
          <table data-testid="eval-delta-table">
            <thead><tr><th>Metric</th><th>A</th><th>B</th><th>B−A</th></tr></thead>
            <tbody>${g}</tbody>
          </table>
        </div>`})()}),(r=document.getElementById("eval-run"))==null||r.addEventListener("click",()=>{const o=document.getElementById("eval-msg");o&&(o.textContent="running…"),(async()=>{try{const l=await Nt({provider:"fake",prompt_version:"v1"});o&&(o.textContent=`ok ${l.run.id} false-green=${T(l.run.false_green_rate)}`),location.hash="/eval",window.dispatchEvent(new HashChangeEvent("hashchange"))}catch(l){o&&(o.textContent=String(l))}})()})}const be="ql-last-generated",we=`When the player taps Play, the HUD is visible.
Coins start at 100.
expect: green`,_e=`Ping the game. The Ping hook returns pong.
expect: green`;function ot(t){const n=t.gate||{};return[`verdict=${t.verdict??"—"}`,`mode=${n.mode??"—"}`,`executed=${String(n.executed??!1)}`,`accepted=${String(n.accepted??!1)}`,n.mock_driver?"mock_driver=true":"",n.expected?`expected=${n.expected}`:"",n.green!=null?`green=${String(n.green)}`:"",n.reason?`reason=${n.reason}`:""].filter(Boolean).join(" · ")}function Se(t){const n=t.gate||{},e=`${t.summary||""} ${n.reason||""}`;return n.reason==="rate_limited"||/\b429\b/.test(e)||/rate limit/i.test(e)}function Ee(t,n){const e=t.gate||{},s=String(e.stdout_tail||"").trim(),i=String(e.nodeid||""),r=!!e.mock_driver,l=!n&&!!e.accepted&&!!i&&!r?`<div class="toolbar" data-testid="gen-launch">
        <button type="button" id="gen-launch-editor" data-testid="gen-launch-editor">Launch Editor</button>
        <button type="button" id="gen-launch-android" data-testid="gen-launch-android">Launch Android</button>
        <label>device
          <select id="gen-device" data-testid="gen-device">
            <option value="">(auto / Editor OK)</option>
          </select>
        </label>
        <span class="meta">Unity Play + Wire, or APK + adb, must already be up.</span>
        <span id="gen-launch-msg" class="meta" data-testid="gen-launch-msg"></span>
      </div>`:r&&!n?'<p class="meta" data-testid="gen-mock-warn">This file is MockDriver (Demo). Unity will not move. Uncheck Demo, set GROQ_API_KEY on this HUD process, and Generate again with steps that match existing pages/hooks.</p>':"",d=Se(t)?'<p class="empty" data-testid="gen-429">Groq rate limit (HTTP 429). Wait about 20 seconds, then Generate again. Optional: run Ollama locally as fallback.</p>':"";return`
    <div class="panel" data-testid="gen-result">
      <p class="meta" data-testid="gen-gate">${a(ot(t))}</p>
      <p class="meta">task <code>${a(t.id)}</code>
        ${i?` · file <code data-testid="gen-nodeid">${a(i)}</code>`:""}</p>
      ${d}
      <p>${a(t.summary||"")}</p>
      ${e.mode==="collect"&&e.accepted&&!r?'<p class="meta">Collect gate passed — not a live Unity/device run.</p>':""}
      ${l}
      ${s?`<pre class="log" data-testid="gen-stdout">${a(s)}</pre>`:""}
    </div>`}function ke(t){return t.length?`
    <div class="table-wrap">
      <table data-testid="gen-table">
        <thead><tr><th>Task</th><th>Verdict</th><th>Accepted</th><th>When</th></tr></thead>
        <tbody>${t.map(e=>{var s;return`
    <tr data-testid="gen-row" data-task-id="${a(e.id)}">
      <td class="wrap"><code>${a(e.id)}</code></td>
      <td><span class="badge ${a(e.verdict||"")}">${a(e.verdict||"—")}</span></td>
      <td>${a(String(((s=e.gate)==null?void 0:s.accepted)??"—"))}</td>
      <td>${a(e.created_at??"")}</td>
    </tr>`}).join("")}</tbody>
      </table>
    </div>`:'<p class="meta" data-testid="gen-empty">No generate tasks in this store yet.</p>'}async function Ie(){const t=document.getElementById("gen-device");if(t)try{const n=await D(),e=t.value;t.innerHTML=['<option value="">(auto / Editor OK)</option>',...(n.devices||[]).map(s=>`<option value="${a(s.id)}">${a(s.id)} · ${a(s.platform)}</option>`)].join(""),e&&(t.value=e)}catch{}}function xe(t){var e,s;const n=(i,r)=>{(async()=>{var g;const o=(g=document.getElementById("gen-device"))==null?void 0:g.value,l=document.getElementById("gen-launch-msg"),d=document.getElementById("gen-msg"),u=`launching ${i}…`;l&&(l.textContent=u),d&&(d.textContent=u);const c=document.getElementById("gen-launch-editor"),v=document.getElementById("gen-launch-android");c&&(c.disabled=!0),v&&(v.disabled=!0);try{await Z({profile:i,tests:[t],device_serial:o||void 0,config:"questline.toml",live_target:r,reporters:["console"]}),location.hash="/live"}catch(_){const $=String(_);l&&(l.textContent=$),d&&(d.textContent=$),c&&(c.disabled=!1),v&&(v.disabled=!1)}})()};(e=document.getElementById("gen-launch-editor"))==null||e.addEventListener("click",()=>{n("editor",!0)}),(s=document.getElementById("gen-launch-android"))==null||s.addEventListener("click",()=>{n("android_local",!0)}),Ie()}async function Le(){let t=!0,n=!1,e="generated-tests",s=!1,i=!1;try{const u=await k();t=!u.read_only,n=!!u.smoke,e=u.default_generate_dest||e,s=!!u.has_pages,i=!!u.has_llm}catch{t=!0}const r=await jt().catch(()=>({tasks:[],empty:!0})),o=n?"SMOKE writes a canned Play→HUD MockDriver test. Launch Editor/Android is hidden here (fake launcher).":"Uncheck Demo to send your steps to Groq/Ollama. Each Generate writes a new test_gen_*.py — it will not launch an old suite file. The collect gate does not start Unity — use Launch Editor / Android after. Demo = canned MockDriver (Unity will not move). HTTP 429 = Groq rate limit: wait ~20s and Generate again (or start Ollama).",l=!n&&!i?'<p class="empty" data-testid="gen-no-llm">No live LLM in this HUD process. Set <code>GROQ_API_KEY</code> (or run Ollama with an <code>ai_ollama</code> profile) and restart <code>questline hud</code>. Without that, Generate with Demo unchecked returns 400 — it will not silently write MockDriver.</p>':"",d=s&&!n?_e:we;return`
    <h1>Generate tests</h1>
    <p class="meta">Write the steps. The agent writes a pytest using pages/locators under this HUD project root. Models do not invent green/red.</p>
    <p class="meta">${a(o)} Eval scores live on <a href="#/eval">Eval</a>.</p>
    ${l}
    ${t?`<form id="gen-form" data-testid="gen-form" class="panel">
      <label>Steps / spec
        <textarea id="gen-spec" data-testid="gen-spec" rows="8">${a(d)}</textarea>
      </label>
      <div class="toolbar">
        <label>dest <input id="gen-dest" data-testid="gen-dest" value="${a(e)}"/></label>
        <label class="check">
          <input type="checkbox" id="gen-demo" data-testid="gen-demo" ${n?"checked":""}/>
          Demo (canned MockDriver)
        </label>
        <button type="button" id="gen-run" data-testid="gen-run">Generate</button>
        <span id="gen-msg" class="meta" data-testid="gen-msg"></span>
      </div>
    </form>
    <div id="gen-out" data-testid="gen-out"></div>`:'<p class="empty">Read-only HUD — Generate is disabled.</p>'}
    <h2>Recent</h2>
    ${ke(r.tasks||[])}
  `}function Ce(){var t;(t=document.getElementById("gen-run"))==null||t.addEventListener("click",()=>{var o,l,d;const n=((o=document.getElementById("gen-spec"))==null?void 0:o.value)||"",e=((l=document.getElementById("gen-dest"))==null?void 0:l.value.trim())||"generated-tests",s=((d=document.getElementById("gen-demo"))==null?void 0:d.checked)??!1,i=document.getElementById("gen-msg"),r=document.getElementById("gen-out");i&&(i.textContent="generating…"),(async()=>{let u=!1;try{u=!!(await k()).smoke}catch{u=!1}try{const c=await Rt({spec:n,dest:e,demo:s});i&&(i.textContent=ot(c.task));const v=c.task.gate||{},g=String(v.nodeid||"");if(g&&!v.mock_driver)try{sessionStorage.setItem(be,g)}catch{}r&&(r.innerHTML=Ee(c.task,u)),g&&!v.mock_driver&&xe(g)}catch(c){i&&(i.textContent=String(c))}})()})}const Q=document.querySelector("#app");let B=!1,N=!1,R=!1;function V(t,n){const e=(l,d)=>`<a href="${l}" class="${t===d?"active":""}">${d}</a>`,s=B?"":`${e("#/launch","Launch")}
        ${e("#/quarantine","Quarantine")}
        ${e("#/profiles","Profiles")}`,i=[B?'<span class="badge warn" title="--read-only">RO</span>':"",N?'<span class="badge warn" title="Playwright smoke fixture — not real runs">SMOKE</span>':"",R?'<span class="badge warn" title="Restart questline hud">STALE API</span>':""].filter(Boolean).join(" "),r=N?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)">
        <strong>SMOKE FIXTURE SERVER</strong> — fake launcher + seeded runs.
        For real Wire/mock runs stop this process and use
        <code>uv run questline hud --open</code> (port 8741).
      </div>`:"",o=R?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)" data-testid="stale-api">
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
        ${e("#/generate","Generate")}
        ${e("#/eval","Eval")}
        ${e("#/trends","Trends")}
        ${e("#/live","Live")}
      </nav>
      ${i}
    </header>
    <main class="main">${r}${o}${n}</main>
  `}function Be(){const e=((location.hash.replace(/^#\/?/,"")||"").split("?")[0]||"").split("/").filter(Boolean);if(e[0]==="runs"&&e[1]&&e[2]==="tests"&&e.length>=4){const s=e.slice(3).join("/");let i=s;try{i=decodeURIComponent(s)}catch{}return{name:"test",params:{runId:e[1],testId:i}}}return e[0]==="runs"&&e[1]?{name:"run",params:{runId:e[1]}}:e[0]==="trends"?{name:"trends",params:{}}:e[0]==="live"?{name:"live",params:{}}:e[0]==="launch"?{name:"launch",params:{}}:e[0]==="quarantine"?{name:"quarantine",params:{}}:e[0]==="profiles"?{name:"profiles",params:{}}:e[0]==="perf"?{name:"perf",params:{}}:e[0]==="eval"?{name:"eval",params:{}}:e[0]==="generate"?{name:"generate",params:{}}:e[0]==="lens"?e[1]==="diff"?{name:"lens-diff",params:{}}:e[1]==="sessions"&&e[2]?{name:"lens-session",params:{id:e[2]}}:e[1]==="sessions"?{name:"lens-sessions",params:{}}:e[1]==="turns"&&e[2]?{name:"lens-turn",params:{id:e[2]}}:e[1]==="turns"?{name:"lens-turns",params:{}}:{name:"lens",params:{}}:{name:"runs",params:{}}}function qe(t){return t.length?`
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
      <td>${a(x(e.duration_s))}</td>
      <td>${a(e.started_at??"")}</td>
    </tr>`).join("")}</tbody>
      </table>
    </div>`:`<div class="empty" data-testid="empty-store">
      No runs in the store yet.<br/>
      Use <a href="#/launch">Launch</a> or run a suite with the questline plugin, then refresh.
    </div>`}async function Pe(){const t=new URLSearchParams(location.hash.split("?")[1]||""),n=t.get("profile")||"",e=t.get("status")||"",s=await Y({profile:n||void 0,status:e||void 0});return`
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
      ${B?"":'<a class="btn" href="#/launch">Launch run</a>'}
    </div>
    ${qe(s.runs)}
  `}async function dt(){const t=Be();try{let n="",e="Runs";t.name==="run"?(n=await At(t.params.runId),e="Runs"):t.name==="test"?(n=await Gt(t.params.runId,t.params.testId),e="Runs"):t.name==="trends"?(n=await Wt(),e="Trends"):t.name==="live"?(n=await Kt(),e="Live"):t.name==="launch"?(n=await Zt(),e="Launch"):t.name==="quarantine"?(n=await ee(),e="Quarantine"):t.name==="profiles"?(n=await ae(),e="Profiles"):t.name==="perf"?(n=await ie(),e="Perf"):t.name==="eval"?(n=await ye(),e="Eval"):t.name==="generate"?(n=await Le(),e="Generate"):t.name==="lens"?(n=await oe(),e="GameLens"):t.name==="lens-diff"?(n=await de(),e="GameLens"):t.name==="lens-sessions"?(n=await le(),e="GameLens"):t.name==="lens-session"?(n=await ce(t.params.id),e="GameLens"):t.name==="lens-turns"?(n=await ue(),e="GameLens"):t.name==="lens-turn"?(n=await pe(t.params.id),e="GameLens"):(n=await Pe(),e="Runs"),Q.innerHTML=V(e,n),Te(t.name)}catch(n){Q.innerHTML=V("Runs",`<div class="empty">Failed to load HUD: ${a(String(n))}</div>`)}}function Te(t){var n;if(t==="runs"&&((n=document.getElementById("f-apply"))==null||n.addEventListener("click",()=>{const e=document.getElementById("f-profile").value.trim(),s=document.getElementById("f-status").value,i=new URLSearchParams;e&&i.set("profile",e),s&&i.set("status",s);const r=i.toString();location.hash=r?`/?${r}`:"/"})),t==="live"){const e=document.getElementById("live-root");e&&Qt(e)}t==="launch"&&te(),t==="quarantine"&&ne(),t==="profiles"&&se(),t==="perf"&&re(),t==="eval"&&$e(),t==="generate"&&Ce(),t==="lens"&&me(),t==="lens-diff"&&fe(),t==="run"&&Dt(),t==="test"&&Ft()}async function Oe(){var t,n,e,s,i,r;try{const o=await k();B=!!o.read_only,N=!!o.smoke,R=!((t=o.api)!=null&&t.test_by_query)||!((n=o.api)!=null&&n.lens)||!((e=o.api)!=null&&e.agents)||!((s=o.api)!=null&&s.eval)||!((i=o.api)!=null&&i.generate)||!((r=o.api)!=null&&r.generate_launch),B||await q()}catch{B=!1,N=!1,R=!0}await dt()}window.addEventListener("hashchange",()=>{dt()});Oe();
