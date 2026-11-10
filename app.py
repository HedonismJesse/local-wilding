"""local-wilding console — a usable agent-harness surface, stdlib only.

    python app.py            # http://localhost:8787

Not a demo prop: an endpoint-agnostic console. Point it at Otari
(default), a local llamafile/LM Studio, or any OpenAI-compatible
harness — set base + key in the endpoint bar. Nothing proprietary.

The product surface is the RECEIPT BOX: every dispatched call mints a
receipt — id, endpoint, model, tools declared + ran, prompt, answer,
cost, served-model, sha256 hashes, and a link to the raw response file
under evidence/. Receipts are listable, deep-linkable (/?r=<id>),
exportable (jsonl/csv), and human-verifiable (hash the text yourself).

The spend ledger collapses to a spent/saved/refusals summary bar.
The devs-wilding demo is one button inside — the same three-beat run
the video shows, driven from the page.

No framework, no deps — same zero-dependency spirit as otari_client.py.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

import local_arm
from agent import run_task
from decide import ReceiptLog
from ledger import SpendLedger
from otari_client import OtariClient
from replay import Recorder, replay_transport

# Public-deploy mode: sends/demo replay recorded evidence — no API keys
# are ever fielded by the public instance. LW_REPLAY=1 to enable.
REPLAY = bool(os.environ.get("LW_REPLAY"))

HOST = os.environ.get("LW_HOST", "127.0.0.1")
PORT = int(os.environ.get("LW_PORT", "8787"))
LEDGER_PATH = "evidence/spend_ledger_console.jsonl"
RECEIPTS_PATH = "evidence/console_receipts.jsonl"
RAW_DIR = Path("evidence/console_raw")

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()

# Endpoint config — in-memory only (env is the persistent path; the UI
# writes here). Point anywhere OpenAI-compatible.
CFG = {"base": "", "key": "", "model": "openai/gpt-oss-120b"}
CFG_LOCK = threading.Lock()

ALL_TOOLS = ["otari_web_search", "otari_web_fetch", "otari_code_execution"]

DEMO_TASK = (
    "Verify this claim: 'The population of India grew more than 15% "
    "between 2015 and 2023.' Find official figures, do the math in code, "
    "and give a verdict with sources."
)
CAP_TASK = "Summarize today's top AI news in one sentence."


def cfg_client() -> OtariClient:
    """Client from the live endpoint bar — Otari by default, any
    OpenAI-compatible base if the operator points elsewhere."""
    with CFG_LOCK:
        base, key, model = CFG["base"], CFG["key"], CFG["model"]
    c = OtariClient(api_key=key or None, base=base or None)
    c.model = model
    return c


# --------------------------------------------------------------- receipts ---

def mint_receipt(arm: str, endpoint: str, model_req: str, prompt: str,
                 out: dict, tools_decl: list[str], job: str,
                 raw: str = "") -> dict:
    r = {
        "id": "r_" + uuid.uuid4().hex[:8],
        "ts": round(time.time(), 3),
        "endpoint": endpoint,
        "arm": arm,
        "model_requested": model_req,
        "model_served": "",
        "tools_declared": tools_decl,
        "tools_ran": [t["tool"] for t in (out.get("trace") or [])],
        "prompt": prompt,
        "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:16],
        "answer": out.get("answer", ""),
        "answer_sha": hashlib.sha256(
            (out.get("answer") or "").encode()).hexdigest()[:16],
        "cost_usd": round(out.get("cost_usd") or 0.0, 6),
        "refused": out.get("refused") or "",
        "job": job,
        "raw": raw,
    }
    Path(RECEIPTS_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(RECEIPTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(r) + "\n")
    return r


def read_receipts() -> list[dict]:
    p = Path(RECEIPTS_PATH)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def receipts_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "ts", "endpoint", "arm", "model_served",
                "cost_usd", "refused", "prompt_sha", "answer_sha"])
    for r in rows:
        w.writerow([r.get(k, "") for k in
                    ["id", "ts", "endpoint", "arm", "model_served",
                     "cost_usd", "refused", "prompt_sha", "answer_sha"]])
    return buf.getvalue()


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


def _send_one(jid: str, arm: str, client: OtariClient, prompt: str,
              tools: list[str], cap: float | None) -> dict:
    """One run_task with recorder + receipt minting."""
    if REPLAY:
        client._post = replay_transport()
    rec = Recorder(directory=RAW_DIR)
    ledger = (SpendLedger(cap_usd=cap, path=LEDGER_PATH)
              if cap is not None else None)
    decl = [{"type": t} for t in tools] or None
    out = run_task(client, prompt, tools=decl, ledger=ledger,
                   on_event=_emit(jid, arm), recorder=rec)
    raw = ""
    if rec.seq:
        raw = str(RAW_DIR / f"{rec.seq:02d}_*.json")
    r = mint_receipt(arm, client.base, client.model, prompt, out,
                     tools, jid, raw)
    _note(jid, arm, "receipt", id=r["id"])
    return {"receipt": r, **out}


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
        else:
            client = cfg_client()
            if not client.api_key and not REPLAY:
                _finish(jid, {"ok": False, "error":
                              "no API key — set OTARI_API_KEY or the "
                              "endpoint bar's key field."})
                return
            client.model = model or client.model
            if REPLAY and not client.api_key:
                client.api_key = "replay"
        out = _send_one(jid, arm, client, prompt, tools,
                        cap if arm != "local" else None)
        _finish(jid, {"ok": True, "arm": arm, **out})
    except Exception as e:
        _finish(jid, {"ok": False, "error": str(e)})


def run_demo(jid: str, cap: float) -> None:
    try:
        arms: dict = {"local": None, "gateway": None, "cap": None}
        if local_arm.available():
            _note(jid, "local", "beat", label="local arm — no tools")
            arms["local"] = _send_one(jid, "local",
                                      local_arm.local_client(),
                                      DEMO_TASK, [], None)
        else:
            _note(jid, "local", "skipped",
                  msg="LOCAL_BASE_URL unset — local arm skipped")
        client = cfg_client()
        if REPLAY and not client.api_key:
            client.api_key = "replay"
        if client.api_key:
            _note(jid, "gateway", "beat", label="gateway arm — tools+budget")
            arms["gateway"] = _send_one(jid, "gateway", client, DEMO_TASK,
                                        ["otari_code_execution"], cap)
            _note(jid, "cap", "beat", label="cap beat — $0.01 refuses")
            arms["cap"] = _send_one(jid, "cap", client, CAP_TASK,
                                    ["otari_code_execution"], 0.01)
        else:
            _note(jid, "gateway", "skipped", msg="no API key")
        _finish(jid, {"ok": True, "demo": True, "arms": arms})
    except Exception as e:
        _finish(jid, {"ok": False, "error": str(e)})


# ------------------------------------------------------------- api bits -----

def api_tools() -> dict:
    client = cfg_client()
    if not client.api_key:
        return {"ok": False, "error": "no API key",
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
    client = cfg_client()
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

PAGE = r"""<!doctype html><html><head><meta charset=utf-8>
<title>local-wilding — harness console</title>
<style>
:root{--bg:#0D1B26;--panel:#12242F;--teal:#3FD9A8;--amber:#FFCF6B;
--txt:#DFF4EE;--dim:#7FA8A0;--red:#E8455F}
*{box-sizing:border-box}html,body{height:100%;overflow:hidden}
body{margin:0;background:var(--bg);color:var(--txt);
font:14px/1.5 Consolas,monospace;display:flex;flex-direction:column}
header{display:flex;gap:12px;align-items:center;padding:10px 16px;
background:var(--panel);border-bottom:1px solid #1E3A47;flex-wrap:wrap;
flex:0 0 auto}
header b{color:var(--teal);font-size:16px}.pill{padding:2px 10px;
border-radius:10px;font-size:12px}
.ok{background:#123a2e;color:var(--teal)}.bad{background:#3a1620;color:var(--red)}
.endpoint{display:flex;gap:6px;align-items:center;flex:1;min-width:280px}
.endpoint input{font-size:12px;padding:3px 8px}
.endpoint .b{flex:2}.endpoint .k{flex:1.2}
main{display:grid;grid-template-columns:minmax(320px,380px) 1fr;
gap:14px;padding:14px;flex:1;min-height:0;overflow:hidden}
.colL,.colR{display:flex;flex-direction:column;gap:14px;min-height:0}
.feedcard{flex:1;min-height:0;display:flex;flex-direction:column}
.rboxcard{flex:0 0 300px;min-height:0;display:flex;flex-direction:column}
@media(max-width:860px){main{grid-template-columns:1fr;overflow-y:auto}}
.card{background:var(--panel);border:1px solid #1E3A47;border-radius:8px;
padding:12px}
h3{margin:0;color:var(--amber);font-size:13px;letter-spacing:.5px}
.step{display:inline-block;background:#123a2e;color:var(--teal);
border-radius:50%;width:18px;height:18px;text-align:center;
line-height:18px;font-size:11px;margin-right:6px}
.secsub{color:var(--dim);font-size:11.5px;font-weight:400}
.hidden{display:none}
.expander{color:var(--dim);font-size:11.5px;cursor:pointer;
padding:4px 6px;text-align:center}
.expander:hover{color:var(--teal)}
.rdet .ans{max-height:110px}
textarea{width:100%;height:90px;background:#0B1620;color:var(--txt);
border:1px solid #1E3A47;border-radius:6px;padding:8px;font:inherit}
input,select{background:#0B1620;color:var(--txt);border:1px solid #1E3A47;
border-radius:5px;padding:4px 6px;font:inherit;width:100%}
button{background:var(--teal);color:#04160f;border:0;border-radius:6px;
padding:8px 14px;font:700 13px Consolas;cursor:pointer;margin-top:8px}
button.ghost{background:#123a2e;color:var(--teal)}
button:disabled{opacity:.4;cursor:wait}
label{display:block;margin:8px 0 3px;color:var(--dim);font-size:12px}
.tool{display:flex;gap:8px;align-items:center;padding:2px 0}
.tool.dis{opacity:.45}
.feed{flex:1;min-height:100px;overflow-y:auto;font-size:12.5px}
#demoPane .feed{min-height:0;max-height:180px}
.ev{padding:3px 6px;border-left:3px solid #1E3A47;margin:3px 0;
white-space:pre-wrap;word-break:break-word}
.ev.local{border-color:#8a7}.ev.gateway{border-color:var(--teal)}
.ev.cap{border-color:var(--red)}
.ev .t{color:var(--dim)} .ev .arm{color:var(--amber)}
.ev.refused{color:var(--red);border-color:var(--red)}
.ev.hl{border-color:var(--amber);background:#1a2b21;color:var(--amber);
font-weight:700}
.ans{white-space:pre-wrap;word-break:break-word;background:#0B1620;
border-radius:6px;padding:10px;margin-top:8px;max-height:260px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:12px}
td,th{padding:3px 8px;text-align:left;border-bottom:1px solid #1E3A47}
th{color:var(--dim);font-weight:400}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.cost{color:var(--amber)}
.rcpt{padding:5px 8px;border-bottom:1px solid #1E3A47;cursor:pointer}
.rcaret{color:var(--dim);display:inline-block;width:14px}
.rcpt:hover{background:#16303d}
.rcpt .meta{color:var(--dim);font-size:11.5px}
.rdet{padding:10px;background:#0B1620;border-radius:6px;margin-top:6px;
font-size:12px;display:none}
.rdet.open{display:block}
.rdet .k{color:var(--dim)} .rdet .hash{color:var(--teal);font-size:11px}
.tag{display:inline-block;background:#123a2e;color:var(--teal);
border-radius:4px;padding:0 6px;font-size:11px;margin-right:4px}
#demoPane{display:none;border-top:1px dashed #1E3A47;margin-top:8px;
padding-top:6px}
#ltable{max-height:280px;overflow-y:auto}
#rbox{flex:1;min-height:0;overflow-y:auto;padding:0 6px}
a{color:var(--teal)}
</style></head><body>
<header><b>local-wilding</b><span>harness console</span>
<span id=keystat class="pill bad">key …</span>
<div class=endpoint>
<input class=b id=epbase placeholder="base url (any OpenAI-compatible)">
<input class=k id=epkey type=password placeholder="api key (memory only)">
<button class=ghost style="width:auto;margin:0" onclick="setEp()">point →</button>
</div>
<button class=ghost style="width:auto;margin:0"
 onclick="demo()">run devs-wilding demo</button></header>
<main>
<div class=colL>
<div class=card><h3><span class=step>1</span>dispatch
<span class=secsub>— any prompt, any endpoint</span></h3>
<textarea id=prompt placeholder="prompt…"></textarea>
<label>model</label><select id=model></select>
<label>budget cap (usd) — reserve before dispatch, refuse on breach</label>
<input id=cap type=number step=0.01 value=0.25>
<label style="cursor:pointer" onclick="toggleTools()">server-side tools
<span id=tsum class=secsub>— probing…</span>
<span id=tcaret style="float:right">▸</span></label>
<div id=tools class=hidden>probing…</div>
<label>arm</label><select id=arm><option value=gateway>endpoint (gateway)</option>
<option value=local>local (free — LOCAL_BASE_URL)</option></select>
<button id=send onclick="send()">dispatch →</button></div>
<div class=card style="padding:0">
<div id=lbar style="display:flex;gap:14px;align-items:center;padding:10px 14px;
 cursor:pointer;user-select:none" onclick="toggleLedger()">
<span style="color:var(--amber)"><span class=step>4</span>spend ledger
<span class=secsub>— enforcement record</span></span>
<span id=lsum style="color:var(--dim);font-size:11.5px">…</span>
<span id=lcaret style="margin-left:auto;color:var(--dim)">▸</span></div>
<div id=ltable style="display:none;padding:0 14px 12px">
<table><tr><th>ts</th><th>event</th><th>label</th><th>est</th>
<th>cost</th><th>spent</th><th>file</th></tr>
<tbody id=ledger></tbody></table></div></div>
</div>
<div class=colR>
<div class="card feedcard"><h3><span class=step>2</span>live feed
<span class=secsub>— events stream as they happen</span></h3>
<div id=feed class=feed></div>
<div id=demoPane><h3>demo — same task, two arms
<span class=secsub>— local 1B (no tools) vs gateway (tools+budget)</span></h3>
<div class=cols><div><label>local — no tools</label>
<div id=dl class=feed></div></div>
<div><label>gateway — tools + budget + receipts</label>
<div id=dg class=feed></div></div></div>
<div id=capfeed></div></div>
<div id=answer></div></div>
<div class="card rboxcard" style="padding:0">
<div id=rbar style="display:flex;gap:14px;align-items:center;padding:10px 14px;
 cursor:pointer;user-select:none" onclick="toggleRbox()">
<span style="color:var(--amber)"><span class=step>3</span>receipt box
<span class=secsub>— one per dispatch, hash-verifiable</span></span>
<span id=rcount style="color:var(--dim)"></span>
<span style="margin-left:auto" onclick="event.stopPropagation()">
<a href="/api/receipts?fmt=jsonl" download>export .jsonl</a> ·
<a href="/api/receipts?fmt=csv" download>export .csv</a></span>
<span id=rcaret2 style="color:var(--dim)">▸</span></div>
<div id=rbox style="display:none"></div></div>
</div>
</main><script>
let job=null;
const $=i=>document.getElementById(i);
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function api(u,o){const r=await fetch(u,o?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)}:undefined);return r.json()}
async function boot(){
 const s=await api('/api/status');
 $('keystat').textContent=s.replay?'replay mode — evidence, no keys'
  :(s.key_set?'key set':'key unset');
 $('keystat').className='pill '+(s.key_set?'ok':'bad');
 $('epbase').value=s.base;
 const tm=await api('/api/models');
 $('model').innerHTML=tm.models.map(m=>`<option>${esc(m)}</option>`).join('');
 const tt=await api('/api/tools');renderTools(tt);
 receipts(); ledger();
 setInterval(()=>{receipts();ledger()},8000);
 const m=location.hash.match(/r_\w+/);
 if(m)setTimeout(()=>openReceipt(m[0]),400)}
function renderTools(tt){
 const ts=tt.tools||[];const on=ts.filter(t=>t.available).length;
 $('tsum').textContent=`— ${on} available`;
 $('tools').innerHTML=ts.map(t=>{
  const dis=t.available===false;
  return `<div class="tool${dis?' dis':''}"><input type=checkbox id=tl_${t.id}
   ${t.available?'checked':''} ${dis?'disabled':''}>
   <span>${esc(t.id)}</span><span style=color:var(--dim)>${esc(t.reason||'')}</span></div>`}).join('')}
function toggleTools(){
 const t=$('tools'),open=!t.classList.contains('hidden');
 t.classList.toggle('hidden',open);
 $('tcaret').textContent=open?'▸':'▾'}
async function setEp(){
 await api('/api/config',{base:$('epbase').value,key:$('epkey').value});
 const tm=await api('/api/models');
 $('model').innerHTML=tm.models.map(m=>`<option>${esc(m)}</option>`).join('');
 const tt=await api('/api/tools');renderTools(tt)}
function evHtml(e){
 const d=e.data||{};let txt=e.ev;
 if(e.ev==='step')txt=`step ${d.step} → ${d.model}`;
 if(e.ev==='tool')txt=`tool ran server-side: ${d.kind}`;
 if(e.ev==='settled')txt=`settled $${(+d.cost_usd).toFixed(4)} served=${d.served}`;
 if(e.ev==='refused')txt=`REFUSED ${d.msg}`;
 if(e.ev==='beat')txt=`▸ ${d.label}`;
 if(e.ev==='skipped')txt=`skipped — ${d.msg}`;
 if(e.ev==='receipt')txt=`receipt minted: ${d.id}`;
 return `<div class="ev ${e.arm} ${e.ev}"><span class=t>${e.t}s</span>
  <span class=arm>${e.arm||''}</span> ${esc(txt)}</div>`}
async function poll(id,feeds){
 const j=await api('/api/job?id='+id);
 (j.events||[]).forEach(e=>{
  if(e._seen)return;e._seen=1;
  const el=(e.arm==='local'&&feeds.dl)||((e.arm==='gateway'||e.arm==='cap')&&feeds.dg)||feeds.main;
  el.insertAdjacentHTML('beforeend',evHtml(e));
  el.scrollTop=el.scrollHeight;
  trimFeed(el)});
 if(j.status==='done'){
  clearInterval(job);job=null;$('send').disabled=false;
  const r=j.result||{};
  const rc=r.receipt||{};
  const el=(feeds.dg&&(r.arm==='gateway'))?feeds.dg
        :((feeds.dl&&(r.arm==='local'))?feeds.dl:feeds.main);
  if(el&&r.ok!==false&&rc.id)el.insertAdjacentHTML('beforeend',
   `<div class="ev hl">✦ served ${esc(rc.model_served||r.model||'')}
    · tools ${esc((rc.tools_ran||[]).join('+')||'none')}
    · $${(+((rc.cost_usd??r.cost_usd)||0)).toFixed(4)}
    · receipt <a href="#${rc.id}">${rc.id}</a></div>`);
  if(r.answer)$('answer').innerHTML=`<div class=ans>${esc(r.answer)}</div>
   <div class=cost>cost $${(r.cost_usd||0).toFixed(4)}${r.refused?' — refused: '+esc(r.refused):''}</div>`;
  else if(r.arms){const g=r.arms.gateway||{},c=r.arms.cap||{};
   $('capfeed').innerHTML=`<div class=ans>local: ${esc((((r.arms||{}).local)||{}).answer||'(skipped)')}</div>
    <div class=ans>gateway: ${esc((g.answer||'').slice(0,900))} <span class=cost>$${(g.cost_usd||0).toFixed(4)}</span></div>
    <div class="ev refused">cap beat: ${esc(c.refused||'(not refused)')}</div>`}
  else if(r.error)$('answer').innerHTML=`<div class=ans style="color:var(--red)">${esc(r.error)}</div>`;
  receipts();ledger()}}
function trimFeed(el){
 const MAX=8,kids=[...el.querySelectorAll('.ev')];
 if(kids.length<=MAX)return;
 kids.slice(0,-MAX).forEach(k=>k.classList.add('hidden'));
 let ex=el.querySelector('.expander');
 if(!ex){ex=document.createElement('div');ex.className='expander';
  ex.onclick=()=>{el.querySelectorAll('.ev.hidden').forEach(k=>
   k.classList.remove('hidden'));ex.remove()};
  el.prepend(ex)}
 ex.textContent=`▸ ${kids.length-MAX} earlier events — show`}
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
async function receipts(){
 const l=await api('/api/receipts');
 const tot=(l.rows||[]).reduce((a,r)=>a+(r.cost_usd||0),0);
 $('rcount').textContent=(l.rows||[]).length+` receipts · $${tot.toFixed(4)} settled`;
 $('rbox').innerHTML=(l.rows||[]).slice().reverse().map(r=>`<div class=rcpt id=${r.id}
  onclick="toggleRcpt('${r.id}')">
  <span class=rcaret id=c_${r.id}>▸</span>
  <b>${esc(r.id)}</b> <span class=tag>${esc(r.arm)}</span>
  <span class=cost>$${(r.cost_usd||0).toFixed(4)}</span>
  <span class=meta>${esc((r.model_served||r.model_requested||'')+' · '+r.endpoint+' · '+new Date(r.ts*1000).toLocaleTimeString())}</span>
  <div class=meta>${esc(r.prompt.slice(0,90))}</div>
  <div class=rdet id=d_${r.id}>
   <div><span class=k>status:</span> ${r.refused?'<span style="color:var(--red)">refused</span>':'ok'} <span class=k>cost:</span> $${(r.cost_usd||0).toFixed(6)}</div>
   <div><span class=k>tools declared:</span> ${esc((r.tools_declared||[]).join(', ')||'none')}</div>
   <div><span class=k>tools ran:</span> ${esc((r.tools_ran||[]).join(', ')||'none')}</div>
   <div><span class=k>prompt_sha:</span> <span class=hash>${r.prompt_sha}</span> <span class=k>answer_sha:</span> <span class=hash>${r.answer_sha}</span></div>
   <div><span class=k>raw:</span> ${esc(r.raw||'—')} <span class=k>job:</span> ${esc(r.job)}</div>
   <div><span class=k>prompt:</span><div class=ans>${esc(r.prompt)}</div></div>
   <div><span class=k>answer:</span><div class=ans>${esc(r.answer||'')}</div></div>
  </div></div>`).join('')}
function toggleRcpt(id){
 const d=$('d_'+id);d.classList.toggle('open');
 const c=$('c_'+id);if(c)c.textContent=d.classList.contains('open')?'▾':'▸';
 if(d.classList.contains('open'))location.hash=id}
function toggleRbox(){
 const b=$('rbox'),open=b.style.display!=='none';
 b.style.display=open?'none':'block';
 $('rcaret2').textContent=open?'▸':'▾'}
function openReceipt(id){
 const el=$(id);if(el){el.scrollIntoView();const d=$('d_'+id);if(d)d.classList.add('open')}}
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
    def _out(self, code: int, body, ctype="application/json",
             fname: str = "") -> None:
        b = body if isinstance(body, bytes) else (
            body.encode() if isinstance(body, str)
            else json.dumps(body).encode())
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        if fname:
            self.send_header("Content-Disposition",
                             f'attachment; filename="{fname}"')
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a) -> None:
        pass

    def do_GET(self) -> None:
        path, _, qs = self.path.partition("?")
        q = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
        if path == "/":
            self._out(200, PAGE, "text/html; charset=utf-8")
        elif path == "/api/status":
            with CFG_LOCK:
                base, model = CFG["base"], CFG["model"]
            c = cfg_client()
            self._out(200, {"key_set": bool(c.api_key) or REPLAY,
                            "base": c.base, "model": model,
                            "local": local_arm.available() or REPLAY,
                            "custom": bool(base), "replay": REPLAY})
        elif path == "/api/tools":
            self._out(200, api_tools())
        elif path == "/api/models":
            self._out(200, api_models())
        elif path == "/api/ledger":
            self._out(200, api_ledger())
        elif path == "/api/receipts":
            rows = read_receipts()
            fmt = q.get("fmt")
            if fmt == "jsonl":
                body = "".join(json.dumps(r) + "\n" for r in rows)
                self._out(200, body, "application/x-ndjson",
                          "receipts.jsonl")
            elif fmt == "csv":
                self._out(200, receipts_csv(rows), "text/csv",
                          "receipts.csv")
            else:
                self._out(200, {"rows": rows})
        elif path == "/api/receipt":
            rid = q.get("id", "")
            hit = next((r for r in read_receipts()
                        if r.get("id") == rid), None)
            self._out(200 if hit else 404, hit or {"error": "not found"})
        elif path == "/api/job":
            jid = q.get("id", "")
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
        if self.path == "/api/config":
            with CFG_LOCK:
                if "base" in body:
                    CFG["base"] = str(body["base"]).rstrip("/")
                if "key" in body:
                    CFG["key"] = str(body["key"])
                if "model" in body:
                    CFG["model"] = str(body["model"])
            self._out(200, {"ok": True, "base": CFG["base"],
                            "key_set": bool(CFG["key"])})
        elif self.path == "/api/send":
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
    print(f"local-wilding console -> http://{HOST}:{PORT}")
    print("endpoint key:", "set" if cfg_client().api_key else "UNSET",
          "| local arm:", "set" if local_arm.available() else "unset")
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
