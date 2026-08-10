import { esc } from "../api";

export async function renderLive(): Promise<string> {
  return `
    <h1>Live</h1>
    <p class="meta">Streaming EventBus events for the in-progress run (WebSocket /live).</p>
    <div class="toolbar">
      <span id="live-status" class="badge running">connecting…</span>
      <button type="button" id="live-clear">Clear</button>
    </div>
    <div id="live-root" class="live-log" data-testid="live-log"></div>
  `;
}

export function startLive(root: HTMLElement): void {
  const status = document.getElementById("live-status");
  const clearBtn = document.getElementById("live-clear");
  clearBtn?.addEventListener("click", () => {
    root.innerHTML = "";
  });

  const proto = location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${location.host}/live`;
  let ws: WebSocket;
  try {
    ws = new WebSocket(url);
  } catch (err) {
    if (status) status.textContent = "failed";
    root.innerHTML = `<div>WebSocket error: ${esc(String(err))}</div>`;
    return;
  }

  ws.onopen = () => {
    if (status) {
      status.textContent = "live";
      status.className = "badge passed";
    }
  };
  ws.onclose = () => {
    if (status) {
      status.textContent = "closed";
      status.className = "badge failed";
    }
  };
  ws.onerror = () => {
    if (status) {
      status.textContent = "error";
      status.className = "badge failed";
    }
  };
  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(String(ev.data)) as Record<string, unknown>;
      const type = String(data.type ?? "?");
      const ts = String(data.timestamp ?? "");
      const extra =
        data.nodeid || data.name || data.test_id || data.status || data.profile || "";
      const line = document.createElement("div");
      line.innerHTML = `<span class="t">${esc(ts)}</span><b>${esc(type)}</b> ${esc(extra)}`;
      root.prepend(line);
    } catch {
      const line = document.createElement("div");
      line.textContent = String(ev.data);
      root.prepend(line);
    }
  };
}
