"""Render the report diagrams (diagrams.html) and large ER diagrams with headless Edge."""
import base64, itertools, json, os, subprocess, tempfile, time, urllib.request, pathlib
import websocket

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figs")
m = json.load(open(os.path.join(HERE, "metrics.json"), encoding="utf-8"))
labels = {"Q1": "3-way × with σ", "Q2": "× with σ (2 tables)", "Q3": "⋈ chain with σ", "Q4": "⋈ chain, 2 filters",
          "Q5": "σ over ∪", "Q6": "σ over γ"}
data = [dict(name=r["name"], label=labels[r["name"]], c1=r["c1"], c2=r["c2"], saving=r["saving"]) for r in m["optimizer"]]
html = open(os.path.join(HERE, "diagrams.html"), encoding="utf-8").read().replace("__DATA__", json.dumps(data, ensure_ascii=False))
page = os.path.join(HERE, "diagrams_built.html")
open(page, "w", encoding="utf-8").write(html)

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9334
proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={tempfile.mkdtemp()}",
                         "--hide-scrollbars", "--remote-allow-origins=*", "about:blank"])
for _ in range(50):
    try:
        tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json")); break
    except Exception:
        time.sleep(0.2)
ws = websocket.create_connection(next(t for t in tabs if t["type"] == "page")["webSocketDebuggerUrl"], timeout=60)
ids = itertools.count(1)

def cdp(method, **params):
    i = next(ids); ws.send(json.dumps({"id": i, "method": method, "params": params}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == i:
            if "error" in msg: raise RuntimeError(msg["error"])
            return msg.get("result", {})

def js(expr):
    return cdp("Runtime.evaluate", expression=f"(async()=>{{{expr}}})()", awaitPromise=True, returnByValue=True).get("result", {}).get("value")

def shot(name, sel, scale=2, pad=0):
    r = js(f"const b=document.querySelector({json.dumps(sel)}).getBoundingClientRect();return {{x:b.left+scrollX,y:b.top+scrollY,w:b.width,h:b.height}};")
    d = cdp("Page.captureScreenshot", format="png", captureBeyondViewport=True,
            clip=dict(x=r["x"] - pad, y=r["y"] - pad, width=r["w"] + 2 * pad, height=r["h"] + 2 * pad, scale=scale))["data"]
    open(os.path.join(OUT, name + ".png"), "wb").write(base64.b64decode(d)); print("saved", name)

cdp("Page.enable"); cdp("Runtime.enable")
cdp("Emulation.setDeviceMetricsOverride", width=1240, height=1000, deviceScaleFactor=1, mobile=False)
cdp("Page.navigate", url=pathlib.Path(page).as_uri()); time.sleep(1.5)
shot("d01_architecture", "#arch"); shot("d02_pipeline", "#pipeline"); shot("d03_costchart", "#costchart")

# large ER diagrams through the app's enlarge modal
cdp("Emulation.setDeviceMetricsOverride", width=1440, height=1700, deviceScaleFactor=1, mobile=False)
cdp("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])
cdp("Page.navigate", url="http://localhost:5000/"); time.sleep(3)
js("localStorage.setItem('ra-theme','light'); return 1;"); cdp("Page.reload"); time.sleep(4)
for db, name in [("database.db", "d04_er_university"), ("pets.db", "d05_er_pets")]:
    js(f"const s=document.getElementById('db-select'); s.value={json.dumps(db)}; s.dispatchEvent(new Event('change')); return 1;")
    time.sleep(3)
    js("document.getElementById('er-diagram').click(); return 1;"); time.sleep(1)
    js("const s=document.querySelector('#modal-er-body svg'); s.style.maxHeight='1500px'; s.style.width='1100px'; return 1;"); time.sleep(0.5)
    shot(name, "#modal-er-body", scale=2, pad=8)
    js("document.getElementById('er-modal').classList.add('hidden'); return 1;")
ws.close(); proc.terminate()
