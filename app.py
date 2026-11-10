"""local-wilding console — a usable Otari control surface, stdlib only.

    python app.py            # http://localhost:8787

Real functions: send a prompt through the gateway with model picker,
budget cap (pre-dispatch refusal via SpendLedger), live tool probe,
receipted feed, spend-ledger view. The devs-wilding demo is one button
inside it — the same two-arm run the video shows, driven from the page.

No framework, no deps — same zero-dependency spirit as otari_client.py.
Jobs run on threads; the page polls /api/job for the live feed.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

import local_arm
from agent import run_task
from ledger import SpendLedger
from otari_client import OtariClient

HOST = os.environ.get("LW_HOST", "127.0.0.1")
PORT = int(os.environ.get("LW_PORT", "8787"))
LEDGER_PATH = "evidence/spend_ledger_console.jsonl"

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()

ALL_TOOLS = ["otari_web_search", "otari_web_fetch", "otari_code_execution"]

DEMO_TASK = (
    "Verify this claim: 'The population of India grew more than 15% "
    "between 2015 and 2023.' Find official figures, do the math in code, "
    "and give a verdict with sources."
)
CAP_TASK = "Summarize today's top AI news in one sentence."


# ---------------------------------------------------------------- jobs ------

def _job() -> str:
    jid = uuid.uuid4().hex[:8]
    with JOBS_LOCK:
        JOBS[jid] = {"status": "running", "started": time.time(),
                     "events": [], "result": None}
    return jid


def _emit(jid: str, arm: str):
    def cb(ev: str, data: dict) -> None:
        with JOBS_LOCK:
            JOBS[jid]["events"].append(
                {"t": round(time.time() - JOBS[jid]["started"], 1),
                 "arm": arm, "ev": ev, "data": data})
    return cb


def _note(jid: str, arm: str, ev: str, **data) -> None:
    _emit(jid, arm)(ev, data)


def _finish(jid: str, result) -> None:
    with JOBS_LOCK:
        JOBS[jid]["status"] = "done"
        JOBS[jid]["result"] = result


def run_send(jid: str, prompt: str, model: str, cap: float,
             tools: list[str], arm: str) -> None:
    try:
        if arm == "local":
            if not local_arm.available():
                _finish(jid, {"ok": False, "error":
                              "LOCAL_BASE_URL unset — start llamafile/LM "
                              "Studio and set it for the free local arm."})
                return
            client = local_arm.local_client()
            ledger = None
            decl_tools = None
        else:
            client = OtariClient()
            if not client.api_key:
                _finish(jid, {"ok": False, "error":
                              "OTARI_API_KEY unset — the gateway arm needs it."})
                return
            client.model = model
            ledger = SpendLedger(cap_usd=cap, path=LEDGER_PATH)
            decl_tools = [{"type": t} for t in tools] or None
        out = run_task(client, prompt, tools=decl_tools, ledger=ledger,
                       on_event=_emit(jid, arm))
        _finish(jid, {"ok": True, "arm": arm, **out})
    except Exception as e:
        _finish(jid, {"ok": False, "error": str(e)})


def run_demo(jid: str, cap: float) -> None:
    try:
        arms: dict = {"local": None, "gateway": None}
        if local_arm.available():
            _note(jid, "local", "beat", label="local arm — no tools")
            arms["local"] = run_task(local_arm.local_client(), DEMO_TASK,
                                     on_event=_emit(jid, "local"))
        else:
            _note(jid, "local", "skipped",
                  msg="LOCAL_BASE_URL unset — local arm skipped")
        client = OtariClient()
        if client.api_key:
            _note(jid, "gateway", "beat", label="gateway arm — tools+budget")
            arms["gateway"] = run_task(
                client, DEMO_TASK,
                tools=[{"type": "otari_code_execution"}],
                ledger=SpendLedger(cap_usd=cap, path=LEDGER_PATH),
                on_event=_emit(jid, "gateway"))
            _note(jid, "cap", "beat", label="cap beat — $0.01 refuses")
            arms["cap"] = run_task(
                client, CAP_TASK,
                tools=[{"type": "otari_code_execution"}],
                ledger=SpendLedger(cap_usd=0.01,
                                   path="evidence/spend_ledger_cap.jsonl"),
                on_event=_emit(jid, "cap"))
        else:
            _note(jid, "gateway", "skipped", msg="OTARI_API_KEY unset")
        _finish(jid, {"ok": True, "demo": True, "arms": arms})
    except Exception as e:
        _finish(jid, {"ok": False, "error": str(e)})


# ------------------------------------------------------------- api bits -----

def api_tools() -> dict:
    client = OtariClient()
    if not client.api_key:
        return {"ok": False, "error": "OTARI_API_KEY unset",
                "tools": [{"id": t, "available": None, "reason": "unknown"}
                          for t in ALL_TOOLS]}
    try:
        req = urllib.request.Request(
            f"{client.base}/tools",
            headers={"Authorization": f"Bearer {client.api_key}"})
        body = json.loads(urllib.request.urlopen(req, timeout=15).read())
        return {"ok": True, "tools": body.get("data", [])}
    except Exception as e:
        return {"ok": False, "error": str(e),
                "tools": [{"id": t, "available": None, "reason": "probe failed"}
                          for t in ALL_TOOLS]}


def api_models() -> dict:
    client = OtariClient()
    if not client.api_key:
        return {"ok": False, "models": ["openai/gpt-oss-120b"],
                "note": "key unset — default list"}
    res = client.models(timeout=15)
    if not res.ok:
        return {"ok": False, "models": ["openai/gpt-oss-120b"],
                "note": res.error[:120]}
    data = res.body.get("data") or []
    return {"ok": True, "models": [m.get("id", "?") for m in data]}


def api_ledger() -> dict:
    rows = []
    spent = saved = 0.0
    refusals = 0
    cap = None
    for p in [LEDGER_PATH, "evidence/spend_ledger.jsonl",
              "evidence/spend_ledger_cap.jsonl"]:
        fp = Path(p)
        if fp.exists():
            for line in fp.read_text(encoding="utf-8").splitlines()[-40:]:
                try:
                    r = {**json.loads(line), "file": fp.name}
                    rows.append(r)
                    ev = r.get("event")
                    if ev == "settle":
                        spent += float(r.get("cost_usd") or 0)
                    elif ev == "refuse":
                        saved += float(r.get("estimated_usd") or 0)
                        refusals += 1
                    elif ev == "release":
                        saved += float(r.get("estimated_usd") or 0)
                    elif ev == "open":
                        cap = r.get("cap_usd")
                except json.JSONDecodeError:
                    pass
    return {"rows": rows[-40:],
            "summary": {"spent": round(spent, 6), "saved": round(saved, 6),
                        "refusals": refusals, "cap": cap}}


# ---------------------------------------------------------------- page ------

PAGE = """<!doctype html><html><head><meta charset=utf-8>
<title>local-wilding — otari console</title>
<style>
:root{--bg:#0D1B26;--panel:#12242F;--teal:#3FD9A8;--amber:#FFCF6B;
--txt:#DFF4EE;--dim:#7FA8A0;--red:#E8455F}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
font:14px/1.5 Consolas,monospace}
header{display:flex;gap:12px;align-items:center;padding:10px 16px;
background:var(--panel);border-bottom:1px solid #1E3A47}
header b{color:var(--teal);font-size:16px}.pill{padding:2px 10px;
border-radius:10px;font-size:12px}
.ok{background:#123a2e;color:var(--teal)}.bad{background:#3a1620;color:var(--red)}
main{display:grid;grid-template-columns:380px 1fr;gap:14px;padding:14px}
.card{background:var(--panel);border:1px solid #1E3A47;border-radius:8px;
padding:12px}
h3{margin:0 0 8px;color:var(--amber);font-size:13px;letter-spacing:.5px}
textarea{width:100%;height:90px;background:#0B1620;color:var(--txt);
border:1px solid #1E3A47;border-radius:6px;padding:8px;font:inherit}
input,select{background:#0B1620;color:var(--txt);border:1px solid #1E3A47;
border-radius:5px;padding:4px 6px;font:inherit;width:100%}
button{background:var(--teal);color:#04160f;border:0;border-radius:6px;
padding:8px 14px;font:700 13px Consolas;cursor:pointer;width:100%;margin-top:8px}
button.ghost{background:#123a2e;color:var(--teal)}
button:disabled{opacity:.4;cursor:wait}
label{display:block;margin:8px 0 3px;color:var(--dim);font-size:12px}
.tool{display:flex;gap:8px;align-items:center;padding:2px 0}
.tool.dis{opacity:.45}
.feed{max-height:340px;overflow-y:auto;font-size:12.5px}
.ev{padding:3px 6px;border-left:3px solid #1E3A47;margin:3px 0;
white-space:pre-wrap;word-break:break-word}
.ev.local{border-color:#8a7}.ev.gateway{border-color:var(--teal)}
.ev.cap{border-color:var(--red)}
.ev .t{color:var(--dim)} .ev .arm{color:var(--amber)}
.ev.refused{color:var(--red);border-color:var(--red)}
.ans{white-space:pre-wrap;word-break:break-word;background:#0B1620;
border-radius:6px;padding:10px;margin-top:8px;max-height:260px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:12px}
td,th{padding:3px 8px;text-align:left;border-bottom:1px solid #1E3A47}
th{color:var(--dim);font-weight:400}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.cost{color:var(--amber)}
#demoPane{grid-column:1/3;display:none}
</style></head><body>
<header><b>local-wilding</b><span>otari console</span>
<span id=keystat class="pill bad">key …</span>
<span id=ep class=pill style=color:var(--dim)></span>
<button class=ghost style="width:auto;margin:0 0 0 auto"
 onclick="demo()">run devs-wilding demo</button></header>
<main>
<div class=card><h3>send</h3>
<textarea id=prompt placeholder="prompt…">Verify this claim: 'The population
of India grew more than 15% between 2015 and 2023.'</textarea>
<label>model</label><select id=model></select>
<label>budget cap (usd) — reserve before dispatch, refuse on breach</label>
<input id=cap type=number step=0.01 value=0.25>
<label>server-side tools (live probe)</label><div id=tools>probing…</div>
<label>arm</label><select id=arm><option value=gateway>gateway (Otari)</option>
<option value=local>local (free — LOCAL_BASE_URL)</option></select>
<button id=send onclick="send()">dispatch →</button></div>
<div class=card><h3>feed</h3><div id=feed class=feed></div>
<div id=answer></div></div>
<div class=card id=demoPane><h3>demo — same task, two arms</h3>
<div class=cols><div><label>local — no tools</label>
<div id=dl class=feed></div></div>
<div><label>gateway — tools + budget + receipts</label>
<div id=dg class=feed></div></div></div>
<div id=capfeed></div></div>
<div class=card style="grid-column:1/3;padding:0">
<div id=lbar style="display:flex;gap:14px;align-items:center;padding:10px 14px;
 cursor:pointer;user-select:none" onclick="toggleLedger()">
<span style="color:var(--amber)">◈ ledger</span>
<span id=lsum style="color:var(--dim)">…</span>
<span id=lcaret style="margin-left:auto;color:var(--dim)">▸</span></div>
<div id=ltable style="display:none;padding:0 14px 12px">
<table><tr><th>ts</th><th>event</th><th>label</th><th>est</th>
<th>cost</th><th>spent</th><th>file</th></tr>
<tbody id=ledger></tbody></table></div></div>
</main><script>
let job=null;
const $=i=>document.getElementById(i);
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function api(u,o){const r=await fetch(u,o?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)}:undefined);return r.json()}
async function boot(){
 const s=await api('/api/status');
 $('keystat').textContent=s.key_set?'key set':'key unset';
 $('keystat').className='pill '+(s.key_set?'ok':'bad');
 $('ep').textContent=s.base;
 const tm=await api('/api/models');
 $('model').innerHTML=tm.models.map(m=>`<option>${esc(m)}</option>`).join('');
 const tt=await api('/api/tools');
 $('tools').innerHTML=(tt.tools||[]).map(t=>{
  const dis=t.available===false;
  return `<div class="tool${dis?' dis':''}"><input type=checkbox id=tl_${t.id}
   ${t.available?'checked':''} ${dis?'disabled':''}>
   <span>${esc(t.id)}</span><span style=color:var(--dim)>${esc(t.reason||'')}</span></div>`}).join('');
 ledger(); setInterval(ledger,8000)}
function evHtml(e){
 const d=e.data||{};let txt=e.ev;
 if(e.ev==='step')txt=`step ${d.step} → ${d.model}`;
 if(e.ev==='tool')txt=`tool ran server-side: ${d.kind}`;
 if(e.ev==='settled')txt=`settled $${(+d.cost_usd).toFixed(4)} served=${d.served}`;
 if(e.ev==='refused')txt=`REFUSED ${d.msg}`;
 if(e.ev==='beat')txt=`▸ ${d.label}`;
 if(e.ev==='skipped')txt=`skipped — ${d.msg}`;
 return `<div class="ev ${e.arm} ${e.ev}"><span class=t>${e.t}s</span>
  <span class=arm>${e.arm||''}</span> ${esc(txt)}</div>`}
async function poll(id,feeds){
 const j=await api('/api/job?id='+id);
 (j.events||[]).forEach((e,i)=>{
  if(e._seen)return;e._seen=1;
  const el=(e.arm==='local'&&feeds.dl)||((e.arm==='gateway'||e.arm==='cap')&&feeds.dg)||feeds.main;
  el.insertAdjacentHTML('beforeend',evHtml(e));
  el.scrollTop=el.scrollHeight});
 if(j.status==='done'){
  clearInterval(job);job=null;$('send').disabled=false;
  const r=j.result||{};
  if(r.answer)$('answer').innerHTML=`<div class=ans>${esc(r.answer)}</div>
   <div class=cost>cost $${(r.cost_usd||0).toFixed(4)}${r.refused?' — refused: '+esc(r.refused):''}</div>`;
  else if(r.arms){const g=r.arms.gateway||{},c=r.arms.cap||{};
   $('capfeed').innerHTML=`<div class=ans>local: ${esc(((r.arms.local||{}).answer||'(skipped)').slice(0,400))}</div>
    <div class=ans>gateway: ${esc((g.answer||'').slice(0,900))} <span class=cost>$${(g.cost_usd||0).toFixed(4)}</span></div>
    <div class="ev refused">cap beat: ${esc(c.refused||'(not refused)')}</div>`}
  else if(r.error)$('answer').innerHTML=`<div class=ans style="color:var(--red)">${esc(r.error)}</div>`;
  ledger()}}
async function send(){
 $('send').disabled=true;$('feed').innerHTML='';$('answer').innerHTML='';
 const tools=[...document.querySelectorAll('#tools input:checked')].map(c=>c.id.slice(3));
 const r=await api('/api/send',{prompt:$('prompt').value,model:$('model').value,
  cap:parseFloat($('cap').value||0.25),tools,arm:$('arm').value});
 job=setInterval(()=>poll(r.job,{main:$('feed')}),800)}
async function demo(){
 $('demoPane').style.display='block';$('dl').innerHTML='';$('dg').innerHTML='';
 $('capfeed').innerHTML='';
 const r=await api('/api/demo',{cap:parseFloat($('cap').value||0.25)});
 job=setInterval(()=>poll(r.job,{main:$('feed'),dl:$('dl'),dg:$('dg')}),800)}
async function ledger(){
 const l=await api('/api/ledger');
 const s=l.summary||{};
 $('lsum').innerHTML=`spent <span class=cost>$${(s.spent||0).toFixed(4)}</span>
  · saved <span style="color:var(--teal)">$${(s.saved||0).toFixed(4)}</span>
  · refusals ${s.refusals||0}${s.cap!=null?` · cap $${s.cap}`:''}`;
 $('ledger').innerHTML=(l.rows||[]).map(r=>`<tr><td>${(r.ts||0)%1000|0}</td>
  <td>${esc(r.event)}</td><td>${esc(r.label||'')}</td>
  <td>${r.estimated_usd!=null?'$'+r.estimated_usd:''}</td>
  <td>${r.cost_usd!=null?'$'+r.cost_usd:''}</td>
  <td>$${r.spent_usd||0}</td><td style=color:var(--dim)>${esc(r.file||'')}</td></tr>`).join('')}
function toggleLedger(){
 const t=$('ltable'),open=t.style.display!=='none';
 t.style.display=open?'none':'block';
 $('lcaret').textContent=open?'▸':'▾'}
boot();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def _out(self, code: int, body, ctype="application/json") -> None:
        b = body if isinstance(body, bytes) else (
            body.encode() if isinstance(body, str)
            else json.dumps(body).encode())
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a) -> None:
        pass

    def do_GET(self) -> None:
        u = self.path.split("?")[0]
        if u == "/":
            self._out(200, PAGE, "text/html; charset=utf-8")
        elif u == "/api/status":
            self._out(200, {"key_set": bool(OtariClient().api_key),
                            "base": OtariClient().base,
                            "local": local_arm.available()})
        elif u == "/api/tools":
            self._out(200, api_tools())
        elif u == "/api/models":
            self._out(200, api_models())
        elif u == "/api/ledger":
            self._out(200, api_ledger())
        elif u == "/api/job":
            jid = self.path.split("id=")[-1]
            with JOBS_LOCK:
                self._out(200, JOBS.get(jid) or {"status": "unknown"})
        else:
            self._out(404, {"error": "not found"})

    def do_POST(self) -> None:
        try:
            body = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", 0)) or b"{}"))
        except Exception:
            body = {}
        if self.path == "/api/send":
            jid = _job()
            threading.Thread(
                target=run_send, daemon=True,
                args=(jid, body.get("prompt", ""), body.get("model", ""),
                      float(body.get("cap", 0.25)), body.get("tools", []),
                      body.get("arm", "gateway"))).start()
            self._out(200, {"job": jid})
        elif self.path == "/api/demo":
            jid = _job()
            threading.Thread(target=run_demo, daemon=True,
                             args=(jid, float(body.get("cap", 0.25)))).start()
            self._out(200, {"job": jid})
        else:
            self._out(404, {"error": "not found"})


if __name__ == "__main__":
    print(f"local-wilding console → http://{HOST}:{PORT}")
    print("gateway key:", "set" if OtariClient().api_key else "UNSET",
          "| local arm:", "set" if local_arm.available() else "unset")
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
