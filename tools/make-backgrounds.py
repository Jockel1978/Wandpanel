#!/usr/bin/env python3
"""Erzeugt die Hintergrundbilder für das Wandpanel (public/bg/*.jpg + thumb/*.jpg).
Benötigt: playwright (Chromium) und Pillow.  Aufruf:  python3 tools/make-backgrounds.py
"""
import math, random, os, io
from PIL import Image
from playwright.sync_api import sync_playwright

W, H = 1920, 1080
OUT = os.path.join(os.path.dirname(__file__), "..", "public", "bg")
os.makedirs(os.path.join(OUT, "thumb"), exist_ok=True)

NOISE = '''<filter id="nz" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/></filter>
<rect width="100%" height="100%" filter="url(#nz)" opacity="0.07" style="mix-blend-mode:overlay"/>'''

def svg(body, defs=""):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs>{defs}</defs>{body}{NOISE}</svg>'

def lg(id, stops, x1=0, y1=0, x2=0, y2=1):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"' + (f' stop-opacity="{a}"' if a is not None else '') + '/>' for o, c, a in stops)
    return f'<linearGradient id="{id}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>'

def rg(id, stops, cx=.5, cy=.5, r=.5):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<radialGradient id="{id}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient>'

def stars(seed, n, ymax, glow=True):
    r = random.Random(seed); out = []
    for _ in range(n):
        x = r.uniform(0, W); y = r.uniform(0, ymax) ** 1.0
        y = ymax * (r.random() ** 1.6)
        rad = r.choice([.6, .8, 1, 1.2, 1.6]) ; op = r.uniform(.35, 1)
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rad}" fill="#fff" opacity="{op:.2f}"/>')
    if glow:
        for _ in range(7):
            x = r.uniform(80, W - 80); y = ymax * r.uniform(.05, .7)
            out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="#cfe4ff" opacity=".25" filter="url(#bl4)"/><circle cx="{x:.0f}" cy="{y:.0f}" r="1.8" fill="#fff"/>')
    return "".join(out)

BL = lambda: '<filter id="bl4" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="4"/></filter>'
def blur(id, sd): return f'<filter id="{id}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{sd}"/></filter>'

def ridge(seed, base, amp, fill, ridged=True, step=6, op=1, sm=1.0):
    r = random.Random(seed)
    comps = [(r.uniform(.0012, .0026) * k * sm, r.uniform(0, 6.28), 1 / (k ** 1.1)) for k in (1, 2, 3, 5, 8, 13, 21)]
    tot = sum(c[2] for c in comps); pts = []
    for x in range(0, W + step, step):
        v = 0
        for f, ph, a in comps:
            s = math.sin(f * x + ph)
            v += a * ((1 - abs(s)) if ridged else s)
        y = base - amp * (v / tot) * (1.4 if ridged else 1.0)
        pts.append((x, y))
    d = f"M0,{H} L" + " L".join(f"{x},{y:.1f}" for x, y in pts) + f" L{W},{H} Z"
    return f'<path d="{d}" fill="{fill}" opacity="{op}"/>'

def pines(seed, y, n, hmin, hmax, color, op=1):
    r = random.Random(seed); out = []
    for _ in range(n):
        x = r.uniform(-20, W + 20); h = r.uniform(hmin, hmax); w = h * r.uniform(.28, .36)
        pts = [(x, y - h)]
        tiers = 6
        for t in range(1, tiers + 1):
            yy = y - h + h * t / tiers * 0.95
            ww = w * t / tiers
            pts.append((x + ww, yy)); pts.append((x + ww * .45, yy - h * .03))
        # rechte Seite abwärts, linke Seite wieder hoch
        right = pts[1:]
        left = [(2 * x - px, py) for (px, py) in reversed(right)]
        poly = [pts[0]] + right + [(x + w * .08, y + 40), (x - w * .08, y + 40)] + left
        out.append('<polygon points="' + " ".join(f"{a:.0f},{b:.0f}" for a, b in poly) + f'" fill="{color}" opacity="{op}"/>')
    return "".join(out)

def ribbon(seed, y0, amp, color, sd, op, thick=70, phase=0):
    r = random.Random(seed); pts = []
    f1 = r.uniform(.0018, .0030); f2 = r.uniform(.004, .007); p1 = r.uniform(0, 6) + phase; p2 = r.uniform(0, 6)
    for x in range(-100, W + 120, 40):
        pts.append((x, y0 + amp * math.sin(f1 * x + p1) + amp * .35 * math.sin(f2 * x + p2)))
    d = "M" + " L".join(f"{x},{y:.1f}" for x, y in pts)
    return f'<path d="{d}" stroke="{color}" stroke-width="{thick}" fill="none" stroke-linecap="round" opacity="{op}" filter="url(#b{sd})"/>'

def city(seed, base, hmin, hmax, wmin, wmax, color, win_colors, win_p=.18, op=1):
    r = random.Random(seed); x = -20; out = []
    while x < W + 20:
        w = r.uniform(wmin, wmax); h = r.uniform(hmin, hmax)
        out.append(f'<rect x="{x:.0f}" y="{base - h:.0f}" width="{w:.0f}" height="{h + 80:.0f}" fill="{color}" opacity="{op}"/>')
        if r.random() < .25:  # Antenne
            out.append(f'<rect x="{x + w / 2 - 1.5:.0f}" y="{base - h - r.uniform(20, 60):.0f}" width="3" height="60" fill="{color}" opacity="{op}"/>')
        for wx in range(int(x + 8), int(x + w - 8), 14):
            for wy in range(int(base - h + 12), int(base - 10), 18):
                if r.random() < win_p:
                    out.append(f'<rect x="{wx}" y="{wy}" width="6" height="8" fill="{r.choice(win_colors)}" opacity="{r.uniform(.5, 1):.2f}"/>')
        x += w + r.uniform(0, 6)
    return "".join(out)

SCENES = {}

# 1 Sternennacht
def nacht():
    d = lg("sky", [(0, "#03060f", None), (.45, "#0a1a35", None), (.8, "#173a5e", None), (1, "#2a5878", None)]) + BL() + \
        rg("moon", [(0, "#dfeaff", .9), (.12, "#9cc0ff", .35), (1, "#9cc0ff", 0)], .5, .5, .5) + \
        lg("m1", [(0, "#24435f", None), (1, "#0e2236", None)]) + lg("m2", [(0, "#12293d", None), (1, "#07121d", None)]) + lg("m3", [(0, "#08141f", None), (1, "#03070c", None)])
    b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>' + stars(11, 380, 620) + \
        f'<circle cx="1480" cy="230" r="330" fill="url(#moon)"/><circle cx="1480" cy="230" r="46" fill="#eef4ff" opacity=".95"/>' + \
        ridge(1, 760, 190, "url(#m1)", True, op=.95) + ridge(2, 850, 170, "url(#m2)", True, sm=1.3) + ridge(3, 960, 120, "url(#m3)", True, sm=1.7) + \
        pines(5, 1090, 38, 150, 330, "#02060a")
    return svg(b, d)
SCENES["nacht"] = nacht

# 2 Sonnenuntergang
def sonne():
    d = lg("sky", [(0, "#150c33", None), (.35, "#5a2570", None), (.62, "#d6456f", None), (.82, "#ff9a62", None), (1, "#ffd08a", None)]) + \
        rg("sun", [(0, "#fff3d0", 1), (.1, "#ffd08a", .85), (.35, "#ff8a5c", .35), (1, "#ff6a4c", 0)], .5, .5, .5) + \
        lg("m1", [(0, "#7a3868", None), (1, "#4a2358", None)]) + lg("m2", [(0, "#4a2158", None), (1, "#2a1245", None)]) + lg("m3", [(0, "#24103d", None), (1, "#0f0622", None)])
    b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>' + stars(21, 120, 330, False) + \
        f'<circle cx="1180" cy="700" r="520" fill="url(#sun)"/><circle cx="1180" cy="700" r="110" fill="#fff6dc"/>' + \
        ridge(31, 740, 150, "url(#m1)", True, op=1) + ridge(32, 850, 140, "url(#m2)", True, sm=1.3) + ridge(33, 960, 110, "url(#m3)", True, sm=1.8)
    return svg(b, d)
SCENES["sonnenuntergang"] = sonne

# 3 Aurora
def aurora():
    d = lg("sky", [(0, "#01040b", None), (.6, "#041326", None), (1, "#0a2a3a", None)]) + BL() + blur("b30", 30) + blur("b50", 50) + blur("b18", 18) + \
        lg("g1", [(0, "#37ffb4", None), (1, "#1fb8ff", None)], 0, 0, 1, 0) + lg("g2", [(0, "#a05cff", None), (1, "#2ff0d0", None)], 0, 0, 1, 0)
    b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>' + stars(41, 420, 700) + \
        ribbon(1, 300, 120, "#2affb0", 50, .55, 180) + ribbon(2, 360, 100, "#18c8ff", 30, .6, 90, 1) + ribbon(3, 250, 90, "#9a5cff", 50, .45, 150, 2) + ribbon(4, 330, 70, "#7dffe0", 18, .5, 28, .5) + \
        ridge(43, 940, 90, "#041019", False, sm=.8) + pines(45, 1090, 46, 110, 300, "#010509") + pines(46, 1100, 30, 70, 160, "#02070c", .95)
    return svg(b, d)
SCENES["aurora"] = aurora

# 4 Meer bei Dämmerung
def meer():
    d = lg("sky", [(0, "#0a1630", None), (.4, "#2c4a7c", None), (.75, "#e48a6a", None), (1, "#ffcf8a", None)]) + \
        lg("sea", [(0, "#f0a070", None), (.06, "#8a6a86", None), (.22, "#2f4672", None), (1, "#061024", None)]) + \
        rg("sun", [(0, "#fff2cc", 1), (.2, "#ffc78a", .6), (1, "#ff9a6a", 0)]) + blur("b6", 6) + blur("b20", 20)
    r = random.Random(51); waves = []
    for i in range(46):
        y = 600 + (i ** 1.55) * 3.2; amp = 3 + i * .5; op = .10 + i * .006
        pts = " L".join(f"{x},{y + amp * math.sin(x * (.004 + i * .00015) + i):.1f}" for x in range(0, W + 30, 30))
        waves.append(f'<path d="M{pts}" stroke="#bcd6ff" stroke-width="{1 + i * .05:.1f}" fill="none" opacity="{op:.2f}"/>')
    b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>' + stars(52, 140, 280, False) + \
        f'<circle cx="960" cy="590" r="380" fill="url(#sun)"/><circle cx="960" cy="590" r="70" fill="#fff4d6"/>' + \
        f'<rect y="590" width="{W}" height="{H - 590}" fill="url(#sea)"/>' + "".join(waves) + \
        f'<rect x="860" y="592" width="200" height="490" fill="#ffc98a" opacity=".55" filter="url(#b20)"/><rect x="925" y="592" width="70" height="440" fill="#fff0c8" opacity=".6" filter="url(#b6)"/><rect x="600" y="640" width="720" height="10" fill="#ffd9a0" opacity=".25" filter="url(#b6)"/><rect x="700" y="700" width="520" height="8" fill="#ffd9a0" opacity=".2" filter="url(#b6)"/>' + \
        ridge(53, 596, 36, "#1a2540", False, sm=.6, op=.9)
    return svg(b, d)
SCENES["meer"] = meer

# 5 Neon-Stadt
def neon():
    d = lg("sky", [(0, "#07011a", None), (.5, "#2a0a55", None), (.82, "#b0207c", None), (1, "#ff5ca8", None)]) + blur("b20", 20) + blur("b40", 40) + \
        rg("glow", [(0, "#ff4fa8", .7), (1, "#ff4fa8", 0)]) + rg("glow2", [(0, "#22d3ff", .45), (1, "#22d3ff", 0)])
    b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>' + stars(61, 160, 420, False) + \
        f'<ellipse cx="1350" cy="820" rx="700" ry="260" fill="url(#glow)"/><ellipse cx="520" cy="860" rx="600" ry="220" fill="url(#glow2)"/>' + \
        city(62, 880, 140, 360, 46, 110, "#1b0f3b", ["#ff7bd0", "#7fe9ff"], .1, .85) + \
        city(63, 960, 120, 330, 60, 140, "#0e0723", ["#ffd36e", "#ff7bd0", "#7fe9ff"], .16) + \
        city(64, 1090, 90, 260, 80, 170, "#05020f", ["#ffd36e", "#7fe9ff"], .12) + \
        '<rect x="0" y="1060" width="1920" height="20" fill="#ff4fa8" opacity=".5" filter="url(#b20)"/>'
    return svg(b, d)
SCENES["neon-city"] = neon

# 6 Nebelwald
def nebel():
    d = lg("sky", [(0, "#16242a", None), (.5, "#3c5a58", None), (1, "#b7cfc0", None)]) + \
        lg("f", [(0, "#cfe0d3", .0), (1, "#cfe0d3", .75)]) + blur("b30", 30) + \
        rg("sun", [(0, "#fff6d8", .8), (1, "#fff6d8", 0)])
    layers = [("#4f7767", 560, 38, 160, 240), ("#3d6355", 640, 40, 200, 300), ("#2c4b42", 740, 36, 240, 360), ("#1d352f", 850, 34, 280, 430), ("#0f201c", 980, 30, 330, 520)]
    b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/><circle cx="1450" cy="300" r="380" fill="url(#sun)"/>'
    for i, (c, y, n, hmin, hmax) in enumerate(layers):
        b += ridge(70 + i, y, 60, c, False, op=1, sm=.7) + pines(80 + i, y + 40 + i * 5, n, hmin * .55, hmax * .55, c)
        b += f'<rect y="{y - 80}" width="{W}" height="{260}" fill="url(#f)" opacity="{.5 - i * .07:.2f}"/>'
    return svg(b, d)
SCENES["nebelwald"] = nebel

# 7 Mesh Violett
def mesh():
    d = blur("b90", 90) + blur("b140", 140)
    blobs = [("#5b3df5", 300, 250, 520), ("#ff3fa0", 1500, 220, 460), ("#18c4ff", 1650, 820, 520), ("#7a4cff", 400, 900, 480), ("#2ee6b8", 980, 620, 300), ("#ff7a3d", 900, 120, 260)]
    b = f'<rect width="{W}" height="{H}" fill="#07071a"/>' + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}" opacity=".62" filter="url(#b140)"/>' for c, x, y, r in blobs) + \
        f'<rect width="{W}" height="{H}" fill="#07071a" opacity=".25"/>'
    return svg(b, d)
SCENES["mesh"] = mesh

# 8 Graphit
def graphit():
    d = lg("bg", [(0, "#10141b", None), (1, "#1c222c", None)], 0, 0, 1, 1) + blur("b60", 60) + \
        rg("g1", [(0, "#6f8bb8", .45), (1, "#6f8bb8", 0)]) + rg("g2", [(0, "#b58cff", .3), (1, "#b58cff", 0)])
    lines = "".join(f'<path d="M{-100 + i * 140},{H + 50} L{500 + i * 140},-50" stroke="#fff" stroke-width="1" opacity=".035"/>' for i in range(24))
    b = f'<rect width="{W}" height="{H}" fill="url(#bg)"/><ellipse cx="300" cy="140" rx="800" ry="500" fill="url(#g1)"/><ellipse cx="1650" cy="960" rx="700" ry="420" fill="url(#g2)"/>' + lines
    return svg(b, d)
SCENES["graphit"] = graphit

# 9 Dünen
def duenen():
    d = lg("sky", [(0, "#2a1a3a", None), (.35, "#8a4a62", None), (.65, "#f08a5a", None), (1, "#ffd08a", None)]) + \
        rg("sun", [(0, "#fff2cc", 1), (.2, "#ffd08a", .5), (1, "#ff9a5a", 0)]) + \
        lg("d1", [(0, "#d98a5c", None), (1, "#a8553f", None)]) + lg("d2", [(0, "#b8613f", None), (1, "#7e3a35", None)]) + lg("d3", [(0, "#7a3534", None), (1, "#3d1a28", None)]) + lg("d4", [(0, "#38172a", None), (1, "#1a0a18", None)])
    b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>' + stars(91, 90, 260, False) + \
        f'<circle cx="1400" cy="560" r="420" fill="url(#sun)"/><circle cx="1400" cy="560" r="64" fill="#fff6dc"/>' + \
        ridge(92, 700, 70, "url(#d1)", False, sm=.8, step=8) + ridge(93, 800, 80, "url(#d2)", False, sm=1.0, step=8) + ridge(94, 900, 90, "url(#d3)", False, sm=1.2, step=8) + ridge(95, 1000, 70, "url(#d4)", False, sm=1.5, step=8)
    return svg(b, d)
SCENES["duenen"] = duenen

if __name__ == "__main__":
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": W, "height": H})
        for name, fn in SCENES.items():
            pg.set_content(f'<body style="margin:0;background:#000">{fn()}</body>')
            png = pg.screenshot(type="png", clip={"x": 0, "y": 0, "width": W, "height": H})
            im = Image.open(io.BytesIO(png)).convert("RGB")
            im.save(os.path.join(OUT, f"{name}.jpg"), quality=86, optimize=True, progressive=True)
            im.resize((320, 180), Image.LANCZOS).save(os.path.join(OUT, "thumb", f"{name}.jpg"), quality=80, optimize=True)
            print("ok", name, os.path.getsize(os.path.join(OUT, f"{name}.jpg")) // 1024, "KB")
        br.close()
