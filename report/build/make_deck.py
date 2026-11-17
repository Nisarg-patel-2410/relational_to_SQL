"""Phase II presentation (16:9) built with python-pptx."""
import json, os
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt, Emu
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figs")
OUT = os.path.abspath(os.path.join(os.getcwd(), "report", "Relational_Algebra_Explorer_Phase2.pptx"))
M = json.load(open(os.path.join(HERE, "metrics.json"), encoding="utf-8"))
N_TESTS = sum(v["checks"] for v in M["tests"].values())
OPT = M["optimizer"]

INK = RGBColor(0x22, 0x1D, 0x17)
INK_SOFT = RGBColor(0x5A, 0x50, 0x45)
MUTED = RGBColor(0x8D, 0x82, 0x73)
TERRA = RGBColor(0xB8, 0x53, 0x2F)
TERRA_LIGHT = RGBColor(0xE2, 0x82, 0x5D)
SAGE = RGBColor(0x4F, 0x7A, 0x55)
BLUE = RGBColor(0x2D, 0x55, 0x77)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PAPER = RGBColor(0xEC, 0xE4, 0xD6)       # light text on dark slides
CARD = RGBColor(0xF7, 0xF4, 0xEE)        # very light tint for cards on white
LINE = RGBColor(0xDD, 0xD3, 0xC2)
CODEBG = RGBColor(0xF3, 0xEF, 0xE7)
HEAD, BODY, MONO = "Cambria", "Calibri", "Consolas"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
SW, SH = 13.333, 7.5


def txt(slide, x, y, w, h, text, size=16, color=INK, bold=False, font=BODY, align=PP_ALIGN.LEFT,
        anchor=MSO_ANCHOR.TOP, italic=False, name=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name: tb.name = name
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = text if isinstance(text, list) else [text]
    for i, ptxt in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        runs = ptxt if isinstance(ptxt, list) else [(ptxt, {})]
        for rt, ro in runs:
            r = p.add_run(); r.text = rt
            f = r.font; f.size = Pt(ro.get("size", size)); f.bold = ro.get("bold", bold); f.italic = ro.get("italic", italic)
            f.name = ro.get("font", font); f.color.rgb = ro.get("color", color)
        p.space_after = Pt(ro.get("after", 6) if paras else 6)
    return tb


def bullets(slide, x, y, w, h, items, size=16, color=INK, gap=8, name=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name: tb.name = name
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(Emu(Inches(0.28)))); pPr.set("indent", str(-Emu(Inches(0.28))))
        bu = etree.SubElement(pPr, qn("a:buClr")); clr = etree.SubElement(bu, qn("a:srgbClr")); clr.set("val", "B8532F")
        bf = etree.SubElement(pPr, qn("a:buFont")); bf.set("typeface", "Arial")
        bc = etree.SubElement(pPr, qn("a:buChar")); bc.set("char", "•")
        p.space_after = Pt(gap)
        parts = it if isinstance(it, list) else [(it, {})]
        for rt, ro in parts:
            r = p.add_run(); r.text = rt
            f = r.font; f.size = Pt(ro.get("size", size)); f.bold = ro.get("bold", False)
            f.name = ro.get("font", BODY); f.color.rgb = ro.get("color", color)
    return tb


def box(slide, x, y, w, h, fill=CARD, line=None, radius=True, name=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                 Inches(x), Inches(y), Inches(w), Inches(h))
    if radius: shp.adjustments[0] = 0.06
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None: shp.line.fill.background()
    else: shp.line.color.rgb = line; shp.line.width = Pt(1)
    shp.shadow.inherit = False
    if name: shp.name = name
    return shp


def stamp(slide, x, y, sym, d=0.72, dark=False, name="Symbol stamp"):
    c = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    c.fill.solid(); c.fill.fore_color.rgb = INK if dark else WHITE
    c.line.color.rgb = TERRA_LIGHT if dark else TERRA; c.line.width = Pt(1.75); c.shadow.inherit = False
    c.name = name
    tf = c.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = sym; r.font.size = Pt(d * 30); r.font.italic = True
    r.font.name = HEAD; r.font.color.rgb = TERRA_LIGHT if dark else TERRA
    return c


def content_slide(title, sym, notes, kicker=None):
    s = prs.slides.add_slide(BLANK)
    stamp(s, 0.6, 0.42, sym)
    txt(s, 1.55, 0.42, 10.8, 0.72, title, size=30, bold=True, font=HEAD, anchor=MSO_ANCHOR.MIDDLE, name="Title")
    if kicker:
        txt(s, 1.55, 1.12, 10.8, 0.4, kicker, size=15, color=INK_SOFT, italic=True, font=HEAD, name="Subtitle")
    s.notes_slide.notes_text_frame.text = notes
    footer(s)
    return s


def footer(s, dark=False):
    n = len(prs.slides)
    txt(s, 0.6, 7.0, 8, 0.3, "Relational Algebra Explorer · Phase II · MANIT Bhopal", size=10,
        color=MUTED, name="Footer")
    txt(s, 12.0, 7.0, 0.73, 0.3, str(n), size=10, color=MUTED, align=PP_ALIGN.RIGHT, name="Slide number")


def dark_slide(notes):
    s = prs.slides.add_slide(BLANK)
    bg = s.background.fill; bg.solid(); bg.fore_color.rgb = INK
    s.notes_slide.notes_text_frame.text = notes
    return s


def picture(slide, path, x, y, w=None, h=None, border=True, name=None):
    pic = slide.shapes.add_picture(os.path.join(FIG, path), Inches(x), Inches(y),
                                   width=Inches(w) if w else None, height=Inches(h) if h else None)
    if border:
        pic.line.color.rgb = LINE; pic.line.width = Pt(0.75)
    pic.name = name or path
    return pic


def fit(path, max_w, max_h):
    from PIL import Image
    im = Image.open(os.path.join(FIG, path)); ar = im.width / im.height
    return (max_w, max_w / ar) if max_w / ar <= max_h else (max_h * ar, max_h)


def stat(slide, x, y, w, value, label, color=TERRA, size=44):
    txt(slide, x, y, w, 0.8, value, size=size, bold=True, font=HEAD, color=color, name=f"Stat {value}")
    txt(slide, x, y + 0.85, w, 0.7, label, size=13, color=INK_SOFT, name=f"Stat label {value}")


def code(slide, x, y, w, h, lines, size=13, label=None, label_color=INK_SOFT):
    box(slide, x, y, w, h, fill=CODEBG, line=LINE, name=f"Code {label or ''}")
    if label:
        txt(slide, x + 0.2, y + 0.15, w - 0.4, 0.3, label, size=11, bold=True, color=label_color, name="Code label")
    txt(slide, x + 0.2, y + (0.5 if label else 0.2), w - 0.4, h - 0.6, lines, size=size, font=MONO, color=BLUE, name="Code text")


# ═══════════════ 1. Title ═══════════════
s = dark_slide("Introduce the team and the project. Phase I (4th semester) built an RA→SQL converter; Phase II "
               "turns it into a workbench for the whole query-processing pipeline: correct nested translation, "
               "new operators, optimizer, cost estimator, reverse translation and step-through execution.")
stamp(s, 0.9, 0.9, "π", d=1.1, dark=True)
txt(s, 0.9, 2.35, 11.5, 1.5, "Relational Algebra Explorer", size=50, bold=True, font=HEAD, color=PAPER, name="Title")
txt(s, 0.9, 3.45, 11.9, 1.0, "Bidirectional Translation, Cost-Based Optimization and Step-wise Execution of Relational Queries",
    size=20, italic=True, font=HEAD, color=TERRA_LIGHT, name="Subtitle")
txt(s, 0.9, 4.75, 7.5, 1.4, ["Santhosh Lukka · Nikhil Lodhi · Nisarg Kanasagra · Abdulla Bohra",
                             "Guide: Mr. Ashish Kumar Sahu, Assistant Professor"], size=16, color=PAPER, name="Team")
txt(s, 0.9, 6.35, 11.5, 0.6, "B.Tech CSE · 3rd Year, 5th Semester · Phase II · Maulana Azad National Institute of Technology, Bhopal",
    size=13, color=MUTED, name="Institute")

# ═══════════════ 2. Phase I recap + defect ═══════════════
s = content_slide("Phase I worked — until expressions were nested", "σ",
                  "Phase I covered the classical operators. Reviewing it, we found the SQL generator flattened the whole "
                  "tree into one SELECT, keeping only the last projection and selection it saw. Show the example: the "
                  "City condition silently disappears. That is why correctness came first in Phase II.",
                  kicker="Review of the 4th-semester converter at the start of Phase II")
box(s, 0.6, 1.8, 4.6, 4.9, name="Phase I card")
txt(s, 0.85, 2.0, 4.1, 0.4, "Phase I delivered", size=18, bold=True, font=HEAD)
bullets(s, 0.85, 2.55, 4.1, 4.0, ["Recursive-descent parser and AST", "π σ × ⋈ ∪ ∩ − ÷ ρ to SQL",
                                  "Division via double NOT EXISTS", "Expression tree with row counts",
                                  "Deployed web application"], size=16)
txt(s, 5.6, 1.8, 7.1, 0.4, "But the generator flattened the tree", size=18, bold=True, font=HEAD, color=TERRA)
code(s, 5.6, 2.35, 7.1, 0.9, ["π OName (σ City='Bhopal' (σ OID>1 (Owners)))"], size=15, label="EXPRESSION")
code(s, 5.6, 3.4, 7.1, 1.15, ["SELECT OName FROM Owners WHERE OID>1"], size=15, label="PHASE I  ·  City='Bhopal' lost", label_color=TERRA)
code(s, 5.6, 4.7, 7.1, 1.15, ["SELECT DISTINCT OName FROM Owners", "WHERE (OID>1) AND (City='Bhopal')"], size=15,
     label="PHASE II  ·  compositional, correct", label_color=SAGE)
txt(s, 5.6, 6.05, 7.1, 0.6, "Inner π inside joins and qualified names like Owners.OID failed the same way.",
    size=14, italic=True, color=INK_SOFT)

# ═══════════════ 3. Objectives ═══════════════
s = content_slide("Phase II: six things we set out to build", "γ",
                  "Walk through the six objectives quickly; each one gets its own slide later.")
items = [("⋈", "Correct translation", "Compositional SQL for any nesting of operators"),
         ("⟕", "Practical operators", "Theta join, left/right/full outer join, γ grouping"),
         ("σ", "Heuristic optimizer", "9 equivalence rules, every rewrite shown"),
         ("n", "Cost estimator", "n(R), V(A,R) statistics; estimate vs actual per node"),
         ("ρ", "SQL → algebra", "Reverse translation, verified by running both"),
         ("▶", "Explain & step", "Plain-English sentence; execute one operator at a time")]
for i, (sym, head, desc) in enumerate(items):
    cx = 0.6 + (i % 3) * 4.1; cy = 1.85 + (i // 3) * 2.45
    box(s, cx, cy, 3.85, 2.15, name=f"Objective {i+1}")
    stamp(s, cx + 0.3, cy + 0.3, sym, d=0.62, name=f"Objective stamp {i+1}")
    txt(s, cx + 1.1, cy + 0.38, 2.6, 0.5, head, size=18, bold=True, font=HEAD)
    txt(s, cx + 0.3, cy + 1.1, 3.3, 0.9, desc, size=15, color=INK_SOFT)

# ═══════════════ 4. Architecture ═══════════════
s = content_slide("Architecture: one AST shared by every feature", "×",
                  "Three tiers. The browser talks JSON to Flask. Every module — parser, optimizer, cost, SQL→RA, "
                  "explainer — works on the same AST classes. All queries run on a read-only SQLite connection.")
w, h = fit("d01_architecture.png", 8.4, 5.3)
picture(s, "d01_architecture.png", 0.6, 1.55, w, h, border=False)
box(s, 9.35, 1.7, 3.4, 4.9, name="Architecture facts")
txt(s, 9.6, 1.9, 3.0, 0.4, "In numbers", size=18, bold=True, font=HEAD)
stat(s, 9.6, 2.4, 3.0, "7", "Python modules sharing one set of AST node classes", size=36)
stat(s, 9.6, 3.85, 3.0, "8", "REST endpoints, one error handler, read-only execution", size=36)
stat(s, 9.6, 5.3, 3.0, "13", "AST node types, up from 10 in Phase I", size=36, color=SAGE)

# ═══════════════ 5. Pipeline + compositional SQL ═══════════════
s = content_slide("From expression to answer, in both directions", "→",
                  "Tokenize, parse, optionally optimize, generate SQL bottom-up, execute. The reverse path parses SQL "
                  "into the same AST, so explanation, cost and optimization work on pasted SQL too.")
w, h = fit("d02_pipeline.png", 12.1, 3.9)
picture(s, "d02_pipeline.png", 0.6, 1.6, w, h, border=False)
y2 = 1.6 + h + 0.3
for i, (head, desc) in enumerate([("Alias by origin", "A subquery built from Owners is named Owners, so Owners.OID keeps working"),
                                  ("Flatten when safe", "Stacked σ and join chains still give the short SQL a student would write"),
                                  ("Scan conditions properly", "(a ∨ b) ∧ c, IN (…) lists and LOWER(x) now parse inside σ")]):
    box(s, 0.6 + i * 4.1, y2, 3.85, 1.55, name=f"Rule {i+1}")
    txt(s, 0.85 + i * 4.1, y2 + 0.18, 3.4, 0.4, head, size=16, bold=True, font=HEAD, color=TERRA)
    txt(s, 0.85 + i * 4.1, y2 + 0.62, 3.4, 0.9, desc, size=14, color=INK_SOFT)

# ═══════════════ 6. New operators ═══════════════
s = content_slide("New operators that real SQL needs", "⟕",
                  "Theta join with a bracketed condition, three outer joins (natural or conditional) and γ for "
                  "grouping. A σ above γ plays the role of HAVING. Show the outer-join example: owners with no pets.")
rows = [("R ⋈[R.a = S.b] S", "JOIN … ON R.a = S.b"), ("R ⟕ S   R ⟖ S   R ⟗ S", "NATURAL LEFT / RIGHT / FULL JOIN"),
        ("R ⟕[c] S", "LEFT JOIN … ON c"), ("γ dept_id; COUNT(*)→n (students)", "SELECT dept_id, COUNT(*) AS n … GROUP BY dept_id"),
        ("σ n>1 (γ City; COUNT(*)→n (Pets))", "filter on the grouped subquery (HAVING)")]
tbl = s.shapes.add_table(len(rows) + 1, 2, Inches(0.6), Inches(1.75), Inches(7.6), Inches(3.6)).table
tbl.columns[0].width = Inches(3.5); tbl.columns[1].width = Inches(4.1)
for ci, hd in enumerate(["Relational algebra", "SQL"]):
    c = tbl.cell(0, ci); c.text = hd; c.fill.solid(); c.fill.fore_color.rgb = INK
    r = c.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(15); r.font.bold = True; r.font.color.rgb = PAPER; r.font.name = BODY
for ri, (a, b) in enumerate(rows, 1):
    for ci, v in enumerate((a, b)):
        c = tbl.cell(ri, ci); c.text = v; c.fill.solid(); c.fill.fore_color.rgb = CARD if ri % 2 else WHITE
        r = c.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(14); r.font.name = MONO if ci == 0 else BODY
        r.font.color.rgb = BLUE if ci == 0 else INK
txt(s, 8.6, 1.75, 4.1, 0.4, "Example: owners with no pets", size=17, bold=True, font=HEAD)
code(s, 8.6, 2.25, 4.13, 1.25, ["π OName (σ PetID IS NULL", "  (Owners ⟕ Owns))"], size=14, label="RELATIONAL ALGEBRA")
code(s, 8.6, 3.65, 4.13, 1.55, ["SELECT DISTINCT OName", "FROM Owners NATURAL LEFT JOIN Owns", "WHERE PetID IS NULL"], size=13, label="GENERATED SQL")
box(s, 8.6, 5.35, 4.13, 0.9, fill=RGBColor(0xE8, 0xF0, 0xE6), name="Result box")
txt(s, 8.85, 5.5, 3.7, 0.6, [[("Result: ", {"bold": True}), ("Kiran — the only owner without a pet", {})]], size=15, color=SAGE)

# ═══════════════ 7. Optimizer rules ═══════════════
s = content_slide("A heuristic optimizer that shows its work", "σ",
                  "Nine textbook equivalence rules. Selections are split, then each conjunct is pushed as low as "
                  "possible; a conjunct relating both sides of × turns it into a join. Outer joins only let σ through "
                  "to the preserved side. Every rewrite is logged with its law.")
rules = [("R1", "Cascade of σ", "σ c1∧c2 ≡ σ c1 σ c2"), ("R2", "σ through π", "σ c π L ≡ π L σ c"),
         ("R3", "Push σ below ⋈", "σ c (E1⋈E2) ≡ σ c E1 ⋈ E2"), ("R4", "σ over × → ⋈θ", "σ c (E1×E2) ≡ E1 ⋈c E2"),
         ("R5", "Merge into ⋈θ", "σ c (E1⋈θE2) ≡ E1 ⋈θ∧c E2"), ("R6", "Into ∪ ∩ −", "σ c (E1∪E2) ≡ σ c E1 ∪ σ c E2"),
         ("R7", "Below γ", "σ c γ G ≡ γ G σ c  (c on G)"), ("R8", "Cascade of π", "π L1 π L2 ≡ π L1"),
         ("R9", "Combine σ", "σ c1 σ c2 ≡ σ c1∧c2")]
for i, (rid, name, law) in enumerate(rules):
    y = 1.75 + i * 0.55
    txt(s, 0.6, y, 0.6, 0.45, rid, size=14, bold=True, font=MONO, color=TERRA)
    txt(s, 1.2, y, 2.3, 0.45, name, size=15, bold=True)
    txt(s, 3.5, y, 3.5, 0.45, law, size=13, font=MONO, color=BLUE)
w, h = fit("f06_opt_summary.png", 5.4, 5.0)
picture(s, "f06_opt_summary.png", 12.73 - w, 1.7, w, h)

# ═══════════════ 8. Optimizer results chart ═══════════════
s = content_slide("Up to 94% cheaper — with identical results", "÷",
                  "Six benchmark queries. Cost = tuples processed, estimated from catalog statistics. Q1 is a selection "
                  "over a three-way Cartesian product: 768 combinations before filtering in the original plan. "
                  "Every optimized plan returned exactly the same rows — the app checks this by executing both.")
cd = CategoryChartData()
cd.categories = [r["name"] for r in OPT]
cd.add_series("Original plan", [r["c1"] for r in OPT])
cd.add_series("Optimized plan", [r["c2"] for r in OPT])
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.65), Inches(8.3), Inches(5.1), cd)
gf.name = "Cost chart"
ch = gf.chart
ch.has_title = True; ch.chart_title.text_frame.text = "Estimated cost (tuples processed, log scale)"
tr = ch.chart_title.text_frame.paragraphs[0].runs[0]; tr.font.size = Pt(14); tr.font.bold = True; tr.font.name = BODY; tr.font.color.rgb = INK
ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
ch.legend.font.size = Pt(12); ch.legend.font.name = BODY; ch.legend.font.color.rgb = INK_SOFT
for ser, col in zip(ch.plots[0].series, (TERRA, SAGE)):
    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = col
ch.plots[0].gap_width = 60; ch.plots[0].overlap = -5
pl = ch.plots[0]; pl.has_data_labels = True
dl = pl.data_labels; dl.font.size = Pt(11); dl.font.name = BODY; dl.font.color.rgb = INK_SOFT
dl.number_format = '[>=100]#,##0;0.0'; dl.number_format_is_linked = False; dl.position = XL_LABEL_POSITION.OUTSIDE_END
va = ch.value_axis; va.has_major_gridlines = True
va.major_gridlines.format.line.color.rgb = RGBColor(0xE6, 0xDD, 0xCD)
va.tick_labels.font.size = Pt(11); va.tick_labels.font.color.rgb = MUTED; va.tick_labels.font.name = BODY
va.format.line.fill.background()
scaling = va._element.find(qn("c:scaling"))
lb = etree.SubElement(scaling, qn("c:logBase")); lb.set("val", "10")
scaling.remove(lb); scaling.insert(0, lb)
ca = ch.category_axis; ca.tick_labels.font.size = Pt(12); ca.tick_labels.font.name = BODY; ca.tick_labels.font.color.rgb = INK_SOFT
ca.format.line.color.rgb = LINE
q1 = OPT[0]
box(s, 9.3, 1.75, 3.45, 4.9, name="Result callouts")
stat(s, 9.55, 1.95, 3.0, f"−{q1['saving']:.0f}%", f"Q1: {q1['c1']:,.0f} → {q1['c2']} tuples (σ over 3-way ×)", size=48)
stat(s, 9.55, 3.55, 3.0, "6 / 6", "queries return identical rows after rewriting", color=SAGE, size=40)
stat(s, 9.55, 5.05, 3.0, "14–94%", "range of estimated savings across the benchmark", color=INK, size=34)

# ═══════════════ 9. Plans side by side ═══════════════
s = content_slide("The rewrite, side by side", "⋈",
                  "Left: the original plan forms the Cartesian product, then filters. Right: marks >= 90 is applied to "
                  "result before any join, and both equality conditions became theta joins. Each node shows estimated "
                  "rows and cumulative cost.")
w, h = fit("f07_opt_trees.png", 12.1, 5.0)
picture(s, "f07_opt_trees.png", (SW - w) / 2, 1.7, w, h)

# ═══════════════ 10. Cost estimation ═══════════════
s = content_slide("Cost estimation from catalog statistics", "n",
                  "System R style estimates from n(R) and V(A,R). Selection, projection and rename are pipelined and "
                  "free; scans, joins, set ops and γ cost the tuples they read and produce. The tool shows estimate "
                  "next to actual — the grade='A' join is off because grades are not uniform, which is exactly the "
                  "independence assumption failing. Good teaching moment.")
code(s, 0.6, 1.75, 6.0, 3.2, ["σ A=c (R)        n(R) / V(A,R)", "σ A<c (R)        n(R) / 3",
                              "R × S            n(R) · n(S)", "R ⋈ S on A       n(R)·n(S) / max V(A)",
                              "π L (R)          min(n(R), Π V(L))", "γ G (R)          min(n(R), Π V(G))"], size=15,
     label="ESTIMATES")
txt(s, 0.6, 5.15, 6.0, 1.6, [[("Cost model: ", {"bold": True}), ("scans cost n(R); σ, π, ρ are pipelined (free); "
                                                                  "joins, set operations and γ cost input + output tuples.", {})]],
    size=15, color=INK_SOFT)
est = M["estimates"]
rows = [("σ gender='Female' (students)", 4.0, 4), ("students ⋈ result", 16.0, 16), ("γ dept_id; COUNT(*)→n", 3, 3),
        ("Owns ⨝ Pets", 6.0, 6), ("σ Species='Dog' (Pets)", 1.2, 2), ("3-way ⋈ with grade='A'", 1.3, 8)]
tbl = s.shapes.add_table(len(rows) + 1, 3, Inches(7.0), Inches(1.75), Inches(5.73), Inches(3.9)).table
for ci, (hd, wd) in enumerate([("Expression", 3.4), ("Estimated", 1.15), ("Actual", 1.18)]):
    tbl.columns[ci].width = Inches(wd)
    c = tbl.cell(0, ci); c.text = hd; c.fill.solid(); c.fill.fore_color.rgb = INK
    r = c.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(14); r.font.bold = True; r.font.color.rgb = PAPER; r.font.name = BODY
for ri, (e, a, b) in enumerate(rows, 1):
    for ci, v in enumerate((e, a, b)):
        c = tbl.cell(ri, ci); c.text = str(v); c.fill.solid()
        c.fill.fore_color.rgb = (RGBColor(0xF6, 0xE3, 0xDA) if ri == len(rows) else (CARD if ri % 2 else WHITE))
        p = c.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.RIGHT
        r = p.runs[0]; r.font.size = Pt(13); r.font.name = MONO if ci == 0 else BODY; r.font.color.rgb = INK
txt(s, 7.0, 5.85, 5.73, 0.9, "Exact for simple operators; the last row shows the uniformity assumption breaking.",
    size=14, italic=True, color=INK_SOFT)

# ═══════════════ 11. SQL -> RA ═══════════════
s = content_slide("SQL → relational algebra, verified by execution", "ρ",
                  "Paste SQL; it is parsed into the same AST and printed as algebra. Then both the user's SQL and the "
                  "SQL regenerated from the algebra are executed; identical rows mean the translation is verified. "
                  "Unsupported constructs (IN/EXISTS subqueries) get a rewrite hint; ORDER BY / LIMIT are flagged.")
w, h = fit("f08_sql2ra.png", 7.4, 4.6)
picture(s, "f08_sql2ra.png", 0.6, 1.75, w, h)
bullets(s, 8.5, 1.8, 4.2, 3.6, ["FROM a, b → ×;  JOIN ON → ⋈[c]", "LEFT/RIGHT/FULL JOIN → ⟕ ⟖ ⟗", "WHERE → σ;  GROUP BY → γ",
                                "HAVING → σ above γ", "AS x → ρ x;  UNION → ∪", "SQL typed in the main editor is converted automatically"], size=15)
stat(s, 8.5, 5.25, 4.2, f"{len(M['sql2ra'])} / {len(M['sql2ra'])}", "benchmark SQL queries translated and verified", color=SAGE, size=36)

# ═══════════════ 12. Explain + step ═══════════════
s = content_slide("Explain it in English, then run it step by step", "▶",
                  "Every expression gets an English sentence built from the tree. Step-through executes the plan in "
                  "post-order: inputs first. Each step shows what the operator does, actual vs estimated rows with the "
                  "formula, the node's SQL and its intermediate table.")
w, h = fit("f04_step.png", 5.0, 5.15)
picture(s, "f04_step.png", 12.73 - w, 1.65, w, h)
txt(s, 0.6, 1.8, 6.6, 0.4, "Generated explanation", size=17, bold=True, font=HEAD)
box(s, 0.6, 2.3, 6.6, 1.6, fill=CODEBG, line=LINE, name="Explanation example")
txt(s, 0.85, 2.45, 6.1, 1.4, M["translations"][1]["ra"], size=14, font=MONO, color=BLUE)
txt(s, 0.85, 2.95, 6.1, 0.9, "“" + M["translations"][1]["en"] + "”", size=15, italic=True, font=HEAD, color=INK)
txt(s, 0.6, 4.25, 6.6, 0.4, "Step-through execution", size=17, bold=True, font=HEAD)
bullets(s, 0.6, 4.75, 6.6, 2.0, ["Post-order: base tables first, root last", "Actual rows beside estimate and formula",
                                 "Node SQL and intermediate result at every step", "Play, pause, step back"], size=15, gap=5)

# ═══════════════ 13. Robustness ═══════════════
s = content_slide("Robust enough for a classroom", "∩",
                  "We wrote a sweep that throws 203 valid and hostile requests at every endpoint. It found nine "
                  "defects — 500 errors, IN lists, path traversal, unsafe uploads, XSS, a missing γ subtree and two "
                  "UI bugs — all fixed. Queries now always run read-only.")
for i, (v, l, c) in enumerate([(str(N_TESTS), "automated checks, all passing", SAGE), ("9", "defects found by the sweep and fixed", TERRA),
                               ("0", "server errors on malformed input", INK), ("RO", "every query runs on a read-only connection", BLUE)]):
    box(s, 0.6 + i * 3.08, 1.8, 2.85, 2.15, name=f"Stat card {i+1}")
    stat(s, 0.85 + i * 3.08, 1.95, 2.4, v, l, color=c, size=44)
txt(s, 0.6, 4.3, 12.1, 0.4, "Defects fixed", size=17, bold=True, font=HEAD)
bullets(s, 0.6, 4.8, 6.0, 2.0, ["Unknown table/column → HTTP 500  → now a readable 400",
                                "σ x IN (1, 2) parsed the list as a relation", "'?' in strings silently replaced by π"], size=14, gap=4)
bullets(s, 6.75, 4.8, 6.0, 2.0, ["Path traversal and empty-DB creation via header", "Unsanitised, unchecked uploads; HTML injection",
                                 "γ subtree missing; tree lines; popup position"], size=14, gap=4)

# ═══════════════ 14. UI ═══════════════
s = content_slide("A calmer interface, in light and dark", "∪",
                  "Redesigned as a 'scholar's notebook': paper tones, serif headings, ruled editor. Dark theme follows "
                  "the OS and can be toggled. The ER diagram is now drawn from whichever database is selected.")
w, h = fit("f01_interface.png", 6.0, 4.3)
picture(s, "f01_interface.png", 0.6, 1.75, w, h)
picture(s, "f13_dark.png", 0.6 + w + 0.13, 1.75, w, h)
txt(s, 0.6, 1.75 + h + 0.2, 12.1, 0.8, "Live ER diagram from foreign keys · symbol palette with syntax tooltips · examples · "
    "upload your own SQLite database", size=15, color=INK_SOFT)

# ═══════════════ 15. Future work status ═══════════════
s = content_slide("Phase I future work: where it stands", "−",
                  "Two of the five Phase I future-work items are done, one is partly enabled, two remain open.")
status = [("Outer joins", "Done", SAGE, "Natural and conditional, with optimizer support"),
          ("Cost estimator", "Done", SAGE, "Per-node estimates, formulas, plan comparison"),
          ("NL-to-SQL training data", "Partly", TERRA, "SQL → RA yields verified (SQL, RA, English) triples"),
          ("PostgreSQL / MySQL", "Open", MUTED, "SQL generation is centralised; dialects are a contained change"),
          ("Multi-user collaboration", "Open", MUTED, "Not started")]
for i, (item, st_, col, note) in enumerate(status):
    y = 1.8 + i * 0.98
    box(s, 0.6, y, 12.13, 0.82, fill=CARD if i % 2 == 0 else WHITE, line=LINE, name=f"Status row {i+1}")
    txt(s, 0.85, y + 0.2, 3.6, 0.45, item, size=17, bold=True, font=HEAD)
    pill = box(s, 4.6, y + 0.18, 1.3, 0.46, fill=col, name=f"Status pill {i+1}")
    tf = pill.text_frame; tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = st_
    r.font.size = Pt(14); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = BODY
    txt(s, 6.2, y + 0.22, 6.3, 0.45, note, size=15, color=INK_SOFT)

# ═══════════════ 16. Conclusion ═══════════════
s = dark_slide("Summarise: correctness first, then the two core ideas of optimization — equivalence rules and cost "
               "estimation — made visible. Next steps: join ordering, projection push-down, histograms, WHERE "
               "subqueries, dialects and redeployment.")
stamp(s, 0.9, 0.75, "∴", d=0.9, dark=True)
txt(s, 2.05, 0.8, 10.5, 0.8, "Conclusion and next steps", size=36, bold=True, font=HEAD, color=PAPER, anchor=MSO_ANCHOR.MIDDLE)
txt(s, 0.9, 2.0, 5.6, 0.4, "Phase II delivered", size=19, bold=True, font=HEAD, color=TERRA_LIGHT)
bullets(s, 0.9, 2.55, 5.6, 4.2, ["Correct SQL for any nesting of operators", "⋈θ, ⟕ ⟖ ⟗ and γ", "Optimizer with 9 logged rules — up to −94% cost",
                                 "Estimated vs actual rows at every node", "SQL → RA with verification", f"{N_TESTS} automated checks; read-only execution"],
        size=16, color=PAPER, gap=7)
txt(s, 7.0, 2.0, 5.6, 0.4, "Next", size=19, bold=True, font=HEAD, color=TERRA_LIGHT)
bullets(s, 7.0, 2.55, 5.6, 4.2, ["Cost-based join ordering (System R DP)", "Projection push-down below joins",
                                 "Histograms instead of uniformity", "IN / EXISTS → semi- and anti-joins",
                                 "PostgreSQL / MySQL output; redeploy online", "Exercise mode for instructors"], size=16, color=PAPER, gap=7)

# ═══════════════ 17. Thank you ═══════════════
s = dark_slide("Open the live demo: run Q1, click Optimize, then Step through. Paste the JOIN SQL into the SQL → RA card.")
stamp(s, (SW - 1.3) / 2, 1.6, "π", d=1.3, dark=True)
txt(s, 0.6, 3.25, 12.13, 1.0, "Thank you", size=54, bold=True, font=HEAD, color=PAPER, align=PP_ALIGN.CENTER)
txt(s, 0.6, 4.35, 12.13, 0.6, "Questions — and a live demo", size=22, italic=True, font=HEAD, color=TERRA_LIGHT, align=PP_ALIGN.CENTER)
txt(s, 0.6, 5.6, 12.13, 0.5, "python app.py  →  http://127.0.0.1:5000", size=16, font=MONO, color=MUTED, align=PP_ALIGN.CENTER)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
prs.save(OUT)
print("saved", OUT, len(prs.slides), "slides")
