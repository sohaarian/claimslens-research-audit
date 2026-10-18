#!/usr/bin/env python3
"""Generate readable vector Figure 3; no external resources required beyond reportlab."""
from pathlib import Path
from math import atan2, sin, cos
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
HERE=Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
W,H=540,190
c=canvas.Canvas(str(HERE/'conservative_policy.pdf'),pagesize=(W,H),pageCompression=1)
c.setTitle('ClaimsLens: conservative policy decision pathway')
ink=(.14,.23,.33); border=(.36,.44,.54); blue=(.94,.96,.98)

def color(rgb,stroke=False):
    (c.setStrokeColorRGB if stroke else c.setFillColorRGB)(*rgb)

def label(lines,cx,cy,size=8.8,bold=False,spacing=12):
    color(ink)
    c.setFont('DejaVuSans-Bold' if bold else 'DejaVuSans',size)
    lines = lines.split('\n') if isinstance(lines,str) else lines
    start=cy+(len(lines)-1)*spacing/2-3.1
    for i,t in enumerate(lines): c.drawCentredString(cx,start-i*spacing,t)

def node(x,y,w,h,lines,fill=blue,size=8.8,bold=False):
    color(fill);color(border,True)
    c.roundRect(x,y,w,h,8,stroke=1,fill=1)
    label(lines,x+w/2,y+h/2,size,bold)

def diamond(cx,cy,rx,ry,lines,size=8.6):
    color((1,.976,.936));color(border,True)
    p=c.beginPath();p.moveTo(cx-rx,cy);p.lineTo(cx,cy+ry);p.lineTo(cx+rx,cy);p.lineTo(cx,cy-ry);p.close()
    c.drawPath(p,stroke=1,fill=1)
    label(lines,cx,cy,size,False,11)

def edge(x0,y0,x1,y1,text=None,tx=None,ty=None):
    color(border,True);c.setLineWidth(1.1);c.line(x0,y0,x1,y1)
    import math
    a=math.atan2(y1-y0,x1-x0);L=6
    p=c.beginPath();p.moveTo(x1,y1);p.lineTo(x1-L*math.cos(a-.48),y1-L*math.sin(a-.48));p.lineTo(x1-L*math.cos(a+.48),y1-L*math.sin(a+.48));p.close();c.setFillColorRGB(*border);c.drawPath(p,stroke=0,fill=1)
    if text: label([text],tx if tx is not None else (x0+x1)/2,ty if ty is not None else (y0+y1)/2+10,7.5)

def poly(points,text=None,tx=None,ty=None):
    color(border,True);c.setLineWidth(1.1)
    for a,b in zip(points,points[1:-1]):c.line(*a,*b)
    a,b=points[-2:];edge(*a,*b,text,tx,ty)

node(8,124,104,45,'Structured source\ntracking item + date',size=8.7)
node(134,124,110,45,'Candidate checks\nidentity, signature, date',size=8.7)
diamond(310,145,50,29,'Linked notice or\nmalformed source?',size=8.3)
diamond(467,145,62,29,'Qualifying signed\ncompletion?',size=8.5)
node(244,16,134,49,'REVIEW_CONFLICT\nshow sources + blockers',fill=(.978,.91,.90),size=8.5)
node(393,65,137,43,'DOCUMENT_FOUND\nnot clinician-reviewed',fill=(.91,.965,.93),size=8.3)
node(393,11,137,43,'REVIEW_MISSING\nrequest missing source',fill=(.985,.964,.88),size=8.4)
edge(112,146,134,146)
edge(244,146,260,146)
edge(360,145,405,145,text='No notice',tx=383,ty=163)
edge(310,116,310,65,text='Notice',tx=334,ty=86)
edge(467,116,467,108,text='Yes',tx=485,ty=115)
poly([(528,145),(535,145),(535,32),(530,32)],text='No evidence',tx=485,ty=58)
c.showPage();c.save()
