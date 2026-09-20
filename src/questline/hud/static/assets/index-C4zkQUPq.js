(function(){const a=document.createElement("link").relList;if(a&&a.supports&&a.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))s(i);new MutationObserver(i=>{for(const r of i)if(r.type==="childList")for(const d of r.addedNodes)d.tagName==="LINK"&&d.rel==="modulepreload"&&s(d)}).observe(document,{childList:!0,subtree:!0});function e(i){const r={};return i.integrity&&(r.integrity=i.integrity),i.referrerPolicy&&(r.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?r.credentials="include":i.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function s(i){if(i.ep)return;i.ep=!0;const r=e(i);fetch(i.href,r)}})();let q=null;async function y(t){const a=await fetch(t),e=await a.text();if(/^\s*</.test(e)||(a.headers.get("content-type")||"").includes("text/html"))throw new Error(`${a.status} ${t}: got HTML instead of JSON. Restart questline hud (old process missing new /api routes).`);if(!a.ok)throw new Error(`${a.status} ${t}: ${e}`);try{return JSON.parse(e)}catch(i){throw new Error(`${t}: invalid JSON (${String(i)})`)}}async function C(){return q||(q=(await y("/api/csrf")).csrf_token,q)}async function _(t,a,e){const s=await C(),i=await fetch(a,{method:t,headers:{"Content-Type":"application/json","X-CSRF-Token":s},body:e===void 0?void 0:JSON.stringify(e)});if(!i.ok){const r=await i.text();throw new Error(`${i.status} ${a}: ${r}`)}if(i.status!==204)return await i.json()}function k(){return y("/api/meta")}function J(t){const a=new URLSearchParams;t.profile&&a.set("profile",t.profile),t.status&&a.set("status",t.status);const e=a.toString();return y(`/api/runs${e?`?${e}`:""}`)}function at(t){return y(`/api/runs/${encodeURIComponent(t)}`)}function nt(t,a){const e=new URLSearchParams({id:a});return y(`/api/runs/${encodeURIComponent(t)}/test?${e.toString()}`)}function st(t=50){return y(`/api/trends?limit=${t}`)}function j(t){const a=t?`?config=${encodeURIComponent(t)}`:"";return y(`/api/profiles${a}`)}function it(){return y("/api/configs")}function H(){return y("/api/devices")}function W(t){return y(`/api/profiles/${encodeURIComponent(t)}`)}function rt(t,a){return _("POST",`/api/profiles/${encodeURIComponent(t)}/validate`,{fields:a,apply:!1})}function M(t,a,e){return _("POST",`/api/profiles/${encodeURIComponent(t)}`,{fields:a,apply:e})}function ot(){return y("/api/reporters")}function G(){return y("/api/launcher")}function dt(t){return _("POST","/api/launcher/start",t)}function lt(){return _("POST","/api/launcher/stop")}function ct(){return y("/api/quarantine")}function ut(t){return _("POST","/api/quarantine",t)}function pt(t){return _("DELETE",`/api/quarantine?test_id=${encodeURIComponent(t)}`)}function ft(t){return _("POST","/api/quarantine/audit",t||{})}function Q(t){return y(`/api/perf/${encodeURIComponent(t)}`)}function mt(t,a){return y(`/api/perf/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(a)}`)}function ht(t=50){return y(`/api/perf/correlation?limit=${t}`)}function vt(t){return`/api/artifacts/file?path=${encodeURIComponent(t)}`}function K(){return y("/api/lens/snapshots")}function gt(t,a){const e=new URLSearchParams({a:t,b:a});return y(`/api/lens/diff?${e.toString()}`)}function $t(){return y("/api/telemetry/sessions")}function yt(t){return y(`/api/telemetry/sessions/${encodeURIComponent(t)}`)}function bt(){return y("/api/lens/agent/turns")}function wt(t){return y(`/api/lens/agent/turns/${encodeURIComponent(t)}`)}function _t(t){return _("POST","/api/lens/agent/run",t)}function V(t){return y(`/api/runs/${encodeURIComponent(t)}/agent-tasks`)}function St(t){return _("POST","/api/agents/triage",t)}function Et(t){return _("POST","/api/agents/diagnose",t)}function kt(t){return _("POST","/api/agents/heal",t)}function xt(){return y("/api/eval/runs")}function It(t,a){return y(`/api/eval/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(a)}`)}function Lt(t){return _("POST","/api/eval/run",t)}function Bt(t){return _("POST","/api/agents/generate",t)}function x(t){if(t==null||Number.isNaN(t))return"—";if(t<60)return`${t.toFixed(1)}s`;const a=Math.floor(t/60),e=t-a*60;return`${a}m ${e.toFixed(0)}s`}function n(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function Ct(t){const a=await at(t),e=a.run,s=a.banner,i=a.tests.map(c=>`
    <tr data-testid="test-row" data-test-id="${n(c.id)}">
      <td class="wrap"><a href="#/runs/${encodeURIComponent(t)}/tests/${encodeURIComponent(c.id)}">${n(c.nodeid)}</a></td>
      <td><span class="badge ${n(c.status)}">${n(c.status)}</span></td>
      <td class="verdict-${n(c.verdict??"")}">${n(c.verdict??"—")}</td>
      <td>${n(x(c.duration_s))}</td>
      <td class="wrap">${n(c.death_step_name??"")}</td>
    </tr>`).join(""),d=(a.ai_calls||[]).map(c=>`
    <tr data-testid="ai-call-row">
      <td>${n(c.provider??"—")}</td>
      <td class="wrap">${n(c.model??"—")}</td>
      <td>${n(c.tokens_in??0)}</td>
      <td>${n(c.tokens_out??0)}</td>
      <td>${n(U(c.cost))}</td>
      <td>${n(c.outcome??"—")}</td>
      <td class="wrap">${n(c.purpose??"")}</td>
    </tr>`).join("")||'<tr><td colspan="7">No AI calls for this run.</td></tr>',l=a.tests.some(c=>c.status==="failed"||c.status==="error");let o=!0;try{o=!(await k()).read_only}catch{o=!0}let u=[];try{u=(await V(t)).tasks||[]}catch{u=[]}return`
    <p class="meta"><a href="#/">← Runs</a> · ${n(e.id)}</p>
    <h1>Run detail</h1>
    <div class="meta">
      profile=${n(e.profile)} · driver=${n(e.driver??"—")} ·
      device=${n(e.device??"—")} · status=${n(e.status)} ·
      duration=${n(x(e.duration_s))}
    </div>
    <div class="banner" data-testid="verdict-banner">
      <div class="stat ok"><span>passed</span><b>${e.passed}</b></div>
      <div class="stat"><span>failed</span><b>${e.failed}</b></div>
      <div class="stat infra"><span>infra</span><b>${s.infra_failures}</b></div>
      <div class="stat test"><span>test</span><b>${s.test_failures}</b></div>
      <div class="stat"><span>authoring</span><b>${s.authoring_failures}</b></div>
    </div>
    ${l&&o?`<div class="toolbar" data-testid="agent-run-actions">
      <button type="button" id="triage-run" data-testid="triage-run">Triage this run</button>
      <span id="triage-msg" class="meta" data-testid="triage-msg"></span>
    </div>
    <div id="triage-result" data-testid="triage-result">${Nt(u)}</div>
    <script type="application/json" id="run-agent-ctx">${JSON.stringify({runId:t})}<\/script>`:""}
    <h2>AI calls</h2>
    <div class="meta">total_usd=${n(U(a.ai_cost_total))}</div>
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
  `}function qt(){const t=document.getElementById("triage-run");t==null||t.addEventListener("click",()=>{(async()=>{var r;const a=document.getElementById("triage-msg"),e=document.getElementById("triage-result"),s=(r=document.getElementById("run-agent-ctx"))==null?void 0:r.textContent;let i="";try{i=String(JSON.parse(s||"{}").runId||"")}catch{}if(i){a&&(a.textContent="running…");try{const d=await St({run_id:i});a&&(a.textContent=`status=${d.task.status} verdict=${d.task.verdict}`),e&&(e.innerHTML=X(d.task))}catch(d){a&&(a.textContent=String(d))}}})()})}function Nt(t){return t.length?t.map(X).join(""):'<p class="meta">No agent tasks yet.</p>'}function X(t){const a=(t.clusters||[]).map(e=>{const s=String(e.bucket??e.key??""),i=String(e.error_type??""),r=Array.isArray(e.test_ids)?e.test_ids.length:"",d=String(e.hypothesis??e.signature??"");return`<li>${n(s)} · ${n(i)} x${n(r)} — ${n(d)}</li>`}).join("");return`
    <div class="panel" data-testid="agent-task" data-task-kind="${n(t.kind??"")}">
      <div class="meta">kind=${n(t.kind??"")} · verdict=${n(t.verdict??"")}
        · cause=${n(t.cause??"")} · status=${n(t.status??"")}</div>
      <p>${n(t.summary??"")}</p>
      ${a?`<ul data-testid="triage-clusters">${a}</ul>`:""}
    </div>`}function U(t){return t==null||Number.isNaN(t)?"0.000000":t.toFixed(6)}async function Pt(t,a){const e=await nt(t,a),s=e.test,i=e.steps.map(p=>{const g=String(p.status??"");return`<li data-testid="step-row">
        <span class="ts">${n(p.started_at??"")}</span>
        <span class="badge ${n(g)}">${n(g)}</span>
        <span>${n(p.name??"")}${p.error_message?` — ${n(p.error_message)}`:""}</span>
      </li>`}).join(""),r=(e.history||[]).map(p=>{const g=String(p.status??""),b=Number(p.duration_s??0)||1,w=Math.max(4,Math.min(28,b*4));return`<i class="${n(g)}" style="height:${w}px" title="${n(g)}"></i>`}).join(""),d=e.death_point||{},l=d.last_started_step||{},o=d.driver_health||{},u=s.verdict==="infra"?"infra":"",c=(e.artifacts||[]).map(p=>{const g=String(p.path??""),b=String(p.kind??""),w=String(p.name??g),v=vt(g);return b==="screenshot"||/\.(png|jpe?g|webp|gif)$/i.test(w)?`<div><a href="${n(v)}" target="_blank" rel="noreferrer">
          <img src="${n(v)}" alt="${n(w)}"/><div>${n(w)}</div></a></div>`:`<div><a href="${n(v)}" target="_blank" rel="noreferrer">${n(w)}</a>
        <div class="meta">${n(b)} · ${n(p.size_bytes??"")} B</div></div>`}).join(""),h=s.status==="failed"||s.status==="error";let $=!0;try{$=!(await k()).read_only}catch{$=!0}const f=String(s.error_type??"").includes("ElementNotFound");let m=[];try{m=((await V(t)).tasks||[]).filter(g=>!g.test_id||g.test_id===a)}catch{m=[]}return`
    <p class="meta">
      <a href="#/">Runs</a> /
      <a href="#/runs/${n(t)}">${n(t.slice(0,8))}…</a>
    </p>
    <h1 data-testid="test-title">${n(s.nodeid)}</h1>
    <div class="meta">
      status=<span class="badge ${n(s.status)}">${n(s.status)}</span> ·
      verdict=<span class="verdict-${n(s.verdict??"")}">${n(s.verdict??"—")}</span> ·
      duration=${n(x(s.duration_s))}
    </div>

    ${h&&$?`<div class="toolbar" data-testid="agent-test-actions">
      <button type="button" id="diagnose-test" data-testid="diagnose-test">Diagnose this test</button>
      <button type="button" id="fix-test" data-testid="fix-test">Fix this test</button>
      ${f?'<button type="button" id="heal-test" data-testid="heal-test">Suggest locator</button>':""}
      <span id="diagnose-msg" class="meta" data-testid="diagnose-msg"></span>
    </div>
    <div id="diagnose-result" data-testid="diagnose-result">${Rt(m)}</div>
    <script type="application/json" id="test-agent-ctx">${JSON.stringify({runId:t,testId:a,locatorMiss:f})}<\/script>`:""}

    <div class="panel death ${u}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${n(l.name??"—")}</b>
        @ ${n(l.started_at??"")}</div>
      <div>error: ${n(s.error_type??"")} — ${n(s.error_message??"")}</div>
      <div>driver health: ${n(JSON.stringify(o||{}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${r||"<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${i||"<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${c||"<span class='meta'>none</span>"}</div>
  `}function Ot(){var r,d,l;const t=document.getElementById("test-agent-ctx");let a="",e="";try{const o=JSON.parse((t==null?void 0:t.textContent)||"{}");a=o.runId||"",e=o.testId||""}catch{return}const s=()=>document.getElementById("diagnose-msg"),i=()=>document.getElementById("diagnose-result");(r=document.getElementById("diagnose-test"))==null||r.addEventListener("click",()=>{T("diagnose",a,e,s(),i())}),(d=document.getElementById("fix-test"))==null||d.addEventListener("click",()=>{window.confirm("Fix mode writes files under the project jail and re-runs the test. Continue?")&&T("fix",a,e,s(),i())}),(l=document.getElementById("heal-test"))==null||l.addEventListener("click",()=>{T("heal",a,e,s(),i())})}async function T(t,a,e,s,i){if(!(!a||!e)){s&&(s.textContent="running…");try{const r=t==="heal"?await kt({run_id:a,test_id:e}):await Et({run_id:a,test_id:e,fix:t==="fix"});s&&(s.textContent=`status=${r.task.status} verdict=${r.task.verdict}`),i&&(i.innerHTML=z(r.task))}catch(r){s&&(s.textContent=String(r))}}}function Rt(t){return t.length?t.map(z).join(""):""}function z(t){const a=t.suggestion||{},e=typeof a.yaml_diff=="string"?a.yaml_diff:"",s=t.gate?`gate accepted=${n(String(t.gate.accepted??""))}`:"";return`
    <div class="panel" data-testid="agent-task" data-task-kind="${n(t.kind??"")}">
      <div class="meta">kind=${n(t.kind??"")} · verdict=${n(t.verdict??"")}
        · cause=${n(t.cause??"")} ${s}</div>
      <p>${n(t.summary??"")}</p>
      ${e?`<pre data-testid="heal-diff">${n(e)}</pre>`:""}
    </div>`}async function jt(){const[t,a]=await Promise.all([st(50),ht(50)]),e=t.series||[],s=Math.max(1,...e.map(o=>Number(o.duration_s??0)||0)),i=e.map(o=>{const u=o.pass_rate==null?0:Number(o.pass_rate),c=Math.max(4,Math.round(u*100)),h=Number(o.duration_s??0);return`<div class="bar ${Number(o.failed??0)>0?"fail":""}" style="height:${c}%">
        <span>${n(o.run_id)} · ${(u*100).toFixed(0)}% · ${n(x(h))}</span>
      </div>`}).join(""),r=e.map(o=>{const u=Number(o.duration_s??0);return`<div class="bar" style="height:${Math.max(4,Math.round(u/s*100))}%">
        <span>${n(o.run_id)} · ${n(x(u))}</span>
      </div>`}).join(""),d=(t.flaky_tests||[]).map(o=>`<tr>
        <td class="wrap">${n(o.nodeid)}</td>
        <td>${n(o.runs)}</td>
        <td>${n(o.passed)}/${n(o.failed)}</td>
        <td>${(Number(o.pass_rate)*100).toFixed(0)}%</td>
        <td>${(Number(o.flake_score)*100).toFixed(0)}%</td>
      </tr>`).join(""),l=(a.tests||[]).map(o=>{const u=(o.points||[]).map(c=>{const h=c.duration_s==null?0:Number(c.duration_s);return`<span class="dot ${c.passed?"ok":"bad"}" title="${n(c.run_id)} · ${n(x(h))}"></span>`}).join("");return`<tr>
        <td class="wrap">${n(o.nodeid)}</td>
        <td>${o.passed}/${o.failed}</td>
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
        <tbody>${d||'<tr><td colspan="5">No flaky tests detected.</td></tr>'}</tbody>
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
  `}async function Tt(){return`
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `}function At(t){const a=document.getElementById("live-status"),e=document.getElementById("live-clear");e==null||e.addEventListener("click",()=>{t.innerHTML=""});const i=`${location.protocol==="https:"?"wss":"ws"}://${location.host}/live`;let r;try{r=new WebSocket(i)}catch(d){a&&(a.textContent="failed"),t.innerHTML=`<div>WebSocket error: ${n(String(d))}</div>`;return}r.onopen=()=>{a&&(a.textContent="live",a.className="badge passed")},r.onclose=()=>{a&&(a.textContent="closed",a.className="badge failed")},r.onerror=()=>{a&&(a.textContent="error",a.className="badge failed")},r.onmessage=d=>{try{const l=JSON.parse(String(d.data)),o=String(l.type??"?"),u=String(l.timestamp??""),c=l.nodeid||l.name||l.test_id||l.status||l.profile||"",h=document.createElement("div");h.innerHTML=`<span class="t">${n(u)}</span><b>${n(o)}</b> ${n(c)}`,t.prepend(h)}catch{const l=document.createElement("div");l.textContent=String(d.data),t.prepend(l)}}}const Y=[{id:"mock",label:"Mock demo",config:"questline.toml",profile:"mock",tests:"examples/demo-tests",live_target:!1,note:"No Unity. CI-style mock driver."},{id:"wire-editor",label:"Wire Editor",config:"examples/wire-smoke/questline.toml",profile:"editor",tests:"examples/wire-smoke",live_target:!0,note:"Unity Play + Wire on :13000. Device picker stays empty (OK)."},{id:"wire-android",label:"Wire Android",config:"examples/wire-smoke/questline.toml",profile:"android_local",tests:"examples/wire-smoke",live_target:!0,note:"Dev APK + adb. Pick a serial if more than one device."}];async function Mt(){var g,b,w;await C();let t,a,e,s;try{[t,a,e,s]=await Promise.all([k(),it().catch(()=>({project_root:"",active:"",configs:[{path:"questline.toml",absolute:"questline.toml"}]})),ot().catch(()=>({reporters:["console"]})),G().catch(()=>({launcher:{state:"idle"}}))])}catch(v){return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-error">
        Failed to load launcher APIs: ${n(String(v))}<br/>
        Stop the old <code>questline hud</code> process and start it again from
        <code>D:\\dev\\questline</code>.
      </div>`}if(t.read_only)return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;const i=((g=a.configs.find(v=>v.path.replace(/\\/g,"/")==="questline.toml"))==null?void 0:g.path)||((b=a.configs[0])==null?void 0:b.path)||"questline.toml",r=await j(i),d=await H(),l=(a.configs||[]).map(v=>{const E=v.path===i?"selected":"";return`<option value="${n(v.path)}" ${E}>${n(v.path)}</option>`}).join(""),o=(r.profiles||[]).map(v=>{const E=r.profiles.includes("editor")?"editor":r.profiles.includes("mock")?"mock":r.profiles[0]||"";return`<option value="${n(v)}" ${v===E?"selected":""}>${n(v)}</option>`}).join(""),u=['<option value="">(no adb pin — OK for Editor)</option>',...(d.devices||[]).map(v=>`<option value="${n(v.id)}">${n(v.id)} · ${n(v.platform)}</option>`)].join(""),c=(e.reporters||[]).map(v=>`<label class="check"><input type="checkbox" name="reporter" value="${n(v)}" ${v==="console"?"checked":""}/> ${n(v)}</label>`).join(""),h=Y.map(v=>`<button type="button" class="preset" data-preset="${n(v.id)}" title="${n(v.note)}">${n(v.label)}</button>`).join(""),$=s.launcher,f=["starting","running","stopping"].includes($.state||""),m=d.hint||((w=d.devices)!=null&&w.length?`${d.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire.");return`
    <h1>Run launcher</h1>
    ${f?`<div class="empty" data-testid="launch-busy">
        A managed run is <strong>${n($.state||"")}</strong>
        (job <code>${n($.job_id||"")}</code>, profile
        <code>${n($.profile||"")}</code>).
        <a href="#/live">Open Live</a> to watch it, or <strong>Stop</strong> below
        before launching another.
      </div>`:""}
    <p class="meta">Profiles come from <code>questline.toml</code> (not from Unity being open).
      Unity Play + Wire = use preset <strong>Wire Editor</strong> or profile <code>editor</code>.
      Device list is <em>adb only</em> — Editor does not appear there.</p>
    <div class="toolbar" data-testid="launch-presets">
      <span class="meta">Presets:</span> ${h}
    </div>
    <div class="panel" data-testid="launch-form">
      <div class="toolbar">
        <label>config
          <select id="launch-config" data-testid="launch-config">${l}</select>
        </label>
        <label>profile
          <select id="launch-profile" data-testid="launch-profile">${o}</select>
        </label>
        <label>device
          <select id="launch-device" data-testid="launch-device">${u}</select>
        </label>
        <button type="button" id="launch-refresh-devices" data-testid="launch-refresh-devices">Refresh devices</button>
      </div>
      <p class="meta" id="launch-device-hint" data-testid="launch-device-hint">${n(m)}</p>
      ${d.error?`<p class="meta">adb error: ${n(d.error)}</p>`:""}
      <label class="block">markers <input id="launch-markers" placeholder="optional -m expression" data-testid="launch-markers"/></label>
      <label class="block">tests (one path/nodeid per line)
        <textarea id="launch-tests" rows="4" data-testid="launch-tests" placeholder="examples/wire-smoke">examples/demo-tests</textarea>
      </label>
      <div class="toolbar wrap">${c||"<span class='meta'>no reporters</span>"}</div>
      <label class="check"><input type="checkbox" id="launch-quarantine"/> include quarantined</label>
      <label class="check"><input type="checkbox" id="launch-live" data-testid="launch-live"/> QUESTLINE_LIVE_TARGET=1 (required for wire-smoke)</label>
      <div class="toolbar">
        <button type="button" id="launch-start" data-testid="launch-start" ${f?"disabled":""}>Launch</button>
        <button type="button" id="launch-stop" data-testid="launch-stop" ${f?"":"disabled"}>Stop</button>
        ${f?'<a class="button" href="#/live" data-testid="launch-open-live">Open Live</a>':""}
      </div>
      <p class="meta">Active project: <code>${n(a.project_root)}</code></p>
    </div>
    <h2>Status</h2>
    <pre class="log" id="launch-status" data-testid="launch-status">${n(JSON.stringify($,null,2))}</pre>
  `}function Ut(){var c,h,$;const t=document.getElementById("launch-status"),a=document.getElementById("launch-config"),e=document.getElementById("launch-profile"),s=document.getElementById("launch-device"),i=document.getElementById("launch-tests"),r=document.getElementById("launch-live"),d=document.getElementById("launch-device-hint"),l=async()=>{if(!(!a||!e))try{const f=await j(a.value),m=f.profiles.includes("editor")?"editor":f.profiles[0]||"";e.innerHTML=f.profiles.map(p=>`<option value="${n(p)}" ${p===m?"selected":""}>${n(p)}</option>`).join("")}catch(f){t&&(t.textContent=String(f))}},o=async()=>{var f;if(s)try{const m=await H();s.innerHTML=['<option value="">(no adb pin — OK for Editor)</option>',...(m.devices||[]).map(p=>`<option value="${n(p.id)}">${n(p.id)} · ${n(p.platform)}</option>`)].join(""),d&&(d.textContent=m.hint||((f=m.devices)!=null&&f.length?`${m.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire."))}catch(m){d&&(d.textContent=String(m))}};a==null||a.addEventListener("change",()=>{l()}),(c=document.getElementById("launch-refresh-devices"))==null||c.addEventListener("click",()=>{o()}),document.querySelectorAll(".preset").forEach(f=>{f.addEventListener("click",()=>{const m=f.dataset.preset||"",p=Y.find(g=>g.id===m);if(p){if(a){if(!Array.from(a.options).some(b=>b.value===p.config)){const b=document.createElement("option");b.value=p.config,b.textContent=p.config,a.appendChild(b)}a.value=p.config}i&&(i.value=p.tests),r&&(r.checked=p.live_target),(async()=>(await l(),e&&(e.value=p.profile)))()}})});const u=async()=>{try{const{launcher:f}=await G();t&&(t.textContent=JSON.stringify(f,null,2));const m=["starting","running","stopping"].includes(f.state||""),p=document.getElementById("launch-start"),g=document.getElementById("launch-stop");p&&(p.disabled=m),g&&(g.disabled=!m)}catch(f){t&&(t.textContent=String(f))}};(h=document.getElementById("launch-start"))==null||h.addEventListener("click",()=>{(async()=>{var E;const f=(e==null?void 0:e.value)||"",m=(s==null?void 0:s.value)||"",p=document.getElementById("launch-markers").value.trim(),b=((i==null?void 0:i.value)||"").split(/\r?\n/).map(S=>S.trim()).filter(Boolean),w=Array.from(document.querySelectorAll('input[name="reporter"]:checked')).map(S=>S.value),v=(E=document.getElementById("launch-quarantine"))==null?void 0:E.checked;try{const{launcher:S}=await dt({profile:f,tests:b,markers:p||void 0,device_serial:m||void 0,reporters:w.length?w:void 0,include_quarantined:!!v,config:(a==null?void 0:a.value)||void 0,live_target:!!(r!=null&&r.checked)});t&&(t.textContent=JSON.stringify(S,null,2)),location.hash="/live"}catch(S){const L=String(S);t&&(t.textContent=L),/\b409\b/.test(L)&&/already/i.test(L)&&(location.hash="/live")}})()}),($=document.getElementById("launch-stop"))==null||$.addEventListener("click",()=>{(async()=>{try{const{launcher:f}=await lt();t&&(t.textContent=JSON.stringify(f,null,2))}catch(f){t&&(t.textContent=String(f))}})()}),u(),window.setInterval(()=>{location.hash.replace(/^#\/?/,"").startsWith("launch")&&u()},2e3)}async function Dt(){if(await C(),(await k()).read_only)return`<h1>Quarantine</h1>
      <div class="empty">Read-only mode — quarantine management disabled.</div>`;const a=await ct(),e=(a.entries||[]).map(s=>`<tr data-testid="quarantine-row">
        <td class="wrap">${n(s.test_id)}</td>
        <td class="wrap">${n(s.reason)}</td>
        <td>${n(s.owner)}</td>
        <td>${n(s.date)}</td>
        <td class="wrap">${n(s.exit_criteria)}</td>
        <td>${n(s.issue??"—")}</td>
        <td><button type="button" class="q-remove" data-id="${n(s.test_id)}">Remove</button></td>
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
  `}function Ft(){var a,e;const t=document.getElementById("q-msg");(a=document.getElementById("q-add"))==null||a.addEventListener("click",()=>{(async()=>{try{await ut({test_id:document.getElementById("q-id").value.trim(),owner:document.getElementById("q-owner").value.trim(),reason:document.getElementById("q-reason").value.trim(),exit_criteria:document.getElementById("q-exit").value.trim(),issue:document.getElementById("q-issue").value.trim()||void 0}),location.reload()}catch(s){t&&(t.textContent=String(s))}})()}),(e=document.getElementById("q-audit"))==null||e.addEventListener("click",()=>{(async()=>{try{const s=await ft({});t&&(t.textContent=s.summary)}catch(s){t&&(t.textContent=String(s))}})()}),document.querySelectorAll(".q-remove").forEach(s=>{s.addEventListener("click",()=>{(async()=>{const i=s.dataset.id||"";try{await pt(i),location.reload()}catch(r){t&&(t.textContent=String(r))}})()})})}async function Jt(){if(await C(),(await k()).read_only)return`<h1>Profiles</h1>
      <div class="empty">Read-only mode — profile editor disabled.</div>`;const{profiles:a,path:e}=await j(),s=a.map(l=>`<option value="${n(l)}">${n(l)}</option>`).join(""),i=a[0]||"";let r="{}",d="";if(i){const l=await W(i);r=JSON.stringify(l.fields,null,2),d=(l.secret_env_names||[]).map(o=>`<code>${n(o)}</code>`).join(" ")}return`
    <h1>Profile editor</h1>
    <p class="meta">Config: <code>${n(e)}</code>. Secrets are env names only — never values.</p>
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
    <textarea id="prof-fields" data-testid="prof-fields" rows="18" class="code">${n(r)}</textarea>
    <pre class="log" id="prof-msg" data-testid="prof-msg"></pre>
  `}function Ht(){var i,r,d,l;const t=document.getElementById("prof-msg"),a=document.getElementById("prof-fields"),e=document.getElementById("prof-name"),s=()=>a?JSON.parse(a.value):{};(i=document.getElementById("prof-load"))==null||i.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",u=await W(o);a&&(a.value=JSON.stringify(u.fields,null,2)),t&&(t.textContent=`loaded ${o}`)}catch(o){t&&(t.textContent=String(o))}})()}),(r=document.getElementById("prof-validate"))==null||r.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",u=await rt(o,s());t&&(t.textContent=u.ok?`OK
${JSON.stringify(u.settings_summary,null,2)}`:u.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()}),(d=document.getElementById("prof-preview"))==null||d.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",u=await M(o,s(),!1);t&&(t.textContent=u.diff||"(no diff)")}catch(o){t&&(t.textContent=String(o))}})()}),(l=document.getElementById("prof-save"))==null||l.addEventListener("click",()=>{(async()=>{try{const o=(e==null?void 0:e.value)||"",u=await M(o,s(),!0);t&&(t.textContent=u.saved?`saved
${u.diff}`:u.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()})}function A(t,a="var(--accent)"){const e=t.map(u=>Number(u.v??0));if(!e.length)return'<span class="meta">no samples</span>';const s=Math.min(...e),i=Math.max(...e),r=Math.max(1e-9,i-s),d=320,l=64,o=e.map((u,c)=>{const h=c/Math.max(1,e.length-1)*d,$=l-(u-s)/r*(l-4)-2;return`${h.toFixed(1)},${$.toFixed(1)}`}).join(" ");return`<svg class="spark" viewBox="0 0 ${d} ${l}" width="${d}" height="${l}">
    <polyline fill="none" stroke="${a}" stroke-width="1.5" points="${o}"/>
  </svg>`}async function Wt(){var i;const t=await J({}),a=t.runs.map(r=>`<option value="${n(r.id)}">${n(r.id.slice(0,8))}… · ${n(r.profile)}</option>`).join(""),e=((i=t.runs[0])==null?void 0:i.id)||"";let s='<div class="empty">Pick a run to load perf series.</div>';if(e){const r=await Q(e);s=Z(e,r.series,r.summary)}return`
    <h1>Perf graphs</h1>
    <p class="meta">Same data as <code>questline perf report</code>, with overlays and compare.</p>
    <div class="toolbar">
      <label>run
        <select id="perf-run" data-testid="perf-run">${a}</select>
      </label>
      <button type="button" id="perf-load" data-testid="perf-load">Load series</button>
    </div>
    <div id="perf-series" data-testid="perf-series">${s}</div>
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
  `}function Z(t,a,e){const s=Object.keys(a);return s.length?s.map(i=>{var d,l;const r=e[i]||{};return`<div class="panel" data-testid="perf-metric">
        <h2>${n(i)} <span class="meta">avg ${n(((l=(d=r.avg)==null?void 0:d.toFixed)==null?void 0:l.call(d,2))??"—")} · n ${n(r.count??0)}</span></h2>
        ${A(a[i]||[])}
      </div>`}).join(""):`<div class="empty">No perf samples for ${n(t)}.</div>`}function Gt(){var r,d;const t=document.getElementById("perf-series"),a=document.getElementById("perf-compare-out"),e=document.getElementById("perf-run"),s=document.getElementById("perf-a"),i=document.getElementById("perf-b");s&&i&&i.options.length>1&&(i.selectedIndex=1),(r=document.getElementById("perf-load"))==null||r.addEventListener("click",()=>{(async()=>{const l=(e==null?void 0:e.value)||"";if(!(!l||!t))try{const o=await Q(l);t.innerHTML=Z(l,o.series,o.summary)}catch(o){t.textContent=String(o)}})()}),(d=document.getElementById("perf-compare"))==null||d.addEventListener("click",()=>{(async()=>{const l=(s==null?void 0:s.value)||"",o=(i==null?void 0:i.value)||"";if(a)try{const u=await mt(l,o),c=u.deltas.map($=>{var f,m,p,g,b,w;return`<tr>
              <td>${n($.metric)}</td>
              <td>${n(((p=(m=(f=$.a)==null?void 0:f.avg)==null?void 0:m.toFixed)==null?void 0:p.call(m,2))??"—")}</td>
              <td>${n(((w=(b=(g=$.b)==null?void 0:g.avg)==null?void 0:b.toFixed)==null?void 0:w.call(b,2))??"—")}</td>
              <td>${$.delta_avg==null?"—":n($.delta_avg.toFixed(2))}</td>
            </tr>`}).join(""),h=Object.keys(u.series_a).map($=>{const f=u.series_a[$]||[],m=u.series_b[$]||[];return`<div class="panel">
              <h2>${n($)} overlay</h2>
              <div class="toolbar">
                <span class="meta">A</span>${A(f,"var(--accent)")}
                <span class="meta">B</span>${A(m,"var(--ok)")}
              </div>
            </div>`}).join("");a.innerHTML=`
          <div class="table-wrap">
            <table data-testid="perf-delta-table">
              <thead><tr><th>Metric</th><th>A avg</th><th>B avg</th><th>Δ avg</th></tr></thead>
              <tbody>${c||'<tr><td colspan="4">No metrics</td></tr>'}</tbody>
            </table>
          </div>
          ${h}`}catch(u){a.textContent=String(u)}})()})}function I(t){const a=(e,s)=>`<a href="${e}" class="${t===s?"active":""}">${s}</a>`;return`<div class="subnav" data-testid="lens-nav">
    ${a("#/lens","Snapshots")}
    ${a("#/lens/diff","Diff")}
    ${a("#/lens/sessions","Sessions")}
    ${a("#/lens/turns","Agent")}
  </div>`}async function Qt(){var d,l,o;const a=(await K()).snapshots||[],e=a.map(u=>`<option value="${n(u.id)}">${n(u.id)} · ${n(u.game_version)}</option>`).join(""),s=((d=a[1])==null?void 0:d.id)||((l=a[0])==null?void 0:l.id)||"",i=((o=a[0])==null?void 0:o.id)||"",r=a.map(u=>`
    <tr data-testid="lens-snap-row" data-snap-id="${n(u.id)}">
      <td class="wrap"><code>${n(u.id)}</code></td>
      <td>${n(u.game_version)}</td>
      <td>${n(u.feature_id??"—")}</td>
      <td>${n(u.created_at??"")}</td>
    </tr>`).join("");return`
    <h1>GameLens</h1>
    ${I("Snapshots")}
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
  `}async function Kt(){var $,f,m;const t=(await K()).snapshots||[],a=new URLSearchParams(location.hash.split("?")[1]||""),e=a.get("a")||(($=t[1])==null?void 0:$.id)||((f=t[0])==null?void 0:f.id)||"",s=a.get("b")||((m=t[0])==null?void 0:m.id)||"";if(!e||!s)return`
      <h1>Typed diff</h1>
      ${I("Diff")}
      <div class="empty" data-testid="lens-diff-empty">Pick two snapshots on GameLens.</div>`;const i=await gt(e,s),r=i.diff.entries||[],d=i.diff.by_system||{},o=Object.keys(d).sort().map(p=>{const g=(d[p]||[]).map(b=>`<li data-testid="lens-diff-entry">${n(ne(b))}</li>`).join("");return`<div class="panel"><h3>[${n(p)}]</h3><ul>${g}</ul></div>`}).join(""),u=i.implications;let c=[];try{(await k()).read_only||(c=(await j()).profiles||[])}catch{c=[]}const h=c.filter(p=>p.startsWith("ai_")).concat(c.filter(p=>!p.startsWith("ai_"))).map(p=>{const g=p==="ai_groq"?"selected":"";return`<option value="${n(p)}" ${g}>${n(p)}</option>`}).join("");return`
    <h1>Typed diff</h1>
    ${I("Diff")}
    <p class="meta" data-testid="lens-diff-meta">
      ${n(i.diff.snapshot_id_a||e)} → ${n(i.diff.snapshot_id_b||s)}
      · ${r.length} entries · framing vs measured stay separate
    </p>
    ${o||'<div class="empty">(no differences)</div>'}
    ${ee(u)}
    <h2>Ask balance agent</h2>
    <p class="meta">Retune <em>priorities</em> only — model reasoning, never SO writes or green/red.</p>
    <div class="panel" data-testid="lens-agent-form">
      <label class="block">profile
        <select id="agent-profile" data-testid="agent-profile">${h||'<option value="ai_groq">ai_groq</option>'}</select>
      </label>
      <label class="block">question
        <textarea id="agent-q" data-testid="agent-q" rows="3">What should a human look at for a retune?</textarea>
      </label>
      <button type="button" id="agent-run" data-testid="agent-run">Ask</button>
      <div id="agent-msg" class="meta" data-testid="agent-msg"></div>
    </div>
    <div id="agent-result"></div>
    <script type="application/json" id="lens-pair">${JSON.stringify({a:e,b:s})}<\/script>
  `}async function Vt(){const a=((await $t()).sessions||[]).map(e=>`
    <tr data-testid="tel-session-row" data-session-id="${n(e.id)}">
      <td class="wrap"><a href="#/lens/sessions/${encodeURIComponent(e.id)}">${n(e.id)}</a></td>
      <td>${n(e.outcome??"—")}</td>
      <td class="wrap">${n(e.config_snapshot_id??"—")}</td>
      <td>${n(e.policy_id??"—")}</td>
      <td>${n(e.seed??"—")}</td>
      <td class="wrap">${n((e.notes||[]).join("; "))}</td>
    </tr>`).join("");return`
    <h1>Telemetry sessions</h1>
    ${I("Sessions")}
    <p class="meta"><code>outcome=lose</code> is measured play, not a bot/framework fail. <code>snap-unset</code> is a join gap.</p>
    <div class="table-wrap">
      <table data-testid="tel-sessions">
        <thead>
          <tr><th>Id</th><th>Outcome</th><th>Snapshot</th><th>Policy</th><th>Seed</th><th>Notes</th></tr>
        </thead>
        <tbody>${a||'<tr><td colspan="6">No telemetry sessions.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function Xt(t){const e=(await yt(t)).session;return`
    <p class="meta"><a href="#/lens/sessions">← Sessions</a> · ${n(e.id)}</p>
    <h1>Session</h1>
    ${I("Sessions")}
    ${ae(e)}
  `}async function zt(){const a=((await bt()).turns||[]).map(e=>`
    <tr data-testid="agent-turn-row" data-turn-id="${n(e.id)}">
      <td class="wrap"><a href="#/lens/turns/${encodeURIComponent(e.id)}">${n(e.id)}</a></td>
      <td>${n(e.status??"")}</td>
      <td>${n(e.framing??"")}</td>
      <td class="wrap">${n(e.question??"")}</td>
      <td>${n(e.created_at??"")}</td>
    </tr>`).join("");return`
    <h1>Balance agent</h1>
    ${I("Agent")}
    <p class="meta">Persisted turns. Numbers in citations are measured; priorities are model reasoning.</p>
    <div class="table-wrap">
      <table data-testid="agent-turns">
        <thead><tr><th>Id</th><th>Status</th><th>Framing</th><th>Question</th><th>Created</th></tr></thead>
        <tbody>${a||'<tr><td colspan="5">No agent turns yet. Ask from a typed diff.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function Yt(t){const a=await wt(t);return`
    <p class="meta"><a href="#/lens/turns">← Agent</a> · ${n(t)}</p>
    <h1>Agent turn</h1>
    ${I("Agent")}
    ${tt(a.turn)}
  `}function Zt(){var e;const t=document.getElementById("lens-open-diff");t==null||t.addEventListener("click",()=>{var r,d;const s=(r=document.getElementById("lens-a"))==null?void 0:r.value,i=(d=document.getElementById("lens-b"))==null?void 0:d.value;!s||!i||(location.hash=`/lens/diff?a=${encodeURIComponent(s)}&b=${encodeURIComponent(i)}`)});const a=(e=document.getElementById("lens-defaults"))==null?void 0:e.textContent;if(a)try{const s=JSON.parse(a),i=document.getElementById("lens-a"),r=document.getElementById("lens-b");i&&s.a&&(i.value=s.a),r&&s.b&&(r.value=s.b)}catch{}}function te(){const t=document.getElementById("agent-run");t==null||t.addEventListener("click",()=>{(async()=>{var o,u,c;const a=document.getElementById("agent-msg"),e=document.getElementById("agent-result"),s=(o=document.getElementById("lens-pair"))==null?void 0:o.textContent;let i="",r="";try{const h=JSON.parse(s||"{}");i=h.a||"",r=h.b||""}catch{}const d=(u=document.getElementById("agent-q"))==null?void 0:u.value,l=(c=document.getElementById("agent-profile"))==null?void 0:c.value;a&&(a.textContent="running…");try{const h=await _t({snapshot_a:i,snapshot_b:r,question:d||void 0,profile:l||void 0});a&&(a.textContent=`status=${h.turn.status}`),e&&(e.innerHTML=tt(h.turn))}catch(h){a&&(a.textContent=String(h))}})()})}function ee(t){if(!t)return'<div class="empty" data-testid="lens-impl-empty">No persisted implications for this pair.</div>';const a=(t.gaps||[]).map(e=>`<li>${n(e)}</li>`).join("");return`
    <h2>Implications</h2>
    <div class="panel" data-testid="lens-implications">
      <div class="meta">status=${n(t.status??"")} · framing=${n(t.framing??"")}
        ${t.pending?` · pending=${n(t.pending)}`:""}</div>
      <h3>Gaps</h3>
      <ul class="gap-list" data-testid="lens-gaps">${a||"<li>(none)</li>"}</ul>
      <h3>Model reasoning</h3>
      <div data-testid="lens-impl-summary">${n(t.summary??"")}</div>
      <h3>Measured</h3>
      <pre class="pre-json" data-testid="lens-measured">${n(JSON.stringify(t.measured??{},null,2))}</pre>
    </div>`}function ae(t){const a=(t.notes||[]).map(e=>`<li>${n(e)}</li>`).join("");return`
    <div class="panel" data-testid="tel-session-detail">
      <div class="meta">outcome=${n(t.outcome??"—")} · snapshot=${n(t.config_snapshot_id??"—")}
        · policy=${n(t.policy_id??"—")} · seed=${n(t.seed??"—")}</div>
      <h3>Notes</h3>
      <ul data-testid="tel-session-notes">${a||"<li>(none)</li>"}</ul>
      <h3>Summary (measured)</h3>
      <pre class="pre-json">${n(JSON.stringify(t.summary??{},null,2))}</pre>
    </div>`}function tt(t){const a=(t.priorities||[]).map(i=>`<li>${n(i)}</li>`).join(""),e=(t.gaps||[]).map(i=>`<li>${n(i)}</li>`).join(""),s=t.ai_cost_total!=null?String(t.ai_cost_total):"—";return`
    <div class="panel" data-testid="agent-turn">
      <div class="meta">status=${n(t.status??"")} · framing=${n(t.framing??"")}
        · cost_usd=${n(s)}${t.pending?` · pending=${n(t.pending)}`:""}</div>
      <h3>Priorities (model reasoning)</h3>
      <ul data-testid="agent-priorities">${a||"<li>(none)</li>"}</ul>
      <h3>Gaps</h3>
      <ul class="gap-list" data-testid="agent-gaps">${e||"<li>(none)</li>"}</ul>
      <h3>Measured citations</h3>
      <pre class="pre-json" data-testid="agent-measured">${n(JSON.stringify(t.citations??{},null,2))}</pre>
    </div>`}function ne(t){if(t.kind==="added_entity")return`+ entity ${t.entity_id}`;if(t.kind==="removed_entity")return`- entity ${t.entity_id}`;const a=t.path||"?";return t.delta!=null?`~ ${t.entity_id}.${a}: ${t.before} -> ${t.after} (delta ${t.delta})`:`~ ${t.entity_id}.${a}: ${JSON.stringify(t.before)} -> ${JSON.stringify(t.after)}`}function N(t){return t==null||Number.isNaN(t)?"—":`${(t*100).toFixed(1)}%`}function P(t){return t==null||Number.isNaN(t)?"—":t.toFixed(3)}async function se(){var l,o,u;const a=(await xt()).runs||[],e=a.map(c=>`<option value="${n(c.id)}">${n(c.id)} · ${n(c.provider||"—")}</option>`).join(""),s=((l=a[1])==null?void 0:l.id)||((o=a[0])==null?void 0:o.id)||"",i=((u=a[0])==null?void 0:u.id)||"",r=a.map(c=>`
    <tr data-testid="eval-row" data-eval-id="${n(c.id)}">
      <td class="wrap"><code>${n(c.id)}</code></td>
      <td>${n(c.provider??"—")}</td>
      <td>${n(c.prompt_version??"")}</td>
      <td>${n(N(c.diagnosis_accuracy))}</td>
      <td>${n(N(c.fix_correctness))}</td>
      <td>${n(N(c.false_green_rate))}</td>
      <td>${n(P(c.iterations_avg))}</td>
      <td>${c.case_count??0}</td>
      <td>${n(c.created_at??"")}</td>
    </tr>`).join("");let d=!0;try{d=!(await k()).read_only}catch{d=!0}return`
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
      ${d?'<button type="button" id="eval-run" data-testid="eval-run">Run fake eval</button>':""}
      <span id="eval-msg" class="meta" data-testid="eval-msg"></span>
    </div>
    <div id="eval-compare-out" data-testid="eval-compare-out"></div>
    ${d?`<h2>Generate from spec</h2>
    <p class="meta">Writes a pytest file; the execution gate must collect and run it.</p>
    <textarea id="eval-spec" data-testid="eval-spec" rows="6" placeholder="When the player taps Play, HUD coins show 100.&#10;Use existing pages.&#10;expect: green"></textarea>
    <div class="toolbar">
      <button type="button" id="eval-generate" data-testid="eval-generate">Generate test</button>
      <span id="eval-gen-msg" class="meta" data-testid="eval-gen-msg"></span>
    </div>`:""}
    <script type="application/json" id="eval-defaults">${JSON.stringify({a:s,b:i})}<\/script>
  `}function ie(){var s,i,r,d;const t=JSON.parse(((s=document.getElementById("eval-defaults"))==null?void 0:s.textContent)||"{}"),a=document.getElementById("eval-a"),e=document.getElementById("eval-b");a&&t.a&&(a.value=t.a),e&&t.b&&(e.value=t.b),(i=document.getElementById("eval-compare"))==null||i.addEventListener("click",()=>{(async()=>{const l=document.getElementById("eval-a").value,o=document.getElementById("eval-b").value,u=document.getElementById("eval-compare-out");if(!u||!l||!o)return;const h=(await It(l,o)).compare,f=["diagnosis_accuracy","fix_correctness","false_green_rate","iterations_avg","cost_usd"].map(m=>{var w,v,E,S,L;const p=(v=(w=h.a)==null?void 0:w.metrics)==null?void 0:v[m],g=(S=(E=h.b)==null?void 0:E.metrics)==null?void 0:S[m],b=(L=h.delta_b_minus_a)==null?void 0:L[m];return`<tr><td>${n(m)}</td><td>${n(P(p??null))}</td>
            <td>${n(P(g??null))}</td><td>${n(P(b??null))}</td></tr>`}).join("");u.innerHTML=`
        <div class="table-wrap">
          <table data-testid="eval-delta-table">
            <thead><tr><th>Metric</th><th>A</th><th>B</th><th>B−A</th></tr></thead>
            <tbody>${f}</tbody>
          </table>
        </div>`})()}),(r=document.getElementById("eval-run"))==null||r.addEventListener("click",()=>{const l=document.getElementById("eval-msg");l&&(l.textContent="running…"),(async()=>{try{const o=await Lt({provider:"fake",prompt_version:"v1"});l&&(l.textContent=`ok ${o.run.id} false-green=${N(o.run.false_green_rate)}`),location.hash="/eval",window.dispatchEvent(new HashChangeEvent("hashchange"))}catch(o){l&&(l.textContent=String(o))}})()}),(d=document.getElementById("eval-generate"))==null||d.addEventListener("click",()=>{var u;const l=((u=document.getElementById("eval-spec"))==null?void 0:u.value)||"",o=document.getElementById("eval-gen-msg");o&&(o.textContent="generating…"),(async()=>{try{const c=await Bt({spec:l}),h=c.task.gate||{};o&&(o.textContent=`verdict=${c.task.verdict} executed=${String(h.executed)} accepted=${String(h.accepted)}`)}catch(c){o&&(o.textContent=String(c))}})()})}const D=document.querySelector("#app");let B=!1,O=!1,R=!1;function F(t,a){const e=(l,o)=>`<a href="${l}" class="${t===o?"active":""}">${o}</a>`,s=B?"":`${e("#/launch","Launch")}
        ${e("#/quarantine","Quarantine")}
        ${e("#/profiles","Profiles")}`,i=[B?'<span class="badge warn" title="--read-only">RO</span>':"",O?'<span class="badge warn" title="Playwright smoke fixture — not real runs">SMOKE</span>':"",R?'<span class="badge warn" title="Restart questline hud">STALE API</span>':""].filter(Boolean).join(" "),r=O?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)">
        <strong>SMOKE FIXTURE SERVER</strong> — fake launcher + seeded runs.
        For real Wire/mock runs stop this process and use
        <code>uv run questline hud --open</code> (port 8741).
      </div>`:"",d=R?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)" data-testid="stale-api">
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
        ${e("#/eval","Eval")}
        ${e("#/trends","Trends")}
        ${e("#/live","Live")}
      </nav>
      ${i}
    </header>
    <main class="main">${r}${d}${a}</main>
  `}function re(){const e=((location.hash.replace(/^#\/?/,"")||"").split("?")[0]||"").split("/").filter(Boolean);if(e[0]==="runs"&&e[1]&&e[2]==="tests"&&e.length>=4){const s=e.slice(3).join("/");let i=s;try{i=decodeURIComponent(s)}catch{}return{name:"test",params:{runId:e[1],testId:i}}}return e[0]==="runs"&&e[1]?{name:"run",params:{runId:e[1]}}:e[0]==="trends"?{name:"trends",params:{}}:e[0]==="live"?{name:"live",params:{}}:e[0]==="launch"?{name:"launch",params:{}}:e[0]==="quarantine"?{name:"quarantine",params:{}}:e[0]==="profiles"?{name:"profiles",params:{}}:e[0]==="perf"?{name:"perf",params:{}}:e[0]==="eval"?{name:"eval",params:{}}:e[0]==="lens"?e[1]==="diff"?{name:"lens-diff",params:{}}:e[1]==="sessions"&&e[2]?{name:"lens-session",params:{id:e[2]}}:e[1]==="sessions"?{name:"lens-sessions",params:{}}:e[1]==="turns"&&e[2]?{name:"lens-turn",params:{id:e[2]}}:e[1]==="turns"?{name:"lens-turns",params:{}}:{name:"lens",params:{}}:{name:"runs",params:{}}}function oe(t){return t.length?`
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
      <td>${n(x(e.duration_s))}</td>
      <td>${n(e.started_at??"")}</td>
    </tr>`).join("")}</tbody>
      </table>
    </div>`:`<div class="empty" data-testid="empty-store">
      No runs in the store yet.<br/>
      Use <a href="#/launch">Launch</a> or run a suite with the questline plugin, then refresh.
    </div>`}async function de(){const t=new URLSearchParams(location.hash.split("?")[1]||""),a=t.get("profile")||"",e=t.get("status")||"",s=await J({profile:a||void 0,status:e||void 0});return`
    <h1>Runs</h1>
    <div class="toolbar">
      <label>profile <input id="f-profile" value="${n(a)}" placeholder="any"/></label>
      <label>status
        <select id="f-status">
          <option value="">any</option>
          ${["passed","failed","running","error"].map(i=>`<option value="${i}" ${e===i?"selected":""}>${i}</option>`).join("")}
        </select>
      </label>
      <button type="button" id="f-apply">Filter</button>
      ${B?"":'<a class="btn" href="#/launch">Launch run</a>'}
    </div>
    ${oe(s.runs)}
  `}async function et(){const t=re();try{let a="",e="Runs";t.name==="run"?(a=await Ct(t.params.runId),e="Runs"):t.name==="test"?(a=await Pt(t.params.runId,t.params.testId),e="Runs"):t.name==="trends"?(a=await jt(),e="Trends"):t.name==="live"?(a=await Tt(),e="Live"):t.name==="launch"?(a=await Mt(),e="Launch"):t.name==="quarantine"?(a=await Dt(),e="Quarantine"):t.name==="profiles"?(a=await Jt(),e="Profiles"):t.name==="perf"?(a=await Wt(),e="Perf"):t.name==="eval"?(a=await se(),e="Eval"):t.name==="lens"?(a=await Qt(),e="GameLens"):t.name==="lens-diff"?(a=await Kt(),e="GameLens"):t.name==="lens-sessions"?(a=await Vt(),e="GameLens"):t.name==="lens-session"?(a=await Xt(t.params.id),e="GameLens"):t.name==="lens-turns"?(a=await zt(),e="GameLens"):t.name==="lens-turn"?(a=await Yt(t.params.id),e="GameLens"):(a=await de(),e="Runs"),D.innerHTML=F(e,a),le(t.name)}catch(a){D.innerHTML=F("Runs",`<div class="empty">Failed to load HUD: ${n(String(a))}</div>`)}}function le(t){var a;if(t==="runs"&&((a=document.getElementById("f-apply"))==null||a.addEventListener("click",()=>{const e=document.getElementById("f-profile").value.trim(),s=document.getElementById("f-status").value,i=new URLSearchParams;e&&i.set("profile",e),s&&i.set("status",s);const r=i.toString();location.hash=r?`/?${r}`:"/"})),t==="live"){const e=document.getElementById("live-root");e&&At(e)}t==="launch"&&Ut(),t==="quarantine"&&Ft(),t==="profiles"&&Ht(),t==="perf"&&Gt(),t==="eval"&&ie(),t==="lens"&&Zt(),t==="lens-diff"&&te(),t==="run"&&qt(),t==="test"&&Ot()}async function ce(){var t,a,e,s;try{const i=await k();B=!!i.read_only,O=!!i.smoke,R=!((t=i.api)!=null&&t.test_by_query)||!((a=i.api)!=null&&a.lens)||!((e=i.api)!=null&&e.agents)||!((s=i.api)!=null&&s.eval),B||await C()}catch{B=!1,O=!1,R=!0}await et()}window.addEventListener("hashchange",()=>{et()});ce();
