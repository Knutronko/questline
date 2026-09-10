(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))s(r);new MutationObserver(r=>{for(const i of r)if(i.type==="childList")for(const l of i.addedNodes)l.tagName==="LINK"&&l.rel==="modulepreload"&&s(l)}).observe(document,{childList:!0,subtree:!0});function a(r){const i={};return r.integrity&&(i.integrity=r.integrity),r.referrerPolicy&&(i.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?i.credentials="include":r.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function s(r){if(r.ep)return;r.ep=!0;const i=a(r);fetch(r.href,i)}})();let q=null;async function b(t){const e=await fetch(t),a=await e.text();if(/^\s*</.test(a)||(e.headers.get("content-type")||"").includes("text/html"))throw new Error(`${e.status} ${t}: got HTML instead of JSON. Restart questline hud (old process missing new /api routes).`);if(!e.ok)throw new Error(`${e.status} ${t}: ${a}`);try{return JSON.parse(a)}catch(r){throw new Error(`${t}: invalid JSON (${String(r)})`)}}async function I(){return q||(q=(await b("/api/csrf")).csrf_token,q)}async function x(t,e,a){const s=await I(),r=await fetch(e,{method:t,headers:{"Content-Type":"application/json","X-CSRF-Token":s},body:a===void 0?void 0:JSON.stringify(a)});if(!r.ok){const i=await r.text();throw new Error(`${r.status} ${e}: ${i}`)}if(r.status!==204)return await r.json()}function C(){return b("/api/meta")}function M(t){const e=new URLSearchParams;t.profile&&e.set("profile",t.profile),t.status&&e.set("status",t.status);const a=e.toString();return b(`/api/runs${a?`?${a}`:""}`)}function K(t){return b(`/api/runs/${encodeURIComponent(t)}`)}function V(t,e){const a=new URLSearchParams({id:e});return b(`/api/runs/${encodeURIComponent(t)}/test?${a.toString()}`)}function G(t=50){return b(`/api/trends?limit=${t}`)}function N(t){const e=t?`?config=${encodeURIComponent(t)}`:"";return b(`/api/profiles${e}`)}function X(){return b("/api/configs")}function A(){return b("/api/devices")}function D(t){return b(`/api/profiles/${encodeURIComponent(t)}`)}function z(t,e){return x("POST",`/api/profiles/${encodeURIComponent(t)}/validate`,{fields:e,apply:!1})}function O(t,e,a){return x("POST",`/api/profiles/${encodeURIComponent(t)}`,{fields:e,apply:a})}function Y(){return b("/api/reporters")}function F(){return b("/api/launcher")}function Z(t){return x("POST","/api/launcher/start",t)}function tt(){return x("POST","/api/launcher/stop")}function et(){return b("/api/quarantine")}function at(t){return x("POST","/api/quarantine",t)}function nt(t){return x("DELETE",`/api/quarantine?test_id=${encodeURIComponent(t)}`)}function st(t){return x("POST","/api/quarantine/audit",t||{})}function H(t){return b(`/api/perf/${encodeURIComponent(t)}`)}function rt(t,e){return b(`/api/perf/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(e)}`)}function it(t=50){return b(`/api/perf/correlation?limit=${t}`)}function ot(t){return`/api/artifacts/file?path=${encodeURIComponent(t)}`}function S(t){if(t==null||Number.isNaN(t))return"—";if(t<60)return`${t.toFixed(1)}s`;const e=Math.floor(t/60),a=t-e*60;return`${e}m ${a.toFixed(0)}s`}function n(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function dt(t){const e=await K(t),a=e.run,s=e.banner,r=e.tests.map(o=>`
    <tr data-testid="test-row" data-test-id="${n(o.id)}">
      <td class="wrap"><a href="#/runs/${encodeURIComponent(t)}/tests/${encodeURIComponent(o.id)}">${n(o.nodeid)}</a></td>
      <td><span class="badge ${n(o.status)}">${n(o.status)}</span></td>
      <td class="verdict-${n(o.verdict??"")}">${n(o.verdict??"—")}</td>
      <td>${n(S(o.duration_s))}</td>
      <td class="wrap">${n(o.death_step_name??"")}</td>
    </tr>`).join(""),l=(e.ai_calls||[]).map(o=>`
    <tr data-testid="ai-call-row">
      <td>${n(o.provider??"—")}</td>
      <td class="wrap">${n(o.model??"—")}</td>
      <td>${n(o.tokens_in??0)}</td>
      <td>${n(o.tokens_out??0)}</td>
      <td>${n(T(o.cost))}</td>
      <td>${n(o.outcome??"—")}</td>
      <td class="wrap">${n(o.purpose??"")}</td>
    </tr>`).join("")||'<tr><td colspan="7">No AI calls for this run.</td></tr>';return`
    <p class="meta"><a href="#/">← Runs</a> · ${n(a.id)}</p>
    <h1>Run detail</h1>
    <div class="meta">
      profile=${n(a.profile)} · driver=${n(a.driver??"—")} ·
      device=${n(a.device??"—")} · status=${n(a.status)} ·
      duration=${n(S(a.duration_s))}
    </div>
    <div class="banner" data-testid="verdict-banner">
      <div class="stat ok"><span>passed</span><b>${a.passed}</b></div>
      <div class="stat"><span>failed</span><b>${a.failed}</b></div>
      <div class="stat infra"><span>infra</span><b>${s.infra_failures}</b></div>
      <div class="stat test"><span>test</span><b>${s.test_failures}</b></div>
      <div class="stat"><span>authoring</span><b>${s.authoring_failures}</b></div>
    </div>
    <h2>AI calls</h2>
    <div class="meta">total_usd=${n(T(e.ai_cost_total))}</div>
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
        <tbody>${r||`<tr><td colspan="5">${a.status==="failed"||a.status==="error"?'No tests recorded — session setup failed before any test ran (often adb device lock or Wire connect). Open <a href="#/launch">Launch</a> Status → <code>error</code> / <code>log_tail</code>.':"No tests."}</td></tr>`}</tbody>
      </table>
    </div>
  `}function T(t){return t==null||Number.isNaN(t)?"0.000000":t.toFixed(6)}async function lt(t,e){const a=await V(t,e),s=a.test,r=a.steps.map(h=>{const f=String(h.status??"");return`<li data-testid="step-row">
        <span class="ts">${n(h.started_at??"")}</span>
        <span class="badge ${n(f)}">${n(f)}</span>
        <span>${n(h.name??"")}${h.error_message?` — ${n(h.error_message)}`:""}</span>
      </li>`}).join(""),i=(a.history||[]).map(h=>{const f=String(h.status??""),u=Number(h.duration_s??0)||1,p=Math.max(4,Math.min(28,u*4));return`<i class="${n(f)}" style="height:${p}px" title="${n(f)}"></i>`}).join(""),l=a.death_point||{},o=l.last_started_step||{},d=l.driver_health||{},c=s.verdict==="infra"?"infra":"",$=(a.artifacts||[]).map(h=>{const f=String(h.path??""),u=String(h.kind??""),p=String(h.name??f),m=ot(f);return u==="screenshot"||/\.(png|jpe?g|webp|gif)$/i.test(p)?`<div><a href="${n(m)}" target="_blank" rel="noreferrer">
          <img src="${n(m)}" alt="${n(p)}"/><div>${n(p)}</div></a></div>`:`<div><a href="${n(m)}" target="_blank" rel="noreferrer">${n(p)}</a>
        <div class="meta">${n(u)} · ${n(h.size_bytes??"")} B</div></div>`}).join("");return`
    <p class="meta">
      <a href="#/">Runs</a> /
      <a href="#/runs/${n(t)}">${n(t.slice(0,8))}…</a>
    </p>
    <h1 data-testid="test-title">${n(s.nodeid)}</h1>
    <div class="meta">
      status=<span class="badge ${n(s.status)}">${n(s.status)}</span> ·
      verdict=<span class="verdict-${n(s.verdict??"")}">${n(s.verdict??"—")}</span> ·
      duration=${n(S(s.duration_s))}
    </div>

    <div class="panel death ${c}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${n(o.name??"—")}</b>
        @ ${n(o.started_at??"")}</div>
      <div>error: ${n(s.error_type??"")} — ${n(s.error_message??"")}</div>
      <div>driver health: ${n(JSON.stringify(d||{}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${i||"<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${r||"<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${$||"<span class='meta'>none</span>"}</div>
  `}async function ct(){const[t,e]=await Promise.all([G(50),it(50)]),a=t.series||[],s=Math.max(1,...a.map(d=>Number(d.duration_s??0)||0)),r=a.map(d=>{const c=d.pass_rate==null?0:Number(d.pass_rate),$=Math.max(4,Math.round(c*100)),h=Number(d.duration_s??0);return`<div class="bar ${Number(d.failed??0)>0?"fail":""}" style="height:${$}%">
        <span>${n(d.run_id)} · ${(c*100).toFixed(0)}% · ${n(S(h))}</span>
      </div>`}).join(""),i=a.map(d=>{const c=Number(d.duration_s??0);return`<div class="bar" style="height:${Math.max(4,Math.round(c/s*100))}%">
        <span>${n(d.run_id)} · ${n(S(c))}</span>
      </div>`}).join(""),l=(t.flaky_tests||[]).map(d=>`<tr>
        <td class="wrap">${n(d.nodeid)}</td>
        <td>${n(d.runs)}</td>
        <td>${n(d.passed)}/${n(d.failed)}</td>
        <td>${(Number(d.pass_rate)*100).toFixed(0)}%</td>
        <td>${(Number(d.flake_score)*100).toFixed(0)}%</td>
      </tr>`).join(""),o=(e.tests||[]).map(d=>{const c=(d.points||[]).map($=>{const h=$.duration_s==null?0:Number($.duration_s);return`<span class="dot ${$.passed?"ok":"bad"}" title="${n($.run_id)} · ${n(S(h))}"></span>`}).join("");return`<tr>
        <td class="wrap">${n(d.nodeid)}</td>
        <td>${d.passed}/${d.failed}</td>
        <td class="corr-dots">${c}</td>
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
  `}async function ut(){return`
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `}function pt(t){const e=document.getElementById("live-status"),a=document.getElementById("live-clear");a==null||a.addEventListener("click",()=>{t.innerHTML=""});const r=`${location.protocol==="https:"?"wss":"ws"}://${location.host}/live`;let i;try{i=new WebSocket(r)}catch(l){e&&(e.textContent="failed"),t.innerHTML=`<div>WebSocket error: ${n(String(l))}</div>`;return}i.onopen=()=>{e&&(e.textContent="live",e.className="badge passed")},i.onclose=()=>{e&&(e.textContent="closed",e.className="badge failed")},i.onerror=()=>{e&&(e.textContent="error",e.className="badge failed")},i.onmessage=l=>{try{const o=JSON.parse(String(l.data)),d=String(o.type??"?"),c=String(o.timestamp??""),$=o.nodeid||o.name||o.test_id||o.status||o.profile||"",h=document.createElement("div");h.innerHTML=`<span class="t">${n(c)}</span><b>${n(d)}</b> ${n($)}`,t.prepend(h)}catch{const o=document.createElement("div");o.textContent=String(l.data),t.prepend(o)}}}const J=[{id:"mock",label:"Mock demo",config:"questline.toml",profile:"mock",tests:"examples/demo-tests",live_target:!1,note:"No Unity. CI-style mock driver."},{id:"wire-editor",label:"Wire Editor",config:"examples/wire-smoke/questline.toml",profile:"editor",tests:"examples/wire-smoke",live_target:!0,note:"Unity Play + Wire on :13000. Device picker stays empty (OK)."},{id:"wire-android",label:"Wire Android",config:"examples/wire-smoke/questline.toml",profile:"android_local",tests:"examples/wire-smoke",live_target:!0,note:"Dev APK + adb. Pick a serial if more than one device."}];async function ft(){var y,g,w;await I();let t,e,a,s;try{[t,e,a,s]=await Promise.all([C(),X().catch(()=>({project_root:"",active:"",configs:[{path:"questline.toml",absolute:"questline.toml"}]})),Y().catch(()=>({reporters:["console"]})),F().catch(()=>({launcher:{state:"idle"}}))])}catch(v){return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-error">
        Failed to load launcher APIs: ${n(String(v))}<br/>
        Stop the old <code>questline hud</code> process and start it again from
        <code>D:\\dev\\questline</code>.
      </div>`}if(t.read_only)return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;const r=((y=e.configs.find(v=>v.path.replace(/\\/g,"/")==="questline.toml"))==null?void 0:y.path)||((g=e.configs[0])==null?void 0:g.path)||"questline.toml",i=await N(r),l=await A(),o=(e.configs||[]).map(v=>{const E=v.path===r?"selected":"";return`<option value="${n(v.path)}" ${E}>${n(v.path)}</option>`}).join(""),d=(i.profiles||[]).map(v=>{const E=i.profiles.includes("editor")?"editor":i.profiles.includes("mock")?"mock":i.profiles[0]||"";return`<option value="${n(v)}" ${v===E?"selected":""}>${n(v)}</option>`}).join(""),c=['<option value="">(no adb pin — OK for Editor)</option>',...(l.devices||[]).map(v=>`<option value="${n(v.id)}">${n(v.id)} · ${n(v.platform)}</option>`)].join(""),$=(a.reporters||[]).map(v=>`<label class="check"><input type="checkbox" name="reporter" value="${n(v)}" ${v==="console"?"checked":""}/> ${n(v)}</label>`).join(""),h=J.map(v=>`<button type="button" class="preset" data-preset="${n(v.id)}" title="${n(v.note)}">${n(v.label)}</button>`).join(""),f=s.launcher,u=["starting","running","stopping"].includes(f.state||""),p=l.hint||((w=l.devices)!=null&&w.length?`${l.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire.");return`
    <h1>Run launcher</h1>
    ${u?`<div class="empty" data-testid="launch-busy">
        A managed run is <strong>${n(f.state||"")}</strong>
        (job <code>${n(f.job_id||"")}</code>, profile
        <code>${n(f.profile||"")}</code>).
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
      <p class="meta" id="launch-device-hint" data-testid="launch-device-hint">${n(p)}</p>
      ${l.error?`<p class="meta">adb error: ${n(l.error)}</p>`:""}
      <label class="block">markers <input id="launch-markers" placeholder="optional -m expression" data-testid="launch-markers"/></label>
      <label class="block">tests (one path/nodeid per line)
        <textarea id="launch-tests" rows="4" data-testid="launch-tests" placeholder="examples/wire-smoke">examples/demo-tests</textarea>
      </label>
      <div class="toolbar wrap">${$||"<span class='meta'>no reporters</span>"}</div>
      <label class="check"><input type="checkbox" id="launch-quarantine"/> include quarantined</label>
      <label class="check"><input type="checkbox" id="launch-live" data-testid="launch-live"/> QUESTLINE_LIVE_TARGET=1 (required for wire-smoke)</label>
      <div class="toolbar">
        <button type="button" id="launch-start" data-testid="launch-start" ${u?"disabled":""}>Launch</button>
        <button type="button" id="launch-stop" data-testid="launch-stop" ${u?"":"disabled"}>Stop</button>
        ${u?'<a class="button" href="#/live" data-testid="launch-open-live">Open Live</a>':""}
      </div>
      <p class="meta">Active project: <code>${n(e.project_root)}</code></p>
    </div>
    <h2>Status</h2>
    <pre class="log" id="launch-status" data-testid="launch-status">${n(JSON.stringify(f,null,2))}</pre>
  `}function ht(){var $,h,f;const t=document.getElementById("launch-status"),e=document.getElementById("launch-config"),a=document.getElementById("launch-profile"),s=document.getElementById("launch-device"),r=document.getElementById("launch-tests"),i=document.getElementById("launch-live"),l=document.getElementById("launch-device-hint"),o=async()=>{if(!(!e||!a))try{const u=await N(e.value),p=u.profiles.includes("editor")?"editor":u.profiles[0]||"";a.innerHTML=u.profiles.map(m=>`<option value="${n(m)}" ${m===p?"selected":""}>${n(m)}</option>`).join("")}catch(u){t&&(t.textContent=String(u))}},d=async()=>{var u;if(s)try{const p=await A();s.innerHTML=['<option value="">(no adb pin — OK for Editor)</option>',...(p.devices||[]).map(m=>`<option value="${n(m.id)}">${n(m.id)} · ${n(m.platform)}</option>`)].join(""),l&&(l.textContent=p.hint||((u=p.devices)!=null&&u.length?`${p.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire."))}catch(p){l&&(l.textContent=String(p))}};e==null||e.addEventListener("change",()=>{o()}),($=document.getElementById("launch-refresh-devices"))==null||$.addEventListener("click",()=>{d()}),document.querySelectorAll(".preset").forEach(u=>{u.addEventListener("click",()=>{const p=u.dataset.preset||"",m=J.find(y=>y.id===p);if(m){if(e){if(!Array.from(e.options).some(g=>g.value===m.config)){const g=document.createElement("option");g.value=m.config,g.textContent=m.config,e.appendChild(g)}e.value=m.config}r&&(r.value=m.tests),i&&(i.checked=m.live_target),(async()=>(await o(),a&&(a.value=m.profile)))()}})});const c=async()=>{try{const{launcher:u}=await F();t&&(t.textContent=JSON.stringify(u,null,2));const p=["starting","running","stopping"].includes(u.state||""),m=document.getElementById("launch-start"),y=document.getElementById("launch-stop");m&&(m.disabled=p),y&&(y.disabled=!p)}catch(u){t&&(t.textContent=String(u))}};(h=document.getElementById("launch-start"))==null||h.addEventListener("click",()=>{(async()=>{var E;const u=(a==null?void 0:a.value)||"",p=(s==null?void 0:s.value)||"",m=document.getElementById("launch-markers").value.trim(),g=((r==null?void 0:r.value)||"").split(/\r?\n/).map(k=>k.trim()).filter(Boolean),w=Array.from(document.querySelectorAll('input[name="reporter"]:checked')).map(k=>k.value),v=(E=document.getElementById("launch-quarantine"))==null?void 0:E.checked;try{const{launcher:k}=await Z({profile:u,tests:g,markers:m||void 0,device_serial:p||void 0,reporters:w.length?w:void 0,include_quarantined:!!v,config:(e==null?void 0:e.value)||void 0,live_target:!!(i!=null&&i.checked)});t&&(t.textContent=JSON.stringify(k,null,2)),location.hash="/live"}catch(k){const B=String(k);t&&(t.textContent=B),/\b409\b/.test(B)&&/already/i.test(B)&&(location.hash="/live")}})()}),(f=document.getElementById("launch-stop"))==null||f.addEventListener("click",()=>{(async()=>{try{const{launcher:u}=await tt();t&&(t.textContent=JSON.stringify(u,null,2))}catch(u){t&&(t.textContent=String(u))}})()}),c(),window.setInterval(()=>{location.hash.replace(/^#\/?/,"").startsWith("launch")&&c()},2e3)}async function mt(){if(await I(),(await C()).read_only)return`<h1>Quarantine</h1>
      <div class="empty">Read-only mode — quarantine management disabled.</div>`;const e=await et(),a=(e.entries||[]).map(s=>`<tr data-testid="quarantine-row">
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
  `}function vt(){var e,a;const t=document.getElementById("q-msg");(e=document.getElementById("q-add"))==null||e.addEventListener("click",()=>{(async()=>{try{await at({test_id:document.getElementById("q-id").value.trim(),owner:document.getElementById("q-owner").value.trim(),reason:document.getElementById("q-reason").value.trim(),exit_criteria:document.getElementById("q-exit").value.trim(),issue:document.getElementById("q-issue").value.trim()||void 0}),location.reload()}catch(s){t&&(t.textContent=String(s))}})()}),(a=document.getElementById("q-audit"))==null||a.addEventListener("click",()=>{(async()=>{try{const s=await st({});t&&(t.textContent=s.summary)}catch(s){t&&(t.textContent=String(s))}})()}),document.querySelectorAll(".q-remove").forEach(s=>{s.addEventListener("click",()=>{(async()=>{const r=s.dataset.id||"";try{await nt(r),location.reload()}catch(i){t&&(t.textContent=String(i))}})()})})}async function $t(){if(await I(),(await C()).read_only)return`<h1>Profiles</h1>
      <div class="empty">Read-only mode — profile editor disabled.</div>`;const{profiles:e,path:a}=await N(),s=e.map(o=>`<option value="${n(o)}">${n(o)}</option>`).join(""),r=e[0]||"";let i="{}",l="";if(r){const o=await D(r);i=JSON.stringify(o.fields,null,2),l=(o.secret_env_names||[]).map(d=>`<code>${n(d)}</code>`).join(" ")}return`
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
    <p class="meta">Secret env slots: ${l||"—"}</p>
    <textarea id="prof-fields" data-testid="prof-fields" rows="18" class="code">${n(i)}</textarea>
    <pre class="log" id="prof-msg" data-testid="prof-msg"></pre>
  `}function bt(){var r,i,l,o;const t=document.getElementById("prof-msg"),e=document.getElementById("prof-fields"),a=document.getElementById("prof-name"),s=()=>e?JSON.parse(e.value):{};(r=document.getElementById("prof-load"))==null||r.addEventListener("click",()=>{(async()=>{try{const d=(a==null?void 0:a.value)||"",c=await D(d);e&&(e.value=JSON.stringify(c.fields,null,2)),t&&(t.textContent=`loaded ${d}`)}catch(d){t&&(t.textContent=String(d))}})()}),(i=document.getElementById("prof-validate"))==null||i.addEventListener("click",()=>{(async()=>{try{const d=(a==null?void 0:a.value)||"",c=await z(d,s());t&&(t.textContent=c.ok?`OK
${JSON.stringify(c.settings_summary,null,2)}`:c.errors.join(`
`))}catch(d){t&&(t.textContent=String(d))}})()}),(l=document.getElementById("prof-preview"))==null||l.addEventListener("click",()=>{(async()=>{try{const d=(a==null?void 0:a.value)||"",c=await O(d,s(),!1);t&&(t.textContent=c.diff||"(no diff)")}catch(d){t&&(t.textContent=String(d))}})()}),(o=document.getElementById("prof-save"))==null||o.addEventListener("click",()=>{(async()=>{try{const d=(a==null?void 0:a.value)||"",c=await O(d,s(),!0);t&&(t.textContent=c.saved?`saved
${c.diff}`:c.errors.join(`
`))}catch(d){t&&(t.textContent=String(d))}})()})}function R(t,e="var(--accent)"){const a=t.map(c=>Number(c.v??0));if(!a.length)return'<span class="meta">no samples</span>';const s=Math.min(...a),r=Math.max(...a),i=Math.max(1e-9,r-s),l=320,o=64,d=a.map((c,$)=>{const h=$/Math.max(1,a.length-1)*l,f=o-(c-s)/i*(o-4)-2;return`${h.toFixed(1)},${f.toFixed(1)}`}).join(" ");return`<svg class="spark" viewBox="0 0 ${l} ${o}" width="${l}" height="${o}">
    <polyline fill="none" stroke="${e}" stroke-width="1.5" points="${d}"/>
  </svg>`}async function gt(){var r;const t=await M({}),e=t.runs.map(i=>`<option value="${n(i.id)}">${n(i.id.slice(0,8))}… · ${n(i.profile)}</option>`).join(""),a=((r=t.runs[0])==null?void 0:r.id)||"";let s='<div class="empty">Pick a run to load perf series.</div>';if(a){const i=await H(a);s=Q(a,i.series,i.summary)}return`
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
  `}function Q(t,e,a){const s=Object.keys(e);return s.length?s.map(r=>{var l,o;const i=a[r]||{};return`<div class="panel" data-testid="perf-metric">
        <h2>${n(r)} <span class="meta">avg ${n(((o=(l=i.avg)==null?void 0:l.toFixed)==null?void 0:o.call(l,2))??"—")} · n ${n(i.count??0)}</span></h2>
        ${R(e[r]||[])}
      </div>`}).join(""):`<div class="empty">No perf samples for ${n(t)}.</div>`}function yt(){var i,l;const t=document.getElementById("perf-series"),e=document.getElementById("perf-compare-out"),a=document.getElementById("perf-run"),s=document.getElementById("perf-a"),r=document.getElementById("perf-b");s&&r&&r.options.length>1&&(r.selectedIndex=1),(i=document.getElementById("perf-load"))==null||i.addEventListener("click",()=>{(async()=>{const o=(a==null?void 0:a.value)||"";if(!(!o||!t))try{const d=await H(o);t.innerHTML=Q(o,d.series,d.summary)}catch(d){t.textContent=String(d)}})()}),(l=document.getElementById("perf-compare"))==null||l.addEventListener("click",()=>{(async()=>{const o=(s==null?void 0:s.value)||"",d=(r==null?void 0:r.value)||"";if(e)try{const c=await rt(o,d),$=c.deltas.map(f=>{var u,p,m,y,g,w;return`<tr>
              <td>${n(f.metric)}</td>
              <td>${n(((m=(p=(u=f.a)==null?void 0:u.avg)==null?void 0:p.toFixed)==null?void 0:m.call(p,2))??"—")}</td>
              <td>${n(((w=(g=(y=f.b)==null?void 0:y.avg)==null?void 0:g.toFixed)==null?void 0:w.call(g,2))??"—")}</td>
              <td>${f.delta_avg==null?"—":n(f.delta_avg.toFixed(2))}</td>
            </tr>`}).join(""),h=Object.keys(c.series_a).map(f=>{const u=c.series_a[f]||[],p=c.series_b[f]||[];return`<div class="panel">
              <h2>${n(f)} overlay</h2>
              <div class="toolbar">
                <span class="meta">A</span>${R(u,"var(--accent)")}
                <span class="meta">B</span>${R(p,"var(--ok)")}
              </div>
            </div>`}).join("");e.innerHTML=`
          <div class="table-wrap">
            <table data-testid="perf-delta-table">
              <thead><tr><th>Metric</th><th>A avg</th><th>B avg</th><th>Δ avg</th></tr></thead>
              <tbody>${$||'<tr><td colspan="4">No metrics</td></tr>'}</tbody>
            </table>
          </div>
          ${h}`}catch(c){e.textContent=String(c)}})()})}const j=document.querySelector("#app");let _=!1,L=!1,P=!1;function U(t,e){const a=(o,d)=>`<a href="${o}" class="${t===d?"active":""}">${d}</a>`,s=_?"":`${a("#/launch","Launch")}
        ${a("#/quarantine","Quarantine")}
        ${a("#/profiles","Profiles")}`,r=[_?'<span class="badge warn" title="--read-only">RO</span>':"",L?'<span class="badge warn" title="Playwright smoke fixture — not real runs">SMOKE</span>':"",P?'<span class="badge warn" title="Restart questline hud">STALE API</span>':""].filter(Boolean).join(" "),i=L?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)">
        <strong>SMOKE FIXTURE SERVER</strong> — fake launcher + seeded runs.
        For real Wire/mock runs stop this process and use
        <code>uv run questline hud --open</code> (port 8741).
      </div>`:"",l=P?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)" data-testid="stale-api">
        <strong>STALE HUD PROCESS</strong> — SPA is newer than the Python API
        (missing <code>/api/runs/…/test?id=</code>). Stop the old
        <code>questline hud</code> and run <code>uv run questline hud --open</code>
        again from the repo root, then hard-refresh.
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
    <main class="main">${i}${l}${e}</main>
  `}function wt(){const e=(location.hash.replace(/^#\/?/,"")||"").split("/").filter(Boolean);if(e[0]==="runs"&&e[1]&&e[2]==="tests"&&e.length>=4){const a=e.slice(3).join("/");let s=a;try{s=decodeURIComponent(a)}catch{}return{name:"test",params:{runId:e[1],testId:s}}}return e[0]==="runs"&&e[1]?{name:"run",params:{runId:e[1]}}:e[0]==="trends"?{name:"trends",params:{}}:e[0]==="live"?{name:"live",params:{}}:e[0]==="launch"?{name:"launch",params:{}}:e[0]==="quarantine"?{name:"quarantine",params:{}}:e[0]==="profiles"?{name:"profiles",params:{}}:e[0]==="perf"?{name:"perf",params:{}}:{name:"runs",params:{}}}function kt(t){return t.length?`
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
      <td>${n(S(a.duration_s))}</td>
      <td>${n(a.started_at??"")}</td>
    </tr>`).join("")}</tbody>
      </table>
    </div>`:`<div class="empty" data-testid="empty-store">
      No runs in the store yet.<br/>
      Use <a href="#/launch">Launch</a> or run a suite with the questline plugin, then refresh.
    </div>`}async function St(){const t=new URLSearchParams(location.hash.split("?")[1]||""),e=t.get("profile")||"",a=t.get("status")||"",s=await M({profile:e||void 0,status:a||void 0});return`
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
      ${_?"":'<a class="btn" href="#/launch">Launch run</a>'}
    </div>
    ${kt(s.runs)}
  `}async function W(){const t=wt();try{let e="",a="Runs";t.name==="run"?(e=await dt(t.params.runId),a="Runs"):t.name==="test"?(e=await lt(t.params.runId,t.params.testId),a="Runs"):t.name==="trends"?(e=await ct(),a="Trends"):t.name==="live"?(e=await ut(),a="Live"):t.name==="launch"?(e=await ft(),a="Launch"):t.name==="quarantine"?(e=await mt(),a="Quarantine"):t.name==="profiles"?(e=await $t(),a="Profiles"):t.name==="perf"?(e=await gt(),a="Perf"):(e=await St(),a="Runs"),j.innerHTML=U(a,e),xt(t.name)}catch(e){j.innerHTML=U("Runs",`<div class="empty">Failed to load HUD: ${n(String(e))}</div>`)}}function xt(t){var e;if(t==="runs"&&((e=document.getElementById("f-apply"))==null||e.addEventListener("click",()=>{const a=document.getElementById("f-profile").value.trim(),s=document.getElementById("f-status").value,r=new URLSearchParams;a&&r.set("profile",a),s&&r.set("status",s);const i=r.toString();location.hash=i?`/?${i}`:"/"})),t==="live"){const a=document.getElementById("live-root");a&&pt(a)}t==="launch"&&ht(),t==="quarantine"&&vt(),t==="profiles"&&bt(),t==="perf"&&yt()}async function Et(){var t;try{const e=await C();_=!!e.read_only,L=!!e.smoke,P=!((t=e.api)!=null&&t.test_by_query),_||await I()}catch{_=!1,L=!1,P=!0}await W()}window.addEventListener("hashchange",()=>{W()});Et();
