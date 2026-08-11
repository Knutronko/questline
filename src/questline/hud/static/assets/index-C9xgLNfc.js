(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const i of document.querySelectorAll('link[rel="modulepreload"]'))s(i);new MutationObserver(i=>{for(const r of i)if(r.type==="childList")for(const d of r.addedNodes)d.tagName==="LINK"&&d.rel==="modulepreload"&&s(d)}).observe(document,{childList:!0,subtree:!0});function a(i){const r={};return i.integrity&&(r.integrity=i.integrity),i.referrerPolicy&&(r.referrerPolicy=i.referrerPolicy),i.crossOrigin==="use-credentials"?r.credentials="include":i.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function s(i){if(i.ep)return;i.ep=!0;const r=a(i);fetch(i.href,r)}})();let _=null;async function b(t){const e=await fetch(t),a=await e.text();if(/^\s*</.test(a)||(e.headers.get("content-type")||"").includes("text/html"))throw new Error(`${e.status} ${t}: got HTML instead of JSON. Restart questline hud (old process missing new /api routes).`);if(!e.ok)throw new Error(`${e.status} ${t}: ${a}`);try{return JSON.parse(a)}catch(i){throw new Error(`${t}: invalid JSON (${String(i)})`)}}async function E(){return _||(_=(await b("/api/csrf")).csrf_token,_)}async function k(t,e,a){const s=await E(),i=await fetch(e,{method:t,headers:{"Content-Type":"application/json","X-CSRF-Token":s},body:a===void 0?void 0:JSON.stringify(a)});if(!i.ok){const r=await i.text();throw new Error(`${i.status} ${e}: ${r}`)}if(i.status!==204)return await i.json()}function q(){return b("/api/meta")}function N(t){const e=new URLSearchParams;t.profile&&e.set("profile",t.profile),t.status&&e.set("status",t.status);const a=e.toString();return b(`/api/runs${a?`?${a}`:""}`)}function H(t){return b(`/api/runs/${encodeURIComponent(t)}`)}function J(t,e){return b(`/api/runs/${encodeURIComponent(t)}/tests/${encodeURIComponent(e)}`)}function Q(t=50){return b(`/api/trends?limit=${t}`)}function L(t){const e=t?`?config=${encodeURIComponent(t)}`:"";return b(`/api/profiles${e}`)}function W(){return b("/api/configs")}function O(){return b("/api/devices")}function T(t){return b(`/api/profiles/${encodeURIComponent(t)}`)}function K(t,e){return k("POST",`/api/profiles/${encodeURIComponent(t)}/validate`,{fields:e,apply:!1})}function P(t,e,a){return k("POST",`/api/profiles/${encodeURIComponent(t)}`,{fields:e,apply:a})}function V(){return b("/api/reporters")}function j(){return b("/api/launcher")}function G(t){return k("POST","/api/launcher/start",t)}function z(){return k("POST","/api/launcher/stop")}function X(){return b("/api/quarantine")}function Y(t){return k("POST","/api/quarantine",t)}function Z(t){return k("DELETE",`/api/quarantine?test_id=${encodeURIComponent(t)}`)}function tt(t){return k("POST","/api/quarantine/audit",t||{})}function M(t){return b(`/api/perf/${encodeURIComponent(t)}`)}function et(t,e){return b(`/api/perf/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(e)}`)}function at(t=50){return b(`/api/perf/correlation?limit=${t}`)}function nt(t){return`/api/artifacts/file?path=${encodeURIComponent(t)}`}function x(t){if(t==null||Number.isNaN(t))return"—";if(t<60)return`${t.toFixed(1)}s`;const e=Math.floor(t/60),a=t-e*60;return`${e}m ${a.toFixed(0)}s`}function n(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function st(t){const e=await H(t),a=e.run,s=e.banner,i=e.tests.map(r=>`
    <tr data-testid="test-row" data-test-id="${n(r.id)}">
      <td class="wrap"><a href="#/runs/${n(t)}/tests/${n(r.id)}">${n(r.nodeid)}</a></td>
      <td><span class="badge ${n(r.status)}">${n(r.status)}</span></td>
      <td class="verdict-${n(r.verdict??"")}">${n(r.verdict??"—")}</td>
      <td>${n(x(r.duration_s))}</td>
      <td class="wrap">${n(r.death_step_name??"")}</td>
    </tr>`).join("");return`
    <p class="meta"><a href="#/">← Runs</a> · ${n(a.id)}</p>
    <h1>Run detail</h1>
    <div class="meta">
      profile=${n(a.profile)} · driver=${n(a.driver??"—")} ·
      device=${n(a.device??"—")} · status=${n(a.status)} ·
      duration=${n(x(a.duration_s))}
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
        <tbody>${i||'<tr><td colspan="5">No tests.</td></tr>'}</tbody>
      </table>
    </div>
  `}async function it(t,e){const a=await J(t,e),s=a.test,i=a.steps.map(f=>{const v=String(f.status??"");return`<li data-testid="step-row">
        <span class="ts">${n(f.started_at??"")}</span>
        <span class="badge ${n(v)}">${n(v)}</span>
        <span>${n(f.name??"")}${f.error_message?` — ${n(f.error_message)}`:""}</span>
      </li>`}).join(""),r=(a.history||[]).map(f=>{const v=String(f.status??""),p=Number(f.duration_s??0)||1,h=Math.max(4,Math.min(28,p*4));return`<i class="${n(v)}" style="height:${h}px" title="${n(v)}"></i>`}).join(""),d=a.death_point||{},c=d.last_started_step||{},o=d.driver_health||{},l=s.verdict==="infra"?"infra":"",$=(a.artifacts||[]).map(f=>{const v=String(f.path??""),p=String(f.kind??""),h=String(f.name??v),m=nt(v);return p==="screenshot"||/\.(png|jpe?g|webp|gif)$/i.test(h)?`<div><a href="${n(m)}" target="_blank" rel="noreferrer">
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
      duration=${n(x(s.duration_s))}
    </div>

    <div class="panel death ${l}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${n(c.name??"—")}</b>
        @ ${n(c.started_at??"")}</div>
      <div>error: ${n(s.error_type??"")} — ${n(s.error_message??"")}</div>
      <div>driver health: ${n(JSON.stringify(o||{}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${r||"<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${i||"<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${$||"<span class='meta'>none</span>"}</div>
  `}async function rt(){const[t,e]=await Promise.all([Q(50),at(50)]),a=t.series||[],s=Math.max(1,...a.map(o=>Number(o.duration_s??0)||0)),i=a.map(o=>{const l=o.pass_rate==null?0:Number(o.pass_rate),$=Math.max(4,Math.round(l*100)),f=Number(o.duration_s??0);return`<div class="bar ${Number(o.failed??0)>0?"fail":""}" style="height:${$}%">
        <span>${n(o.run_id)} · ${(l*100).toFixed(0)}% · ${n(x(f))}</span>
      </div>`}).join(""),r=a.map(o=>{const l=Number(o.duration_s??0);return`<div class="bar" style="height:${Math.max(4,Math.round(l/s*100))}%">
        <span>${n(o.run_id)} · ${n(x(l))}</span>
      </div>`}).join(""),d=(t.flaky_tests||[]).map(o=>`<tr>
        <td class="wrap">${n(o.nodeid)}</td>
        <td>${n(o.runs)}</td>
        <td>${n(o.passed)}/${n(o.failed)}</td>
        <td>${(Number(o.pass_rate)*100).toFixed(0)}%</td>
        <td>${(Number(o.flake_score)*100).toFixed(0)}%</td>
      </tr>`).join(""),c=(e.tests||[]).map(o=>{const l=(o.points||[]).map($=>{const f=$.duration_s==null?0:Number($.duration_s);return`<span class="dot ${$.passed?"ok":"bad"}" title="${n($.run_id)} · ${n(x(f))}"></span>`}).join("");return`<tr>
        <td class="wrap">${n(o.nodeid)}</td>
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
  `}async function ot(){return`
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `}function dt(t){const e=document.getElementById("live-status"),a=document.getElementById("live-clear");a==null||a.addEventListener("click",()=>{t.innerHTML=""});const i=`${location.protocol==="https:"?"wss":"ws"}://${location.host}/live`;let r;try{r=new WebSocket(i)}catch(d){e&&(e.textContent="failed"),t.innerHTML=`<div>WebSocket error: ${n(String(d))}</div>`;return}r.onopen=()=>{e&&(e.textContent="live",e.className="badge passed")},r.onclose=()=>{e&&(e.textContent="closed",e.className="badge failed")},r.onerror=()=>{e&&(e.textContent="error",e.className="badge failed")},r.onmessage=d=>{try{const c=JSON.parse(String(d.data)),o=String(c.type??"?"),l=String(c.timestamp??""),$=c.nodeid||c.name||c.test_id||c.status||c.profile||"",f=document.createElement("div");f.innerHTML=`<span class="t">${n(l)}</span><b>${n(o)}</b> ${n($)}`,t.prepend(f)}catch{const c=document.createElement("div");c.textContent=String(d.data),t.prepend(c)}}}const U=[{id:"mock",label:"Mock demo",config:"questline.toml",profile:"mock",tests:"examples/demo-tests",live_target:!1,note:"No Unity. CI-style mock driver."},{id:"wire-editor",label:"Wire Editor",config:"examples/wire-smoke/questline.toml",profile:"editor",tests:"examples/wire-smoke",live_target:!0,note:"Unity Play + Wire on :13000. Device picker stays empty (OK)."},{id:"wire-android",label:"Wire Android",config:"examples/wire-smoke/questline.toml",profile:"android_local",tests:"examples/wire-smoke",live_target:!0,note:"Dev APK + adb. Pick a serial if more than one device."}];async function ct(){var h,m,y;await E();let t,e,a,s;try{[t,e,a,s]=await Promise.all([q(),W().catch(()=>({project_root:"",active:"",configs:[{path:"questline.toml",absolute:"questline.toml"}]})),V().catch(()=>({reporters:["console"]})),j().catch(()=>({launcher:{state:"idle"}}))])}catch(u){return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-error">
        Failed to load launcher APIs: ${n(String(u))}<br/>
        Stop the old <code>questline hud</code> process and start it again from
        <code>D:\\dev\\questline</code>.
      </div>`}if(t.read_only)return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;const i=((h=e.configs.find(u=>u.path.replace(/\\/g,"/")==="questline.toml"))==null?void 0:h.path)||((m=e.configs[0])==null?void 0:m.path)||"questline.toml",r=await L(i),d=await O(),c=(e.configs||[]).map(u=>{const g=u.path===i?"selected":"";return`<option value="${n(u.path)}" ${g}>${n(u.path)}</option>`}).join(""),o=(r.profiles||[]).map(u=>{const g=r.profiles.includes("editor")?"editor":r.profiles.includes("mock")?"mock":r.profiles[0]||"";return`<option value="${n(u)}" ${u===g?"selected":""}>${n(u)}</option>`}).join(""),l=['<option value="">(no adb pin — OK for Editor)</option>',...(d.devices||[]).map(u=>`<option value="${n(u.id)}">${n(u.id)} · ${n(u.platform)}</option>`)].join(""),$=(a.reporters||[]).map(u=>`<label class="check"><input type="checkbox" name="reporter" value="${n(u)}" ${u==="console"?"checked":""}/> ${n(u)}</label>`).join(""),f=U.map(u=>`<button type="button" class="preset" data-preset="${n(u.id)}" title="${n(u.note)}">${n(u.label)}</button>`).join(""),v=s.launcher,p=d.hint||((y=d.devices)!=null&&y.length?`${d.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire.");return`
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
      <p class="meta" id="launch-device-hint" data-testid="launch-device-hint">${n(p)}</p>
      ${d.error?`<p class="meta">adb error: ${n(d.error)}</p>`:""}
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
  `}function lt(){var $,f,v;const t=document.getElementById("launch-status"),e=document.getElementById("launch-config"),a=document.getElementById("launch-profile"),s=document.getElementById("launch-device"),i=document.getElementById("launch-tests"),r=document.getElementById("launch-live"),d=document.getElementById("launch-device-hint"),c=async()=>{if(!(!e||!a))try{const p=await L(e.value),h=p.profiles.includes("editor")?"editor":p.profiles[0]||"";a.innerHTML=p.profiles.map(m=>`<option value="${n(m)}" ${m===h?"selected":""}>${n(m)}</option>`).join("")}catch(p){t&&(t.textContent=String(p))}},o=async()=>{var p;if(s)try{const h=await O();s.innerHTML=['<option value="">(no adb pin — OK for Editor)</option>',...(h.devices||[]).map(m=>`<option value="${n(m.id)}">${n(m.id)} · ${n(m.platform)}</option>`)].join(""),d&&(d.textContent=h.hint||((p=h.devices)!=null&&p.length?`${h.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire."))}catch(h){d&&(d.textContent=String(h))}};e==null||e.addEventListener("change",()=>{c()}),($=document.getElementById("launch-refresh-devices"))==null||$.addEventListener("click",()=>{o()}),document.querySelectorAll(".preset").forEach(p=>{p.addEventListener("click",()=>{const h=p.dataset.preset||"",m=U.find(y=>y.id===h);if(m){if(e){if(!Array.from(e.options).some(u=>u.value===m.config)){const u=document.createElement("option");u.value=m.config,u.textContent=m.config,e.appendChild(u)}e.value=m.config}i&&(i.value=m.tests),r&&(r.checked=m.live_target),(async()=>(await c(),a&&(a.value=m.profile)))()}})});const l=async()=>{try{const{launcher:p}=await j();t&&(t.textContent=JSON.stringify(p,null,2))}catch(p){t&&(t.textContent=String(p))}};(f=document.getElementById("launch-start"))==null||f.addEventListener("click",()=>{(async()=>{var C;const p=(a==null?void 0:a.value)||"",h=(s==null?void 0:s.value)||"",m=document.getElementById("launch-markers").value.trim(),u=((i==null?void 0:i.value)||"").split(/\r?\n/).map(w=>w.trim()).filter(Boolean),g=Array.from(document.querySelectorAll('input[name="reporter"]:checked')).map(w=>w.value),A=(C=document.getElementById("launch-quarantine"))==null?void 0:C.checked;try{const{launcher:w}=await G({profile:p,tests:u,markers:m||void 0,device_serial:h||void 0,reporters:g.length?g:void 0,include_quarantined:!!A,config:(e==null?void 0:e.value)||void 0,live_target:!!(r!=null&&r.checked)});t&&(t.textContent=JSON.stringify(w,null,2)),location.hash="/live"}catch(w){t&&(t.textContent=String(w))}})()}),(v=document.getElementById("launch-stop"))==null||v.addEventListener("click",()=>{(async()=>{try{const{launcher:p}=await z();t&&(t.textContent=JSON.stringify(p,null,2))}catch(p){t&&(t.textContent=String(p))}})()}),l(),window.setInterval(()=>{location.hash.replace(/^#\/?/,"").startsWith("launch")&&l()},2e3)}async function ut(){if(await E(),(await q()).read_only)return`<h1>Quarantine</h1>
      <div class="empty">Read-only mode — quarantine management disabled.</div>`;const e=await X(),a=(e.entries||[]).map(s=>`<tr data-testid="quarantine-row">
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
  `}function pt(){var e,a;const t=document.getElementById("q-msg");(e=document.getElementById("q-add"))==null||e.addEventListener("click",()=>{(async()=>{try{await Y({test_id:document.getElementById("q-id").value.trim(),owner:document.getElementById("q-owner").value.trim(),reason:document.getElementById("q-reason").value.trim(),exit_criteria:document.getElementById("q-exit").value.trim(),issue:document.getElementById("q-issue").value.trim()||void 0}),location.reload()}catch(s){t&&(t.textContent=String(s))}})()}),(a=document.getElementById("q-audit"))==null||a.addEventListener("click",()=>{(async()=>{try{const s=await tt({});t&&(t.textContent=s.summary)}catch(s){t&&(t.textContent=String(s))}})()}),document.querySelectorAll(".q-remove").forEach(s=>{s.addEventListener("click",()=>{(async()=>{const i=s.dataset.id||"";try{await Z(i),location.reload()}catch(r){t&&(t.textContent=String(r))}})()})})}async function ft(){if(await E(),(await q()).read_only)return`<h1>Profiles</h1>
      <div class="empty">Read-only mode — profile editor disabled.</div>`;const{profiles:e,path:a}=await L(),s=e.map(c=>`<option value="${n(c)}">${n(c)}</option>`).join(""),i=e[0]||"";let r="{}",d="";if(i){const c=await T(i);r=JSON.stringify(c.fields,null,2),d=(c.secret_env_names||[]).map(o=>`<code>${n(o)}</code>`).join(" ")}return`
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
    <p class="meta">Secret env slots: ${d||"—"}</p>
    <textarea id="prof-fields" data-testid="prof-fields" rows="18" class="code">${n(r)}</textarea>
    <pre class="log" id="prof-msg" data-testid="prof-msg"></pre>
  `}function ht(){var i,r,d,c;const t=document.getElementById("prof-msg"),e=document.getElementById("prof-fields"),a=document.getElementById("prof-name"),s=()=>e?JSON.parse(e.value):{};(i=document.getElementById("prof-load"))==null||i.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await T(o);e&&(e.value=JSON.stringify(l.fields,null,2)),t&&(t.textContent=`loaded ${o}`)}catch(o){t&&(t.textContent=String(o))}})()}),(r=document.getElementById("prof-validate"))==null||r.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await K(o,s());t&&(t.textContent=l.ok?`OK
${JSON.stringify(l.settings_summary,null,2)}`:l.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()}),(d=document.getElementById("prof-preview"))==null||d.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await P(o,s(),!1);t&&(t.textContent=l.diff||"(no diff)")}catch(o){t&&(t.textContent=String(o))}})()}),(c=document.getElementById("prof-save"))==null||c.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await P(o,s(),!0);t&&(t.textContent=l.saved?`saved
${l.diff}`:l.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()})}function I(t,e="var(--accent)"){const a=t.map(l=>Number(l.v??0));if(!a.length)return'<span class="meta">no samples</span>';const s=Math.min(...a),i=Math.max(...a),r=Math.max(1e-9,i-s),d=320,c=64,o=a.map((l,$)=>{const f=$/Math.max(1,a.length-1)*d,v=c-(l-s)/r*(c-4)-2;return`${f.toFixed(1)},${v.toFixed(1)}`}).join(" ");return`<svg class="spark" viewBox="0 0 ${d} ${c}" width="${d}" height="${c}">
    <polyline fill="none" stroke="${e}" stroke-width="1.5" points="${o}"/>
  </svg>`}async function mt(){var i;const t=await N({}),e=t.runs.map(r=>`<option value="${n(r.id)}">${n(r.id.slice(0,8))}… · ${n(r.profile)}</option>`).join(""),a=((i=t.runs[0])==null?void 0:i.id)||"";let s='<div class="empty">Pick a run to load perf series.</div>';if(a){const r=await M(a);s=D(a,r.series,r.summary)}return`
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
  `}function D(t,e,a){const s=Object.keys(e);return s.length?s.map(i=>{var d,c;const r=a[i]||{};return`<div class="panel" data-testid="perf-metric">
        <h2>${n(i)} <span class="meta">avg ${n(((c=(d=r.avg)==null?void 0:d.toFixed)==null?void 0:c.call(d,2))??"—")} · n ${n(r.count??0)}</span></h2>
        ${I(e[i]||[])}
      </div>`}).join(""):`<div class="empty">No perf samples for ${n(t)}.</div>`}function vt(){var r,d;const t=document.getElementById("perf-series"),e=document.getElementById("perf-compare-out"),a=document.getElementById("perf-run"),s=document.getElementById("perf-a"),i=document.getElementById("perf-b");s&&i&&i.options.length>1&&(i.selectedIndex=1),(r=document.getElementById("perf-load"))==null||r.addEventListener("click",()=>{(async()=>{const c=(a==null?void 0:a.value)||"";if(!(!c||!t))try{const o=await M(c);t.innerHTML=D(c,o.series,o.summary)}catch(o){t.textContent=String(o)}})()}),(d=document.getElementById("perf-compare"))==null||d.addEventListener("click",()=>{(async()=>{const c=(s==null?void 0:s.value)||"",o=(i==null?void 0:i.value)||"";if(e)try{const l=await et(c,o),$=l.deltas.map(v=>{var p,h,m,y,u,g;return`<tr>
              <td>${n(v.metric)}</td>
              <td>${n(((m=(h=(p=v.a)==null?void 0:p.avg)==null?void 0:h.toFixed)==null?void 0:m.call(h,2))??"—")}</td>
              <td>${n(((g=(u=(y=v.b)==null?void 0:y.avg)==null?void 0:u.toFixed)==null?void 0:g.call(u,2))??"—")}</td>
              <td>${v.delta_avg==null?"—":n(v.delta_avg.toFixed(2))}</td>
            </tr>`}).join(""),f=Object.keys(l.series_a).map(v=>{const p=l.series_a[v]||[],h=l.series_b[v]||[];return`<div class="panel">
              <h2>${n(v)} overlay</h2>
              <div class="toolbar">
                <span class="meta">A</span>${I(p,"var(--accent)")}
                <span class="meta">B</span>${I(h,"var(--ok)")}
              </div>
            </div>`}).join("");e.innerHTML=`
          <div class="table-wrap">
            <table data-testid="perf-delta-table">
              <thead><tr><th>Metric</th><th>A avg</th><th>B avg</th><th>Δ avg</th></tr></thead>
              <tbody>${$||'<tr><td colspan="4">No metrics</td></tr>'}</tbody>
            </table>
          </div>
          ${f}`}catch(l){e.textContent=String(l)}})()})}const B=document.querySelector("#app");let S=!1;function R(t,e){const a=(i,r)=>`<a href="${i}" class="${t===r?"active":""}">${r}</a>`,s=S?"":`${a("#/launch","Launch")}
        ${a("#/quarantine","Quarantine")}
        ${a("#/profiles","Profiles")}`;return`
    <header class="topbar">
      <a class="brand" href="#/">Questline <span>HUD</span></a>
      <nav class="nav">
        ${a("#/","Runs")}
        ${s}
        ${a("#/perf","Perf")}
        ${a("#/trends","Trends")}
        ${a("#/live","Live")}
      </nav>
      ${S?'<span class="badge warn" title="--read-only">RO</span>':""}
    </header>
    <main class="main">${e}</main>
  `}function $t(){const e=(location.hash.replace(/^#\/?/,"")||"").split("/").filter(Boolean);return e[0]==="runs"&&e[1]&&e[2]==="tests"&&e[3]?{name:"test",params:{runId:e[1],testId:e[3]}}:e[0]==="runs"&&e[1]?{name:"run",params:{runId:e[1]}}:e[0]==="trends"?{name:"trends",params:{}}:e[0]==="live"?{name:"live",params:{}}:e[0]==="launch"?{name:"launch",params:{}}:e[0]==="quarantine"?{name:"quarantine",params:{}}:e[0]==="profiles"?{name:"profiles",params:{}}:e[0]==="perf"?{name:"perf",params:{}}:{name:"runs",params:{}}}function bt(t){return t.length?`
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
      <td>${n(x(a.duration_s))}</td>
      <td>${n(a.started_at??"")}</td>
    </tr>`).join("")}</tbody>
      </table>
    </div>`:`<div class="empty" data-testid="empty-store">
      No runs in the store yet.<br/>
      Use <a href="#/launch">Launch</a> or run a suite with the questline plugin, then refresh.
    </div>`}async function yt(){const t=new URLSearchParams(location.hash.split("?")[1]||""),e=t.get("profile")||"",a=t.get("status")||"",s=await N({profile:e||void 0,status:a||void 0});return`
    <h1>Runs</h1>
    <div class="toolbar">
      <label>profile <input id="f-profile" value="${n(e)}" placeholder="any"/></label>
      <label>status
        <select id="f-status">
          <option value="">any</option>
          ${["passed","failed","running","error"].map(i=>`<option value="${i}" ${a===i?"selected":""}>${i}</option>`).join("")}
        </select>
      </label>
      <button type="button" id="f-apply">Filter</button>
      ${S?"":'<a class="btn" href="#/launch">Launch run</a>'}
    </div>
    ${bt(s.runs)}
  `}async function F(){const t=$t();try{let e="",a="Runs";t.name==="run"?(e=await st(t.params.runId),a="Runs"):t.name==="test"?(e=await it(t.params.runId,t.params.testId),a="Runs"):t.name==="trends"?(e=await rt(),a="Trends"):t.name==="live"?(e=await ot(),a="Live"):t.name==="launch"?(e=await ct(),a="Launch"):t.name==="quarantine"?(e=await ut(),a="Quarantine"):t.name==="profiles"?(e=await ft(),a="Profiles"):t.name==="perf"?(e=await mt(),a="Perf"):(e=await yt(),a="Runs"),B.innerHTML=R(a,e),gt(t.name)}catch(e){B.innerHTML=R("Runs",`<div class="empty">Failed to load HUD: ${n(String(e))}</div>`)}}function gt(t){var e;if(t==="runs"&&((e=document.getElementById("f-apply"))==null||e.addEventListener("click",()=>{const a=document.getElementById("f-profile").value.trim(),s=document.getElementById("f-status").value,i=new URLSearchParams;a&&i.set("profile",a),s&&i.set("status",s);const r=i.toString();location.hash=r?`/?${r}`:"/"})),t==="live"){const a=document.getElementById("live-root");a&&dt(a)}t==="launch"&&lt(),t==="quarantine"&&pt(),t==="profiles"&&ht(),t==="perf"&&vt()}async function wt(){try{S=!!(await q()).read_only,S||await E()}catch{S=!1}await F()}window.addEventListener("hashchange",()=>{F()});wt();
