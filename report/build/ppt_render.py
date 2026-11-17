"""Render every slide to PNG with PowerPoint itself and build a contact sheet."""
import glob, os, sys
import win32com.client as win32
from PIL import Image

pptx = os.path.abspath(sys.argv[1])
out = os.path.abspath(sys.argv[2])
os.makedirs(out, exist_ok=True)
for f in glob.glob(os.path.join(out, "*.png")):
    os.remove(f)
app = win32.DispatchEx("PowerPoint.Application")
try:
    pres = app.Presentations.Open(pptx, ReadOnly=True, Untitled=False, WithWindow=False)
    for i, slide in enumerate(pres.Slides, 1):
        slide.Export(os.path.join(out, f"s{i:02d}.png"), "PNG", 1600, 900)
    pres.Close()
finally:
    app.Quit()
files = sorted(glob.glob(os.path.join(out, "s*.png")))
ims = [Image.open(f) for f in files]
for im in ims:
    im.thumbnail((640, 360))
cols = 3
for start in range(0, len(ims), 9):
    grp = ims[start:start + 9]; rows = (len(grp) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 650, rows * 370), "gray")
    for k, im in enumerate(grp):
        sheet.paste(im, ((k % cols) * 650, (k // cols) * 370))
    sheet.save(os.path.join(out, f"sheet{start // 9 + 1}.png"))
print(len(files), "slides rendered")
