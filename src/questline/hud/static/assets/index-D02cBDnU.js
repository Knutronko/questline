(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))s(r);new MutationObserver(r=>{for(const i of r)if(i.type==="childList")for(const c of i.addedNodes)c.tagName==="LINK"&&c.rel==="modulepreload"&&s(c)}).observe(document,{childList:!0,subtree:!0});function a(r){const i={};return r.integrity&&(i.integrity=r.integrity),r.referrerPolicy&&(i.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?i.credentials="include":r.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function s(r){if(r.ep)return;r.ep=!0;const i=a(r);fetch(r.href,i)}})();let _=null;async function b(t){const e=await fetch(t),a=await e.text();if(/^\s*</.test(a)||(e.headers.get("content-type")||"").includes("text/html"))throw new Error(`${e.status} ${t}: got HTML instead of JSON. Restart questline hud (old process missing new /api routes).`);if(!e.ok)throw new Error(`${e.status} ${t}: ${a}`);try{return JSON.parse(a)}catch(r){throw new Error(`${t}: invalid JSON (${String(r)})`)}}async function E(){return _||(_=(await b("/api/csrf")).csrf_token,_)}async function x(t,e,a){const s=await E(),r=await fetch(e,{method:t,headers:{"Content-Type":"application/json","X-CSRF-Token":s},body:a===void 0?void 0:JSON.stringify(a)});if(!r.ok){const i=await r.text();throw new Error(`${r.status} ${e}: ${i}`)}if(r.status!==204)return await r.json()}function I(){return b("/api/meta")}function O(t){const e=new URLSearchParams;t.profile&&e.set("profile",t.profile),t.status&&e.set("status",t.status);const a=e.toString();return b(`/api/runs${a?`?${a}`:""}`)}function J(t){return b(`/api/runs/${encodeURIComponent(t)}`)}function Q(t,e){return b(`/api/runs/${encodeURIComponent(t)}/tests/${encodeURIComponent(e)}`)}function W(t=50){return b(`/api/trends?limit=${t}`)}function C(t){const e=t?`?config=${encodeURIComponent(t)}`:"";return b(`/api/profiles${e}`)}function K(){return b("/api/configs")}function T(){return b("/api/devices")}function j(t){return b(`/api/profiles/${encodeURIComponent(t)}`)}function V(t,e){return x("POST",`/api/profiles/${encodeURIComponent(t)}/validate`,{fields:e,apply:!1})}function B(t,e,a){return x("POST",`/api/profiles/${encodeURIComponent(t)}`,{fields:e,apply:a})}function G(){return b("/api/reporters")}function M(){return b("/api/launcher")}function X(t){return x("POST","/api/launcher/start",t)}function z(){return x("POST","/api/launcher/stop")}function Y(){return b("/api/quarantine")}function Z(t){return x("POST","/api/quarantine",t)}function tt(t){return x("DELETE",`/api/quarantine?test_id=${encodeURIComponent(t)}`)}function et(t){return x("POST","/api/quarantine/audit",t||{})}function U(t){return b(`/api/perf/${encodeURIComponent(t)}`)}function at(t,e){return b(`/api/perf/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(e)}`)}function nt(t=50){return b(`/api/perf/correlation?limit=${t}`)}function st(t){return`/api/artifacts/file?path=${encodeURIComponent(t)}`}function k(t){if(t==null||Number.isNaN(t))return"—";if(t<60)return`${t.toFixed(1)}s`;const e=Math.floor(t/60),a=t-e*60;return`${e}m ${a.toFixed(0)}s`}function n(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function rt(t){const e=await J(t),a=e.run,s=e.banner,r=e.tests.map(i=>`
    <tr data-testid="test-row" data-test-id="${n(i.id)}">
      <td class="wrap"><a href="#/runs/${n(t)}/tests/${n(i.id)}">${n(i.nodeid)}</a></td>
      <td><span class="badge ${n(i.status)}">${n(i.status)}</span></td>
      <td class="verdict-${n(i.verdict??"")}">${n(i.verdict??"—")}</td>
      <td>${n(k(i.duration_s))}</td>
      <td class="wrap">${n(i.death_step_name??"")}</td>
    </tr>`).join("");return`
    <p class="meta"><a href="#/">← Runs</a> · ${n(a.id)}</p>
    <h1>Run detail</h1>
    <div class="meta">
      profile=${n(a.profile)} · driver=${n(a.driver??"—")} ·
      device=${n(a.device??"—")} · status=${n(a.status)} ·
      duration=${n(k(a.duration_s))}
    </div>
    <div class="banner" data-testid="verdict-banner">
      <div class="stat ok"><span>passed</span><b>${a.passed}</b></div>
      <div class="stat"><span>failed</span><b>${a.failed}</b></div>
      <div class="stat infra"><span>infra</span><b>${s.infra_failures}</b></div>
      <div class="stat test"><span>test</span><b>${s.test_failures}</b></div>
      <div class="stat"><span>authoring</span><b>${s.authoring_failures}</b></div>
    </div>
    <h2>Tests</h2>
    <div class="table-wrap">
      <table data-testid="tests-table">
        <thead>
          <tr><th>Test</th><th>Status</th><th>Verdict</th><th>Duration</th><th>Death step</th></tr>
        </thead>
        <tbody>${r||'<tr><td colspan="5">No tests.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function it(t,e){const a=await Q(t,e),s=a.test,r=a.steps.map(f=>{const v=String(f.status??"");return`<li data-testid="step-row">
        <span class="ts">${n(f.started_at??"")}</span>
        <span class="badge ${n(v)}">${n(v)}</span>
        <span>${n(f.name??"")}${f.error_message?` — ${n(f.error_message)}`:""}</span>
      </li>`}).join(""),i=(a.history||[]).map(f=>{const v=String(f.status??""),p=Number(f.duration_s??0)||1,h=Math.max(4,Math.min(28,p*4));return`<i class="${n(v)}" style="height:${h}px" title="${n(v)}"></i>`}).join(""),c=a.death_point||{},d=c.last_started_step||{},o=c.driver_health||{},l=s.verdict==="infra"?"infra":"",$=(a.artifacts||[]).map(f=>{const v=String(f.path??""),p=String(f.kind??""),h=String(f.name??v),m=st(v);return p==="screenshot"||/\.(png|jpe?g|webp|gif)$/i.test(h)?`<div><a href="${n(m)}" target="_blank" rel="noreferrer">
          <img src="${n(m)}" alt="${n(h)}"/><div>${n(h)}</div></a></div>`:`<div><a href="${n(m)}" target="_blank" rel="noreferrer">${n(h)}</a>
        <div class="meta">${n(p)} · ${n(f.size_bytes??"")} B</div></div>`}).join("");return`
    <p class="meta">
      <a href="#/">Runs</a> /
      <a href="#/runs/${n(t)}">${n(t.slice(0,8))}…</a>
    </p>
    <h1 data-testid="test-title">${n(s.nodeid)}</h1>
    <div class="meta">
      status=<span class="badge ${n(s.status)}">${n(s.status)}</span> ·
      verdict=<span class="verdict-${n(s.verdict??"")}">${n(s.verdict??"—")}</span> ·
      duration=${n(k(s.duration_s))}
    </div>

    <div class="panel death ${l}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${n(d.name??"—")}</b>
        @ ${n(d.started_at??"")}</div>
      <div>error: ${n(s.error_type??"")} — ${n(s.error_message??"")}</div>
      <div>driver health: ${n(JSON.stringify(o||{}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${i||"<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${r||"<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${$||"<span class='meta'>none</span>"}</div>
  `}async function ot(){const[t,e]=await Promise.all([W(50),nt(50)]),a=t.series||[],s=Math.max(1,...a.map(o=>Number(o.duration_s??0)||0)),r=a.map(o=>{const l=o.pass_rate==null?0:Number(o.pass_rate),$=Math.max(4,Math.round(l*100)),f=Number(o.duration_s??0);return`<div class="bar ${Number(o.failed??0)>0?"fail":""}" style="height:${$}%">
        <span>${n(o.run_id)} · ${(l*100).toFixed(0)}% · ${n(k(f))}</span>
      </div>`}).join(""),i=a.map(o=>{const l=Number(o.duration_s??0);return`<div class="bar" style="height:${Math.max(4,Math.round(l/s*100))}%">
        <span>${n(o.run_id)} · ${n(k(l))}</span>
      </div>`}).join(""),c=(t.flaky_tests||[]).map(o=>`<tr>
        <td class="wrap">${n(o.nodeid)}</td>
        <td>${n(o.runs)}</td>
        <td>${n(o.passed)}/${n(o.failed)}</td>
        <td>${(Number(o.pass_rate)*100).toFixed(0)}%</td>
        <td>${(Number(o.flake_score)*100).toFixed(0)}%</td>
      </tr>`).join(""),d=(e.tests||[]).map(o=>{const l=(o.points||[]).map($=>{const f=$.duration_s==null?0:Number($.duration_s);return`<span class="dot ${$.passed?"ok":"bad"}" title="${n($.run_id)} · ${n(k(f))}"></span>`}).join("");return`<tr>
        <td class="wrap">${n(o.nodeid)}</td>
        <td>${o.passed}/${o.failed}</td>
        <td class="corr-dots">${l}</td>
      </tr>`}).join("");return`
    <h1>Trends</h1>
    <h2>Pass rate (recent runs)</h2>
    <div class="chart" data-testid="pass-chart">${r||"<span class='meta'>no data</span>"}</div>
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
        <tbody>${d||'<tr><td colspan="3">No mixed pass/fail series yet.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function dt(){return`
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `}function ct(t){const e=document.getElementById("live-status"),a=document.getElementById("live-clear");a==null||a.addEventListener("click",()=>{t.innerHTML=""});const r=`${location.protocol==="https:"?"wss":"ws"}://${location.host}/live`;let i;try{i=new WebSocket(r)}catch(c){e&&(e.textContent="failed"),t.innerHTML=`<div>WebSocket error: ${n(String(c))}</div>`;return}i.onopen=()=>{e&&(e.textContent="live",e.className="badge passed")},i.onclose=()=>{e&&(e.textContent="closed",e.className="badge failed")},i.onerror=()=>{e&&(e.textContent="error",e.className="badge failed")},i.onmessage=c=>{try{const d=JSON.parse(String(c.data)),o=String(d.type??"?"),l=String(d.timestamp??""),$=d.nodeid||d.name||d.test_id||d.status||d.profile||"",f=document.createElement("div");f.innerHTML=`<span class="t">${n(l)}</span><b>${n(o)}</b> ${n($)}`,t.prepend(f)}catch{const d=document.createElement("div");d.textContent=String(c.data),t.prepend(d)}}}const D=[{id:"mock",label:"Mock demo",config:"questline.toml",profile:"mock",tests:"examples/demo-tests",live_target:!1,note:"No Unity. CI-style mock driver."},{id:"wire-editor",label:"Wire Editor",config:"examples/wire-smoke/questline.toml",profile:"editor",tests:"examples/wire-smoke",live_target:!0,note:"Unity Play + Wire on :13000. Device picker stays empty (OK)."},{id:"wire-android",label:"Wire Android",config:"examples/wire-smoke/questline.toml",profile:"android_local",tests:"examples/wire-smoke",live_target:!0,note:"Dev APK + adb. Pick a serial if more than one device."}];async function lt(){var h,m,y;await E();let t,e,a,s;try{[t,e,a,s]=await Promise.all([I(),K().catch(()=>({project_root:"",active:"",configs:[{path:"questline.toml",absolute:"questline.toml"}]})),G().catch(()=>({reporters:["console"]})),M().catch(()=>({launcher:{state:"idle"}}))])}catch(u){return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-error">
        Failed to load launcher APIs: ${n(String(u))}<br/>
        Stop the old <code>questline hud</code> process and start it again from
        <code>D:\\dev\\questline</code>.
      </div>`}if(t.read_only)return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;const r=((h=e.configs.find(u=>u.path.replace(/\\/g,"/")==="questline.toml"))==null?void 0:h.path)||((m=e.configs[0])==null?void 0:m.path)||"questline.toml",i=await C(r),c=await T(),d=(e.configs||[]).map(u=>{const g=u.path===r?"selected":"";return`<option value="${n(u.path)}" ${g}>${n(u.path)}</option>`}).join(""),o=(i.profiles||[]).map(u=>{const g=i.profiles.includes("editor")?"editor":i.profiles.includes("mock")?"mock":i.profiles[0]||"";return`<option value="${n(u)}" ${u===g?"selected":""}>${n(u)}</option>`}).join(""),l=['<option value="">(no adb pin — OK for Editor)</option>',...(c.devices||[]).map(u=>`<option value="${n(u.id)}">${n(u.id)} · ${n(u.platform)}</option>`)].join(""),$=(a.reporters||[]).map(u=>`<label class="check"><input type="checkbox" name="reporter" value="${n(u)}" ${u==="console"?"checked":""}/> ${n(u)}</label>`).join(""),f=D.map(u=>`<button type="button" class="preset" data-preset="${n(u.id)}" title="${n(u.note)}">${n(u.label)}</button>`).join(""),v=s.launcher,p=c.hint||((y=c.devices)!=null&&y.length?`${c.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire.");return`
    <h1>Run launcher</h1>
    <p class="meta">Profiles come from <code>questline.toml</code> (not from Unity being open).
      Unity Play + Wire = use preset <strong>Wire Editor</strong> or profile <code>editor</code>.
      Device list is <em>adb only</em> — Editor does not appear there.</p>
    <div class="toolbar" data-testid="launch-presets">
      <span class="meta">Presets:</span> ${f}
    </div>
    <div class="panel" data-testid="launch-form">
      <div class="toolbar">
        <label>config
          <select id="launch-config" data-testid="launch-config">${d}</select>
        </label>
        <label>profile
          <select id="launch-profile" data-testid="launch-profile">${o}</select>
        </label>
        <label>device
          <select id="launch-device" data-testid="launch-device">${l}</select>
        </label>
        <button type="button" id="launch-refresh-devices" data-testid="launch-refresh-devices">Refresh devices</button>
      </div>
      <p class="meta" id="launch-device-hint" data-testid="launch-device-hint">${n(p)}</p>
      ${c.error?`<p class="meta">adb error: ${n(c.error)}</p>`:""}
      <label class="block">markers <input id="launch-markers" placeholder="optional -m expression" data-testid="launch-markers"/></label>
      <label class="block">tests (one path/nodeid per line)
        <textarea id="launch-tests" rows="4" data-testid="launch-tests" placeholder="examples/wire-smoke">examples/demo-tests</textarea>
      </label>
      <div class="toolbar wrap">${$||"<span class='meta'>no reporters</span>"}</div>
      <label class="check"><input type="checkbox" id="launch-quarantine"/> include quarantined</label>
      <label class="check"><input type="checkbox" id="launch-live" data-testid="launch-live"/> QUESTLINE_LIVE_TARGET=1 (required for wire-smoke)</label>
      <div class="toolbar">
        <button type="button" id="launch-start" data-testid="launch-start">Launch</button>
        <button type="button" id="launch-stop" data-testid="launch-stop">Stop</button>
      </div>
      <p class="meta">Active project: <code>${n(e.project_root)}</code></p>
    </div>
    <h2>Status</h2>
    <pre class="log" id="launch-status" data-testid="launch-status">${n(JSON.stringify(v,null,2))}</pre>
  `}function ut(){var $,f,v;const t=document.getElementById("launch-status"),e=document.getElementById("launch-config"),a=document.getElementById("launch-profile"),s=document.getElementById("launch-device"),r=document.getElementById("launch-tests"),i=document.getElementById("launch-live"),c=document.getElementById("launch-device-hint"),d=async()=>{if(!(!e||!a))try{const p=await C(e.value),h=p.profiles.includes("editor")?"editor":p.profiles[0]||"";a.innerHTML=p.profiles.map(m=>`<option value="${n(m)}" ${m===h?"selected":""}>${n(m)}</option>`).join("")}catch(p){t&&(t.textContent=String(p))}},o=async()=>{var p;if(s)try{const h=await T();s.innerHTML=['<option value="">(no adb pin — OK for Editor)</option>',...(h.devices||[]).map(m=>`<option value="${n(m.id)}">${n(m.id)} · ${n(m.platform)}</option>`)].join(""),c&&(c.textContent=h.hint||((p=h.devices)!=null&&p.length?`${h.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire."))}catch(h){c&&(c.textContent=String(h))}};e==null||e.addEventListener("change",()=>{d()}),($=document.getElementById("launch-refresh-devices"))==null||$.addEventListener("click",()=>{o()}),document.querySelectorAll(".preset").forEach(p=>{p.addEventListener("click",()=>{const h=p.dataset.preset||"",m=D.find(y=>y.id===h);if(m){if(e){if(!Array.from(e.options).some(u=>u.value===m.config)){const u=document.createElement("option");u.value=m.config,u.textContent=m.config,e.appendChild(u)}e.value=m.config}r&&(r.value=m.tests),i&&(i.checked=m.live_target),(async()=>(await d(),a&&(a.value=m.profile)))()}})});const l=async()=>{try{const{launcher:p}=await M();t&&(t.textContent=JSON.stringify(p,null,2))}catch(p){t&&(t.textContent=String(p))}};(f=document.getElementById("launch-start"))==null||f.addEventListener("click",()=>{(async()=>{var P;const p=(a==null?void 0:a.value)||"",h=(s==null?void 0:s.value)||"",m=document.getElementById("launch-markers").value.trim(),u=((r==null?void 0:r.value)||"").split(/\r?\n/).map(w=>w.trim()).filter(Boolean),g=Array.from(document.querySelectorAll('input[name="reporter"]:checked')).map(w=>w.value),H=(P=document.getElementById("launch-quarantine"))==null?void 0:P.checked;try{const{launcher:w}=await X({profile:p,tests:u,markers:m||void 0,device_serial:h||void 0,reporters:g.length?g:void 0,include_quarantined:!!H,config:(e==null?void 0:e.value)||void 0,live_target:!!(i!=null&&i.checked)});t&&(t.textContent=JSON.stringify(w,null,2)),location.hash="/live"}catch(w){t&&(t.textContent=String(w))}})()}),(v=document.getElementById("launch-stop"))==null||v.addEventListener("click",()=>{(async()=>{try{const{launcher:p}=await z();t&&(t.textContent=JSON.stringify(p,null,2))}catch(p){t&&(t.textContent=String(p))}})()}),l(),window.setInterval(()=>{location.hash.replace(/^#\/?/,"").startsWith("launch")&&l()},2e3)}async function pt(){if(await E(),(await I()).read_only)return`<h1>Quarantine</h1>
      <div class="empty">Read-only mode — quarantine management disabled.</div>`;const e=await Y(),a=(e.entries||[]).map(s=>`<tr data-testid="quarantine-row">
        <td class="wrap">${n(s.test_id)}</td>
        <td class="wrap">${n(s.reason)}</td>
        <td>${n(s.owner)}</td>
        <td>${n(s.date)}</td>
        <td class="wrap">${n(s.exit_criteria)}</td>
        <td>${n(s.issue??"—")}</td>
        <td><button type="button" class="q-remove" data-id="${n(s.test_id)}">Remove</button></td>
      </tr>`).join("");return`
    <h1>Quarantine</h1>
    <p class="meta">Ledger: <code>${n(e.path)}</code> — same <code>QuarantineLedger</code> as CLI.</p>
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
        <tbody>${a||'<tr><td colspan="7">No quarantine entries.</td></tr>'}</tbody>
      </table>
    </div>
  `}function ft(){var e,a;const t=document.getElementById("q-msg");(e=document.getElementById("q-add"))==null||e.addEventListener("click",()=>{(async()=>{try{await Z({test_id:document.getElementById("q-id").value.trim(),owner:document.getElementById("q-owner").value.trim(),reason:document.getElementById("q-reason").value.trim(),exit_criteria:document.getElementById("q-exit").value.trim(),issue:document.getElementById("q-issue").value.trim()||void 0}),location.reload()}catch(s){t&&(t.textContent=String(s))}})()}),(a=document.getElementById("q-audit"))==null||a.addEventListener("click",()=>{(async()=>{try{const s=await et({});t&&(t.textContent=s.summary)}catch(s){t&&(t.textContent=String(s))}})()}),document.querySelectorAll(".q-remove").forEach(s=>{s.addEventListener("click",()=>{(async()=>{const r=s.dataset.id||"";try{await tt(r),location.reload()}catch(i){t&&(t.textContent=String(i))}})()})})}async function ht(){if(await E(),(await I()).read_only)return`<h1>Profiles</h1>
      <div class="empty">Read-only mode — profile editor disabled.</div>`;const{profiles:e,path:a}=await C(),s=e.map(d=>`<option value="${n(d)}">${n(d)}</option>`).join(""),r=e[0]||"";let i="{}",c="";if(r){const d=await j(r);i=JSON.stringify(d.fields,null,2),c=(d.secret_env_names||[]).map(o=>`<code>${n(o)}</code>`).join(" ")}return`
    <h1>Profile editor</h1>
    <p class="meta">Config: <code>${n(a)}</code>. Secrets are env names only — never values.</p>
    <div class="toolbar">
      <label>profile
        <select id="prof-name" data-testid="prof-name">${s}</select>
      </label>
      <button type="button" id="prof-load" data-testid="prof-load">Load</button>
      <button type="button" id="prof-validate" data-testid="prof-validate">Validate</button>
      <button type="button" id="prof-preview" data-testid="prof-preview">Diff preview</button>
      <button type="button" id="prof-save" data-testid="prof-save">Save</button>
    </div>
    <p class="meta">Secret env slots: ${c||"—"}</p>
    <textarea id="prof-fields" data-testid="prof-fields" rows="18" class="code">${n(i)}</textarea>
    <pre class="log" id="prof-msg" data-testid="prof-msg"></pre>
  `}function mt(){var r,i,c,d;const t=document.getElementById("prof-msg"),e=document.getElementById("prof-fields"),a=document.getElementById("prof-name"),s=()=>e?JSON.parse(e.value):{};(r=document.getElementById("prof-load"))==null||r.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await j(o);e&&(e.value=JSON.stringify(l.fields,null,2)),t&&(t.textContent=`loaded ${o}`)}catch(o){t&&(t.textContent=String(o))}})()}),(i=document.getElementById("prof-validate"))==null||i.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await V(o,s());t&&(t.textContent=l.ok?`OK
${JSON.stringify(l.settings_summary,null,2)}`:l.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()}),(c=document.getElementById("prof-preview"))==null||c.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await B(o,s(),!1);t&&(t.textContent=l.diff||"(no diff)")}catch(o){t&&(t.textContent=String(o))}})()}),(d=document.getElementById("prof-save"))==null||d.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await B(o,s(),!0);t&&(t.textContent=l.saved?`saved
${l.diff}`:l.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()})}function L(t,e="var(--accent)"){const a=t.map(l=>Number(l.v??0));if(!a.length)return'<span class="meta">no samples</span>';const s=Math.min(...a),r=Math.max(...a),i=Math.max(1e-9,r-s),c=320,d=64,o=a.map((l,$)=>{const f=$/Math.max(1,a.length-1)*c,v=d-(l-s)/i*(d-4)-2;return`${f.toFixed(1)},${v.toFixed(1)}`}).join(" ");return`<svg class="spark" viewBox="0 0 ${c} ${d}" width="${c}" height="${d}">
    <polyline fill="none" stroke="${e}" stroke-width="1.5" points="${o}"/>
  </svg>`}async function vt(){var r;const t=await O({}),e=t.runs.map(i=>`<option value="${n(i.id)}">${n(i.id.slice(0,8))}… · ${n(i.profile)}</option>`).join(""),a=((r=t.runs[0])==null?void 0:r.id)||"";let s='<div class="empty">Pick a run to load perf series.</div>';if(a){const i=await U(a);s=F(a,i.series,i.summary)}return`
    <h1>Perf graphs</h1>
    <p class="meta">Same data as <code>questline perf report</code>, with overlays and compare.</p>
    <div class="toolbar">
      <label>run
        <select id="perf-run" data-testid="perf-run">${e}</select>
      </label>
      <button type="button" id="perf-load" data-testid="perf-load">Load series</button>
    </div>
    <div id="perf-series" data-testid="perf-series">${s}</div>
    <h2>Build-over-build compare</h2>
    <div class="toolbar">
      <label>A (baseline)
        <select id="perf-a" data-testid="perf-a">${e}</select>
      </label>
      <label>B
        <select id="perf-b" data-testid="perf-b">${e}</select>
      </label>
      <button type="button" id="perf-compare" data-testid="perf-compare">Compare</button>
    </div>
    <div id="perf-compare-out" data-testid="perf-compare-out"></div>
    <script>
      // defaults selected via DOM after paint
    <\/script>
  `}function F(t,e,a){const s=Object.keys(e);return s.length?s.map(r=>{var c,d;const i=a[r]||{};return`<div class="panel" data-testid="perf-metric">
        <h2>${n(r)} <span class="meta">avg ${n(((d=(c=i.avg)==null?void 0:c.toFixed)==null?void 0:d.call(c,2))??"—")} · n ${n(i.count??0)}</span></h2>
        ${L(e[r]||[])}
      </div>`}).join(""):`<div class="empty">No perf samples for ${n(t)}.</div>`}function $t(){var i,c;const t=document.getElementById("perf-series"),e=document.getElementById("perf-compare-out"),a=document.getElementById("perf-run"),s=document.getElementById("perf-a"),r=document.getElementById("perf-b");s&&r&&r.options.length>1&&(r.selectedIndex=1),(i=document.getElementById("perf-load"))==null||i.addEventListener("click",()=>{(async()=>{const d=(a==null?void 0:a.value)||"";if(!(!d||!t))try{const o=await U(d);t.innerHTML=F(d,o.series,o.summary)}catch(o){t.textContent=String(o)}})()}),(c=document.getElementById("perf-compare"))==null||c.addEventListener("click",()=>{(async()=>{const d=(s==null?void 0:s.value)||"",o=(r==null?void 0:r.value)||"";if(e)try{const l=await at(d,o),$=l.deltas.map(v=>{var p,h,m,y,u,g;return`<tr>
              <td>${n(v.metric)}</td>
              <td>${n(((m=(h=(p=v.a)==null?void 0:p.avg)==null?void 0:h.toFixed)==null?void 0:m.call(h,2))??"—")}</td>
              <td>${n(((g=(u=(y=v.b)==null?void 0:y.avg)==null?void 0:u.toFixed)==null?void 0:g.call(u,2))??"—")}</td>
              <td>${v.delta_avg==null?"—":n(v.delta_avg.toFixed(2))}</td>
            </tr>`}).join(""),f=Object.keys(l.series_a).map(v=>{const p=l.series_a[v]||[],h=l.series_b[v]||[];return`<div class="panel">
              <h2>${n(v)} overlay</h2>
              <div class="toolbar">
                <span class="meta">A</span>${L(p,"var(--accent)")}
                <span class="meta">B</span>${L(h,"var(--ok)")}
              </div>
            </div>`}).join("");e.innerHTML=`
          <div class="table-wrap">
            <table data-testid="perf-delta-table">
              <thead><tr><th>Metric</th><th>A avg</th><th>B avg</th><th>Δ avg</th></tr></thead>
              <tbody>${$||'<tr><td colspan="4">No metrics</td></tr>'}</tbody>
            </table>
          </div>
          ${f}`}catch(l){e.textContent=String(l)}})()})}const R=document.querySelector("#app");let S=!1,q=!1;function N(t,e){const a=(c,d)=>`<a href="${c}" class="${t===d?"active":""}">${d}</a>`,s=S?"":`${a("#/launch","Launch")}
        ${a("#/quarantine","Quarantine")}
        ${a("#/profiles","Profiles")}`,r=[S?'<span class="badge warn" title="--read-only">RO</span>':"",q?'<span class="badge warn" title="Playwright smoke fixture — not real runs">SMOKE</span>':""].filter(Boolean).join(" "),i=q?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)">
        <strong>SMOKE FIXTURE SERVER</strong> — fake launcher + seeded runs.
        For real Wire/mock runs stop this process and use
        <code>uv run questline hud --open</code> (port 8741).
      </div>`:"";return`
    <header class="topbar">
      <a class="brand" href="#/">Questline <span>HUD</span></a>
      <nav class="nav">
        ${a("#/","Runs")}
        ${s}
        ${a("#/perf","Perf")}
        ${a("#/trends","Trends")}
        ${a("#/live","Live")}
      </nav>
      ${r}
    </header>
    <main class="main">${i}${e}</main>
  `}function bt(){const e=(location.hash.replace(/^#\/?/,"")||"").split("/").filter(Boolean);return e[0]==="runs"&&e[1]&&e[2]==="tests"&&e[3]?{name:"test",params:{runId:e[1],testId:e[3]}}:e[0]==="runs"&&e[1]?{name:"run",params:{runId:e[1]}}:e[0]==="trends"?{name:"trends",params:{}}:e[0]==="live"?{name:"live",params:{}}:e[0]==="launch"?{name:"launch",params:{}}:e[0]==="quarantine"?{name:"quarantine",params:{}}:e[0]==="profiles"?{name:"profiles",params:{}}:e[0]==="perf"?{name:"perf",params:{}}:{name:"runs",params:{}}}function yt(t){return t.length?`
    <div class="table-wrap">
      <table data-testid="runs-table">
        <thead>
          <tr>
            <th>Run</th><th>Profile</th><th>Driver</th><th>Device</th>
            <th>Status</th><th>Pass</th><th>Infra</th><th>Test</th>
            <th>Duration</th><th>Started</th>
          </tr>
        </thead>
        <tbody>${t.map(a=>`
    <tr data-testid="run-row" data-run-id="${n(a.id)}">
      <td class="wrap"><a href="#/runs/${n(a.id)}">${n(a.id.slice(0,8))}…</a></td>
      <td>${n(a.profile)}</td>
      <td>${n(a.driver??"—")}</td>
      <td>${n(a.device??"—")}</td>
      <td><span class="badge ${n(a.status)}">${n(a.status)}</span></td>
      <td>${a.passed}/${a.total}</td>
      <td class="verdict-infra">${a.infra_failures}</td>
      <td class="verdict-test">${a.test_failures}</td>
      <td>${n(k(a.duration_s))}</td>
      <td>${n(a.started_at??"")}</td>
    </tr>`).join("")}</tbody>
      </table>
    </div>`:`<div class="empty" data-testid="empty-store">
      No runs in the store yet.<br/>
      Use <a href="#/launch">Launch</a> or run a suite with the questline plugin, then refresh.
    </div>`}async function gt(){const t=new URLSearchParams(location.hash.split("?")[1]||""),e=t.get("profile")||"",a=t.get("status")||"",s=await O({profile:e||void 0,status:a||void 0});return`
    <h1>Runs</h1>
    <div class="toolbar">
      <label>profile <input id="f-profile" value="${n(e)}" placeholder="any"/></label>
      <label>status
        <select id="f-status">
          <option value="">any</option>
          ${["passed","failed","running","error"].map(r=>`<option value="${r}" ${a===r?"selected":""}>${r}</option>`).join("")}
        </select>
      </label>
      <button type="button" id="f-apply">Filter</button>
      ${S?"":'<a class="btn" href="#/launch">Launch run</a>'}
    </div>
    ${yt(s.runs)}
  `}async function A(){const t=bt();try{let e="",a="Runs";t.name==="run"?(e=await rt(t.params.runId),a="Runs"):t.name==="test"?(e=await it(t.params.runId,t.params.testId),a="Runs"):t.name==="trends"?(e=await ot(),a="Trends"):t.name==="live"?(e=await dt(),a="Live"):t.name==="launch"?(e=await lt(),a="Launch"):t.name==="quarantine"?(e=await pt(),a="Quarantine"):t.name==="profiles"?(e=await ht(),a="Profiles"):t.name==="perf"?(e=await vt(),a="Perf"):(e=await gt(),a="Runs"),R.innerHTML=N(a,e),wt(t.name)}catch(e){R.innerHTML=N("Runs",`<div class="empty">Failed to load HUD: ${n(String(e))}</div>`)}}function wt(t){var e;if(t==="runs"&&((e=document.getElementById("f-apply"))==null||e.addEventListener("click",()=>{const a=document.getElementById("f-profile").value.trim(),s=document.getElementById("f-status").value,r=new URLSearchParams;a&&r.set("profile",a),s&&r.set("status",s);const i=r.toString();location.hash=i?`/?${i}`:"/"})),t==="live"){const a=document.getElementById("live-root");a&&ct(a)}t==="launch"&&ut(),t==="quarantine"&&ft(),t==="profiles"&&mt(),t==="perf"&&$t()}async function kt(){try{const t=await I();S=!!t.read_only,q=!!t.smoke,S||await E()}catch{S=!1,q=!1}await A()}window.addEventListener("hashchange",()=>{A()});kt();
