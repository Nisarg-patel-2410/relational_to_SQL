"""Capture high-resolution figures of the running app (http://localhost:5000) with headless Edge over CDP."""
import base64, itertools, json, os, subprocess, tempfile, time, urllib.request
import websocket

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figs")
os.makedirs(OUT, exist_ok=True)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9333
profile = tempfile.mkdtemp(prefix="edgeprof")
proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
                         "--window-size=1440,1000", "--hide-scrollbars", "--force-color-profile=srgb",
                         "--remote-allow-origins=*", "about:blank"])
for _ in range(50):
    try:
        tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
        page = next(t for t in tabs if t["type"] == "page")
        break
    except Exception:
        time.sleep(0.2)
ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=60)
ids = itertools.count(1)


def cdp(method, **params):
    i = next(ids)
    ws.send(json.dumps({"id": i, "method": method, "params": params}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == i:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg.get("result", {})


def js(expr):
    r = cdp("Runtime.evaluate", expression=f"(async () => {{ {expr} }})()", awaitPromise=True, returnByValue=True)
    if r.get("exceptionDetails"):
        raise RuntimeError(r["exceptionDetails"])
    return r.get("result", {}).get("value")


def shot(name, selector=None, pad=10, union=None):
    """Screenshot an element (or several, by union of their boxes) at 2x."""
    sels = union or [selector]
    rect = js("const rs=" + json.dumps(sels) + ".map(s=>document.querySelector(s)).filter(Boolean).map(e=>e.getBoundingClientRect());"
              "const x=Math.min(...rs.map(r=>r.left)),y=Math.min(...rs.map(r=>r.top)),"
              "r=Math.max(...rs.map(r=>r.right)),b=Math.max(...rs.map(r=>r.bottom));"
              "return {x:x+scrollX,y:y+scrollY,w:r-x,h:b-y};")
    clip = dict(x=max(rect["x"] - pad, 0), y=max(rect["y"] - pad, 0), width=rect["w"] + 2 * pad, height=rect["h"] + 2 * pad, scale=2)
    data = cdp("Page.captureScreenshot", format="png", clip=clip, captureBeyondViewport=True)["data"]
    path = os.path.join(OUT, name + ".png")
    open(path, "wb").write(base64.b64decode(data))
    print("saved", name, int(clip["width"]), "x", int(clip["height"]))


def wait(ms):
    js(f"await new Promise(r=>setTimeout(r,{ms})); return 1;")


def run(query, db="database.db"):
    js(f"""const s=document.getElementById('db-select');
           if (s.value !== {json.dumps(db)}) {{ s.value={json.dumps(db)}; s.dispatchEvent(new Event('change')); await new Promise(r=>setTimeout(r,1500)); }}
           document.getElementById('ra-query').value={json.dumps(query)};
           document.getElementById('ra-form').requestSubmit(); return 1;""")
    wait(3000)


cdp("Page.enable"); cdp("Runtime.enable")
cdp("Emulation.setDeviceMetricsOverride", width=1440, height=1000, deviceScaleFactor=2, mobile=False)
cdp("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"}])
cdp("Page.navigate", url="http://localhost:5000/")
wait(3500)
js("localStorage.setItem('ra-theme','light'); document.documentElement.dataset.theme='light'; return 1;")
cdp("Page.reload"); wait(4000)

# 1. full interface (top of page, viewport-sized)
run("π students.name, subject.subject_name (σ grade='A' (students ⋈ result ⋈ subject))")
js("window.scrollTo(0,0); return 1;"); wait(400)
data = cdp("Page.captureScreenshot", format="png", clip=dict(x=0, y=0, width=1440, height=1000, scale=1.4))["data"]
open(os.path.join(OUT, "f01_interface.png"), "wb").write(base64.b64decode(data)); print("saved f01_interface")

# 2. editor + generated SQL + English
shot("f02_editor_sql", union=[".editor-card", ".sql-card"])
# 3. expression tree with estimates
shot("f03_tree", ".tree-card")
# 4. step-through panel (step 4 of the join query)
js("document.getElementById('step-first').click(); for (let i=0;i<3;i++) document.getElementById('step-next').click(); return 1;"); wait(600)
shot("f04_step", ".tree-card")
# 5. results table
shot("f05_results", ".rows-card")

# 6. optimizer on the cross-product query
run("π name, subject_name, marks (σ students.student_id = result.student_id ∧ result.subject_id = subject.subject_id ∧ marks >= 90 (students × result × subject))")
js("document.getElementById('optimize-btn').click(); return 1;"); wait(3500)
shot("f06_opt_summary", union=[".opt-card .card-header", "#opt-summary", "#opt-steps"])
js("document.querySelectorAll('.opt-tree').forEach(e=>{e.style.maxHeight='none';e.style.overflow='visible'}); return 1;"); wait(800)
shot("f07_opt_trees", ".opt-trees")

# 7. SQL -> RA with verification
js("""document.getElementById('sql-input').value="SELECT s.name, d.dept_name FROM students s JOIN department d ON s.dept_id = d.dept_id WHERE s.gender = 'Female'";
      document.getElementById('sql2ra-btn').click(); return 1;"""); wait(2500)
shot("f08_sql2ra", ".sql2ra-card")

# 8. gamma + outer join tree on pets db, plus ER diagram
run("σ n > 1 (γ City; COUNT(*)→n (Pets))", db="pets.db")
shot("f09_gamma_tree", union=[".sql-card", ".tree-card"])
run("π OName (σ PetID IS NULL (Owners ⟕ Owns))", db="pets.db")
shot("f10_outer", union=[".sql-card"])
shot("f11_er_pets", ".er-card")
run("π name, email (professor)", db="database.db"); wait(1500)
shot("f12_er_uni", ".er-card")

# 9. dark theme glimpse
js("document.getElementById('theme-toggle').click(); return 1;"); wait(1500)
run("π name, dept_name (σ students.dept_id = department.dept_id ∧ gender='Female' (students × department))")
js("window.scrollTo(0,0); return 1;"); wait(400)
data = cdp("Page.captureScreenshot", format="png", clip=dict(x=0, y=0, width=1440, height=1000, scale=1.4))["data"]
open(os.path.join(OUT, "f13_dark.png"), "wb").write(base64.b64decode(data)); print("saved f13_dark")
js("document.getElementById('theme-toggle').click(); return 1;")

# 10. error message
run("π name (nosuchtable)")
shot("f14_error", ".editor-card")

ws.close()
proc.terminate()
