#!/usr/bin/env python3
"""Local web UI for connecting HubSpot to the SDR plugin.

Serves a small, single-page setup form on http://127.0.0.1:<random-port>.
The user pastes their HubSpot private-app token into a masked field and clicks
"Save & Connect". The token is POSTed over localhost only (never as a shell
argument, so it never reaches the audit log), saved to
~/.claude/sdr-plugin-config.json (mode 600), then verified and used to
provision the required custom properties.

Security:
  - Binds to 127.0.0.1 on an ephemeral port — not reachable off this machine.
  - A random nonce is embedded in the page and required on every POST, so other
    local pages cannot drive the form (they can't read our nonce cross-origin).
  - The token is never printed, logged, or placed in a URL.

Reuses the verify + provision logic from ensure_hubspot_setup.py.

Usage:
  python3 setup_ui.py [--no-browser] [--timeout SECONDS]

Prints a JSON summary of the outcome to stdout when the window is done.
"""
import argparse
import json
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ensure_hubspot_setup as hs  # noqa: E402
from _config import CONFIG_PATH, redact, save_token  # noqa: E402

NONCE = secrets.token_urlsafe(24)
_RESULT = {"status": "closed", "message": "Setup window closed before connecting."}
_RESULT_LOCK = threading.Lock()


def provision(token: str) -> dict:
    """Validate the token and create any missing custom properties.

    Returns a UI-friendly dict. Mirrors ensure_hubspot_setup.main() but shaped
    for the web response and reusing the same helpers.
    """
    ok, account = hs.verify_token(token)
    if not ok:
        return {"ok": False, "stage": "verify",
                "message": "HubSpot didn't accept that token. Double-check you copied "
                           "the whole thing (it starts with “pat-”) and try again."}

    portal_id = str(account.get("portalId", ""))
    required = hs.load_config()
    by_type: dict[str, list[dict]] = {}
    for prop in required:
        by_type.setdefault(prop["objectType"], []).append(prop)

    chips, results = [], {}
    for object_type, props in by_type.items():
        existing = hs.get_existing_properties(object_type, token)
        for prop in props:
            name = prop["name"]
            if name in existing:
                state = "existing"
            else:
                r = hs.create_property(object_type, prop, token)
                state = "created" if r.get("status") == "created" else "failed"
            results[name] = {"status": state, "objectType": object_type}
            chips.append({"label": prop.get("label", name), "object": object_type, "state": state})

    all_ok = all(r["status"] in ("existing", "created") for r in results.values())
    if all_ok:
        hs.write_marker(hs.DEFAULT_MARKER, portal_id, results)

    return {
        "ok": all_ok,
        "portalId": portal_id,
        "masked": redact(token),
        "config_path": str(CONFIG_PATH).replace(str(Path.home()), "~"),
        "properties": chips,
        "message": "HubSpot is connected and ready." if all_ok
                   else "Connected, but some properties couldn't be created — your token "
                        "may be missing the schema-write permission.",
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence default stderr logging (privacy)
        pass

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] not in ("/", "/index.html"):
            self._send(404, b"not found", "text/plain")
            return
        page = PAGE.replace("__NONCE__", NONCE)
        self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except Exception:
            data = {}

        if data.get("nonce") != NONCE:
            self._send(403, json.dumps({"ok": False, "message": "Bad session."}).encode(), "application/json")
            return

        if path == "/shutdown":
            self._send(204, b"", "text/plain")
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        if path != "/save":
            self._send(404, b"{}", "application/json")
            return

        token = str(data.get("token", "")).strip()
        if not token:
            self._send(400, json.dumps({"ok": False, "message": "Please paste your token first."}).encode(), "application/json")
            return

        try:
            save_token(token)
            result = provision(token)
        except Exception as e:  # never leak the token in an error
            result = {"ok": False, "message": f"Something went wrong saving the token: {type(e).__name__}."}

        if result.get("ok"):
            with _RESULT_LOCK:
                _RESULT.clear()
                _RESULT.update({"status": "connected", **{k: v for k, v in result.items()
                                                           if k in ("portalId", "masked", "config_path")}})
        self._send(200, json.dumps(result).encode("utf-8"), "application/json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-browser", action="store_true", help="Don't auto-open a browser")
    ap.add_argument("--timeout", type=int, default=900, help="Auto-close after N seconds of inactivity")
    args = ap.parse_args()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"

    threading.Timer(args.timeout, server.shutdown).start()

    print(f"Opening the HubSpot setup window in your browser:\n  {url}", flush=True)
    print("Leave this running — it closes itself once you're connected.\n", flush=True)
    if not args.no_browser:
        threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    with _RESULT_LOCK:
        print(json.dumps(_RESULT))


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Connect HubSpot · SDR Plugin</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..600;1,9..144,400&family=Hanken+Grotesk:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#181210; --ink-2:#221a16; --line:rgba(245,237,226,.12);
  --cream:#f5ede2; --muted:#b9a896; --faint:#8a7766;
  --coral:#ff6b4a; --amber:#ffb24a; --good:#7bd88f; --bad:#ff7a6b;
  --r:18px;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0; background:var(--ink); color:var(--cream);
  font-family:"Hanken Grotesk",sans-serif; font-size:16px; line-height:1.5;
  -webkit-font-smoothing:antialiased;
  display:flex; align-items:center; justify-content:center; padding:32px;
  background-image:
    radial-gradient(120% 90% at 12% -10%, rgba(255,107,74,.18), transparent 55%),
    radial-gradient(120% 90% at 110% 110%, rgba(255,178,74,.12), transparent 50%);
}
/* grain */
body::before{
  content:""; position:fixed; inset:0; pointer-events:none; opacity:.05; z-index:0;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
.card{
  position:relative; z-index:1; width:100%; max-width:512px;
  background:linear-gradient(180deg,var(--ink-2),#1c1511);
  border:1px solid var(--line); border-radius:var(--r);
  padding:40px 40px 34px; overflow:hidden;
  box-shadow:0 1px 0 rgba(245,237,226,.06) inset, 0 40px 90px -50px rgba(0,0,0,.9);
  animation:rise .7s cubic-bezier(.2,.7,.2,1) both;
}
.card::before{ /* accent seam */
  content:""; position:absolute; left:0; top:0; height:100%; width:3px;
  background:linear-gradient(180deg,var(--coral),var(--amber));
}
@keyframes rise{from{opacity:0;transform:translateY(14px) scale(.99)}to{opacity:1;transform:none}}
.stagger>*{opacity:0;animation:fade .6s ease forwards}
.stagger>*:nth-child(1){animation-delay:.10s}
.stagger>*:nth-child(2){animation-delay:.18s}
.stagger>*:nth-child(3){animation-delay:.26s}
.stagger>*:nth-child(4){animation-delay:.34s}
.stagger>*:nth-child(5){animation-delay:.42s}
@keyframes fade{to{opacity:1;transform:none}}
.kicker{font-family:"IBM Plex Mono",monospace; font-size:11px; letter-spacing:.22em;
  text-transform:uppercase; color:var(--coral); margin:0 0 14px}
h1{font-family:"Fraunces",serif; font-weight:540; font-size:34px; line-height:1.05;
  letter-spacing:-.01em; margin:0 0 8px}
.sub{color:var(--muted); margin:0 0 28px; max-width:40ch}
label{display:block; font-size:13px; font-weight:600; letter-spacing:.01em;
  color:var(--cream); margin:0 0 8px}
.field{position:relative; display:flex; align-items:center}
input[type=password],input[type=text]{
  width:100%; font-family:"IBM Plex Mono",monospace; font-size:16px; letter-spacing:.04em;
  color:var(--cream); background:#120d0b; border:1px solid var(--line);
  border-radius:12px; padding:15px 52px 15px 16px; outline:none;
  transition:border-color .2s, box-shadow .2s;
}
input::placeholder{color:#5e4f44; letter-spacing:.18em}
input:focus{border-color:var(--coral); box-shadow:0 0 0 3px rgba(255,107,74,.18)}
.reveal{position:absolute; right:8px; width:38px; height:38px; border:0; cursor:pointer;
  background:transparent; color:var(--faint); border-radius:9px; font-size:17px;
  display:grid; place-items:center; transition:color .2s, background .2s}
.reveal:hover{color:var(--cream); background:rgba(245,237,226,.06)}
.help{margin:12px 0 0}
.help summary{cursor:pointer; font-size:13px; color:var(--amber); list-style:none;
  display:inline-flex; align-items:center; gap:6px}
.help summary::-webkit-details-marker{display:none}
.help summary::before{content:"›"; transition:transform .2s; display:inline-block}
.help[open] summary::before{transform:rotate(90deg)}
.steps{margin:12px 0 0; padding:14px 16px; background:#120d0b; border:1px solid var(--line);
  border-radius:12px; counter-reset:s; font-size:13.5px; color:var(--muted)}
.steps p{margin:0 0 9px; padding-left:26px; position:relative}
.steps p:last-child{margin:0}
.steps p::before{counter-increment:s; content:counter(s); position:absolute; left:0; top:-1px;
  width:18px; height:18px; border-radius:50%; background:rgba(255,107,74,.16); color:var(--coral);
  font-family:"IBM Plex Mono",monospace; font-size:11px; display:grid; place-items:center}
.steps b{color:var(--cream); font-weight:600}
.lockline{display:flex; gap:9px; align-items:flex-start; margin:20px 0 0; color:var(--faint); font-size:12.5px}
.lockline svg{flex:none; margin-top:1px}
button.go{margin:22px 0 0; width:100%; border:0; cursor:pointer; border-radius:12px;
  padding:15px 18px; font-family:"Hanken Grotesk"; font-size:15.5px; font-weight:600; color:#241008;
  background:linear-gradient(95deg,var(--coral),var(--amber)); letter-spacing:.01em;
  transition:transform .15s, filter .2s, opacity .2s;
  display:inline-flex; align-items:center; justify-content:center; gap:10px}
button.go:hover:not(:disabled){transform:translateY(-1px); filter:brightness(1.05)}
button.go:active:not(:disabled){transform:translateY(0)}
button.go:disabled{opacity:.4; cursor:not-allowed}
.spinner{width:16px; height:16px; border-radius:50%; border:2px solid rgba(36,16,8,.35);
  border-top-color:#241008; animation:spin .7s linear infinite; display:none}
@keyframes spin{to{transform:rotate(360deg)}}
.banner{margin:16px 0 0; padding:12px 14px; border-radius:11px; font-size:13.5px;
  background:rgba(255,122,107,.10); border:1px solid rgba(255,122,107,.3); color:#ffb3a8; display:none}
/* states */
[data-state=saving] .go{pointer-events:none}
[data-state=saving] .spinner{display:inline-block}
[data-state=saving] .go .lbl{opacity:.85}
[data-state=error] .banner{display:block; animation:fade .3s ease both}
[data-state=success] #form{display:none}
#success{display:none}
[data-state=success] #success{display:block; animation:fade .5s ease both}
/* success panel */
.badge{width:56px; height:56px; border-radius:50%; display:grid; place-items:center;
  background:rgba(123,216,143,.14); border:1px solid rgba(123,216,143,.4); margin:0 0 18px}
.badge svg path{stroke-dasharray:24; stroke-dashoffset:24; animation:draw .5s .15s ease forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.portal{font-family:"IBM Plex Mono",monospace; font-size:12.5px; color:var(--faint); margin:2px 0 18px}
.keypill{display:inline-flex; align-items:center; gap:8px; font-family:"IBM Plex Mono",monospace;
  font-size:13px; color:var(--cream); background:#120d0b; border:1px solid var(--line);
  border-radius:999px; padding:8px 14px; margin:0 0 22px}
.keypill .dot{width:7px; height:7px; border-radius:50%; background:var(--good)}
.chips{display:flex; flex-wrap:wrap; gap:8px; margin:0 0 22px}
.chip{font-size:12.5px; padding:7px 12px; border-radius:999px; border:1px solid var(--line);
  background:rgba(245,237,226,.03); color:var(--muted); display:inline-flex; gap:7px; align-items:center;
  opacity:0; transform:translateY(6px); animation:fade .4s ease forwards}
.chip .tick{color:var(--good)}
.chip.failed .tick{color:var(--bad)}
.done-note{color:var(--muted); font-size:14px; margin:6px 0 0}
</style>
</head>
<body>
<main class="card" id="root" data-state="idle">
  <!-- SETUP FORM -->
  <form id="form" class="stagger" autocomplete="off">
    <p class="kicker">SDR Plugin · Step 1 of 1</p>
    <h1>Connect HubSpot</h1>
    <p class="sub">Paste your HubSpot key once. We'll save it on this computer and set up everything your pipeline needs.</p>

    <div>
      <label for="tok">HubSpot private app token</label>
      <div class="field">
        <input id="tok" type="password" inputmode="text" spellcheck="false"
               placeholder="pat-na1-••••••••••••" aria-label="HubSpot private app token">
        <button type="button" class="reveal" id="reveal" aria-label="Show or hide token" title="Show / hide">👁</button>
      </div>
      <details class="help">
        <summary>Where do I find this?</summary>
        <div class="steps">
          <p>In HubSpot, open <b>Settings</b> (the gear, top right).</p>
          <p>Go to <b>Integrations → Private Apps</b>, then <b>Create a private app</b>.</p>
          <p>Name it <b>“Claude SDR”</b>. Under <b>Scopes</b>, enable read &amp; write for <b>Contacts</b> and <b>Companies</b>.</p>
          <p>Click <b>Create</b>, then <b>copy the token</b> (it starts with “pat-”) and paste it above.</p>
        </div>
      </details>
    </div>

    <div class="banner" id="banner" role="alert"></div>

    <p class="lockline">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>
      <span>Stored only on this computer, in a locked file. Your key is sent to HubSpot — nowhere else.</span>
    </p>

    <button type="submit" class="go" id="go" disabled>
      <span class="spinner"></span><span class="lbl">Save &amp; Connect</span>
    </button>
  </form>

  <!-- SUCCESS -->
  <section id="success" class="stagger" aria-live="polite">
    <div class="badge">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#7bd88f" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.5l5 5L20 6.5"/></svg>
    </div>
    <p class="kicker" style="color:var(--good)">Connected</p>
    <h1 id="s-title">You're all set.</h1>
    <p class="portal" id="s-portal"></p>
    <div class="keypill"><span class="dot"></span><span id="s-key"></span></div>
    <div class="chips" id="s-chips"></div>
    <p class="done-note">You can close this tab and head back to Claude — try <b>/find-leads</b> next.</p>
  </section>
</main>

<script>
const NONCE = "__NONCE__";
const root = document.getElementById('root');
const form = document.getElementById('form');
const tok = document.getElementById('tok');
const go = document.getElementById('go');
const banner = document.getElementById('banner');

document.getElementById('reveal').addEventListener('click', () => {
  tok.type = tok.type === 'password' ? 'text' : 'password';
});
tok.addEventListener('input', () => { go.disabled = tok.value.trim().length === 0; });

function fail(msg){ banner.textContent = msg; root.dataset.state = 'error'; }

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!tok.value.trim()) return;
  root.dataset.state = 'saving';
  go.querySelector('.lbl').textContent = 'Connecting to HubSpot…';
  try {
    const res = await fetch('/save', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ token: tok.value.trim(), nonce: NONCE })
    });
    const data = await res.json();
    if (!data.ok){ go.querySelector('.lbl').textContent = 'Save & Connect'; fail(data.message || 'That didn\'t work. Please try again.'); return; }
    renderSuccess(data);
  } catch(err){
    go.querySelector('.lbl').textContent = 'Save & Connect';
    fail('Couldn\'t reach the setup helper. Make sure the terminal window is still running.');
  }
});

function renderSuccess(d){
  document.getElementById('s-portal').textContent = d.portalId ? ('HubSpot portal ' + d.portalId + '  ·  saved to ' + d.config_path) : ('Saved to ' + d.config_path);
  document.getElementById('s-key').textContent = d.masked || 'token saved';
  const wrap = document.getElementById('s-chips');
  wrap.innerHTML = '';
  (d.properties || []).forEach((p, i) => {
    const c = document.createElement('span');
    c.className = 'chip' + (p.state === 'failed' ? ' failed' : '');
    c.style.animationDelay = (0.15 + i*0.07) + 's';
    const mark = p.state === 'failed' ? '✕' : '✓';
    c.innerHTML = '<span class="tick">'+mark+'</span>' + p.label + ' <span style="opacity:.5">· '+p.object+'</span>';
    wrap.appendChild(c);
  });
  root.dataset.state = 'success';
  // tell the helper it can stop
  try { fetch('/shutdown', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({nonce:NONCE}), keepalive:true}); } catch(e){}
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
