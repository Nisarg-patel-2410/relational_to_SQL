"""Open the report in Word, update all fields (TOC, lists, page numbers), save, export PDF."""
import os, sys
import win32com.client as win32

docx = os.path.abspath(sys.argv[1])
pdf = os.path.splitext(docx)[0] + ".pdf"
word = win32.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
try:
    d = word.Documents.Open(docx)
    for _ in range(2):                     # second pass fixes page numbers shifted by the TOC itself
        d.Fields.Update()
        for toc in d.TablesOfContents:
            toc.Update()
    d.Save()
    d.ExportAsFixedFormat(pdf, 17, OpenAfterExport=False, OptimizeFor=0, CreateBookmarks=1)  # 17 = PDF
    print("pages:", d.ComputeStatistics(2))
    d.Close(False)
finally:
    word.Quit()
print("pdf:", pdf)
