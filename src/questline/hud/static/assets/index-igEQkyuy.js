(function(){const n=document.createElement("link").relList;if(n&&n.supports&&n.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))s(i);new MutationObserver(i=>{for(const r of i)if(r.type==="childList")for(const l of r.addedNodes)l.tagName==="LINK"&&l.rel==="modulepreload"&&s(l)}).observe(document,{childList:!0,subtree:!0});function e(i){const r={};return i.integrity&&(r.integrity=i.integrity),i.referrerPolicy&&(r.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?r.credentials="include":i.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function s(i){if(i.ep)return;i.ep=!0;const r=e(i);fetch(i.href,r)}})();let C=null;async function g(t){const n=await fetch(t),e=await n.text();if(/^\s*</.test(e)||(n.headers.get("content-type")||"").includes("text/html"))throw new Error(`${n.status} ${t}: got HTML instead of JSON. Restart questline hud (old process missing new /api routes).`);if(!n.ok)throw new Error(`${n.status} ${t}: ${e}`);try{return JSON.parse(e)}catch(i){throw new Error(`${t}: invalid JSON (${String(i)})`)}}async function L(){return C||(C=(await g("/api/csrf")).csrf_token,C)}async function S(t,n,e){const s=await L(),i=await fetch(n,{method:t,headers:{"Content-Type":"application/json","X-CSRF-Token":s},body:e===void 0?void 0:JSON.stringify(e)});if(!i.ok){const r=await i.text();throw new Error(`${i.status} ${n}: ${r}`)}if(i.status!==204)return await i.json()}function q(){return g("/api/meta")}function M(t){const n=new URLSearchParams;t.profile&&n.set("profile",t.profile),t.status&&n.set("status",t.status);const e=n.toString();return g(`/api/runs${e?`?${e}`:""}`)}function X(t){return g(`/api/runs/${encodeURIComponent(t)}`)}function z(t,n){const e=new URLSearchParams({id:n});return g(`/api/runs/${encodeURIComponent(t)}/test?${e.toString()}`)}function Y(t=50){return g(`/api/trends?limit=${t}`)}function N(t){const n=t?`?config=${encodeURIComponent(t)}`:"";return g(`/api/profiles${n}`)}function Z(){return g("/api/configs")}function D(){return g("/api/devices")}function F(t){return g(`/api/profiles/${encodeURIComponent(t)}`)}function tt(t,n){return S("POST",`/api/profiles/${encodeURIComponent(t)}/validate`,{fields:n,apply:!1})}function j(t,n,e){return S("POST",`/api/profiles/${encodeURIComponent(t)}`,{fields:n,apply:e})}function et(){return g("/api/reporters")}function J(){return g("/api/launcher")}function at(t){return S("POST","/api/launcher/start",t)}function nt(){return S("POST","/api/launcher/stop")}function st(){return g("/api/quarantine")}function it(t){return S("POST","/api/quarantine",t)}function rt(t){return S("DELETE",`/api/quarantine?test_id=${encodeURIComponent(t)}`)}function ot(t){return S("POST","/api/quarantine/audit",t||{})}function H(t){return g(`/api/perf/${encodeURIComponent(t)}`)}function dt(t,n){return g(`/api/perf/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(n)}`)}function lt(t=50){return g(`/api/perf/correlation?limit=${t}`)}function ct(t){return`/api/artifacts/file?path=${encodeURIComponent(t)}`}function W(){return g("/api/lens/snapshots")}function ut(t,n){const e=new URLSearchParams({a:t,b:n});return g(`/api/lens/diff?${e.toString()}`)}function pt(){return g("/api/telemetry/sessions")}function ft(t){return g(`/api/telemetry/sessions/${encodeURIComponent(t)}`)}function ht(){return g("/api/lens/agent/turns")}function mt(t){return g(`/api/lens/agent/turns/${encodeURIComponent(t)}`)}function vt(t){return S("POST","/api/lens/agent/run",t)}function k(t){if(t==null||Number.isNaN(t))return"—";if(t<60)return`${t.toFixed(1)}s`;const n=Math.floor(t/60),e=t-n*60;return`${n}m ${e.toFixed(0)}s`}function a(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function $t(t){const n=await X(t),e=n.run,s=n.banner,i=n.tests.map(o=>`
    <tr data-testid="test-row" data-test-id="${a(o.id)}">
      <td class="wrap"><a href="#/runs/${encodeURIComponent(t)}/tests/${encodeURIComponent(o.id)}">${a(o.nodeid)}</a></td>
      <td><span class="badge ${a(o.status)}">${a(o.status)}</span></td>
      <td class="verdict-${a(o.verdict??"")}">${a(o.verdict??"—")}</td>
      <td>${a(k(o.duration_s))}</td>
      <td class="wrap">${a(o.death_step_name??"")}</td>
    </tr>`).join(""),l=(n.ai_calls||[]).map(o=>`
    <tr data-testid="ai-call-row">
      <td>${a(o.provider??"—")}</td>
      <td class="wrap">${a(o.model??"—")}</td>
      <td>${a(o.tokens_in??0)}</td>
      <td>${a(o.tokens_out??0)}</td>
      <td>${a(T(o.cost))}</td>
      <td>${a(o.outcome??"—")}</td>
      <td class="wrap">${a(o.purpose??"")}</td>
    </tr>`).join("")||'<tr><td colspan="7">No AI calls for this run.</td></tr>';return`
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
    <h2>AI calls</h2>
    <div class="meta">total_usd=${a(T(n.ai_cost_total))}</div>
    <div class="table-wrap">
      <table data-testid="ai-calls-table">
        <thead>
          <tr>
            <th>Provider</th><th>Model</th><th>In</th><th>Out</th>
            <th>Cost</th><th>Outcome</th><th>Purpose</th>
          </tr>
        </thead>
        <tbody>${l}</tbody>
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
  `}function T(t){return t==null||Number.isNaN(t)?"0.000000":t.toFixed(6)}async function gt(t,n){const e=await z(t,n),s=e.test,i=e.steps.map(f=>{const m=String(f.status??"");return`<li data-testid="step-row">
        <span class="ts">${a(f.started_at??"")}</span>
        <span class="badge ${a(m)}">${a(m)}</span>
        <span>${a(f.name??"")}${f.error_message?` — ${a(f.error_message)}`:""}</span>
      </li>`}).join(""),r=(e.history||[]).map(f=>{const m=String(f.status??""),p=Number(f.duration_s??0)||1,h=Math.max(4,Math.min(28,p*4));return`<i class="${a(m)}" style="height:${h}px" title="${a(m)}"></i>`}).join(""),l=e.death_point||{},o=l.last_started_step||{},d=l.driver_health||{},c=s.verdict==="infra"?"infra":"",v=(e.artifacts||[]).map(f=>{const m=String(f.path??""),p=String(f.kind??""),h=String(f.name??m),u=ct(m);return p==="screenshot"||/\.(png|jpe?g|webp|gif)$/i.test(h)?`<div><a href="${a(u)}" target="_blank" rel="noreferrer">
          <img src="${a(u)}" alt="${a(h)}"/><div>${a(h)}</div></a></div>`:`<div><a href="${a(u)}" target="_blank" rel="noreferrer">${a(h)}</a>
        <div class="meta">${a(p)} · ${a(f.size_bytes??"")} B</div></div>`}).join("");return`
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

    <div class="panel death ${c}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${a(o.name??"—")}</b>
        @ ${a(o.started_at??"")}</div>
      <div>error: ${a(s.error_type??"")} — ${a(s.error_message??"")}</div>
      <div>driver health: ${a(JSON.stringify(d||{}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${r||"<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${i||"<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${v||"<span class='meta'>none</span>"}</div>
  `}async function yt(){const[t,n]=await Promise.all([Y(50),lt(50)]),e=t.series||[],s=Math.max(1,...e.map(d=>Number(d.duration_s??0)||0)),i=e.map(d=>{const c=d.pass_rate==null?0:Number(d.pass_rate),v=Math.max(4,Math.round(c*100)),f=Number(d.duration_s??0);return`<div class="bar ${Number(d.failed??0)>0?"fail":""}" style="height:${v}%">
        <span>${a(d.run_id)} · ${(c*100).toFixed(0)}% · ${a(k(f))}</span>
      </div>`}).join(""),r=e.map(d=>{const c=Number(d.duration_s??0);return`<div class="bar" style="height:${Math.max(4,Math.round(c/s*100))}%">
        <span>${a(d.run_id)} · ${a(k(c))}</span>
      </div>`}).join(""),l=(t.flaky_tests||[]).map(d=>`<tr>
        <td class="wrap">${a(d.nodeid)}</td>
        <td>${a(d.runs)}</td>
        <td>${a(d.passed)}/${a(d.failed)}</td>
        <td>${(Number(d.pass_rate)*100).toFixed(0)}%</td>
        <td>${(Number(d.flake_score)*100).toFixed(0)}%</td>
      </tr>`).join(""),o=(n.tests||[]).map(d=>{const c=(d.points||[]).map(v=>{const f=v.duration_s==null?0:Number(v.duration_s);return`<span class="dot ${v.passed?"ok":"bad"}" title="${a(v.run_id)} · ${a(k(f))}"></span>`}).join("");return`<tr>
        <td class="wrap">${a(d.nodeid)}</td>
        <td>${d.passed}/${d.failed}</td>
        <td class="corr-dots">${c}</td>
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
        <tbody>${l||'<tr><td colspan="5">No flaky tests detected.</td></tr>'}</tbody>
      </table>
    </div>
    <h2>Duration vs pass (correlation)</h2>
    <p class="meta">Green = pass, red = fail per run (same flaky nodeids).</p>
    <div class="table-wrap">
      <table data-testid="corr-table">
        <thead><tr><th>Test</th><th>P/F</th><th>Runs</th></tr></thead>
        <tbody>${o||'<tr><td colspan="3">No mixed pass/fail series yet.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function bt(){return`
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `}function wt(t){const n=document.getElementById("live-status"),e=document.getElementById("live-clear");e==null||e.addEventListener("click",()=>{t.innerHTML=""});const i=`${location.protocol==="https:"?"wss":"ws"}://${location.host}/live`;let r;try{r=new WebSocket(i)}catch(l){n&&(n.textContent="failed"),t.innerHTML=`<div>WebSocket error: ${a(String(l))}</div>`;return}r.onopen=()=>{n&&(n.textContent="live",n.className="badge passed")},r.onclose=()=>{n&&(n.textContent="closed",n.className="badge failed")},r.onerror=()=>{n&&(n.textContent="error",n.className="badge failed")},r.onmessage=l=>{try{const o=JSON.parse(String(l.data)),d=String(o.type??"?"),c=String(o.timestamp??""),v=o.nodeid||o.name||o.test_id||o.status||o.profile||"",f=document.createElement("div");f.innerHTML=`<span class="t">${a(c)}</span><b>${a(d)}</b> ${a(v)}`,t.prepend(f)}catch{const o=document.createElement("div");o.textContent=String(l.data),t.prepend(o)}}}const G=[{id:"mock",label:"Mock demo",config:"questline.toml",profile:"mock",tests:"examples/demo-tests",live_target:!1,note:"No Unity. CI-style mock driver."},{id:"wire-editor",label:"Wire Editor",config:"examples/wire-smoke/questline.toml",profile:"editor",tests:"examples/wire-smoke",live_target:!0,note:"Unity Play + Wire on :13000. Device picker stays empty (OK)."},{id:"wire-android",label:"Wire Android",config:"examples/wire-smoke/questline.toml",profile:"android_local",tests:"examples/wire-smoke",live_target:!0,note:"Dev APK + adb. Pick a serial if more than one device."}];async function St(){var b,y,w;await L();let t,n,e,s;try{[t,n,e,s]=await Promise.all([q(),Z().catch(()=>({project_root:"",active:"",configs:[{path:"questline.toml",absolute:"questline.toml"}]})),et().catch(()=>({reporters:["console"]})),J().catch(()=>({launcher:{state:"idle"}}))])}catch($){return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-error">
        Failed to load launcher APIs: ${a(String($))}<br/>
        Stop the old <code>questline hud</code> process and start it again from
        <code>D:\\dev\\questline</code>.
      </div>`}if(t.read_only)return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;const i=((b=n.configs.find($=>$.path.replace(/\\/g,"/")==="questline.toml"))==null?void 0:b.path)||((y=n.configs[0])==null?void 0:y.path)||"questline.toml",r=await N(i),l=await D(),o=(n.configs||[]).map($=>{const E=$.path===i?"selected":"";return`<option value="${a($.path)}" ${E}>${a($.path)}</option>`}).join(""),d=(r.profiles||[]).map($=>{const E=r.profiles.includes("editor")?"editor":r.profiles.includes("mock")?"mock":r.profiles[0]||"";return`<option value="${a($)}" ${$===E?"selected":""}>${a($)}</option>`}).join(""),c=['<option value="">(no adb pin — OK for Editor)</option>',...(l.devices||[]).map($=>`<option value="${a($.id)}">${a($.id)} · ${a($.platform)}</option>`)].join(""),v=(e.reporters||[]).map($=>`<label class="check"><input type="checkbox" name="reporter" value="${a($)}" ${$==="console"?"checked":""}/> ${a($)}</label>`).join(""),f=G.map($=>`<button type="button" class="preset" data-preset="${a($.id)}" title="${a($.note)}">${a($.label)}</button>`).join(""),m=s.launcher,p=["starting","running","stopping"].includes(m.state||""),h=l.hint||((w=l.devices)!=null&&w.length?`${l.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire.");return`
    <h1>Run launcher</h1>
    ${p?`<div class="empty" data-testid="launch-busy">
        A managed run is <strong>${a(m.state||"")}</strong>
        (job <code>${a(m.job_id||"")}</code>, profile
        <code>${a(m.profile||"")}</code>).
        <a href="#/live">Open Live</a> to watch it, or <strong>Stop</strong> below
        before launching another.
      </div>`:""}
    <p class="meta">Profiles come from <code>questline.toml</code> (not from Unity being open).
      Unity Play + Wire = use preset <strong>Wire Editor</strong> or profile <code>editor</code>.
      Device list is <em>adb only</em> — Editor does not appear there.</p>
    <div class="toolbar" data-testid="launch-presets">
      <span class="meta">Presets:</span> ${f}
    </div>
    <div class="panel" data-testid="launch-form">
      <div class="toolbar">
        <label>config
          <select id="launch-config" data-testid="launch-config">${o}</select>
        </label>
        <label>profile
          <select id="launch-profile" data-testid="launch-profile">${d}</select>
        </label>
        <label>device
          <select id="launch-device" data-testid="launch-device">${c}</select>
        </label>
        <button type="button" id="launch-refresh-devices" data-testid="launch-refresh-devices">Refresh devices</button>
      </div>
      <p class="meta" id="launch-device-hint" data-testid="launch-device-hint">${a(h)}</p>
      ${l.error?`<p class="meta">adb error: ${a(l.error)}</p>`:""}
      <label class="block">markers <input id="launch-markers" placeholder="optional -m expression" data-testid="launch-markers"/></label>
      <label class="block">tests (one path/nodeid per line)
        <textarea id="launch-tests" rows="4" data-testid="launch-tests" placeholder="examples/wire-smoke">examples/demo-tests</textarea>
      </label>
      <div class="toolbar wrap">${v||"<span class='meta'>no reporters</span>"}</div>
      <label class="check"><input type="checkbox" id="launch-quarantine"/> include quarantined</label>
      <label class="check"><input type="checkbox" id="launch-live" data-testid="launch-live"/> QUESTLINE_LIVE_TARGET=1 (required for wire-smoke)</label>
      <div class="toolbar">
        <button type="button" id="launch-start" data-testid="launch-start" ${p?"disabled":""}>Launch</button>
        <button type="button" id="launch-stop" data-testid="launch-stop" ${p?"":"disabled"}>Stop</button>
        ${p?'<a class="button" href="#/live" data-testid="launch-open-live">Open Live</a>':""}
      </div>
      <p class="meta">Active project: <code>${a(n.project_root)}</code></p>
    </div>
    <h2>Status</h2>
    <pre class="log" id="launch-status" data-testid="launch-status">${a(JSON.stringify(m,null,2))}</pre>
  `}function _t(){var v,f,m;const t=document.getElementById("launch-status"),n=document.getElementById("launch-config"),e=document.getElementById("launch-profile"),s=document.getElementById("launch-device"),i=document.getElementById("launch-tests"),r=document.getElementById("launch-live"),l=document.getElementById("launch-device-hint"),o=async()=>{if(!(!n||!e))try{const p=await N(n.value),h=p.profiles.includes("editor")?"editor":p.profiles[0]||"";e.innerHTML=p.profiles.map(u=>`<option value="${a(u)}" ${u===h?"selected":""}>${a(u)}</option>`).join("")}catch(p){t&&(t.textContent=String(p))}},d=async()=>{var p;if(s)try{const h=await D();s.innerHTML=['<option value="">(no adb pin — OK for Editor)</option>',...(h.devices||[]).map(u=>`<option value="${a(u.id)}">${a(u.id)} · ${a(u.platform)}</option>`)].join(""),l&&(l.textContent=h.hint||((p=h.devices)!=null&&p.length?`${h.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire."))}catch(h){l&&(l.textContent=String(h))}};n==null||n.addEventListener("change",()=>{o()}),(v=document.getElementById("launch-refresh-devices"))==null||v.addEventListener("click",()=>{d()}),document.querySelectorAll(".preset").forEach(p=>{p.addEventListener("click",()=>{const h=p.dataset.preset||"",u=G.find(b=>b.id===h);if(u){if(n){if(!Array.from(n.options).some(y=>y.value===u.config)){const y=document.createElement("option");y.value=u.config,y.textContent=u.config,n.appendChild(y)}n.value=u.config}i&&(i.value=u.tests),r&&(r.checked=u.live_target),(async()=>(await o(),e&&(e.value=u.profile)))()}})});const c=async()=>{try{const{launcher:p}=await J();t&&(t.textContent=JSON.stringify(p,null,2));const h=["starting","running","stopping"].includes(p.state||""),u=document.getElementById("launch-start"),b=document.getElementById("launch-stop");u&&(u.disabled=h),b&&(b.disabled=!h)}catch(p){t&&(t.textContent=String(p))}};(f=document.getElementById("launch-start"))==null||f.addEventListener("click",()=>{(async()=>{var E;const p=(e==null?void 0:e.value)||"",h=(s==null?void 0:s.value)||"",u=document.getElementById("launch-markers").value.trim(),y=((i==null?void 0:i.value)||"").split(/\r?\n/).map(_=>_.trim()).filter(Boolean),w=Array.from(document.querySelectorAll('input[name="reporter"]:checked')).map(_=>_.value),$=(E=document.getElementById("launch-quarantine"))==null?void 0:E.checked;try{const{launcher:_}=await at({profile:p,tests:y,markers:u||void 0,device_serial:h||void 0,reporters:w.length?w:void 0,include_quarantined:!!$,config:(n==null?void 0:n.value)||void 0,live_target:!!(r!=null&&r.checked)});t&&(t.textContent=JSON.stringify(_,null,2)),location.hash="/live"}catch(_){const R=String(_);t&&(t.textContent=R),/\b409\b/.test(R)&&/already/i.test(R)&&(location.hash="/live")}})()}),(m=document.getElementById("launch-stop"))==null||m.addEventListener("click",()=>{(async()=>{try{const{launcher:p}=await nt();t&&(t.textContent=JSON.stringify(p,null,2))}catch(p){t&&(t.textContent=String(p))}})()}),c(),window.setInterval(()=>{location.hash.replace(/^#\/?/,"").startsWith("launch")&&c()},2e3)}async function kt(){if(await L(),(await q()).read_only)return`<h1>Quarantine</h1>
      <div class="empty">Read-only mode — quarantine management disabled.</div>`;const n=await st(),e=(n.entries||[]).map(s=>`<tr data-testid="quarantine-row">
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
  `}function It(){var n,e;const t=document.getElementById("q-msg");(n=document.getElementById("q-add"))==null||n.addEventListener("click",()=>{(async()=>{try{await it({test_id:document.getElementById("q-id").value.trim(),owner:document.getElementById("q-owner").value.trim(),reason:document.getElementById("q-reason").value.trim(),exit_criteria:document.getElementById("q-exit").value.trim(),issue:document.getElementById("q-issue").value.trim()||void 0}),location.reload()}catch(s){t&&(t.textContent=String(s))}})()}),(e=document.getElementById("q-audit"))==null||e.addEventListener("click",()=>{(async()=>{try{const s=await ot({});t&&(t.textContent=s.summary)}catch(s){t&&(t.textContent=String(s))}})()}),document.querySelectorAll(".q-remove").forEach(s=>{s.addEventListener("click",()=>{(async()=>{const i=s.dataset.id||"";try{await rt(i),location.reload()}catch(r){t&&(t.textContent=String(r))}})()})})}async function Et(){if(await L(),(await q()).read_only)return`<h1>Profiles</h1>
      <div class="empty">Read-only mode — profile editor disabled.</div>`;const{profiles:n,path:e}=await N(),s=n.map(o=>`<option value="${a(o)}">${a(o)}</option>`).join(""),i=n[0]||"";let r="{}",l="";if(i){const o=await F(i);r=JSON.stringify(o.fields,null,2),l=(o.secret_env_names||[]).map(d=>`<code>${a(d)}</code>`).join(" ")}return`
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
    <p class="meta">Secret env slots: ${l||"—"}</p>
    <textarea id="prof-fields" data-testid="prof-fields" rows="18" class="code">${a(r)}</textarea>
    <pre class="log" id="prof-msg" data-testid="prof-msg"></pre>
  `}function xt(){var i,r,l,o;const t=document.getElementById("prof-msg"),n=document.getElementById("prof-fields"),e=document.getElementById("prof-name"),s=()=>n?JSON.parse(n.value):{};(i=document.getElementById("prof-load"))==null||i.addEventListener("click",()=>{(async()=>{try{const d=(e==null?void 0:e.value)||"",c=await F(d);n&&(n.value=JSON.stringify(c.fields,null,2)),t&&(t.textContent=`loaded ${d}`)}catch(d){t&&(t.textContent=String(d))}})()}),(r=document.getElementById("prof-validate"))==null||r.addEventListener("click",()=>{(async()=>{try{const d=(e==null?void 0:e.value)||"",c=await tt(d,s());t&&(t.textContent=c.ok?`OK
${JSON.stringify(c.settings_summary,null,2)}`:c.errors.join(`
`))}catch(d){t&&(t.textContent=String(d))}})()}),(l=document.getElementById("prof-preview"))==null||l.addEventListener("click",()=>{(async()=>{try{const d=(e==null?void 0:e.value)||"",c=await j(d,s(),!1);t&&(t.textContent=c.diff||"(no diff)")}catch(d){t&&(t.textContent=String(d))}})()}),(o=document.getElementById("prof-save"))==null||o.addEventListener("click",()=>{(async()=>{try{const d=(e==null?void 0:e.value)||"",c=await j(d,s(),!0);t&&(t.textContent=c.saved?`saved
${c.diff}`:c.errors.join(`
`))}catch(d){t&&(t.textContent=String(d))}})()})}function O(t,n="var(--accent)"){const e=t.map(c=>Number(c.v??0));if(!e.length)return'<span class="meta">no samples</span>';const s=Math.min(...e),i=Math.max(...e),r=Math.max(1e-9,i-s),l=320,o=64,d=e.map((c,v)=>{const f=v/Math.max(1,e.length-1)*l,m=o-(c-s)/r*(o-4)-2;return`${f.toFixed(1)},${m.toFixed(1)}`}).join(" ");return`<svg class="spark" viewBox="0 0 ${l} ${o}" width="${l}" height="${o}">
    <polyline fill="none" stroke="${n}" stroke-width="1.5" points="${d}"/>
  </svg>`}async function Lt(){var i;const t=await M({}),n=t.runs.map(r=>`<option value="${a(r.id)}">${a(r.id.slice(0,8))}… · ${a(r.profile)}</option>`).join(""),e=((i=t.runs[0])==null?void 0:i.id)||"";let s='<div class="empty">Pick a run to load perf series.</div>';if(e){const r=await H(e);s=Q(e,r.series,r.summary)}return`
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
  `}function Q(t,n,e){const s=Object.keys(n);return s.length?s.map(i=>{var l,o;const r=e[i]||{};return`<div class="panel" data-testid="perf-metric">
        <h2>${a(i)} <span class="meta">avg ${a(((o=(l=r.avg)==null?void 0:l.toFixed)==null?void 0:o.call(l,2))??"—")} · n ${a(r.count??0)}</span></h2>
        ${O(n[i]||[])}
      </div>`}).join(""):`<div class="empty">No perf samples for ${a(t)}.</div>`}function qt(){var r,l;const t=document.getElementById("perf-series"),n=document.getElementById("perf-compare-out"),e=document.getElementById("perf-run"),s=document.getElementById("perf-a"),i=document.getElementById("perf-b");s&&i&&i.options.length>1&&(i.selectedIndex=1),(r=document.getElementById("perf-load"))==null||r.addEventListener("click",()=>{(async()=>{const o=(e==null?void 0:e.value)||"";if(!(!o||!t))try{const d=await H(o);t.innerHTML=Q(o,d.series,d.summary)}catch(d){t.textContent=String(d)}})()}),(l=document.getElementById("perf-compare"))==null||l.addEventListener("click",()=>{(async()=>{const o=(s==null?void 0:s.value)||"",d=(i==null?void 0:i.value)||"";if(n)try{const c=await dt(o,d),v=c.deltas.map(m=>{var p,h,u,b,y,w;return`<tr>
              <td>${a(m.metric)}</td>
              <td>${a(((u=(h=(p=m.a)==null?void 0:p.avg)==null?void 0:h.toFixed)==null?void 0:u.call(h,2))??"—")}</td>
              <td>${a(((w=(y=(b=m.b)==null?void 0:b.avg)==null?void 0:y.toFixed)==null?void 0:w.call(y,2))??"—")}</td>
              <td>${m.delta_avg==null?"—":a(m.delta_avg.toFixed(2))}</td>
            </tr>`}).join(""),f=Object.keys(c.series_a).map(m=>{const p=c.series_a[m]||[],h=c.series_b[m]||[];return`<div class="panel">
              <h2>${a(m)} overlay</h2>
              <div class="toolbar">
                <span class="meta">A</span>${O(p,"var(--accent)")}
                <span class="meta">B</span>${O(h,"var(--ok)")}
              </div>
            </div>`}).join("");n.innerHTML=`
          <div class="table-wrap">
            <table data-testid="perf-delta-table">
              <thead><tr><th>Metric</th><th>A avg</th><th>B avg</th><th>Δ avg</th></tr></thead>
              <tbody>${v||'<tr><td colspan="4">No metrics</td></tr>'}</tbody>
            </table>
          </div>
          ${f}`}catch(c){n.textContent=String(c)}})()})}function I(t){const n=(e,s)=>`<a href="${e}" class="${t===s?"active":""}">${s}</a>`;return`<div class="subnav" data-testid="lens-nav">
    ${n("#/lens","Snapshots")}
    ${n("#/lens/diff","Diff")}
    ${n("#/lens/sessions","Sessions")}
    ${n("#/lens/turns","Agent")}
  </div>`}async function Ct(){var l,o,d;const n=(await W()).snapshots||[],e=n.map(c=>`<option value="${a(c.id)}">${a(c.id)} · ${a(c.game_version)}</option>`).join(""),s=((l=n[1])==null?void 0:l.id)||((o=n[0])==null?void 0:o.id)||"",i=((d=n[0])==null?void 0:d.id)||"",r=n.map(c=>`
    <tr data-testid="lens-snap-row" data-snap-id="${a(c.id)}">
      <td class="wrap"><code>${a(c.id)}</code></td>
      <td>${a(c.game_version)}</td>
      <td>${a(c.feature_id??"—")}</td>
      <td>${a(c.created_at??"")}</td>
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
  `}async function Bt(){var m,p,h;const t=(await W()).snapshots||[],n=new URLSearchParams(location.hash.split("?")[1]||""),e=n.get("a")||((m=t[1])==null?void 0:m.id)||((p=t[0])==null?void 0:p.id)||"",s=n.get("b")||((h=t[0])==null?void 0:h.id)||"";if(!e||!s)return`
      <h1>Typed diff</h1>
      ${I("Diff")}
      <div class="empty" data-testid="lens-diff-empty">Pick two snapshots on GameLens.</div>`;const i=await ut(e,s),r=i.diff.entries||[],l=i.diff.by_system||{},d=Object.keys(l).sort().map(u=>{const b=(l[u]||[]).map(y=>`<li data-testid="lens-diff-entry">${a(Mt(y))}</li>`).join("");return`<div class="panel"><h3>[${a(u)}]</h3><ul>${b}</ul></div>`}).join(""),c=i.implications;let v=[];try{(await q()).read_only||(v=(await N()).profiles||[])}catch{v=[]}const f=v.filter(u=>u.startsWith("ai_")).concat(v.filter(u=>!u.startsWith("ai_"))).map(u=>{const b=u==="ai_groq"?"selected":"";return`<option value="${a(u)}" ${b}>${a(u)}</option>`}).join("");return`
    <h1>Typed diff</h1>
    ${I("Diff")}
    <p class="meta" data-testid="lens-diff-meta">
      ${a(i.diff.snapshot_id_a||e)} → ${a(i.diff.snapshot_id_b||s)}
      · ${r.length} entries · framing vs measured stay separate
    </p>
    ${d||'<div class="empty">(no differences)</div>'}
    ${Ut(c)}
    <h2>Ask balance agent</h2>
    <p class="meta">Retune <em>priorities</em> only — model reasoning, never SO writes or green/red.</p>
    <div class="panel" data-testid="lens-agent-form">
      <label class="block">profile
        <select id="agent-profile" data-testid="agent-profile">${f||'<option value="ai_groq">ai_groq</option>'}</select>
      </label>
      <label class="block">question
        <textarea id="agent-q" data-testid="agent-q" rows="3">What should a human look at for a retune?</textarea>
      </label>
      <button type="button" id="agent-run" data-testid="agent-run">Ask</button>
      <div id="agent-msg" class="meta" data-testid="agent-msg"></div>
    </div>
    <div id="agent-result"></div>
    <script type="application/json" id="lens-pair">${JSON.stringify({a:e,b:s})}<\/script>
  `}async function Pt(){const n=((await pt()).sessions||[]).map(e=>`
    <tr data-testid="tel-session-row" data-session-id="${a(e.id)}">
      <td class="wrap"><a href="#/lens/sessions/${encodeURIComponent(e.id)}">${a(e.id)}</a></td>
      <td>${a(e.outcome??"—")}</td>
      <td class="wrap">${a(e.config_snapshot_id??"—")}</td>
      <td>${a(e.policy_id??"—")}</td>
      <td>${a(e.seed??"—")}</td>
      <td class="wrap">${a((e.notes||[]).join("; "))}</td>
    </tr>`).join("");return`
    <h1>Telemetry sessions</h1>
    ${I("Sessions")}
    <p class="meta"><code>outcome=lose</code> is measured play, not a bot/framework fail. <code>snap-unset</code> is a join gap.</p>
    <div class="table-wrap">
      <table data-testid="tel-sessions">
        <thead>
          <tr><th>Id</th><th>Outcome</th><th>Snapshot</th><th>Policy</th><th>Seed</th><th>Notes</th></tr>
        </thead>
        <tbody>${n||'<tr><td colspan="6">No telemetry sessions.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function Nt(t){const e=(await ft(t)).session;return`
    <p class="meta"><a href="#/lens/sessions">← Sessions</a> · ${a(e.id)}</p>
    <h1>Session</h1>
    ${I("Sessions")}
    ${At(e)}
  `}async function Rt(){const n=((await ht()).turns||[]).map(e=>`
    <tr data-testid="agent-turn-row" data-turn-id="${a(e.id)}">
      <td class="wrap"><a href="#/lens/turns/${encodeURIComponent(e.id)}">${a(e.id)}</a></td>
      <td>${a(e.status??"")}</td>
      <td>${a(e.framing??"")}</td>
      <td class="wrap">${a(e.question??"")}</td>
      <td>${a(e.created_at??"")}</td>
    </tr>`).join("");return`
    <h1>Balance agent</h1>
    ${I("Agent")}
    <p class="meta">Persisted turns. Numbers in citations are measured; priorities are model reasoning.</p>
    <div class="table-wrap">
      <table data-testid="agent-turns">
        <thead><tr><th>Id</th><th>Status</th><th>Framing</th><th>Question</th><th>Created</th></tr></thead>
        <tbody>${n||'<tr><td colspan="5">No agent turns yet. Ask from a typed diff.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function Ot(t){const n=await mt(t);return`
    <p class="meta"><a href="#/lens/turns">← Agent</a> · ${a(t)}</p>
    <h1>Agent turn</h1>
    ${I("Agent")}
    ${K(n.turn)}
  `}function jt(){var e;const t=document.getElementById("lens-open-diff");t==null||t.addEventListener("click",()=>{var r,l;const s=(r=document.getElementById("lens-a"))==null?void 0:r.value,i=(l=document.getElementById("lens-b"))==null?void 0:l.value;!s||!i||(location.hash=`/lens/diff?a=${encodeURIComponent(s)}&b=${encodeURIComponent(i)}`)});const n=(e=document.getElementById("lens-defaults"))==null?void 0:e.textContent;if(n)try{const s=JSON.parse(n),i=document.getElementById("lens-a"),r=document.getElementById("lens-b");i&&s.a&&(i.value=s.a),r&&s.b&&(r.value=s.b)}catch{}}function Tt(){const t=document.getElementById("agent-run");t==null||t.addEventListener("click",()=>{(async()=>{var d,c,v;const n=document.getElementById("agent-msg"),e=document.getElementById("agent-result"),s=(d=document.getElementById("lens-pair"))==null?void 0:d.textContent;let i="",r="";try{const f=JSON.parse(s||"{}");i=f.a||"",r=f.b||""}catch{}const l=(c=document.getElementById("agent-q"))==null?void 0:c.value,o=(v=document.getElementById("agent-profile"))==null?void 0:v.value;n&&(n.textContent="running…");try{const f=await vt({snapshot_a:i,snapshot_b:r,question:l||void 0,profile:o||void 0});n&&(n.textContent=`status=${f.turn.status}`),e&&(e.innerHTML=K(f.turn))}catch(f){n&&(n.textContent=String(f))}})()})}function Ut(t){if(!t)return'<div class="empty" data-testid="lens-impl-empty">No persisted implications for this pair.</div>';const n=(t.gaps||[]).map(e=>`<li>${a(e)}</li>`).join("");return`
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
    </div>`}function At(t){const n=(t.notes||[]).map(e=>`<li>${a(e)}</li>`).join("");return`
    <div class="panel" data-testid="tel-session-detail">
      <div class="meta">outcome=${a(t.outcome??"—")} · snapshot=${a(t.config_snapshot_id??"—")}
        · policy=${a(t.policy_id??"—")} · seed=${a(t.seed??"—")}</div>
      <h3>Notes</h3>
      <ul data-testid="tel-session-notes">${n||"<li>(none)</li>"}</ul>
      <h3>Summary (measured)</h3>
      <pre class="pre-json">${a(JSON.stringify(t.summary??{},null,2))}</pre>
    </div>`}function K(t){const n=(t.priorities||[]).map(i=>`<li>${a(i)}</li>`).join(""),e=(t.gaps||[]).map(i=>`<li>${a(i)}</li>`).join(""),s=t.ai_cost_total!=null?String(t.ai_cost_total):"—";return`
    <div class="panel" data-testid="agent-turn">
      <div class="meta">status=${a(t.status??"")} · framing=${a(t.framing??"")}
        · cost_usd=${a(s)}${t.pending?` · pending=${a(t.pending)}`:""}</div>
      <h3>Priorities (model reasoning)</h3>
      <ul data-testid="agent-priorities">${n||"<li>(none)</li>"}</ul>
      <h3>Gaps</h3>
      <ul class="gap-list" data-testid="agent-gaps">${e||"<li>(none)</li>"}</ul>
      <h3>Measured citations</h3>
      <pre class="pre-json" data-testid="agent-measured">${a(JSON.stringify(t.citations??{},null,2))}</pre>
    </div>`}function Mt(t){if(t.kind==="added_entity")return`+ entity ${t.entity_id}`;if(t.kind==="removed_entity")return`- entity ${t.entity_id}`;const n=t.path||"?";return t.delta!=null?`~ ${t.entity_id}.${n}: ${t.before} -> ${t.after} (delta ${t.delta})`:`~ ${t.entity_id}.${n}: ${JSON.stringify(t.before)} -> ${JSON.stringify(t.after)}`}const U=document.querySelector("#app");let x=!1,B=!1,P=!1;function A(t,n){const e=(o,d)=>`<a href="${o}" class="${t===d?"active":""}">${d}</a>`,s=x?"":`${e("#/launch","Launch")}
        ${e("#/quarantine","Quarantine")}
        ${e("#/profiles","Profiles")}`,i=[x?'<span class="badge warn" title="--read-only">RO</span>':"",B?'<span class="badge warn" title="Playwright smoke fixture — not real runs">SMOKE</span>':"",P?'<span class="badge warn" title="Restart questline hud">STALE API</span>':""].filter(Boolean).join(" "),r=B?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)">
        <strong>SMOKE FIXTURE SERVER</strong> — fake launcher + seeded runs.
        For real Wire/mock runs stop this process and use
        <code>uv run questline hud --open</code> (port 8741).
      </div>`:"",l=P?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)" data-testid="stale-api">
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
    <main class="main">${r}${l}${n}</main>
  `}function Dt(){const e=((location.hash.replace(/^#\/?/,"")||"").split("?")[0]||"").split("/").filter(Boolean);if(e[0]==="runs"&&e[1]&&e[2]==="tests"&&e.length>=4){const s=e.slice(3).join("/");let i=s;try{i=decodeURIComponent(s)}catch{}return{name:"test",params:{runId:e[1],testId:i}}}return e[0]==="runs"&&e[1]?{name:"run",params:{runId:e[1]}}:e[0]==="trends"?{name:"trends",params:{}}:e[0]==="live"?{name:"live",params:{}}:e[0]==="launch"?{name:"launch",params:{}}:e[0]==="quarantine"?{name:"quarantine",params:{}}:e[0]==="profiles"?{name:"profiles",params:{}}:e[0]==="perf"?{name:"perf",params:{}}:e[0]==="lens"?e[1]==="diff"?{name:"lens-diff",params:{}}:e[1]==="sessions"&&e[2]?{name:"lens-session",params:{id:e[2]}}:e[1]==="sessions"?{name:"lens-sessions",params:{}}:e[1]==="turns"&&e[2]?{name:"lens-turn",params:{id:e[2]}}:e[1]==="turns"?{name:"lens-turns",params:{}}:{name:"lens",params:{}}:{name:"runs",params:{}}}function Ft(t){return t.length?`
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
    </div>`}async function Jt(){const t=new URLSearchParams(location.hash.split("?")[1]||""),n=t.get("profile")||"",e=t.get("status")||"",s=await M({profile:n||void 0,status:e||void 0});return`
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
      ${x?"":'<a class="btn" href="#/launch">Launch run</a>'}
    </div>
    ${Ft(s.runs)}
  `}async function V(){const t=Dt();try{let n="",e="Runs";t.name==="run"?(n=await $t(t.params.runId),e="Runs"):t.name==="test"?(n=await gt(t.params.runId,t.params.testId),e="Runs"):t.name==="trends"?(n=await yt(),e="Trends"):t.name==="live"?(n=await bt(),e="Live"):t.name==="launch"?(n=await St(),e="Launch"):t.name==="quarantine"?(n=await kt(),e="Quarantine"):t.name==="profiles"?(n=await Et(),e="Profiles"):t.name==="perf"?(n=await Lt(),e="Perf"):t.name==="lens"?(n=await Ct(),e="GameLens"):t.name==="lens-diff"?(n=await Bt(),e="GameLens"):t.name==="lens-sessions"?(n=await Pt(),e="GameLens"):t.name==="lens-session"?(n=await Nt(t.params.id),e="GameLens"):t.name==="lens-turns"?(n=await Rt(),e="GameLens"):t.name==="lens-turn"?(n=await Ot(t.params.id),e="GameLens"):(n=await Jt(),e="Runs"),U.innerHTML=A(e,n),Ht(t.name)}catch(n){U.innerHTML=A("Runs",`<div class="empty">Failed to load HUD: ${a(String(n))}</div>`)}}function Ht(t){var n;if(t==="runs"&&((n=document.getElementById("f-apply"))==null||n.addEventListener("click",()=>{const e=document.getElementById("f-profile").value.trim(),s=document.getElementById("f-status").value,i=new URLSearchParams;e&&i.set("profile",e),s&&i.set("status",s);const r=i.toString();location.hash=r?`/?${r}`:"/"})),t==="live"){const e=document.getElementById("live-root");e&&wt(e)}t==="launch"&&_t(),t==="quarantine"&&It(),t==="profiles"&&xt(),t==="perf"&&qt(),t==="lens"&&jt(),t==="lens-diff"&&Tt()}async function Wt(){var t,n;try{const e=await q();x=!!e.read_only,B=!!e.smoke,P=!((t=e.api)!=null&&t.test_by_query)||!((n=e.api)!=null&&n.lens),x||await L()}catch{x=!1,B=!1,P=!0}await V()}window.addEventListener("hashchange",()=>{V()});Wt();
