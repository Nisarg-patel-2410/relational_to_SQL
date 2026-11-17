"""
Builds the Phase II project report (MANIT format) as .docx.
Fields (TOC, lists of figures/tables, page numbers) are filled in afterwards by Word.
"""
import json, os, re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, RGBColor, Emu

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figs")
OUT = os.path.abspath(os.path.join(os.getcwd(), "report", "MANIT_Report_Phase2_sem_5.docx"))
M = json.load(open(os.path.join(HERE, "metrics.json"), encoding="utf-8"))

# ── report facts (edit here) ─────────────────────────────────────────────
TITLE = ("Relational Algebra Explorer: Bidirectional Translation, Cost-Based Optimization "
         "and Step-wise Execution of Relational Queries")
STUDENTS = [("Santhosh Lukka", "24112011130"), ("Nikhil Lodhi", "24112011129"),
            ("Nisarg Kanasagra", "24112011136"), ("Abdulla Bohra", "24112011138")]
GUIDE = ("Mr. Ashish Kumar Sahu", "Assistant Professor")
YEAR_SEM = "B.Tech 3rd Year, 5th Semester"
PERIOD = ("1 July 2026", "31 December 2026")
DATE = "17 November 2026"
SESSION = "2026–27"
HINDI_INST = "मौलाना आजाद राष्ट्रीय प्रौद्योगिकी संस्थान - भोपाल"
HINDI_DEPT = "कंप्यूटर विज्ञान और अभियांत्रिकी विभाग"

T = M["tests"]
N_TESTS = sum(v["checks"] for v in T.values())
OPT = M["optimizer"]

doc = Document()

# ── page setup & styles ─────────────────────────────────────────────────
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
sec.left_margin, sec.right_margin = Inches(1.25), Inches(1.0)
sec.top_margin, sec.bottom_margin = Inches(1.0), Inches(1.0)
TEXT_W = 8.27 - 2.25


def set_cs_font(rpr_owner, name):
    rpr = rpr_owner.get_or_add_rPr() if hasattr(rpr_owner, "get_or_add_rPr") else rpr_owner
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts"); rpr.append(fonts)
    for k in ("w:ascii", "w:hAnsi", "w:eastAsia"):
        fonts.set(qn(k), name)
    fonts.set(qn("w:cs"), "Mangal")
    for k in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):   # theme fonts override explicit ones
        if fonts.get(qn(k)) is not None:
            del fonts.attrib[qn(k)]


st = doc.styles
normal = st["Normal"]
normal.font.name = "Times New Roman"; normal.font.size = Pt(12)
set_cs_font(normal.element.get_or_add_rPr(), "Times New Roman")
pf = normal.paragraph_format
pf.line_spacing = 1.5; pf.space_after = Pt(6); pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

for name, size, before, after, align in [("Heading 1", 16, 0, 18, WD_ALIGN_PARAGRAPH.CENTER),
                                         ("Heading 2", 14, 18, 8, WD_ALIGN_PARAGRAPH.LEFT),
                                         ("Heading 3", 12, 12, 6, WD_ALIGN_PARAGRAPH.LEFT)]:
    h = st[name]
    h.font.name = "Times New Roman"; h.font.size = Pt(size); h.font.bold = True
    h.font.color.rgb = RGBColor(0, 0, 0); h.font.italic = False
    set_cs_font(h.element.get_or_add_rPr(), "Times New Roman")
    h.paragraph_format.space_before = Pt(before); h.paragraph_format.space_after = Pt(after)
    h.paragraph_format.keep_with_next = True; h.paragraph_format.alignment = align
    h.paragraph_format.line_spacing = 1.3

from docx.enum.style import WD_STYLE_TYPE
for cname in ("Figure Caption", "Table Caption"):
    cs = st.add_style(cname, WD_STYLE_TYPE.PARAGRAPH)
    cs.base_style = normal
    cs.font.size = Pt(11); cs.font.bold = False
    cs.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cs.paragraph_format.line_spacing = 1.15
    cs.paragraph_format.space_before = Pt(4); cs.paragraph_format.space_after = Pt(12)
    cs.paragraph_format.first_line_indent = Inches(0)
st["Table Caption"].paragraph_format.keep_with_next = True
st["Table Caption"].paragraph_format.space_after = Pt(6)


# ── helpers ──────────────────────────────────────────────────────────────
def add_field(paragraph, instr, placeholder=""):
    r = paragraph.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); r._r.append(b)
    r2 = paragraph.add_run()
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr; r2._r.append(it)
    r3 = paragraph.add_run()
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate"); r3._r.append(s)
    paragraph.add_run(placeholder)
    r5 = paragraph.add_run()
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r5._r.append(e)


TOKEN = re.compile(r"(\*\*.+?\*\*|`.+?`|\*.+?\*)")


def runs(par, text, size=None, bold=None):
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**"):
            r = par.add_run(part[2:-2]); r.bold = True
        elif part.startswith("`"):
            r = par.add_run(part[1:-1]); r.font.name = "Consolas"; r.font.size = Pt((size or 12) - 1.5)
            set_cs_font(r._r.get_or_add_rPr(), "Consolas")
        elif part.startswith("*") and len(part) > 2:
            r = par.add_run(part[1:-1]); r.italic = True
        else:
            r = par.add_run(part)
        if size and not part.startswith("`"):
            r.font.size = Pt(size)
        if bold:
            r.bold = True
    return par


def P(text, indent=True, align=None, size=None, after=None, keep=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.first_line_indent = Inches(0.5)
    if align is not None:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if keep:
        p.paragraph_format.keep_with_next = True
    return runs(p, text, size=size)


def bullets(items, numbered=False):
    style = "List Number" if numbered else "List Bullet"
    for it in items:
        p = doc.add_paragraph(style=style)
        p.paragraph_format.space_after = Pt(3); p.paragraph_format.line_spacing = 1.4
        runs(p, it)


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def chapter(n, title):
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.page_break_before = True
    p.add_run(f"CHAPTER {n}")
    p.add_run().add_break()
    p.add_run(title)


def front_heading(title):
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.page_break_before = True
    p.add_run(title)


def H2(t): doc.add_paragraph(t, style="Heading 2")
def H3(t): doc.add_paragraph(t, style="Heading 3")


def cell_shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def table(caption, headers, rows, widths, code_cols=(), size=10, align_cols=None):
    cp = doc.add_paragraph(style="Table Caption"); runs(cp, caption)
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl = t._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge, sz, color in [("top", 12, "000000"), ("bottom", 12, "000000"), ("insideH", 4, "BFBFBF")]:
        el = OxmlElement(f"w:{edge}"); el.set(qn("w:val"), "single"); el.set(qn("w:sz"), str(sz)); el.set(qn("w:color"), color)
        borders.append(el)
    for edge in ("left", "right", "insideV"):
        el = OxmlElement(f"w:{edge}"); el.set(qn("w:val"), "nil"); borders.append(el)
    tblPr.append(borders)
    for ri, row in enumerate([headers] + rows):
        for ci, val in enumerate(row):
            c = t.cell(ri, ci)
            c.width = Inches(widths[ci])
            p = c.paragraphs[0]
            p.paragraph_format.first_line_indent = Inches(0)
            p.paragraph_format.line_spacing = 1.1
            p.paragraph_format.space_after = Pt(2); p.paragraph_format.space_before = Pt(2)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if (align_cols is None or align_cols[ci] == "l") else (
                WD_ALIGN_PARAGRAPH.CENTER if align_cols[ci] == "c" else WD_ALIGN_PARAGRAPH.RIGHT)
            if ri == 0:
                r = p.add_run(str(val)); r.bold = True; r.font.size = Pt(size)
                cell_shade(c, "EFEFEF")
            elif ci in code_cols:
                r = p.add_run(str(val)); r.font.name = "Consolas"; r.font.size = Pt(size - 1)
                set_cs_font(r._r.get_or_add_rPr(), "Consolas")
            else:
                runs(p, str(val), size=size)
    # repeat header row
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for r in t.rows:
        cant = OxmlElement("w:cantSplit"); cant.set(qn("w:val"), "true"); r._tr.get_or_add_trPr().append(cant)
    sp = doc.add_paragraph(); sp.paragraph_format.space_after = Pt(4); sp.paragraph_format.line_spacing = 1.0
    return t


def figure(path, caption, width=6.0):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Inches(0); p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(6); p.paragraph_format.line_spacing = 1.0
    p.add_run().add_picture(os.path.join(FIG, path), width=Inches(width))
    cp = doc.add_paragraph(style="Figure Caption"); runs(cp, caption)


def letterhead():
    for text, font, size, bold in [(HINDI_INST, "Mangal", 15, False),
                                   ("Maulana Azad National Institute of Technology – Bhopal", "Times New Roman", 14, True)]:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(2)
        r = p.add_run(text); r.font.size = Pt(size); r.bold = bold
        if font == "Mangal":
            rpr = r._r.get_or_add_rPr(); f = OxmlElement("w:rFonts")
            f.set(qn("w:ascii"), "Mangal"); f.set(qn("w:hAnsi"), "Mangal"); f.set(qn("w:cs"), "Mangal"); rpr.append(f)
            szcs = OxmlElement("w:szCs"); szcs.set(qn("w:val"), str(size * 2)); rpr.append(szcs)
    doc.add_paragraph()
    for text, font, size, bold in [("Department of Computer Science and Engineering", "Times New Roman", 13, True),
                                   (HINDI_DEPT, "Mangal", 12, False)]:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(2)
        r = p.add_run(text); r.font.size = Pt(size); r.bold = bold
        if font == "Mangal":
            rpr = r._r.get_or_add_rPr(); f = OxmlElement("w:rFonts")
            f.set(qn("w:ascii"), "Mangal"); f.set(qn("w:hAnsi"), "Mangal"); f.set(qn("w:cs"), "Mangal"); rpr.append(f)
            szcs = OxmlElement("w:szCs"); szcs.set(qn("w:val"), str(size * 2)); rpr.append(szcs)


def rule():
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr(); bd = OxmlElement("w:pBdr"); b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single"); b.set(qn("w:sz"), "8"); b.set(qn("w:space"), "1"); b.set(qn("w:color"), "000000")
    bd.append(b); pPr.append(bd)


def page_numbers(section, fmt, start=1):
    sectPr = section._sectPr
    pg = sectPr.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType"); sectPr.append(pg)
    pg.set(qn("w:fmt"), fmt); pg.set(qn("w:start"), str(start))
    section.footer.is_linked_to_previous = False
    fp = section.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in list(fp.runs):
        r._r.getparent().remove(r._r)
    add_field(fp, "PAGE", "1")


names_list = ", ".join(f"{n} ({s})" for n, s in STUDENTS[:-1]) + f", and {STUDENTS[-1][0]} ({STUDENTS[-1][1]})"

# ═════════════════════════════ FRONT MATTER ═══════════════════════════════
# Certificate
letterhead()
p = doc.add_paragraph(style="Heading 1"); p.paragraph_format.space_before = Pt(18); p.paragraph_format.space_after = Pt(6)
r = p.add_run("CERTIFICATE"); r.font.size = Pt(14)
rule()
P(f"This is to certify that {names_list}, students of {YEAR_SEM} (Computer Science & Engineering), "
  f"have successfully completed their project \"{TITLE}\" in partial fulfilment of their Bachelor of "
  f"Technology in Computer Science & Engineering. This work extends the project carried out by the same "
  f"group in the 4th Semester.")
for _ in range(3):
    doc.add_paragraph()
for i, line in enumerate([GUIDE[0], GUIDE[1], "Department of Computer Science and Engineering", "MANIT Bhopal"]):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.2
    r = p.add_run(line); r.bold = i == 0

# Declaration
page_break()
letterhead()
p = doc.add_paragraph(style="Heading 1"); p.paragraph_format.space_before = Pt(18); p.paragraph_format.space_after = Pt(6)
r = p.add_run("DECLARATION"); r.font.size = Pt(14)
rule()
P(f"We hereby declare that the work presented in this Project Report, entitled \"{TITLE}\", in partial "
  f"fulfilment of the requirements for the award of the degree, submitted in the Department of Computer Science "
  f"and Engineering, Maulana Azad National Institute of Technology, Bhopal, is an authentic record of our work "
  f"carried out from {PERIOD[0]} to {PERIOD[1]} under the noble guidance of our guide {GUIDE[0]}. The following "
  f"project and its report, in part or whole, have not been presented or submitted by us for any purpose in any "
  f"other institute or organization. We hereby declare that the facts mentioned above are true to the best of our "
  f"knowledge. In case of any unlikely discrepancy that may possibly occur, we will be the ones to take responsibility.")
doc.add_paragraph()
t = doc.add_table(rows=2, cols=2)
for i, (n, s) in enumerate(STUDENTS):
    c = t.cell(i // 2, i % 2)
    c.paragraphs[0].paragraph_format.first_line_indent = Inches(0)
    c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = c.paragraphs[0].add_run(n); rr.bold = True
    p2 = c.add_paragraph(f"Scholar No. {s}"); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.first_line_indent = Inches(0); p2.paragraph_format.space_after = Pt(14)
doc.add_paragraph()
P(f"Place: Bhopal", indent=False, after=0)
P(f"Date: {DATE}", indent=False)

# Acknowledgement
front_heading("ACKNOWLEDGEMENT")
P(f"We consider it a great privilege to express our heartfelt and sincere gratitude to our esteemed mentor and "
  f"guide, {GUIDE[0]}, {GUIDE[1]}, Department of Computer Science and Engineering, MANIT Bhopal. His guidance "
  f"through both phases of this project — from the first converter built in the 4th Semester to the optimizer, "
  f"cost estimator and reverse translator presented here — shaped every major design decision. His insistence "
  f"on theoretical rigour pushed us to ground each new feature in the equivalence rules and estimation formulas "
  f"of database theory rather than in ad-hoc heuristics, and his feedback on the first phase directly defined the "
  f"agenda of the second.")
P("We are also grateful to our respected Director for permitting us to utilize all the necessary college facilities "
  "and resources, and to the Head of the Department for allowing us to use the departmental laboratories and other "
  "services throughout the project duration.")
P("We are thankful to all the faculty members, staff, and laboratory attendants of our department for their "
  "cooperation, technical assistance, and encouragement at every stage of this project. Finally, we express our deep "
  "appreciation to our family members and batch mates, many of whom tried early versions of the tool and reported "
  "the confusing moments that led to several of the improvements described in this report.")
doc.add_paragraph()
P("Place: Bhopal", indent=False, after=0)
P(f"Date: {DATE}", indent=False)

# Abstract
front_heading("ABSTRACT")
p = doc.add_paragraph(); p.paragraph_format.first_line_indent = Inches(0.5)
r = p.add_run("यह परियोजना रिपोर्ट रिलेशनल बीजगणित से SQL कनवर्टर के द्वितीय चरण का विवरण प्रस्तुत करती है। "
              "इस चरण में कनवर्टर को एक पूर्ण शैक्षिक प्लेटफ़ॉर्म में विकसित किया गया है, जिसमें नेस्टेड प्रश्नों के लिए "
              "संरचनात्मक SQL निर्माण, थीटा एवं आउटर जॉइन, समूहन एवं एकत्रीकरण (γ), नियम-आधारित क्वेरी अनुकूलक, "
              "लागत अनुमानक, SQL से रिलेशनल बीजगणित में विपरीत रूपांतरण, सरल अंग्रेज़ी में व्याख्या तथा चरणबद्ध "
              f"निष्पादन शामिल हैं। सभी परिणामों को MANIT भोपाल के विश्वविद्यालय डेटाबेस पर {N_TESTS} स्वचालित "
              "परीक्षणों द्वारा सत्यापित किया गया है।")
rpr = r._r.get_or_add_rPr(); f = OxmlElement("w:rFonts"); f.set(qn("w:cs"), "Mangal"); f.set(qn("w:ascii"), "Times New Roman"); rpr.append(f)
q1 = OPT[0]
P(f"This report presents the second phase of the Relational Algebra to SQL Converter developed in the 4th Semester. "
  f"Phase I delivered a recursive-descent parser, an Abstract Syntax Tree (AST) and a SQL generator for the classical "
  f"operators. A review of that system at the start of Phase II found that its SQL generator flattened every "
  f"expression into a single SELECT statement, silently discarding inner projections and all but the last selection "
  f"— so nested queries, the most instructive ones, were translated incorrectly.")
P("Phase II replaces the generator with a compositional translator that emits one correctly-aliased subquery per "
  "operator, and builds on it a complete query-processing workbench: theta joins and left, right and full outer joins; "
  "grouping and aggregation (γ); a heuristic optimizer that applies nine textbook equivalence rules and logs every "
  "rewrite; a cost estimator based on catalog statistics n(R) and V(A, R); a reverse translator from SQL to relational "
  "algebra whose output is verified by executing both queries; a plain-English explanation of every expression; and a "
  "step-through mode that executes a plan one operator at a time.")
P(f"On the University database the optimizer reduced the estimated cost of a three-table Cartesian-product query from "
  f"{q1['c1']:,.0f} to {q1['c2']} tuples processed (−{q1['saving']}%), and every optimized plan in the benchmark returned "
  f"exactly the same rows as the original. All {len(M['sql2ra'])} benchmark SQL queries were translated to relational "
  f"algebra and verified by round-trip execution. The system is covered by {N_TESTS} automated checks, including a "
  f"robustness sweep of malformed input that found and fixed nine defects. The web interface was redesigned, gained a "
  f"live ER diagram drawn from the selected database, and now runs every query read-only. The project was carried out "
  f"from {PERIOD[0]} to {PERIOD[1]} and fulfils the partial requirements for the B.Tech degree at MANIT Bhopal, "
  f"Session {SESSION}.")

# TOC & lists
front_heading("TABLE OF CONTENTS")
p = doc.add_paragraph(); p.paragraph_format.first_line_indent = Inches(0)
add_field(p, 'TOC \\o "1-2" \\h \\z \\u', "Right-click and choose Update Field to build the table of contents.")
front_heading("LIST OF FIGURES")
p = doc.add_paragraph(); p.paragraph_format.first_line_indent = Inches(0)
add_field(p, 'TOC \\h \\z \\t "Figure Caption,1"', "Update field to list figures.")
front_heading("LIST OF TABLES")
p = doc.add_paragraph(); p.paragraph_format.first_line_indent = Inches(0)
add_field(p, 'TOC \\h \\z \\t "Table Caption,1"', "Update field to list tables.")

front_heading("ABBREVIATIONS / NOTATIONS")
table("Table 0.1 Abbreviations", ["Abbreviation", "Expansion"], [
    ["API", "Application Programming Interface"], ["AST", "Abstract Syntax Tree"],
    ["CDP", "Chrome DevTools Protocol (used for automated screenshots)"], ["DBMS", "Database Management System"],
    ["ER", "Entity-Relationship"], ["FK / PK", "Foreign Key / Primary Key"], ["IR", "Intermediate Representation"],
    ["JSON", "JavaScript Object Notation"], ["MANIT", "Maulana Azad National Institute of Technology"],
    ["RA", "Relational Algebra"], ["REST", "Representational State Transfer"],
    ["SQL", "Structured Query Language"], ["UI", "User Interface"], ["XSS", "Cross-Site Scripting"]],
    [1.6, 4.2])
table("Table 0.2 Relational algebra notation used in this report", ["Symbol", "Meaning", "SQL equivalent"], [
    ["π L", "Projection onto attribute list L (duplicates removed)", "SELECT DISTINCT L"],
    ["σ c", "Selection of tuples satisfying condition c", "WHERE c"],
    ["×", "Cartesian product", "CROSS JOIN"], ["⋈", "Natural join", "NATURAL JOIN"],
    ["⋈[c] (⋈θ)", "Theta join on condition c", "JOIN … ON c"],
    ["⟕  ⟖  ⟗", "Left, right and full outer join", "LEFT / RIGHT / FULL JOIN"],
    ["∪  ∩  −", "Union, intersection, set difference", "UNION / INTERSECT / EXCEPT"],
    ["÷", "Division", "double NOT EXISTS"], ["ρ x(a, b)", "Rename relation (and attributes)", "AS x / column aliases"],
    ["γ G; f(A)→n", "Group by G, compute aggregate f(A) named n", "GROUP BY G with f(A) AS n"],
    ["n(R), V(A, R)", "Tuple count of R; number of distinct values of A in R", "COUNT(*), COUNT(DISTINCT A)"],
    ["∧  ∨  ¬", "Logical and, or, not", "AND / OR / NOT"]], [1.2, 3.0, 1.8])

# ═════════════════════════════ MAIN MATTER ═════════════════════════════════
body = doc.add_section(WD_SECTION.NEW_PAGE)
page_numbers(doc.sections[0], "lowerRoman", 1)
page_numbers(body, "decimal", 1)

# ── Chapter 1 ──
chapter(1, "INTRODUCTION")
H2("1.1 Background and Motivation")
P("Relational algebra and SQL describe the same data in two very different voices. Relational algebra, introduced by "
  "E. F. Codd in 1970, is a procedural, set-based language: an expression states exactly which operators are applied "
  "and in what order. SQL is declarative and bag-based: a query states what result is wanted and leaves the order of "
  "work to the database's query optimizer. Every database course teaches both, and every real database engine works by "
  "translating SQL into an algebraic plan, rewriting that plan, estimating its cost and executing it operator by operator.")
P("In the 4th Semester we built a web tool that translates relational algebra into SQL (Phase I). Students could type "
  "an expression, read the generated SQL, inspect the expression tree and see the query result. Phase I made the "
  "*translation* visible. Phase II, presented in this report, makes the rest of query processing visible as well: how an "
  "optimizer rewrites a plan, why one plan is cheaper than another, what each operator produces along the way, and how a "
  "SQL query looks when written back as algebra.")
H2("1.2 Summary of Phase I")
P("Phase I implemented a tokenizer, a recursive-descent parser producing an AST, and a SQL generator for projection, "
  "selection, Cartesian product, natural join, union, intersection, difference, division and rename. Division was "
  "implemented with the double NOT EXISTS pattern and natural join used schema metadata to find shared attributes. The "
  "tool was validated on a seven-table University database and deployed as a web application. The Phase I report "
  "listed five directions for future work: outer joins, PostgreSQL and MySQL backends, AST-based training data for "
  "language models, a query cost estimator, and multi-user collaboration.")
H2("1.3 Problem Statement for Phase II")
P("A systematic review of the Phase I code at the start of this phase uncovered a correctness problem that outweighed "
  "every planned feature. The SQL generator walked the whole tree, collected the *last* projection and the *last* selection "
  "it met, and emitted a single `SELECT … FROM … WHERE …`. Consequently:")
bullets(["a projection inside a join, such as `π OID, City (Owners) ⋈ Owns`, was discarded, so the join ran on the full relation and could match on unintended attributes;",
         "of two stacked selections, `σ City='Bhopal' (σ OID>1 (Owners))`, only one condition survived;",
         "qualified names such as `Owners.OID` broke as soon as the relation they referred to was a derived one;",
         "parenthesised conditions, `IN (…)` lists and SQL functions could not be written inside σ at all."])
P("Beyond correctness, Phase I covered only the classical operators, offered no insight into optimization or cost, "
  "translated in one direction only, and reported many user mistakes as generic server errors. Phase II therefore set "
  "out to make the converter *correct by construction* for arbitrarily nested expressions and to extend it into a "
  "teaching workbench for the whole query-processing pipeline.")
H2("1.4 Project Objectives")
bullets(["Replace the flattening SQL generator with a compositional one that is correct for any nesting of operators.",
         "Extend the language with theta joins, left/right/full outer joins and grouping with aggregation (γ).",
         "Implement a heuristic optimizer based on relational algebra equivalence rules, and show every rewrite it makes.",
         "Implement a cost estimator using catalog statistics, and display estimated against actual row counts for every node.",
         "Implement the reverse translation, SQL → relational algebra, and verify each translation by executing both queries.",
         "Explain every expression in plain English and allow a plan to be executed one operator at a time.",
         "Harden the application: validated input, read-only execution, clear error messages and an automated test suite.",
         "Redesign the user interface and generate the ER diagram from whichever database is selected."], numbered=True)
H2("1.5 Scope of Work")
P(f"The system is a Python (Flask) web application with a JavaScript front end and SQLite storage. It is evaluated on the "
  f"University database from Phase I (seven relations) and on a new three-relation Owners–Owns–Pets database designed "
  f"to exercise division and outer joins. Translation targets the SQLite dialect; other dialects remain future work. The "
  f"work was carried out from {PERIOD[0]} to {PERIOD[1]} during the 5th Semester of B.Tech (3rd Year), Session {SESSION}.")

# ── Chapter 2 ──
chapter(2, "LITERATURE SURVEY")
H2("2.1 Extensions of Relational Algebra")
P("Codd's original algebra (1970) has five primitive operators — selection, projection, union, difference and "
  "Cartesian product — from which joins, intersection and division are derived. Practical query languages needed more. "
  "*Outer joins* preserve tuples that have no match, padding the missing attributes with NULL; they are the algebraic "
  "counterpart of SQL's LEFT, RIGHT and FULL JOIN. *Grouping and aggregation*, written γ (Garcia-Molina, Ullman and Widom, "
  "2008), partitions a relation on grouping attributes and computes aggregates such as COUNT and AVG per group; it is the "
  "counterpart of GROUP BY, and a selection placed above γ corresponds to HAVING. The *theta join* R ⋈θ S, equivalent to "
  "σθ(R × S), is the form in which most practical joins are written. Phase II adds all three families.")
H2("2.2 Heuristic Query Optimization")
P("Because relational algebra is closed, an expression can be rewritten into an equivalent one using algebraic laws. "
  "Standard texts (Silberschatz, Korth and Sudarshan, 2020, Ch. 16; Elmasri and Navathe, 2016, Ch. 19) list the "
  "equivalence rules used by optimizers: conjunctive selections may be split into a cascade of selections; selection "
  "commutes with projection when it uses only projected attributes; selection distributes over joins when its condition "
  "involves only one input; a selection over a Cartesian product whose condition relates both inputs is a theta join; and "
  "a cascade of projections collapses to the outermost one. The classical heuristic is to perform selections as early as "
  "possible, because every tuple removed before a join is a tuple the join never has to process. Phase II implements "
  "these rules as an explicit, logged rewrite system so that each step can be shown to the learner.")
H2("2.3 Cost Estimation from Catalog Statistics")
P("Cost-based optimization originates with System R (Selinger et al., 1979), which estimated result sizes from catalog "
  "statistics — the number of tuples n(R) and the number of distinct values V(A, R) of each attribute — and chose the "
  "cheapest plan. Its estimates rest on uniformity and independence assumptions: an equality selection σA=c keeps "
  "n(R)/V(A, R) tuples, a range predicate keeps about one third, and conjunctive predicates multiply their "
  "selectivities. A join on attribute A produces about n(R)·n(S)/max(V(A, R), V(A, S)) tuples. Graefe (1993) and "
  "Ioannidis (1996) survey how these estimates feed plan selection. Phase II implements the same estimates and reports, "
  "next to each estimate, the actual size obtained by executing the sub-plan — which makes the assumptions, and the "
  "places where they fail, directly observable.")
H2("2.4 Translating SQL into Relational Algebra")
P("Every relational DBMS begins query processing by translating SQL into an algebraic form. Ceri and Gottlob (1985) "
  "gave a formal translation of SQL into relational algebra and studied the equivalence of SQL queries through it. The "
  "core mapping is direct: FROM becomes a product or join of the listed relations, WHERE a selection, GROUP BY and "
  "aggregates a γ, HAVING a selection above γ, and the SELECT list a projection. Correlated subqueries in WHERE require "
  "semi-joins or decorrelation and are considerably harder. Phase II implements the direct mapping and reports "
  "unsupported constructs with a message suggesting a join-based rewrite.")
H2("2.5 Existing Tools and Gap Analysis")
P("Interactive relational algebra interpreters such as RelaX and radb are widely used in teaching. They evaluate algebra "
  "expressions, but their focus is evaluation rather than exposing the query-processing pipeline. Table 2.1 compares the "
  "capabilities of our tool at the end of Phase I and Phase II.")
table("Table 2.1 Capabilities at the end of Phase I and Phase II",
      ["Capability", "Phase I", "Phase II"], [
          ["Classical operators π σ × ⋈ ∪ ∩ − ÷ ρ", "Yes", "Yes"],
          ["Correct SQL for nested expressions", "No (flattened)", "Yes (compositional)"],
          ["Theta join, outer joins ⟕ ⟖ ⟗", "No", "Yes"],
          ["Grouping and aggregation γ", "No", "Yes"],
          ["Plain-English explanation", "No", "Yes"],
          ["Heuristic optimizer with rewrite log", "No", "Yes (9 rules)"],
          ["Cost estimate per node (est. vs actual)", "No", "Yes"],
          ["SQL → relational algebra", "No", "Yes, round-trip verified"],
          ["Step-through execution", "No", "Yes"],
          ["ER diagram of the selected database", "Static image", "Generated from schema"],
          ["Read-only execution, validated input", "No", "Yes"],
          ["Automated tests", "None", f"{N_TESTS} checks"]], [3.2, 1.3, 1.5], align_cols="lcc")
H2("2.6 Project Timeline")
P(f"Phase II was planned over twenty-six weeks from {PERIOD[0]} to {PERIOD[1]}. Table 2.2 lists the work packages.")
table("Table 2.2 Phase II execution timeline", ["Weeks", "Activity", "Deliverable / Milestone"], [
    ["1–2", "Review of Phase I; defect analysis", "Flattening defect identified; literature on optimization"],
    ["3–5", "Compositional SQL generator; tokenizer extensions", "Correct nested SQL; ⋈θ, ⟕ ⟖ ⟗"],
    ["6–8", "Grouping and aggregation; English explainer", "γ operator; explanation for every node"],
    ["9–12", "Cost estimator and heuristic optimizer", "Rules R1–R9; cost model; evaluation queries"],
    ["13–15", "SQL → RA translator", "Reverse translation with round-trip check"],
    ["16–18", "UI redesign; step-through; live ER diagram", "New interface and visualizations"],
    ["19–20", "Robustness sweep; security; test suites", f"{N_TESTS} automated checks passing"],
    ["21–22", "Report and presentation", "This report (dated " + DATE + ")"],
    ["23–26", "Final evaluation and demonstration", "Viva and demonstration (December 2026)"]], [0.7, 2.6, 2.7])

# ── Chapter 3 ──
chapter(3, "SYSTEM DESIGN AND IMPLEMENTATION")
H2("3.1 System Architecture")
P("The system has three tiers (Figure 3.1). The browser interface sends expressions to a Flask REST API. The API "
  "delegates to independent Python modules — the parser and SQL generator, the optimizer, the cost estimator, the "
  "SQL → RA translator and the explainer — which all share one set of AST node classes. Every query is executed through "
  "a read-only SQLite connection, so no expression or pasted SQL can modify the data.")
figure("d01_architecture.png", "Figure 3.1 System architecture of the Relational Algebra Explorer (Phase II)", 6.0)
table("Table 3.1 Source modules and their size", ["Module", "Responsibility", "Lines"], [
    ["converter.py", "Tokenizer, parser, AST classes, SQL generator", M["loc"]["converter.py"]],
    ["optimizer.py", "Equivalence-rule rewriter with step log", M["loc"]["optimizer.py"]],
    ["cost.py", "Statistics, selectivity and cost estimation", M["loc"]["cost.py"]],
    ["sql_to_ra.py", "SQL tokenizer and parser to AST", M["loc"]["sql_to_ra.py"]],
    ["explainer.py", "AST to plain English", M["loc"]["explainer.py"]],
    ["conditions.py", "Condition splitting and attribute extraction", M["loc"]["conditions.py"]],
    ["ra_printer.py", "AST back to relational algebra text", M["loc"]["ra_printer.py"]],
    ["app.py", "REST API, validation, read-only execution", M["loc"]["app.py"]],
    ["script.js / style.css / index.html", "User interface", M["loc"]["static/script.js"] + M["loc"]["static/style.css"] + M["loc"]["static/index.html"]]],
    [2.2, 3.0, 0.8], code_cols=(0,), align_cols="llr")
H2("3.2 Translation Pipeline")
P("Figure 3.2 traces a query through the system. The input is tokenized, parsed into an AST and — when requested — "
  "rewritten by the optimizer. SQL is generated bottom-up and executed; the result rows, the annotated tree and the "
  "English explanation are returned together. The reverse direction parses SQL into the same AST classes, so every "
  "feature (explanation, cost, optimization, step-through) works on translated SQL as well.")
figure("d02_pipeline.png", "Figure 3.2 Translation pipeline in both directions", 6.0)
H2("3.3 Tokenizer and Grammar Extensions")
P("The tokenizer recognises each operator symbol, identifiers and conditions. Three extensions were needed in Phase II. "
  "First, a *condition scanner* after σ reads the whole condition, keeping a parenthesised group when it is itself a "
  "condition (`(a=1 ∨ b=2) ∧ c=3`), an `IN (…)` list or a SQL function call such as `LOWER(name)`, and stopping at the "
  "parenthesis that opens the relation. Second, a join symbol may be followed by a bracketed condition — `⋈[c]`, "
  "`⟕[c]` — which turns it into a theta or conditional outer join. Third, γ is followed by a grouping specification "
  "`group_cols; AGG(x)→name, …`, in which parentheses that follow an aggregate name belong to the specification. The "
  "parser keeps the three precedence levels of Phase I (Table 3.2) and now reports a missing parenthesis, leftover text, "
  "an invalid table or column name, or an operator without its argument as a specific error.")
table("Table 3.2 Operator precedence and AST node types", ["Level", "Operators", "AST node classes"], [
    ["1 (highest)", "π  σ  ρ  γ  (unary, prefix)", "ProjectionNode, SelectionNode, RenameNode, GroupNode"],
    ["2", "×  ⋈  ⋈[c]  ⟕  ⟖  ⟗  ÷  (left-associative)", "CrossJoinNode, NaturalJoinNode, ThetaJoinNode, OuterJoinNode, DivisionNode"],
    ["3 (lowest)", "∪  ∩  −  (left-associative)", "UnionNode, IntersectNode, MinusNode"]], [1.0, 2.4, 2.6])
H2("3.4 Compositional SQL Generation")
P("The new SQLConverter translates each node into a complete query and nests children as subqueries only where "
  "necessary. A *source* function returns a FROM clause and a list of WHERE conditions: selections add their condition "
  "to the list, chains of joins are written left-to-right as one FROM clause, and any other sub-expression becomes an "
  "aliased subquery. Projection emits `SELECT DISTINCT` to honour set semantics. Two rules keep the output readable "
  "and correct:")
bullets(["**Alias by origin.** A subquery derived from relation R by π or σ is aliased `AS R`, so qualified names such as `Owners.OID` written by the user keep working; aliases are made unique within a FROM clause, falling back to t1, t2, … .",
         "**Flatten when safe.** Stacked selections and joins merge into one SELECT, so simple expressions still produce the simple SQL a student would write by hand."])
P("Table 3.3 contrasts the two generators on a query from the Phase II test set.")
table("Table 3.3 Phase I versus Phase II SQL for a nested expression", ["Generator", "SQL for  π OName (σ City='Bhopal' (σ OID>1 (Owners)))"], [
    ["Phase I (flattening)", "SELECT OName FROM Owners WHERE OID>1      ← condition City='Bhopal' lost"],
    ["Phase II", "SELECT DISTINCT OName FROM Owners WHERE (OID>1) AND (City='Bhopal')"]], [1.5, 4.5], code_cols=(1,))
H2("3.5 New Operators")
table("Table 3.4 Translation of the operators added in Phase II", ["Relational algebra", "Generated SQL"], [
    ["R ⋈[R.a = S.b] S", "SELECT * FROM R JOIN S ON R.a = S.b"],
    ["R ⟕ S   /   R ⟕[c] S", "… FROM R NATURAL LEFT JOIN S   /   … FROM R LEFT JOIN S ON c"],
    ["R ⟖ S,  R ⟗ S", "NATURAL RIGHT JOIN,  NATURAL FULL JOIN"],
    ["γ dept_id; COUNT(*)→n (students)", "SELECT dept_id, COUNT(*) AS n FROM students GROUP BY dept_id"],
    ["σ n>1 (γ City; COUNT(*)→n (Pets))", "SELECT * FROM (SELECT City, COUNT(*) AS n FROM Pets GROUP BY City) AS t1 WHERE n>1"],
    ["γ COUNT(DISTINCT City)→c (Pets)", "SELECT COUNT(DISTINCT City) AS c FROM Pets"]], [2.5, 3.5], code_cols=(0, 1))
P("Outer joins are generated with SQLite's native RIGHT and FULL JOIN support (SQLite 3.39 and later). For γ, a "
  "selection placed above the grouping becomes a filter on the grouped subquery, which is the algebraic form of HAVING. "
  "When no alias is given, an aggregate is named automatically, for example `count_all` or `avg_marks`.")
H2("3.6 Heuristic Query Optimizer")
P("The optimizer copies the AST and rewrites the copy with the rules of Table 3.5, recording each application with the "
  "law it used and where it was applied. The algorithm first splits every conjunctive selection into its conjuncts (R1). "
  "It then optimizes the input of the selection and *places* each conjunct as low as the rules allow: below projections "
  "that keep its attributes (R2), into the join input that supplies all its attributes (R3), into both inputs of ∪ and ∩ "
  "or the left input of − (R6), and below γ when it mentions only grouping attributes (R7). A conjunct that relates both "
  "inputs of a Cartesian product turns the product into a theta join (R4) or is merged into an existing join condition "
  "(R5). Finally, cascaded projections are removed (R8) and adjacent selections recombined (R9).")
table("Table 3.5 Equivalence rules implemented by the optimizer", ["Rule", "Name", "Law"], [
    ["R1", "Cascade of σ", "σ c1∧c2 (E) ≡ σ c1 (σ c2 (E))"],
    ["R2", "σ commutes with π", "σ c (π L (E)) ≡ π L (σ c (E)),  c uses only L"],
    ["R3", "Push σ below a join", "σ c (E1 ⋈ E2) ≡ σ c (E1) ⋈ E2,  c uses only E1"],
    ["R4", "σ over × becomes ⋈θ", "σ c (E1 × E2) ≡ E1 ⋈c E2"],
    ["R5", "Merge σ into ⋈θ", "σ c (E1 ⋈θ E2) ≡ E1 ⋈θ∧c E2"],
    ["R6", "Push σ into set operations", "σ c (E1 ∪ E2) ≡ σ c (E1) ∪ σ c (E2);  σ c (E1 − E2) ≡ σ c (E1) − E2"],
    ["R7", "Push σ below γ", "σ c (γ G (E)) ≡ γ G (σ c (E)),  c uses only G"],
    ["R8", "Cascade of π", "π L1 (π L2 (E)) ≡ π L1 (E)"],
    ["R9", "Combine σ", "σ c1 (σ c2 (E)) ≡ σ c1∧c2 (E)"]], [0.5, 1.8, 3.7], code_cols=(2,))
P("Deciding which input supplies a condition's attributes requires schema knowledge. The optimizer extracts every "
  "attribute reference from the condition — ignoring literals, keywords and function names — and checks it against the "
  "output columns of each sub-plan (obtained from SQLite) and the relation names visible in it, so `Owners.OID` is "
  "matched only on the Owners side. Outer joins receive special treatment: a selection may move only into the "
  "*preserved* input (the left of ⟕, the right of ⟖, neither for ⟗), because filtering the NULL-padded side before the "
  "join would change the result. As a safety net, the application executes both the original and the optimized plan "
  "and reports whether their results are identical.")
H2("3.7 Cost Estimator")
P("The cost estimator reads n(R) and V(A, R) for every attribute of every base relation from the database and "
  "propagates estimated sizes and distinct-value counts up the tree using the formulas of Table 3.6. Selectivity of a "
  "condition is computed recursively: OR combines as 1 − Π(1 − sᵢ), AND as Π sᵢ, NOT as 1 − s; atomic predicates use "
  "the System R defaults. An equality with a constant also fixes V(A) = 1 for the attribute above that point.")
table("Table 3.6 Result-size estimates", ["Operator", "Estimated result size"], [
    ["σ A = c (R)", "n(R) / V(A, R)"], ["σ A = B (R)", "n(R) / max(V(A, R), V(B, R))"],
    ["σ A < c, A > c, BETWEEN, LIKE", "n(R) / 3,  n(R) / 4,  n(R) / 10"],
    ["R × S", "n(R) · n(S)"], ["R ⋈ S on common attributes A", "n(R) · n(S) / Π max(V(A, R), V(A, S))"],
    ["R ⋈θ S", "n(R) · n(S) · sel(θ)"], ["R ⟕ S, R ⟖ S, R ⟗ S", "max(join estimate, n(R)), n(S), n(R)+n(S)"],
    ["π L (R)", "min(n(R), Π V(A, R) for A in L)"], ["γ G (R)", "min(n(R), Π V(g, R)); 1 without grouping"],
    ["R ∪ S,  R ∩ S,  R − S", "n(R) + n(S),  min(n(R), n(S)),  n(R)"], ["R ÷ S", "≈ n(R) / n(S)"]],
    [2.4, 3.6], code_cols=(0, 1))
P("Plans are compared by the number of tuples they process. A table scan costs n(R). Selection, projection and rename "
  "are *pipelined* — applied to tuples as they stream past — and add no cost of their own. Joins, set operations, γ and "
  "division cost the tuples they read from their inputs plus the tuples they produce. This model rewards exactly what "
  "the heuristics aim for: shrinking relations before they reach a join. Each node in the interface shows its estimated "
  "rows, its cumulative cost and, on hover, the formula that produced the estimate.")
H2("3.8 SQL to Relational Algebra Translator")
P("The reverse translator tokenizes SQL (strings, quoted identifiers, numbers, operators) and parses the SQLite subset "
  "listed in Table 3.7 into the same AST classes used by the forward direction. A printer then writes the tree as "
  "relational algebra, inserting parentheses only where precedence requires them. Because the result is an ordinary "
  "AST, it can immediately be explained, costed, optimized and stepped through.")
table("Table 3.7 SQL constructs and their relational algebra translation", ["SQL", "Relational algebra"], [
    ["FROM a, b  /  CROSS JOIN", "a × b"], ["JOIN … ON c   /   NATURAL JOIN", "a ⋈[c] b   /   a ⋈ b"],
    ["LEFT / RIGHT / FULL [OUTER] JOIN … ON c", "a ⟕[c] b,  a ⟖[c] b,  a ⟗[c] b"],
    ["table AS x,  (subquery) AS x", "ρ x (table),  ρ x (…)"], ["WHERE c", "σ c"],
    ["GROUP BY g with aggregates", "γ g; AGG(x)→name"], ["HAVING c (aggregates replaced by their names)", "σ c above γ"],
    ["SELECT list,  column aliases", "π list,  ρ Q(names)"], ["UNION / INTERSECT / EXCEPT", "∪  ∩  −"],
    ["ORDER BY, LIMIT;  IN / EXISTS subqueries", "dropped with a warning;  rejected with a rewrite hint"]],
    [3.0, 3.0], code_cols=(0, 1))
P("Every translation is verified: the AST is converted back to SQL and both the user's SQL and the generated SQL are "
  "executed read-only. The interface reports whether the two return the same rows. Semantic differences that cannot be "
  "removed — SQL's bag semantics versus the set semantics of π, or a LIMIT clause that has no algebraic counterpart — "
  "are reported as warnings rather than hidden.")
H2("3.9 Plain-English Explanation")
P("The explainer walks the same AST and builds a noun phrase for each node: a table becomes its name, π becomes "
  "\"the A and B of …\", σ \"… where …\", and each join, set operation and γ has its own phrase. Conditions are verbalised "
  "operator by operator (≥ becomes \"is at least\", ∧ becomes \"and\") while string literals are left untouched. Compound "
  "operands are bracketed so that the sentence stays unambiguous. Because the sentence is derived from the tree rather "
  "than from the SQL text, it always describes exactly the query that was executed.")
H2("3.10 Step-through Execution")
P("The tree endpoint executes the sub-plan rooted at every node and returns its SQL, its row count, a preview of up to "
  "100 rows and its cost estimate. The interface orders the nodes in post-order — inputs before the operators that "
  "consume them — and lets the user step forwards, backwards or play the sequence. At each step the current node is "
  "highlighted, completed nodes are marked, and a panel shows a description of the operator, the actual and estimated "
  "row counts with the estimation formula, the node's SQL and its intermediate result.")
H2("3.11 Robustness and Security")
P(f"A robustness sweep (test_api.py) sends every endpoint {T['test_api.py']['checks']} valid and invalid requests — empty "
  "and malformed expressions, unknown tables and columns, wrong JSON types, hostile SQL, deeply nested parentheses — and "
  "accepts only a successful result or a readable error message. It uncovered nine defects, all fixed in this phase:")
bullets(["database errors (unknown table or column) surfaced as HTTP 500 server errors instead of explanations;",
         "`σ dept_id IN (1, 2) (students)` failed because the list was taken for the relation;",
         "a legacy workaround replaced every `?` with π, corrupting string literals;",
         "the database-name header allowed path traversal, and an unknown name silently created an empty database;",
         "uploaded files were saved under unsanitised names and without checking that they were SQLite databases;",
         "the expression tree omitted the children of γ nodes;",
         "tree connector lines were never drawn (an SVG class-name defect);",
         "table and column names were inserted into the page as raw HTML (an XSS risk);",
         "the hover popup was positioned relative to an animated card instead of the window."])
P("In addition, every query now runs on a read-only SQLite connection, request bodies are type-checked, and all "
  "endpoints share one error handler that converts parsing, database and recursion errors into specific messages.")

# ── Chapter 4 ──
chapter(4, "RESULTS AND ANALYSIS")
H2("4.1 Test Databases")
P("The University database from Phase I contains seven relations linked by declared foreign keys (Table 4.1, "
  "Figure 4.1). Its attribute list below is read directly from the database. A second database, Owners–Owns–Pets "
  "(Figure 4.2), was created for Phase II: owner Asha owns pets from every city, owner Kiran owns no pet, and one pet "
  "has no owner, which makes division and outer joins produce non-trivial answers.")
table("Table 4.1 Relations of the University database", ["Relation", "Attributes (PK underlined in diagram)", "Rows"], [
    ["dean", "dean_id, name, email, phone", 2], ["department", "dept_id, dept_name, dean_id → dean", 3],
    ["professor", "prof_id, name, email, gender, dept_id → department, is_hod", 5],
    ["students", "student_id, name, gender, dept_id → department, mentor_id", 8],
    ["subject", "subject_id, subject_name, dept_id → department, prof_id → professor", 6],
    ["result", "result_id, student_id → students, subject_id → subject, marks, total_marks, pass_marks, grade", 16],
    ["mentor", "mentor_id, student_id → students", 2]], [1.1, 4.3, 0.6], code_cols=(0,), align_cols="llr")
figure("d04_er_university.png", "Figure 4.1 ER diagram of the University database, generated by the tool from the live schema", 4.3)
figure("d05_er_pets.png", "Figure 4.2 ER diagram of the Owners–Owns–Pets database", 3.4)
H2("4.2 Query Translation Examples")
P("Table 4.2 shows representative translations, including the generated SQL and the English explanation produced by "
  "the tool. All were executed against the databases above.")
table("Table 4.2 Relational algebra, generated SQL and generated explanation", ["Relational algebra", "Generated SQL", "Explanation (generated)"],
      [[x["ra"], x["sql"].replace("\n", " "), x["en"]] for x in M["translations"]], [1.9, 2.2, 1.9], code_cols=(0, 1), size=9)
H2("4.3 Optimizer Evaluation")
P("Six queries were chosen to exercise different rules. For each, Table 4.3 lists the estimated cost of the original "
  "and the optimized plan, the rules applied, and whether both plans return identical rows (verified by execution).")
table("Table 4.3 Optimizer results", ["Query", "Original cost", "Optimized cost", "Saving", "Rules applied", "Same rows"],
      [[r["name"], f"{r['c1']:,.1f}", f"{r['c2']:,.1f}", f"{r['saving']}%", ", ".join(dict.fromkeys(r["rules"])), "Yes" if r["match"] else "No"]
       for r in OPT], [0.6, 1.0, 1.0, 0.8, 1.7, 0.9], align_cols="lrrrlc")
q = {r["name"]: r for r in OPT}
table("Table 4.4 Benchmark queries", ["Query", "Relational algebra (original)"],
      [[r["name"], r["ra"]] for r in OPT], [0.6, 5.4], code_cols=(1,), size=9)
figure("d03_costchart.png", "Figure 4.3 Estimated cost of original and optimized plans (log scale)", 6.0)
P(f"The largest gain, −{q['Q1']['saving']}% for Q1, comes from the classic pattern of a selection over a Cartesian "
  f"product: the original plan forms all {768:,} combinations of students, results and subjects before filtering, "
  f"whereas the optimized plan pushes `marks >= 90` into the result relation and turns both equality conditions into "
  f"joins. Q5 and Q6 show the rules for set operations (R6) and grouping (R7). Q4 gains least because its joins are "
  f"already natural joins over small relations. In every case the optimized plan returned exactly the same rows as the "
  f"original.")
H2("4.4 Accuracy of Cost Estimates")
P("Table 4.5 compares estimated and actual result sizes. Estimates for single selections, projections, grouping and "
  "key–foreign-key joins are exact or close. The weakest estimate is the three-way join with `grade='A'`: the estimator "
  "assumes grades are uniformly distributed and independent of the join, while in the data half of the results are A "
  "grades. Showing estimate and actual side by side lets students see precisely this effect of the uniformity and "
  "independence assumptions.")
table("Table 4.5 Estimated versus actual result size", ["Expression", "Estimated", "Actual"],
      [[e["q"], e["est"], e["actual"]] for e in M["estimates"]], [4.4, 0.8, 0.8], code_cols=(0,), align_cols="lrr", size=9.5)
H2("4.5 SQL to Relational Algebra Results")
table("Table 4.6 SQL translated to relational algebra (all verified by execution)", ["SQL", "Relational algebra", "Verified"],
      [[e["sql"], e["ra"], "Yes" if e["match"] else "No"] for e in M["sql2ra"]], [2.6, 2.7, 0.7], code_cols=(0, 1), size=9, align_cols="llc")
H2("4.6 Performance")
P("Translation, optimization and estimation are interactive-speed operations. Table 4.7 gives mean times measured "
  "over repeated runs on the development machine (Python 3.14, SQLite 3.50). Optimization and cost estimation query "
  "the database for column lists and statistics, which dominates their time; parsing and SQL generation take well under "
  "a millisecond except for division, which reads the schemas of both operands.")
table("Table 4.7 Mean processing time (milliseconds)", ["Workload", "Parse + SQL", "Optimize", "Cost estimate"],
      [[t["label"], t["convert"], "–" if t["optimize"] is None else t["optimize"], "–" if t["cost"] is None else t["cost"]] for t in M["timing"]],
      [2.9, 1.0, 1.0, 1.1], align_cols="lrrr")
H2("4.7 Testing and Validation")
table("Table 4.8 Automated test suites", ["Suite", "What it checks", "Checks", "Result"], [
    ["test_complex.py", "Nested expressions, joins, division, outer joins; result rows compared with expected sets", T["test_complex.py"]["checks"], T["test_complex.py"]["last"]],
    ["test_features.py", "Optimizer (same rows, no cost increase, expected rules), cost formulas, γ, SQL → RA round trips", T["test_features.py"]["checks"], T["test_features.py"]["last"]],
    ["test_api.py", "Every endpoint with valid and malformed input; no server errors, readable messages, data intact", T["test_api.py"]["checks"], T["test_api.py"]["last"]]],
    [1.3, 3.2, 0.7, 0.8], code_cols=(0,), align_cols="llrl", size=9.5)
P(f"In total {N_TESTS} checks pass. Every test that involves a query compares *executed results*, not SQL text, so "
  f"it remains valid when the generator's formatting changes.")

# ── Chapter 5 ──
chapter(5, "APPLICATION AND USER INTERFACE")
H2("5.1 Interface Overview and Redesign")
P("The Phase I interface used a dark theme with glowing gradients. Phase II redesigns it as a quiet \"scholar's "
  "notebook\": warm paper tones, ink-coloured text, a serif display face and a ruled expression editor, with terracotta "
  "and sage as accent colours. A matching dark theme follows the operating-system setting and can be switched from the "
  "header. The left column holds the schema browser, examples, symbol palette, table list and ER diagram; the main "
  "column holds the editor, the SQL → RA panel and the results (Figure 5.1).")
figure("f01_interface.png", "Figure 5.1 Main interface of the redesigned Relational Algebra Explorer", 6.0)
H2("5.2 Editor, Generated SQL and Explanation")
P("Expressions can be typed or assembled from the symbol palette, whose tooltips show the syntax of each operator, "
  "including γ and the outer joins. Running a query shows the generated SQL and, under it, the English explanation "
  "(Figure 5.2). SQL typed into the editor is detected automatically and converted to relational algebra first.")
figure("f02_editor_sql.png", "Figure 5.2 Expression editor, generated SQL and plain-English explanation", 5.6)
H2("5.3 Expression Tree with Cost Estimates")
P("Each node of the expression tree shows its actual row count and, beneath it, the estimated rows and cumulative "
  "cost (Figure 5.3). Hovering over a node shows the first rows of its intermediate result; clicking shows the full "
  "result in the results panel.")
figure("f03_tree.png", "Figure 5.3 Expression tree with actual rows, estimated rows and cost per node", 5.6)
H2("5.4 Step-through Execution")
figure("f04_step.png", "Figure 5.4 Step-through execution: step 4 of 7, reading the subject relation", 5.4)
H2("5.5 Optimizer and Cost View")
P("The optimizer panel compares the costs of both plans with proportional bars, lists every rule application with its "
  "formal law, offers the optimized expression for re-running and draws both plans side by side (Figures 5.5 and 5.6).")
figure("f06_opt_summary.png", "Figure 5.5 Optimizer summary: cost comparison, verification and rule log for Q1", 5.6)
figure("f07_opt_trees.png", "Figure 5.6 Original and optimized plans for Q1 with per-node estimates", 6.0)
H2("5.6 SQL to Relational Algebra Panel")
figure("f08_sql2ra.png", "Figure 5.7 SQL translated to relational algebra, explained and verified by execution", 5.6)
H2("5.7 New Operators in the Interface")
figure("f09_gamma_tree.png", "Figure 5.8 Grouping with HAVING-style selection: σ n > 1 (γ City; COUNT(*)→n (Pets))", 5.4)
figure("f10_outer.png", "Figure 5.9 Left outer join finding owners without pets", 5.6)
H2("5.8 Error Handling")
P("Errors are reported in place with a specific message (Figure 5.10): unknown tables and columns, missing "
  "parentheses, operators without arguments, invalid names and SQL constructs that cannot be translated, each with a "
  "hint where one is possible.")
figure("f14_error.png", "Figure 5.10 A database error reported in the editor", 5.4)
H2("5.9 Dark Theme")
figure("f13_dark.png", "Figure 5.11 The interface in its dark theme", 6.0)

# ── Chapter 6 ──
chapter(6, "CONCLUSION AND FUTURE WORK")
H2("6.1 Conclusion")
P("Phase II turned a one-directional converter into a workbench for the whole relational query-processing pipeline. "
  "The most important change is invisible in the interface: the compositional SQL generator makes translation correct "
  "for any nesting of operators, removing a defect that affected exactly the expressions students learn most from. On "
  "that foundation the project added the operators of practical SQL — theta and outer joins and grouping — and the two "
  "ideas at the heart of query optimization: rewriting by equivalence rules and estimating cost from statistics.")
P(f"The evaluation shows the optimizer reducing estimated cost by up to {q['Q1']['saving']}% while preserving results, "
  f"cost estimates that are exact for simple operators and instructively wrong where the independence assumption fails, "
  f"and every benchmark SQL query translated to algebra and verified by execution. A systematic robustness sweep, a "
  f"read-only execution model and {N_TESTS} automated checks make the tool dependable enough for classroom use.")
H2("6.2 Status of Phase I Future Work")
table("Table 6.1 Future-work items from the Phase I report", ["Phase I item", "Status after Phase II"], [
    ["Outer joins (left, right, full)", "Done — natural and conditional forms, with optimizer support"],
    ["PostgreSQL and MySQL backends", "Open — SQL generation is centralised, making dialects a contained change"],
    ["AST as training data for NL-to-SQL models", "Partly enabled — SQL → RA produces verified (SQL, RA, English) triples"],
    ["Query plan cost estimator", "Done — per-node estimates, formulas and plan comparison"],
    ["Multi-user collaboration", "Open"]], [2.4, 3.6])
H2("6.3 Future Work")
bullets(["**Cost-based join ordering.** Enumerate join orders with dynamic programming, as in System R, instead of keeping the user's order.",
         "**Projection push-down.** Insert projections below joins to keep only the attributes needed above them.",
         "**Histograms.** Replace uniformity assumptions with per-attribute histograms to fix estimates such as the grade='A' case.",
         "**Subqueries in WHERE.** Translate IN and EXISTS subqueries into semi-joins and anti-joins.",
         "**Dialects and deployment.** Generate PostgreSQL and MySQL SQL, and redeploy the Phase II version online.",
         "**Exercise mode.** Let instructors store reference answers and check student expressions by comparing results."])

# ── References ──
front_heading("REFERENCES")
refs = [
    "Codd, E. F. (1970). A relational model of data for large shared data banks. Communications of the ACM, 13(6): 377–387.",
    "Selinger, P. G., Astrahan, M. M., Chamberlin, D. D., Lorie, R. A. and Price, T. G. (1979). Access path selection in a relational database management system. In Proceedings of ACM SIGMOD 1979, pp. 23–34.",
    "Ceri, S. and Gottlob, G. (1985). Translating SQL into relational algebra: Optimization, semantics, and equivalence of SQL queries. IEEE Transactions on Software Engineering, SE-11(4): 324–345.",
    "Graefe, G. (1993). Query evaluation techniques for large databases. ACM Computing Surveys, 25(2): 73–169.",
    "Ioannidis, Y. E. (1996). Query optimization. ACM Computing Surveys, 28(1): 121–123.",
    "Silberschatz, A., Korth, H. F. and Sudarshan, S. (2020). Database System Concepts (7th ed.). McGraw-Hill: New York.",
    "Elmasri, R. and Navathe, S. B. (2016). Fundamentals of Database Systems (7th ed.). Pearson: Boston.",
    "Garcia-Molina, H., Ullman, J. D. and Widom, J. (2008). Database Systems: The Complete Book (2nd ed.). Pearson: Upper Saddle River.",
    "Ramakrishnan, R. and Gehrke, J. (2003). Database Management Systems (3rd ed.). McGraw-Hill: New York.",
    "Ullman, J. D. (1988). Principles of Database and Knowledge-Base Systems (Vol. 1). Computer Science Press: Rockville.",
    "Date, C. J. (2004). An Introduction to Database Systems (8th ed.). Pearson: New Delhi.",
    "Aho, A. V., Lam, M. S., Sethi, R. and Ullman, J. D. (2007). Compilers: Principles, Techniques, and Tools (2nd ed.). Pearson: New Delhi.",
    "RelaX – Relational Algebra Calculator. (2024). Retrieved from https://dbis-uibk.github.io/relax/",
    "SQLite Documentation: SELECT, joins and PRAGMA statements. Retrieved from https://www.sqlite.org/docs.html",
]
for i, rtext in enumerate(refs, 1):
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.4); p.paragraph_format.first_line_indent = Inches(-0.4)
    p.paragraph_format.line_spacing = 1.3
    p.add_run(f"{i}.\t{rtext}")

# ── Appendices ──
front_heading("APPENDIX 1   Sample Query Translation Cases")
P("The following cases are part of the automated test suites and were validated against the databases of Chapter 4.", indent=False)
table("Table A.1 Sample translation cases", ["No.", "Relational algebra", "Generated SQL"], [
    [i + 1, x["ra"], x["sql"].replace("\n", " ")] for i, x in enumerate(M["translations"])] + [
    [6, "σ (Species='Dog' ∨ Species='Cat') ∧ City='Indore' (Pets)", "SELECT * FROM Pets WHERE (Species='Dog' OR Species='Cat') AND City='Indore'"],
    [7, "π OID (Owners) − π OID (Owns)", "SELECT DISTINCT OID FROM Owners EXCEPT SELECT DISTINCT OID FROM Owns"],
    [8, "π P.PName (ρ P (Pets) ⋈[P.City = O.City] ρ O (σ OName='Ravi' (Owners)))",
     "SELECT DISTINCT P.PName FROM Pets AS P JOIN (SELECT * FROM Owners WHERE OName='Ravi') AS O ON P.City = O.City"]],
    [0.4, 2.6, 3.0], code_cols=(1, 2), size=9, align_cols="cll")
front_heading("APPENDIX 2   REST API and Running the Application")
table("Table A.2 REST API endpoints", ["Endpoint", "Method", "Purpose"], [
    ["/query", "POST", "Translate an expression, execute it, return SQL, rows and English explanation"],
    ["/query-tree", "POST", "Expression tree with per-node SQL, rows, estimates and formulas"],
    ["/optimize", "POST", "Optimized plan, rule log, costs of both plans and result verification"],
    ["/sql-to-ra", "POST", "SQL to relational algebra with round-trip verification and warnings"],
    ["/schema, /tables", "GET", "Tables, columns, primary and foreign keys of the selected database"],
    ["/databases, /upload-db", "GET / POST", "List databases; upload a validated SQLite file"]], [1.6, 0.9, 3.5], code_cols=(0,))
P("To run the application locally: install the requirements with `pip install -r requirements.txt`, start the server "
  "with `python app.py` and open `http://127.0.0.1:5000`. The sample Owners–Owns–Pets database is created with "
  "`python seed_pets_db.py`, and the three test suites run with `python test_complex.py`, `python test_features.py` "
  "and `python test_api.py`.", indent=False)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
doc.save(OUT)
print("saved", OUT)
