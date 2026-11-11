# provenance: author=devin; created=2026-11-10; source=operator-approved v8 storyboard; purpose=scripted browser capture of the console beats for the devs-wilding video; intent=production-tooling
"""v8 console-cut capture: playwright records the UI through each storyboard
beat; card beats render as styled HTML screenshots. Output -> shots_v8/."""
import os, time, json
from playwright.sync_api import sync_playwright

W, H = 1600, 900
OUT = "shots_v8"
BASE = "http://127.0.0.1:8788"
CLAIM = ("Verify this claim: 'The population of India grew more than 15% "
         "between 2015 and 2023.' Find official figures, do the math in code, "
         "and give a verdict with sources.")

# beat durations come from vo_clone measurements
DUR = {"b0": 10.2, "b1": 8.4, "b2": 23.4, "b3": 20.9,
       "b4": 9.4, "b5": 7.9, "b6": 4.2, "b7": 8.4}

INJECT = """(() => {
  const s=document.createElement('style'); s.textContent=`
   #lwcursor{position:fixed;left:0;top:0;width:18px;height:18px;
    border:3px solid #3FD9A8;border-radius:50%;
    background:rgba(63,217,168,.28);z-index:99999;pointer-events:none;
    transition:transform .45s cubic-bezier(.35,0,.2,1);
    transform:translate(-60px,-60px)}
   .lw-spot{outline:2px solid #3FD9A8!important;outline-offset:4px;
    box-shadow:0 0 26px rgba(63,217,168,.45)!important;border-radius:6px}`;
  document.head.appendChild(s);
  const c=document.createElement('div'); c.id='lwcursor';
  document.body.appendChild(c);
})()"""

JS_CURSOR = """sel=>{
 const el=document.querySelector(sel); if(!el)return;
 const r=el.getBoundingClientRect();
 document.getElementById('lwcursor').style.transform=
  `translate(${r.left+r.width/2-9}px,${r.top+r.height/2-9}px)`;}"""

JS_SPOT = """([sel,on])=>{
 const el=document.querySelector(sel); if(!el)return;
 el.classList.toggle('lw-spot',!!on);}"""

CSS = """body{margin:0;background:#0D1B26;color:#DFF4EE;
 font-family:Segoe UI,system-ui,sans-serif;display:flex;align-items:center;
 justify-content:center;height:100vh}
.card{max-width:1100px;padding:64px 72px;background:#12242F;border-radius:14px;
 border:1px solid #1d3a47}
h1{font-size:44px;margin:0 0 26px;color:#DFF4EE;font-weight:600;line-height:1.25}
.big{font-size:56px;color:#E8455F;font-weight:700;margin:14px 0}
.teal{color:#3FD9A8}.amber{color:#FFCF6B}.dim{color:#7FA8A0;font-size:24px}
.code{font-family:Consolas,monospace;font-size:30px;background:#0b1620;
 border-radius:8px;padding:14px 22px;margin:12px 0;color:#3FD9A8}
.steps{display:flex;gap:18px;align-items:center;font-size:26px}
.steps .code{flex:1}
.tag{position:fixed;top:34px;left:44px;font-family:Consolas,monospace;
 font-size:22px;color:#3FD9A8;letter-spacing:2px}
"""

CARDS = {
 "b0": f"""<div class=tag>local-wilding</div><div class=card>
  <h1>a 1B model answered this claim —<br>and cited its sources.</h1>
  <div class=big>none of the sources exist.</div>
  <div class=dim>the answer was fluent, confident — and fabricated.</div></div>""",
 "b8": f"""<div class=tag>local-wilding</div><div class=card>
  <h1>the honest limits</h1>
  <div class=code>replay mode — recorded evidence, no keys, no spend</div>
  <div class=code>live mode — your endpoint, your key, real settle</div>
  <div class=code>receipts mint per job — per-step is the next pass</div>
  <div class=dim style="margin-top:22px">printed where you can see them — not buried in a readme.</div></div>""",
 "b9": f"""<div class=tag>local-wilding</div><div class=card>
  <div class=steps>
   <div class=code>git clone</div><span class=dim>→</span>
   <div class=code>pip install -r requirements.txt</div><span class=dim>→</span>
   <div class=code>python app.py</div><span class=dim>→</span>
   <div class=code teal>click</div></div>
  <div class=dim style="margin-top:22px">three lines. the console opens. the demo is one button.</div></div>""",
 "b10": f"""<div class=tag>local-wilding</div><div class=card>
  <h1>tools · budgets · <span class=teal>receipts</span> · a local control arm</h1>
  <div class=dim>every dispatch mints a hash-verifiable receipt linked to raw evidence.<br>
  honest limits, printed where you can see them.</div>
  <div class=code style="margin-top:26px">local-wilding — the entry you can clone and run</div></div>""",
}


def prep(page):
    page.goto(BASE)
    page.wait_for_selector("#send")
    page.wait_for_timeout(900)
    page.evaluate(INJECT)
    page.wait_for_timeout(300)


def cursor(page, sel, dwell=500):
    page.evaluate(JS_CURSOR, sel)
    page.wait_for_timeout(dwell)


def spot(page, sel, on=True):
    page.evaluate(JS_SPOT, [sel, on])


def shoot(page_fn, name):
    """record one beat context → webm"""
    ctx = browser.new_context(
        viewport={"width": W, "height": H},
        record_video_dir=os.path.join(OUT, name),
        record_video_size={"width": W, "height": H},
        device_scale_factor=1,
    )
    page = ctx.new_page()
    page_fn(page)
    ctx.close()  # finalizes webm


def shot_card(name, html):
    ctx = browser.new_context(viewport={"width": W, "height": H},
                              device_scale_factor=1)
    page = ctx.new_page()
    page.set_content(f"<style>{CSS}</style>{html}")
    page.wait_for_timeout(400)
    page.screenshot(path=os.path.join(OUT, f"{name}.png"))
    ctx.close()


import sys, json, random
ONLY = set(sys.argv[1:]) or None


def human_type(page, sel, text):
    """bursty typing: variable per-char delay, pauses at word edges"""
    el = page.locator(sel)
    el.click()
    for ch in text:
        el.press_sequentially(ch, delay=0)
        wait = random.gauss(48, 22)
        if ch in " ,.':":
            wait += random.uniform(60, 240)
        if random.random() < 0.03:
            wait += random.uniform(150, 420)
        page.wait_for_timeout(max(28, wait))


def want(name):
    return ONLY is None or name in ONLY


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    os.makedirs(OUT, exist_ok=True)

    # ---- cards ----
    for name, html in CARDS.items():
        if want(name):
            shot_card(name, html)
            print("card", name)

    # ---- b1 console reveal + endpoint tour ----
    def b1(p):
        prep(p)
        cursor(p, "#epbase", 700); spot(p, ".endpoint")
        p.wait_for_timeout(1600)
        cursor(p, ".endpoint button", 600)
        p.wait_for_timeout(900); spot(p, ".endpoint", False)
        cursor(p, "#model", 700); spot(p, "#model")
        p.wait_for_timeout(1400); spot(p, "#model", False)
        cursor(p, "#cap", 600); spot(p, "#cap")
        p.wait_for_timeout(1500); spot(p, "#cap", False)
        cursor(p, "#arm", 700); spot(p, "#arm")
        p.wait_for_timeout(1600); spot(p, "#arm", False)
        cursor(p, "#prompt", 700)
        p.wait_for_timeout(1800)
    if want("b1"):
        shoot(b1, "b1")

    # ---- b2 live send -> receipt ----
    def b2(p):
        prep(p)
        cursor(p, "#prompt", 600)
        human_type(p, "#prompt", CLAIM)
        p.wait_for_timeout(700)
        cursor(p, "#send", 500); spot(p, "#send")
        p.wait_for_timeout(400); spot(p, "#send", False)
        p.click("#send")
        try:
            p.wait_for_selector("#feed .ev.hl", timeout=25000)
        except Exception:
            pass
        p.wait_for_timeout(900)
        cursor(p, "#feed .ev.hl a", 700); spot(p, "#feed .ev.hl")
        p.wait_for_timeout(1000); spot(p, "#feed .ev.hl", False)
        cursor(p, "#rbar", 600)
        p.click("#rbar")
        p.wait_for_timeout(700)
        cursor(p, "#rbox .rcpt", 600)
        p.click("#rbox .rcpt")
        p.wait_for_timeout(1800)
    if want("b2"):
        shoot(b2, "b2")

    # ---- b3 demo split-feed ----
    def b3(p):
        prep(p)
        cursor(p, "button[onclick='demo()']", 600)
        p.click("button[onclick='demo()']")
        # watch the streams a moment, then tour the columns
        p.wait_for_timeout(4000)
        cursor(p, "#dl", 800); spot(p, "#dl")
        p.wait_for_timeout(1500); spot(p, "#dl", False)
        cursor(p, "#dg", 800); spot(p, "#dg")
        try:
            p.wait_for_selector("#dg .ev.hl, #capfeed .ans", timeout=9000)
        except Exception:
            pass
        p.wait_for_timeout(1300); spot(p, "#dg", False)
        cursor(p, "#capfeed", 800); spot(p, "#capfeed")
        p.wait_for_timeout(1600); spot(p, "#capfeed", False)
        # dwell on the local arm's flawed answer — scroll it into view
        p.evaluate("document.querySelector('#answer')?.scrollIntoView()")
        spot(p, "#answer")
        p.wait_for_timeout(3500); spot(p, "#answer", False)
        p.wait_for_timeout(1200)
    if want("b3"):
        shoot(b3, "b3")

    # ---- b4 refusal ----
    def b4(p):
        prep(p)
        cursor(p, "#cap", 500)
        p.fill("#cap", "0.01")
        p.wait_for_timeout(700)
        cursor(p, "#send", 500)
        p.click("#send")
        try:
            p.wait_for_selector(".ev.refused, #answer .cost", timeout=6000)
        except Exception:
            pass
        p.wait_for_timeout(1500)
        cursor(p, "#lbar", 700); spot(p, "#lbar")
        p.wait_for_timeout(1600); spot(p, "#lbar", False)
        p.wait_for_timeout(900)
    if want("b4"):
        shoot(b4, "b4")

    # ---- b5 receipt box ----
    def b5(p):
        prep(p)
        cursor(p, "#rbar", 600)
        p.click("#rbar")
        p.wait_for_timeout(700)
        cursor(p, "#rbox .rcpt", 600)
        p.click("#rbox .rcpt")
        p.wait_for_timeout(800)
        cursor(p, "#rbox .rcpt .hash", 800); spot(p, "#rbox .rcpt .rdet")
        p.wait_for_timeout(1900); spot(p, "#rbox .rcpt .rdet", False)
        cursor(p, "a[href*='jsonl']", 900)
        p.wait_for_timeout(900)
        with p.expect_download() as dl:
            p.click("a[href*='jsonl']")
        dl.value.save_as(os.path.join(OUT, "receipts_export.jsonl"))
        p.wait_for_timeout(1400)
    if want("b5"):
        shoot(b5, "b5")

    # ---- b6 evidence walk — scroll the real raw response ----
    def b6(p):
        raw = json.load(open("evidence/01_step1_openai_gpt-oss-120b.json"))
        body = json.dumps(raw["body"], indent=2)[:4000]
        p.set_content(f"""<style>{CSS}
         .term{{font-family:Consolas,monospace;font-size:15px;background:#0B1620;
          border:1px solid #1d3a47;border-radius:10px;padding:26px 30px;
          width:1280px;margin:40px auto;color:#DFF4EE;white-space:pre-wrap}}
         .path{{color:#3FD9A8;font-family:Consolas,monospace;font-size:20px;
          text-align:center;margin-top:60px}}</style>
         <div class=tag>local-wilding</div>
         <div class=path>evidence/console_raw — the bytes the endpoint returned</div>
         <div class=term id=t>{body}</div>
         <script>setInterval(()=>{{window.scrollBy(0,3)}},60)</script>""")
        p.wait_for_timeout(14000)
    if want("b6"):
        shoot(b6, "b6")

    # ---- b7 self-score — real certificate output, line reveal ----
    def b7(p):
        import subprocess
        out = subprocess.run([sys.executable, "sphere_fitness.py"],
                             capture_output=True, text=True).stdout
        lines = "".join(f"<div class=ln>{l}</div>"
                        for l in out.strip().splitlines())
        p.set_content(f"""<style>{CSS}
         .term{{font-family:Consolas,monospace;font-size:17px;background:#0B1620;
          border:1px solid #1d3a47;border-radius:10px;padding:30px 36px;
          width:900px;margin:80px auto;color:#DFF4EE}}
         .ln{{opacity:0;animation:rv .4s forwards}}
         @keyframes rv{{to{{opacity:1}}}}
         .cmd{{color:#3FD9A8}}</style>
         <div class=tag>local-wilding</div>
         <div class=term><div class="ln cmd">$ python sphere_fitness.py</div>{lines}</div>
         <script>document.querySelectorAll('.ln').forEach(
           (l,i)=>l.style.animationDelay=(i*0.55)+'s')</script>""")
        p.wait_for_timeout(15000)
    if want("b7"):
        shoot(b7, "b7")

    browser.close()
print("done ->", OUT)
