(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))s(r);new MutationObserver(r=>{for(const i of r)if(i.type==="childList")for(const d of i.addedNodes)d.tagName==="LINK"&&d.rel==="modulepreload"&&s(d)}).observe(document,{childList:!0,subtree:!0});function a(r){const i={};return r.integrity&&(i.integrity=r.integrity),r.referrerPolicy&&(i.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?i.credentials="include":r.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function s(r){if(r.ep)return;r.ep=!0;const i=a(r);fetch(r.href,i)}})();let I=null;async function $(t){const e=await fetch(t),a=await e.text();if(/^\s*</.test(a)||(e.headers.get("content-type")||"").includes("text/html"))throw new Error(`${e.status} ${t}: got HTML instead of JSON. Restart questline hud (old process missing new /api routes).`);if(!e.ok)throw new Error(`${e.status} ${t}: ${a}`);try{return JSON.parse(a)}catch(r){throw new Error(`${t}: invalid JSON (${String(r)})`)}}async function q(){return I||(I=(await $("/api/csrf")).csrf_token,I)}async function E(t,e,a){const s=await q(),r=await fetch(e,{method:t,headers:{"Content-Type":"application/json","X-CSRF-Token":s},body:a===void 0?void 0:JSON.stringify(a)});if(!r.ok){const i=await r.text();throw new Error(`${r.status} ${e}: ${i}`)}if(r.status!==204)return await r.json()}function B(){return $("/api/meta")}function U(t){const e=new URLSearchParams;t.profile&&e.set("profile",t.profile),t.status&&e.set("status",t.status);const a=e.toString();return $(`/api/runs${a?`?${a}`:""}`)}function W(t){return $(`/api/runs/${encodeURIComponent(t)}`)}function K(t,e){const a=new URLSearchParams({id:e});return $(`/api/runs/${encodeURIComponent(t)}/test?${a.toString()}`)}function V(t=50){return $(`/api/trends?limit=${t}`)}function N(t){const e=t?`?config=${encodeURIComponent(t)}`:"";return $(`/api/profiles${e}`)}function G(){return $("/api/configs")}function M(){return $("/api/devices")}function A(t){return $(`/api/profiles/${encodeURIComponent(t)}`)}function X(t,e){return E("POST",`/api/profiles/${encodeURIComponent(t)}/validate`,{fields:e,apply:!1})}function O(t,e,a){return E("POST",`/api/profiles/${encodeURIComponent(t)}`,{fields:e,apply:a})}function z(){return $("/api/reporters")}function D(){return $("/api/launcher")}function Y(t){return E("POST","/api/launcher/start",t)}function Z(){return E("POST","/api/launcher/stop")}function tt(){return $("/api/quarantine")}function et(t){return E("POST","/api/quarantine",t)}function at(t){return E("DELETE",`/api/quarantine?test_id=${encodeURIComponent(t)}`)}function nt(t){return E("POST","/api/quarantine/audit",t||{})}function F(t){return $(`/api/perf/${encodeURIComponent(t)}`)}function st(t,e){return $(`/api/perf/compare?a=${encodeURIComponent(t)}&b=${encodeURIComponent(e)}`)}function rt(t=50){return $(`/api/perf/correlation?limit=${t}`)}function it(t){return`/api/artifacts/file?path=${encodeURIComponent(t)}`}function k(t){if(t==null||Number.isNaN(t))return"—";if(t<60)return`${t.toFixed(1)}s`;const e=Math.floor(t/60),a=t-e*60;return`${e}m ${a.toFixed(0)}s`}function n(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}async function ot(t){const e=await W(t),a=e.run,s=e.banner,r=e.tests.map(i=>`
    <tr data-testid="test-row" data-test-id="${n(i.id)}">
      <td class="wrap"><a href="#/runs/${encodeURIComponent(t)}/tests/${encodeURIComponent(i.id)}">${n(i.nodeid)}</a></td>
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
        <tbody>${r||`<tr><td colspan="5">${a.status==="failed"||a.status==="error"?'No tests recorded — session setup failed before any test ran (often adb device lock or Wire connect). Open <a href="#/launch">Launch</a> Status → <code>error</code> / <code>log_tail</code>.':"No tests."}</td></tr>`}</tbody>
      </table>
    </div>
  `}async function dt(t,e){const a=await K(t,e),s=a.test,r=a.steps.map(h=>{const f=String(h.status??"");return`<li data-testid="step-row">
        <span class="ts">${n(h.started_at??"")}</span>
        <span class="badge ${n(f)}">${n(f)}</span>
        <span>${n(h.name??"")}${h.error_message?` — ${n(h.error_message)}`:""}</span>
      </li>`}).join(""),i=(a.history||[]).map(h=>{const f=String(h.status??""),u=Number(h.duration_s??0)||1,p=Math.max(4,Math.min(28,u*4));return`<i class="${n(f)}" style="height:${p}px" title="${n(f)}"></i>`}).join(""),d=a.death_point||{},c=d.last_started_step||{},o=d.driver_health||{},l=s.verdict==="infra"?"infra":"",b=(a.artifacts||[]).map(h=>{const f=String(h.path??""),u=String(h.kind??""),p=String(h.name??f),m=it(f);return u==="screenshot"||/\.(png|jpe?g|webp|gif)$/i.test(p)?`<div><a href="${n(m)}" target="_blank" rel="noreferrer">
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
      duration=${n(k(s.duration_s))}
    </div>

    <div class="panel death ${l}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${n(c.name??"—")}</b>
        @ ${n(c.started_at??"")}</div>
      <div>error: ${n(s.error_type??"")} — ${n(s.error_message??"")}</div>
      <div>driver health: ${n(JSON.stringify(o||{}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${i||"<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${r||"<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${b||"<span class='meta'>none</span>"}</div>
  `}async function ct(){const[t,e]=await Promise.all([V(50),rt(50)]),a=t.series||[],s=Math.max(1,...a.map(o=>Number(o.duration_s??0)||0)),r=a.map(o=>{const l=o.pass_rate==null?0:Number(o.pass_rate),b=Math.max(4,Math.round(l*100)),h=Number(o.duration_s??0);return`<div class="bar ${Number(o.failed??0)>0?"fail":""}" style="height:${b}%">
        <span>${n(o.run_id)} · ${(l*100).toFixed(0)}% · ${n(k(h))}</span>
      </div>`}).join(""),i=a.map(o=>{const l=Number(o.duration_s??0);return`<div class="bar" style="height:${Math.max(4,Math.round(l/s*100))}%">
        <span>${n(o.run_id)} · ${n(k(l))}</span>
      </div>`}).join(""),d=(t.flaky_tests||[]).map(o=>`<tr>
        <td class="wrap">${n(o.nodeid)}</td>
        <td>${n(o.runs)}</td>
        <td>${n(o.passed)}/${n(o.failed)}</td>
        <td>${(Number(o.pass_rate)*100).toFixed(0)}%</td>
        <td>${(Number(o.flake_score)*100).toFixed(0)}%</td>
      </tr>`).join(""),c=(e.tests||[]).map(o=>{const l=(o.points||[]).map(b=>{const h=b.duration_s==null?0:Number(b.duration_s);return`<span class="dot ${b.passed?"ok":"bad"}" title="${n(b.run_id)} · ${n(k(h))}"></span>`}).join("");return`<tr>
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
  `}async function lt(){return`
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `}function ut(t){const e=document.getElementById("live-status"),a=document.getElementById("live-clear");a==null||a.addEventListener("click",()=>{t.innerHTML=""});const r=`${location.protocol==="https:"?"wss":"ws"}://${location.host}/live`;let i;try{i=new WebSocket(r)}catch(d){e&&(e.textContent="failed"),t.innerHTML=`<div>WebSocket error: ${n(String(d))}</div>`;return}i.onopen=()=>{e&&(e.textContent="live",e.className="badge passed")},i.onclose=()=>{e&&(e.textContent="closed",e.className="badge failed")},i.onerror=()=>{e&&(e.textContent="error",e.className="badge failed")},i.onmessage=d=>{try{const c=JSON.parse(String(d.data)),o=String(c.type??"?"),l=String(c.timestamp??""),b=c.nodeid||c.name||c.test_id||c.status||c.profile||"",h=document.createElement("div");h.innerHTML=`<span class="t">${n(l)}</span><b>${n(o)}</b> ${n(b)}`,t.prepend(h)}catch{const c=document.createElement("div");c.textContent=String(d.data),t.prepend(c)}}}const H=[{id:"mock",label:"Mock demo",config:"questline.toml",profile:"mock",tests:"examples/demo-tests",live_target:!1,note:"No Unity. CI-style mock driver."},{id:"wire-editor",label:"Wire Editor",config:"examples/wire-smoke/questline.toml",profile:"editor",tests:"examples/wire-smoke",live_target:!0,note:"Unity Play + Wire on :13000. Device picker stays empty (OK)."},{id:"wire-android",label:"Wire Android",config:"examples/wire-smoke/questline.toml",profile:"android_local",tests:"examples/wire-smoke",live_target:!0,note:"Dev APK + adb. Pick a serial if more than one device."}];async function pt(){var y,g,w;await q();let t,e,a,s;try{[t,e,a,s]=await Promise.all([B(),G().catch(()=>({project_root:"",active:"",configs:[{path:"questline.toml",absolute:"questline.toml"}]})),z().catch(()=>({reporters:["console"]})),D().catch(()=>({launcher:{state:"idle"}}))])}catch(v){return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-error">
        Failed to load launcher APIs: ${n(String(v))}<br/>
        Stop the old <code>questline hud</code> process and start it again from
        <code>D:\\dev\\questline</code>.
      </div>`}if(t.read_only)return`<h1>Launch</h1>
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;const r=((y=e.configs.find(v=>v.path.replace(/\\/g,"/")==="questline.toml"))==null?void 0:y.path)||((g=e.configs[0])==null?void 0:g.path)||"questline.toml",i=await N(r),d=await M(),c=(e.configs||[]).map(v=>{const x=v.path===r?"selected":"";return`<option value="${n(v.path)}" ${x}>${n(v.path)}</option>`}).join(""),o=(i.profiles||[]).map(v=>{const x=i.profiles.includes("editor")?"editor":i.profiles.includes("mock")?"mock":i.profiles[0]||"";return`<option value="${n(v)}" ${v===x?"selected":""}>${n(v)}</option>`}).join(""),l=['<option value="">(no adb pin — OK for Editor)</option>',...(d.devices||[]).map(v=>`<option value="${n(v.id)}">${n(v.id)} · ${n(v.platform)}</option>`)].join(""),b=(a.reporters||[]).map(v=>`<label class="check"><input type="checkbox" name="reporter" value="${n(v)}" ${v==="console"?"checked":""}/> ${n(v)}</label>`).join(""),h=H.map(v=>`<button type="button" class="preset" data-preset="${n(v.id)}" title="${n(v.note)}">${n(v.label)}</button>`).join(""),f=s.launcher,u=["starting","running","stopping"].includes(f.state||""),p=d.hint||((w=d.devices)!=null&&w.length?`${d.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire.");return`
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
      <div class="toolbar wrap">${b||"<span class='meta'>no reporters</span>"}</div>
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
  `}function ft(){var b,h,f;const t=document.getElementById("launch-status"),e=document.getElementById("launch-config"),a=document.getElementById("launch-profile"),s=document.getElementById("launch-device"),r=document.getElementById("launch-tests"),i=document.getElementById("launch-live"),d=document.getElementById("launch-device-hint"),c=async()=>{if(!(!e||!a))try{const u=await N(e.value),p=u.profiles.includes("editor")?"editor":u.profiles[0]||"";a.innerHTML=u.profiles.map(m=>`<option value="${n(m)}" ${m===p?"selected":""}>${n(m)}</option>`).join("")}catch(u){t&&(t.textContent=String(u))}},o=async()=>{var u;if(s)try{const p=await M();s.innerHTML=['<option value="">(no adb pin — OK for Editor)</option>',...(p.devices||[]).map(m=>`<option value="${n(m.id)}">${n(m.id)} · ${n(m.platform)}</option>`)].join(""),d&&(d.textContent=p.hint||((u=p.devices)!=null&&u.length?`${p.devices.length} adb device(s)`:"No adb devices — normal for Unity Editor Wire."))}catch(p){d&&(d.textContent=String(p))}};e==null||e.addEventListener("change",()=>{c()}),(b=document.getElementById("launch-refresh-devices"))==null||b.addEventListener("click",()=>{o()}),document.querySelectorAll(".preset").forEach(u=>{u.addEventListener("click",()=>{const p=u.dataset.preset||"",m=H.find(y=>y.id===p);if(m){if(e){if(!Array.from(e.options).some(g=>g.value===m.config)){const g=document.createElement("option");g.value=m.config,g.textContent=m.config,e.appendChild(g)}e.value=m.config}r&&(r.value=m.tests),i&&(i.checked=m.live_target),(async()=>(await c(),a&&(a.value=m.profile)))()}})});const l=async()=>{try{const{launcher:u}=await D();t&&(t.textContent=JSON.stringify(u,null,2));const p=["starting","running","stopping"].includes(u.state||""),m=document.getElementById("launch-start"),y=document.getElementById("launch-stop");m&&(m.disabled=p),y&&(y.disabled=!p)}catch(u){t&&(t.textContent=String(u))}};(h=document.getElementById("launch-start"))==null||h.addEventListener("click",()=>{(async()=>{var x;const u=(a==null?void 0:a.value)||"",p=(s==null?void 0:s.value)||"",m=document.getElementById("launch-markers").value.trim(),g=((r==null?void 0:r.value)||"").split(/\r?\n/).map(S=>S.trim()).filter(Boolean),w=Array.from(document.querySelectorAll('input[name="reporter"]:checked')).map(S=>S.value),v=(x=document.getElementById("launch-quarantine"))==null?void 0:x.checked;try{const{launcher:S}=await Y({profile:u,tests:g,markers:m||void 0,device_serial:p||void 0,reporters:w.length?w:void 0,include_quarantined:!!v,config:(e==null?void 0:e.value)||void 0,live_target:!!(i!=null&&i.checked)});t&&(t.textContent=JSON.stringify(S,null,2)),location.hash="/live"}catch(S){const C=String(S);t&&(t.textContent=C),/\b409\b/.test(C)&&/already/i.test(C)&&(location.hash="/live")}})()}),(f=document.getElementById("launch-stop"))==null||f.addEventListener("click",()=>{(async()=>{try{const{launcher:u}=await Z();t&&(t.textContent=JSON.stringify(u,null,2))}catch(u){t&&(t.textContent=String(u))}})()}),l(),window.setInterval(()=>{location.hash.replace(/^#\/?/,"").startsWith("launch")&&l()},2e3)}async function ht(){if(await q(),(await B()).read_only)return`<h1>Quarantine</h1>
      <div class="empty">Read-only mode — quarantine management disabled.</div>`;const e=await tt(),a=(e.entries||[]).map(s=>`<tr data-testid="quarantine-row">
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
  `}function mt(){var e,a;const t=document.getElementById("q-msg");(e=document.getElementById("q-add"))==null||e.addEventListener("click",()=>{(async()=>{try{await et({test_id:document.getElementById("q-id").value.trim(),owner:document.getElementById("q-owner").value.trim(),reason:document.getElementById("q-reason").value.trim(),exit_criteria:document.getElementById("q-exit").value.trim(),issue:document.getElementById("q-issue").value.trim()||void 0}),location.reload()}catch(s){t&&(t.textContent=String(s))}})()}),(a=document.getElementById("q-audit"))==null||a.addEventListener("click",()=>{(async()=>{try{const s=await nt({});t&&(t.textContent=s.summary)}catch(s){t&&(t.textContent=String(s))}})()}),document.querySelectorAll(".q-remove").forEach(s=>{s.addEventListener("click",()=>{(async()=>{const r=s.dataset.id||"";try{await at(r),location.reload()}catch(i){t&&(t.textContent=String(i))}})()})})}async function vt(){if(await q(),(await B()).read_only)return`<h1>Profiles</h1>
      <div class="empty">Read-only mode — profile editor disabled.</div>`;const{profiles:e,path:a}=await N(),s=e.map(c=>`<option value="${n(c)}">${n(c)}</option>`).join(""),r=e[0]||"";let i="{}",d="";if(r){const c=await A(r);i=JSON.stringify(c.fields,null,2),d=(c.secret_env_names||[]).map(o=>`<code>${n(o)}</code>`).join(" ")}return`
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
    <textarea id="prof-fields" data-testid="prof-fields" rows="18" class="code">${n(i)}</textarea>
    <pre class="log" id="prof-msg" data-testid="prof-msg"></pre>
  `}function bt(){var r,i,d,c;const t=document.getElementById("prof-msg"),e=document.getElementById("prof-fields"),a=document.getElementById("prof-name"),s=()=>e?JSON.parse(e.value):{};(r=document.getElementById("prof-load"))==null||r.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await A(o);e&&(e.value=JSON.stringify(l.fields,null,2)),t&&(t.textContent=`loaded ${o}`)}catch(o){t&&(t.textContent=String(o))}})()}),(i=document.getElementById("prof-validate"))==null||i.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await X(o,s());t&&(t.textContent=l.ok?`OK
${JSON.stringify(l.settings_summary,null,2)}`:l.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()}),(d=document.getElementById("prof-preview"))==null||d.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await O(o,s(),!1);t&&(t.textContent=l.diff||"(no diff)")}catch(o){t&&(t.textContent=String(o))}})()}),(c=document.getElementById("prof-save"))==null||c.addEventListener("click",()=>{(async()=>{try{const o=(a==null?void 0:a.value)||"",l=await O(o,s(),!0);t&&(t.textContent=l.saved?`saved
${l.diff}`:l.errors.join(`
`))}catch(o){t&&(t.textContent=String(o))}})()})}function R(t,e="var(--accent)"){const a=t.map(l=>Number(l.v??0));if(!a.length)return'<span class="meta">no samples</span>';const s=Math.min(...a),r=Math.max(...a),i=Math.max(1e-9,r-s),d=320,c=64,o=a.map((l,b)=>{const h=b/Math.max(1,a.length-1)*d,f=c-(l-s)/i*(c-4)-2;return`${h.toFixed(1)},${f.toFixed(1)}`}).join(" ");return`<svg class="spark" viewBox="0 0 ${d} ${c}" width="${d}" height="${c}">
    <polyline fill="none" stroke="${e}" stroke-width="1.5" points="${o}"/>
  </svg>`}async function $t(){var r;const t=await U({}),e=t.runs.map(i=>`<option value="${n(i.id)}">${n(i.id.slice(0,8))}… · ${n(i.profile)}</option>`).join(""),a=((r=t.runs[0])==null?void 0:r.id)||"";let s='<div class="empty">Pick a run to load perf series.</div>';if(a){const i=await F(a);s=J(a,i.series,i.summary)}return`
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
  `}function J(t,e,a){const s=Object.keys(e);return s.length?s.map(r=>{var d,c;const i=a[r]||{};return`<div class="panel" data-testid="perf-metric">
        <h2>${n(r)} <span class="meta">avg ${n(((c=(d=i.avg)==null?void 0:d.toFixed)==null?void 0:c.call(d,2))??"—")} · n ${n(i.count??0)}</span></h2>
        ${R(e[r]||[])}
      </div>`}).join(""):`<div class="empty">No perf samples for ${n(t)}.</div>`}function gt(){var i,d;const t=document.getElementById("perf-series"),e=document.getElementById("perf-compare-out"),a=document.getElementById("perf-run"),s=document.getElementById("perf-a"),r=document.getElementById("perf-b");s&&r&&r.options.length>1&&(r.selectedIndex=1),(i=document.getElementById("perf-load"))==null||i.addEventListener("click",()=>{(async()=>{const c=(a==null?void 0:a.value)||"";if(!(!c||!t))try{const o=await F(c);t.innerHTML=J(c,o.series,o.summary)}catch(o){t.textContent=String(o)}})()}),(d=document.getElementById("perf-compare"))==null||d.addEventListener("click",()=>{(async()=>{const c=(s==null?void 0:s.value)||"",o=(r==null?void 0:r.value)||"";if(e)try{const l=await st(c,o),b=l.deltas.map(f=>{var u,p,m,y,g,w;return`<tr>
              <td>${n(f.metric)}</td>
              <td>${n(((m=(p=(u=f.a)==null?void 0:u.avg)==null?void 0:p.toFixed)==null?void 0:m.call(p,2))??"—")}</td>
              <td>${n(((w=(g=(y=f.b)==null?void 0:y.avg)==null?void 0:g.toFixed)==null?void 0:w.call(g,2))??"—")}</td>
              <td>${f.delta_avg==null?"—":n(f.delta_avg.toFixed(2))}</td>
            </tr>`}).join(""),h=Object.keys(l.series_a).map(f=>{const u=l.series_a[f]||[],p=l.series_b[f]||[];return`<div class="panel">
              <h2>${n(f)} overlay</h2>
              <div class="toolbar">
                <span class="meta">A</span>${R(u,"var(--accent)")}
                <span class="meta">B</span>${R(p,"var(--ok)")}
              </div>
            </div>`}).join("");e.innerHTML=`
          <div class="table-wrap">
            <table data-testid="perf-delta-table">
              <thead><tr><th>Metric</th><th>A avg</th><th>B avg</th><th>Δ avg</th></tr></thead>
              <tbody>${b||'<tr><td colspan="4">No metrics</td></tr>'}</tbody>
            </table>
          </div>
          ${h}`}catch(l){e.textContent=String(l)}})()})}const T=document.querySelector("#app");let _=!1,L=!1,P=!1;function j(t,e){const a=(c,o)=>`<a href="${c}" class="${t===o?"active":""}">${o}</a>`,s=_?"":`${a("#/launch","Launch")}
        ${a("#/quarantine","Quarantine")}
        ${a("#/profiles","Profiles")}`,r=[_?'<span class="badge warn" title="--read-only">RO</span>':"",L?'<span class="badge warn" title="Playwright smoke fixture — not real runs">SMOKE</span>':"",P?'<span class="badge warn" title="Restart questline hud">STALE API</span>':""].filter(Boolean).join(" "),i=L?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)">
        <strong>SMOKE FIXTURE SERVER</strong> — fake launcher + seeded runs.
        For real Wire/mock runs stop this process and use
        <code>uv run questline hud --open</code> (port 8741).
      </div>`:"",d=P?`<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)" data-testid="stale-api">
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
    <main class="main">${i}${d}${e}</main>
  `}function yt(){const e=(location.hash.replace(/^#\/?/,"")||"").split("/").filter(Boolean);if(e[0]==="runs"&&e[1]&&e[2]==="tests"&&e.length>=4){const a=e.slice(3).join("/");let s=a;try{s=decodeURIComponent(a)}catch{}return{name:"test",params:{runId:e[1],testId:s}}}return e[0]==="runs"&&e[1]?{name:"run",params:{runId:e[1]}}:e[0]==="trends"?{name:"trends",params:{}}:e[0]==="live"?{name:"live",params:{}}:e[0]==="launch"?{name:"launch",params:{}}:e[0]==="quarantine"?{name:"quarantine",params:{}}:e[0]==="profiles"?{name:"profiles",params:{}}:e[0]==="perf"?{name:"perf",params:{}}:{name:"runs",params:{}}}function wt(t){return t.length?`
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
    </div>`}async function St(){const t=new URLSearchParams(location.hash.split("?")[1]||""),e=t.get("profile")||"",a=t.get("status")||"",s=await U({profile:e||void 0,status:a||void 0});return`
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
    ${wt(s.runs)}
  `}async function Q(){const t=yt();try{let e="",a="Runs";t.name==="run"?(e=await ot(t.params.runId),a="Runs"):t.name==="test"?(e=await dt(t.params.runId,t.params.testId),a="Runs"):t.name==="trends"?(e=await ct(),a="Trends"):t.name==="live"?(e=await lt(),a="Live"):t.name==="launch"?(e=await pt(),a="Launch"):t.name==="quarantine"?(e=await ht(),a="Quarantine"):t.name==="profiles"?(e=await vt(),a="Profiles"):t.name==="perf"?(e=await $t(),a="Perf"):(e=await St(),a="Runs"),T.innerHTML=j(a,e),kt(t.name)}catch(e){T.innerHTML=j("Runs",`<div class="empty">Failed to load HUD: ${n(String(e))}</div>`)}}function kt(t){var e;if(t==="runs"&&((e=document.getElementById("f-apply"))==null||e.addEventListener("click",()=>{const a=document.getElementById("f-profile").value.trim(),s=document.getElementById("f-status").value,r=new URLSearchParams;a&&r.set("profile",a),s&&r.set("status",s);const i=r.toString();location.hash=i?`/?${i}`:"/"})),t==="live"){const a=document.getElementById("live-root");a&&ut(a)}t==="launch"&&ft(),t==="quarantine"&&mt(),t==="profiles"&&bt(),t==="perf"&&gt()}async function Et(){var t;try{const e=await B();_=!!e.read_only,L=!!e.smoke,P=!((t=e.api)!=null&&t.test_by_query),_||await q()}catch{_=!1,L=!1,P=!0}await Q()}window.addEventListener("hashchange",()=>{Q()});Et();
