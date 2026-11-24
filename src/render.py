"""Zillenial Talk episode renderer.

Usage:  python src/render.py episodes/ep-003-what-is-ai/episode.json

Reads editorial content from episode.json (narration, captions, scenes) and produces:
  audio/voiceovers/<slug>/*.wav   per-phrase voice (Windows SAPI, offline)
  captions/<slug>.srt             synced captions
  renders/<slug>.mp4              1080x1920 9:16 video with burned-in captions
  thumbnails/<slug>.png           cover image
No editorial text lives in this file except brand strings.
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import effects as FX

W, H, FPS, SR = 1080, 1920, 30, 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = "C:/Windows/Fonts/"

# ---- brand palette (text always paired with labels; color is never the only signal)
NAVY, PURPLE = (20, 18, 58), (66, 40, 140)
TEAL, YELLOW, CORAL, WHITE, SOFT = (46, 230, 197), (255, 209, 102), (255, 107, 107), (255, 255, 255), (200, 196, 235)


def font(size, bold=True):
    for n in (["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]):
        p = FONT_DIR + n
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def back(t):
    t = clamp(t)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def pop(lt, t0, dur=0.45):
    return back((lt - t0) / dur) if lt >= t0 else 0.0


def fade(lt, t0, dur=0.3):
    return clamp((lt - t0) / dur)


def gradient(c1, c2):
    y = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(c1) * (1 - y) + np.array(c2) * y).astype(np.uint8)
    arr = np.repeat(arr, W, axis=1)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def ctext(d, cx, cy, s, f, fill=WHITE, stroke=0, sfill=NAVY):
    w = d.textlength(s, font=f)
    d.text((cx - w / 2, cy), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)


def rbox(d, cx, cy, w, h, s=1.0, fill=(255, 255, 255, 30), outline=None, width=4, r=36):
    w, h = w * s, h * s
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], r, fill=fill, outline=outline, width=width)


def cat(d, cx, cy, r, col, s=1.0, glasses=False):
    r *= s
    if r < 2:
        return
    dark = tuple(int(c * 0.55) for c in col)
    d.polygon([(cx - r * .95, cy - r * .1), (cx - r * .75, cy - r * 1.25), (cx - r * .15, cy - r * .75)], fill=col)
    d.polygon([(cx + r * .95, cy - r * .1), (cx + r * .75, cy - r * 1.25), (cx + r * .15, cy - r * .75)], fill=col)
    d.ellipse([cx - r, cy - r * .8, cx + r, cy + r * .8], fill=col)
    for sx in (-1, 1):
        ex = cx + sx * r * .42
        d.ellipse([ex - r * .14, cy - r * .25, ex + r * .14, cy + r * .1], fill=NAVY)
        d.line([(cx + sx * r * .45, cy + r * .25), (cx + sx * r * 1.25, cy + r * .15)], fill=dark, width=max(2, int(r * .04)))
        d.line([(cx + sx * r * .45, cy + r * .32), (cx + sx * r * 1.25, cy + r * .42)], fill=dark, width=max(2, int(r * .04)))
    d.polygon([(cx - r * .1, cy + r * .12), (cx + r * .1, cy + r * .12), (cx, cy + r * .26)], fill=CORAL)
    if glasses:
        for sx in (-1, 1):
            ex = cx + sx * r * .42
            d.ellipse([ex - r * .26, cy - r * .38, ex + r * .26, cy + r * .2], outline=WHITE, width=max(3, int(r * .06)))
        d.line([(cx - r * .16, cy - r * .1), (cx + r * .16, cy - r * .1)], fill=WHITE, width=max(3, int(r * .05)))


def check(d, cx, cy, r, col=TEAL):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    d.line([(cx - r * .45, cy), (cx - r * .1, cy + r * .4), (cx + r * .5, cy - r * .35)], fill=NAVY, width=int(r * .28))


# ---------------- scene visuals: f(d, lt, ph) where ph = phrase start offsets within scene
def v_spam(d, lt, ph):
    s = pop(lt, 0.2)
    cx, cy = 540, 700
    rbox(d, cx, cy, 560, 360, s, fill=(255, 255, 255, 235), r=40)
    if s > 0:
        w, h = 560 * s, 360 * s
        d.line([(cx - w / 2 + 14, cy - h / 2 + 14), (cx, cy + h * .05), (cx + w / 2 - 14, cy - h / 2 + 14)], fill=(150, 140, 200), width=10)
    if lt >= ph[1]:
        p = pop(lt, ph[1])
        rbox(d, 540, 1000, 700, 110, p, fill=(255, 107, 107, 60), outline=CORAL, width=5, r=55)
        if p > .6:
            ctext(d, 540, 968, "RULES WRITTEN: 0", font(56), WHITE)
    if lt >= ph[2]:
        p = pop(lt, ph[2], .5)
        r = 120 * p
        d.ellipse([800 - r, 520 - r, 800 + r, 520 + r], fill=YELLOW)
        if p > .5:
            ctext(d, 800, 520 - 85, "?", font(int(190 * p)), NAVY)


def v_cats(d, lt, ph):
    cols = [(255, 170, 90), (170, 170, 190), (240, 220, 200), (120, 120, 150), (255, 140, 160), (160, 220, 180)]
    if lt < ph[1]:
        cat(d, 540, 760, 230, cols[0], pop(lt, 0.2))
        if lt > 0.8:
            p = pop(lt, 0.8)
            rbox(d, 540, 1070, 300 * 1, 100, p, fill=(46, 230, 197, 60), outline=TEAL, width=5, r=50)
            if p > .6:
                ctext(d, 540, 1040, "CAT", font(60), WHITE)
        return
    for i, c in enumerate(cols):
        t0 = ph[1] + i * 0.55
        gx, gy = 220 + (i % 3) * 320, 520 + (i // 3) * 280
        cat(d, gx, gy, 95, c, pop(lt, t0, .4))
    if lt >= ph[2]:
        p = pop(lt, ph[2], .5)
        rbox(d, 540, 1040, 520, 250, p, fill=(255, 255, 255, 20), outline=TEAL, width=5, r=40)
        cat(d, 540, 1040, 85, (110, 100, 170), p, glasses=True)
        if p > .8:
            check(d, 740, 960, 42)
            ctext(d, 540, 1180, "A cat it has never seen", font(44, False), SOFT)


def v_flow(d, lt, ph):
    if lt < ph[1]:
        p = pop(lt, 0.2)
        r = 230 * p
        d.ellipse([540 - r, 720 - r, 540 + r, 720 + r], fill=(46, 230, 197, 255))
        if p > .6:
            ctext(d, 540, 720 - 120, "AI", font(int(240 * p)), NAVY)
        return
    labels = ["LOTS OF EXAMPLES", "LEARNS PATTERNS", "AI MODEL"]
    for i, lab in enumerate(labels):
        t0 = ph[1] + i * 1.7
        p = pop(lt, t0, .45)
        cy = 520 + i * 215
        rbox(d, 540, cy, 800, 150, p, fill=(255, 255, 255, 38), outline=(TEAL if i == 2 else SOFT), width=5, r=40)
        if p > .6:
            ctext(d, 540, cy - 36, lab, font(60), WHITE)
        if i < 2 and lt > t0 + .5:
            a = clamp((lt - t0 - .5) / .3)
            ay = cy + 85
            d.polygon([(500, ay), (580, ay), (540, ay + 40)], fill=(255, 209, 102, int(255 * a)))
    if lt >= ph[2]:
        for i, lab in enumerate(["SPAM FILTER", "PHOTO SEARCH", "CHATBOT"]):
            p = pop(lt, ph[2] + i * .35, .4)
            rbox(d, 190 + i * 350, 1090, 320, 84, p, fill=(255, 209, 102, 255), r=42)
            if p > .7:
                ctext(d, 190 + i * 350, 1090 - 24, lab, font(34), NAVY)


def v_breaks(d, lt, ph):
    p = pop(lt, 0.2)
    ctext(d, 540, 420, "WHERE THE ANALOGY BREAKS", font(50), YELLOW) if p > .5 else None
    rbox(d, 290, 760, 440, 480, p, fill=(255, 255, 255, 36), outline=SOFT, r=40)
    rbox(d, 790, 760, 440, 480, p, fill=(255, 255, 255, 36), outline=SOFT, r=40)
    if p > .7:
        ctext(d, 290, 560, "TODDLER", font(54), WHITE)
        cat(d, 290, 740, 100, (255, 170, 90))
        ctext(d, 290, 880, "understands", font(46, False), SOFT)
        ctext(d, 790, 560, "AI", font(54), WHITE)
        for i in range(12):
            gx, gy = 650 + (i % 4) * 66, 700 + (i // 4) * 66
            d.ellipse([gx - 14, gy - 14, gx + 14, gy + 14], fill=TEAL)
        ctext(d, 790, 880, "finds patterns", font(46, False), SOFT)
    if lt >= ph[1]:
        q = pop(lt, ph[1] + .5, .5)
        rbox(d, 790, 1060, 520, 100, q, fill=(255, 107, 107, 70), outline=CORAL, width=5, r=50)
        if q > .7:
            ctext(d, 790, 1028, "! can be confidently wrong", font(38), WHITE)


def v_takeaway(d, lt, ph):
    if lt < ph[2]:
        p = pop(lt, 0.2)
        rbox(d, 540, 760, 900, 560, p, fill=(255, 255, 255, 36), outline=TEAL, width=6, r=50)
        if p > .7:
            ctext(d, 540, 540, "AI =", font(130), TEAL)
            ctext(d, 540, 710, "software that learns", font(66), WHITE)
            ctext(d, 540, 800, "patterns from examples", font(66), WHITE)
            ctext(d, 540, 930, "not only rules a human wrote", font(42, False), SOFT)
    else:
        p = pop(lt, ph[2], .5)
        ctext(d, 540, int(600), "ZILLENIAL", font(int(150 * clamp(p, .01, 1.1))), WHITE, stroke=0) if p > .3 else None
        ctext(d, 540, 760, "TALK", font(int(150 * clamp(p, .01, 1.1))), TEAL) if p > .3 else None
        if lt > ph[2] + .8:
            ctext(d, 540, 960, "Big tech words. Simple real-life stories.", font(44, False), SOFT)
            ctext(d, 540, 1030, "@zillenial_talk", font(48), YELLOW)


def v_endcard(d, lt, ph):
    p = pop(lt, 0.2, .5)
    if p > .3:
        ctext(d, 540, 600, "ZILLENIAL", font(int(150 * clamp(p, .01, 1.1))), WHITE)
        ctext(d, 540, 760, "TALK", font(int(150 * clamp(p, .01, 1.1))), TEAL)
    if lt > 1.0:
        ctext(d, 540, 960, "Big tech words. Simple real-life stories.", font(44, False), SOFT)
        ctext(d, 540, 1030, "@zillenial_talk", font(48), YELLOW)


def v_card(d, lt, ph, card):
    p = pop(lt, 0.2)
    rbox(d, 540, 760, 900, 600, p, fill=(255, 255, 255, 36), outline=TEAL, width=6, r=50)
    if p > .7:
        ctext(d, 540, 520, card["title"], font(88), TEAL)
        y = 680
        for i, ln in enumerate(card["lines"]):
            if lt > 0.5 + i * 0.9:
                ctext(d, 540, y, ln, font(58), WHITE)
            y += 100
        if card.get("foot") and lt > 0.5 + len(card["lines"]) * 0.9:
            ctext(d, 540, 1020, card["foot"], font(42, False), SOFT)


def v_jargon(d, lt, ph):
    words = [("LLM", 250, 560), ("AGENTS", 760, 640), ("RAG", 300, 800), ("TOKENS", 740, 900), ("MCP", 520, 1040), ("API", 200, 1000)]
    for i, (w, x, y) in enumerate(words):
        p = pop(lt, 0.4 + i * 0.55, .4)
        wd = 250 if len(w) > 3 else 190
        rbox(d, x, y, wd, 100, p, fill=(255, 255, 255, 235), r=50)
        if p > .7:
            ctext(d, x, y - 30, w, font(48), NAVY)
    if lt >= ph[2]:
        q = pop(lt, ph[2], .5)
        r = 110 * q
        d.ellipse([540 - r, 420 - r, 540 + r, 420 + r], fill=YELLOW)
        if q > .5:
            ctext(d, 540, 420 - 80, "?", font(int(170 * q)), NAVY)


def v_roadmap(d, lt, ph):
    stops = ["AI BASICS", "TALKING TO AI", "AI APPS & APIs", "AGENTS", "MCP & CODING TOOLS", "FORWARD DEPLOYED ENGINEER"]
    d.line([(150, 470), (150, 470 + 5 * 130)], fill=(200, 196, 235, 120), width=8)
    for i, s in enumerate(stops):
        t0 = 0.3 + i * 1.5
        p = pop(lt, t0, .45)
        cy = 470 + i * 130
        r = 34 * p
        d.ellipse([150 - r, cy - r, 150 + r, cy + r], fill=(YELLOW if i == 5 else TEAL))
        if p > .6:
            d.text((220, cy - 32), f"{i + 1}  {s}", font=font(44 if i < 5 else 36), fill=WHITE + (255,))


def v_recipe(d, lt, ph):
    p = pop(lt, 0.2)
    rbox(d, 540, 760, 800, 560, p, fill=(255, 250, 235, 245), r=30)
    if p > .7:
        ctext(d, 540, 520, "RECIPE CARD", font(64), (120, 70, 40))
        for i, ln in enumerate(["1. Add 2 cups flour", "2. Stir for 2 minutes", "3. Bake 20 minutes"]):
            if lt > 0.8 + i * 0.9:
                ctext(d, 540, 650 + i * 100, ln, font(54, False), (70, 50, 40))
        if lt > ph[1]:
            ctext(d, 540, 960, "Every step written by a human", font(40), CORAL if False else (150, 60, 60))


def v_chef(d, lt, ph):
    p = pop(lt, 0.2)
    cx, cy = 540, 700
    r = 150 * p
    d.ellipse([cx - r * .75, cy - r * 1.55, cx + r * .75, cy - r * .45], fill=WHITE)
    d.rectangle([cx - r * .6, cy - r * .55, cx + r * .6, cy - r * .1], fill=WHITE)
    d.ellipse([cx - r * .7, cy - r * .1, cx + r * .7, cy + r * 1.1], fill=(255, 205, 170))
    d.ellipse([cx - r * .3, cy + r * .2, cx - r * .15, cy + r * .35], fill=NAVY)
    d.ellipse([cx + r * .15, cy + r * .2, cx + r * .3, cy + r * .35], fill=NAVY)
    if lt > 0.8:
        n = int(clamp((lt - 0.8) / 0.25, 0, 12))
        for i in range(n):
            gx, gy = 190 + (i % 6) * 140, 980 + (i // 6) * 110
            d.ellipse([gx - 45, gy - 28, gx + 45, gy + 28], fill=(255, 255, 255, 235))
            d.ellipse([gx - 25, gy - 14, gx + 25, gy + 14], fill=(255, 170, 90))
        ctext(d, 540, 880, "thousands of dishes cooked", font(40, False), SOFT)


VISUALS = {"spam": v_spam, "cats": v_cats, "flow": v_flow, "breaks": v_breaks, "takeaway": v_takeaway,
           "endcard": v_endcard, "card": v_card, "jargon": v_jargon, "roadmap": v_roadmap, "recipe": v_recipe, "chef": v_chef}


# ---------------- playful layer: emoji stickers, animated bg, mascot, sfx
PINK, SKIN, HAIR = (255, 120, 200), (255, 205, 170), (70, 40, 40)
_EMO = {}


def emoji_img(ch, size):
    size = max(12, int(size // 6 * 6))
    if (ch, 0) not in _EMO:
        f = ImageFont.truetype(FONT_DIR + "seguiemj.ttf", 109)
        im = Image.new("RGBA", (200, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
        _EMO[(ch, 0)] = im.crop(im.getbbox() or (0, 0, 200, 160))
    if (ch, size) not in _EMO:
        src = _EMO[(ch, 0)]
        sc = size / max(src.size)
        _EMO[(ch, size)] = src.resize((max(1, int(src.size[0] * sc)), max(1, int(src.size[1] * sc))), Image.LANCZOS)
    return _EMO[(ch, size)]


def blit(frame, img, cx, cy):
    x, y = int(cx - img.size[0] / 2), int(cy - img.size[1] / 2)
    x, y = max(0, min(W - img.size[0], x)), max(0, min(H - img.size[1], y))
    frame.alpha_composite(img, (x, y))


DEFAULT_STICKERS = {
    "spam": [("📬", 150, 480, 120, 0.8), ("🚫", 900, 900, 120, "p1"), ("🤔", 160, 960, 120, "p2")],
    "cats": [("🐾", 110, 1160, 90, "p1"), ("😻", 940, 1160, 100, "p2")],
    "flow": [("🧠", 130, 1190, 90, "p1"), ("✨", 120, 420, 90, "p1+1.5"), ("🚀", 960, 1190, 90, "p2+1")],
    "breaks": [("⚠️", 990, 1190, 90, "p1+0.5"), ("🤷", 120, 1190, 100, "p1")],
    "takeaway": [("💡", 960, 470, 120, 0.6), ("🎉", 130, 1120, 110, "p2")],
    "endcard": [("👋", 540, 420, 150, 0.3), ("✨", 150, 700, 100, 0.6), ("✨", 930, 830, 100, 0.8)],
    "jargon": [("😵", 540, 1210, 130, "p2")],
    "roadmap": [("🗺️", 940, 470, 130, 0.4), ("🏁", 950, 1110, 100, "p3")],
    "card": [("✅", 940, 500, 110, 0.8), ("✨", 130, 1100, 90, 1.5)],
    "recipe": [("🍳", 910, 480, 130, 0.6), ("🥣", 160, 1100, 110, "p1")],
    "chef": [("🍲", 180, 500, 120, 0.6), ("🧂", 920, 860, 100, "p2"), ("👩", 910, 520, 120, 0.9)],
}


def resolve_t(spec, offs):
    if isinstance(spec, (int, float)):
        return float(spec)
    base, _, plus = spec.partition("+")
    i = int(base[1:])
    return offs[min(i, len(offs) - 1)] + (float(plus) if plus else 0.0)


def bg_fx(frame, tt):
    sm = Image.new("RGBA", (W // 4, H // 4), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sm, "RGBA")
    for fx, fy, r, col, a, sp in [(.2, .25, 95, PINK, 80, .05), (.8, .5, 105, TEAL, 60, .04), (.3, .85, 90, YELLOW, 45, .06), (.85, .12, 80, PINK, 60, .07)]:
        cx = fx * W / 4 + 25 * math.sin(tt * sp * 6 + fx * 9)
        cy = fy * H / 4 + 30 * math.cos(tt * sp * 5 + fy * 7)
        ds.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (a,))
    from PIL import ImageFilter
    sm = sm.filter(ImageFilter.GaussianBlur(14)).resize((W, H), Image.BILINEAR)
    frame.alpha_composite(sm)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    for i in range(18):
        x = (i * 137 % 1000) + 40 + 30 * math.sin(tt * .8 + i)
        y = H + 100 - ((tt * 38 + i * 173) % (H + 200))
        s = 9 + (i % 4) * 5
        col = [WHITE, YELLOW, TEAL, PINK][i % 4] + (120,)
        k = i % 3
        if k == 0:
            d.ellipse([x - s / 2, y - s / 2, x + s / 2, y + s / 2], fill=col)
        elif k == 1:
            d.line([(x - s, y), (x + s, y)], fill=col, width=4)
            d.line([(x, y - s), (x, y + s)], fill=col, width=4)
        else:
            d.polygon([(x, y - s), (x + s * .6, y), (x, y + s), (x - s * .6, y)], fill=col)
    frame.alpha_composite(layer)


def draw_mascot(d, cx, cy, tt, mouth):
    cy += 7 * math.sin(tt * 3)
    r = 68
    d.ellipse([cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10], fill=TEAL + (255,))
    d.ellipse([cx - 28, cy - r - 36, cx + 28, cy - r + 14], fill=HAIR + (255,))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SKIN + (255,))
    d.chord([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], 195, 345, fill=HAIR + (255,))
    blink = (tt % 3.3) < 0.12
    for sx in (-1, 1):
        ex, ey = cx + sx * r * .36, cy + r * .02
        if blink:
            d.line([(ex - 11, ey), (ex + 11, ey)], fill=NAVY + (255,), width=5)
        else:
            d.ellipse([ex - 8, ey - 12, ex + 8, ey + 12], fill=NAVY + (255,))
        d.ellipse([cx + sx * r * .62 - 13, cy + r * .3 - 8, cx + sx * r * .62 + 13, cy + r * .3 + 8], fill=(255, 140, 160, 150))
    mh = 6 + 30 * mouth
    d.ellipse([cx - 20, cy + r * .42 - mh / 3, cx + 20, cy + r * .42 + mh], fill=(150, 40, 70, 255))
    if mouth > .35:
        d.ellipse([cx - 12, cy + r * .42 + mh * .45, cx + 12, cy + r * .42 + mh * .95], fill=(255, 130, 140, 255))


def sfx_pop():
    t = np.arange(int(.12 * SR)) / SR
    return (np.sin(2 * np.pi * np.cumsum(500 + 900 * t / .12) / SR) * np.exp(-t * 35) * .5).astype(np.float32)


def sfx_whoosh():
    n = int(.4 * SR)
    sm = np.convolve(np.random.RandomState(1).randn(n), np.ones(60) / 60, "same")
    t = np.arange(n) / SR
    return (sm * np.sin(np.pi * t / .4) ** 2 * 2.5).astype(np.float32)


def sfx_ding():
    out = np.zeros(int(.9 * SR), dtype=np.float32)
    for k, f in enumerate((784, 988, 1175)):
        t = np.arange(int(.5 * SR)) / SR
        i = int(k * .13 * SR)
        out[i:i + len(t)] += (np.sin(2 * np.pi * f * t) * np.exp(-t * 6) * .4).astype(np.float32)
    return out


# ---------------- captions
def strip(w):
    return "".join(ch for ch in w.lower() if ch.isalnum())


STOP = {"a", "an", "the", "of", "to", "in", "on", "at", "and", "or", "but", "that", "is", "it's", "i'm", "for", "with", "from", "not", "just", "them", "they"}


def chunk_words(words):
    out, cur = [], []
    for w in words:
        cur.append(w)
        end_punct = w[-1] in ",.?!"
        if len(cur) >= 4 or (len(cur) >= 3 and end_punct):
            carry = []
            while len(cur) > 2 and not end_punct and strip(cur[-1]) in STOP:
                carry.insert(0, cur.pop())
            out.append(cur)
            cur = carry
    if cur:
        if out and len(cur) < 2:
            out[-1] += cur
        else:
            out.append(cur)
    return out


def draw_caption(d, words, hl, lt_in_chunk):
    f = font(72)
    lines, cur, curw = [], [], 0
    space = d.textlength(" ", font=f)
    for w in words:
        ww = d.textlength(w, font=f)
        if cur and curw + space + ww > 940:
            lines.append((cur, curw))
            cur, curw = [], 0
        curw += (space if cur else 0) + ww
        cur.append(w)
    lines.append((cur, curw))
    lh = 104
    total_h = lh * len(lines)
    p = clamp(lt_in_chunk / 0.12)
    y0 = 1330 + (1 - p) * 14
    maxw = max(w for _, w in lines)
    d.rounded_rectangle([540 - maxw / 2 - 36, y0 - 18, 540 + maxw / 2 + 36, y0 + total_h + 6], 36, fill=(12, 10, 40, int(200 * p)), outline=(255, 120, 200, int(255 * p)), width=5)
    for li, (ws, lw) in enumerate(lines):
        x = 540 - lw / 2
        for w in ws:
            col = YELLOW if strip(w) in hl else WHITE
            d.text((x, y0 + li * lh), w, font=f, fill=col + (int(255 * p),), stroke_width=4, stroke_fill=(12, 10, 40, int(255 * p)))
            x += d.textlength(w, font=f) + space


# ---------------- audio
def read_wav(path):
    with wave.open(path, "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    assert sw == 2, "expected 16-bit"
    a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    # trim leading/trailing silence
    idx = np.where(np.abs(a) > 0.01)[0]
    if len(idx):
        a = a[max(0, idx[0] - int(.02 * sr)): idx[-1] + int(.05 * sr)]
    if sr != SR:
        a = np.interp(np.linspace(0, len(a) - 1, int(len(a) * SR / sr)), np.arange(len(a)), a).astype(np.float32)
    return a


def music_bed(seconds):
    t = np.arange(int(seconds * SR)) / SR
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)]
    out = np.zeros_like(t, dtype=np.float32)
    seg = 4.0
    for i, ch in enumerate(chords * int(seconds / (seg * 4) + 2)):
        s0, s1 = int(i * seg * SR), int(min((i + 1) * seg * SR, len(t)))
        if s0 >= len(t):
            break
        tt = t[s0:s1]
        env = np.minimum(1, np.minimum((tt - tt[0]) / 1.2, (tt[-1] - tt) / 1.2 + 0.0001))
        for f0 in ch:
            out[s0:s1] += (np.sin(2 * np.pi * f0 * tt) * .6 + np.sin(2 * np.pi * f0 * 2 * tt) * .15).astype(np.float32) * env.astype(np.float32)
    return out / 3.0


def main(ep_path):
    ep = json.load(open(ep_path, encoding="utf-8"))
    import re
    cur = json.load(open(os.path.join(ROOT, "curriculum", "curriculum.json"), encoding="utf-8"))
    season = next(s for s in cur["seasons"] if s["from"] <= ep["episode"] <= s["to"])
    season_dir = f"season-{season['id']:02d}-" + re.sub(r"[^a-z0-9]+", "-", season["name"].lower()).strip("-")
    slug = f"S{season['id']:02d}E{ep['episode']:03d}-{ep['slug']}"
    SEASON_ID = season["id"]
    os.makedirs(os.path.join(ROOT, "renders", season_dir), exist_ok=True)
    # spoken + captioned series tag appended to the first phrase (keeps phrase indexes stable)
    p0 = ep["scenes"][0]["phrases"][0]
    tag = f" Season {season['id']}, episode {ep['episode']}."
    p0["say"] = p0.get("say", p0["text"]) + tag
    p0["text"] = p0["text"] + tag
    p0["hl"] = list(p0.get("hl", [])) + ["Season", f"{season['id']},", "episode", f"{ep['episode']}."]
    vo_dir = os.path.join(ROOT, "audio", "voiceovers", slug)
    os.makedirs(vo_dir, exist_ok=True)
    for sub in ("captions", "renders", "thumbnails"):
        os.makedirs(os.path.join(ROOT, sub), exist_ok=True)

    # 1) voice
    lines = []
    for sc in ep["scenes"]:
        for i, ph in enumerate(sc["phrases"]):
            ph["id"] = f"{sc['id']}_{i}"
            lines.append(f"{ph['id']}\t{ph.get('say', ph['text'])}")
    txt = os.path.join(vo_dir, "phrases.tsv")
    open(txt, "w", encoding="utf-8").write("\n".join(lines))
    v = ep.get("voice", {})
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(ROOT, "src", "tts_sapi.ps1"),
                    "-In", txt, "-OutDir", vo_dir, "-Voice", v.get("name", "Microsoft Zira Desktop"), "-Rate", str(v.get("rate", 1))], check=True)

    # 2) timeline
    t = 0.5
    audio_parts, scenes_tl, caps = [], [], []
    for sc in ep["scenes"]:
        s_start, offs = t, []
        for ph in sc["phrases"]:
            a = read_wav(os.path.join(vo_dir, ph["id"] + ".wav"))
            dur = len(a) / SR
            offs.append(t - s_start)
            audio_parts.append((t, a))
            words = ph["text"].split()
            chunks = chunk_words(words)
            weights = [sum(len(w) + 1 for w in c) for c in chunks]
            tot, cs = sum(weights), t
            hl = {strip(h) for h in ph.get("hl", [])}
            for c, wgt in zip(chunks, weights):
                cd = dur * wgt / tot
                caps.append((cs, cs + cd, c, hl))
                cs += cd
            t += dur + 0.3
        t += 0.35
        raw = sc.get("stickers")
        stk = [(e, x, y, s, resolve_t(t0, offs)) for (e, x, y, s, t0) in
               ([tuple(r) for r in raw] if raw else DEFAULT_STICKERS.get(sc["visual"], []))]
        fxs = FX.resolve_all(sc.get("fx") if sc.get("fx") is not None else FX.DEFAULT_FX.get(sc["visual"], []), offs)
        scenes_tl.append((sc["visual"], s_start, t, offs, sc.get("card"), stk, fxs))
    total = t + 0.8

    voice = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for st, a in audio_parts:
        i = int(st * SR)
        voice[i:i + len(a)] += a
    voice /= max(0.01, np.abs(voice).max()) / 0.9
    # lip-sync envelope (one value per video frame)
    win = SR // FPS
    nfr = len(voice) // win
    rms = np.sqrt((voice[:nfr * win].reshape(nfr, win) ** 2).mean(axis=1))
    ref = np.percentile(rms[rms > 0.01], 90) if (rms > 0.01).any() else 1.0
    env = np.clip(rms / ref, 0, 1)
    for i in range(1, len(env)):
        env[i] = env[i - 1] * .45 + env[i] * .55
    # sound effects: whoosh at each scene start, pop per sticker, ding on the end card
    sfx = np.zeros_like(voice)

    def put(a, at, gain):
        i = int(at * SR)
        if 0 <= i < len(sfx):
            seg = a[:len(sfx) - i]
            sfx[i:i + len(seg)] += seg * gain
    for vis, s0, s1, offs, card, stk, fxs in scenes_tl:
        put(sfx_whoosh(), s0, .10)
        for f in fxs:
            if f["type"] in ("confetti", "sparkle"):
                put(sfx_pop(), s0 + f["t0"], .14)
                put(sfx_ding(), s0 + f["t0"] + .05, .05)
            elif f["type"] in ("punch", "shake"):
                put(sfx_pop(), s0 + f["t0"], .10)
        for (e, x, y, s, t0) in stk:
            put(sfx_pop(), s0 + t0, .16)
        if vis == "endcard":
            put(sfx_ding(), s0 + .3, .12)
    mb = music_bed(len(voice) / SR + 1)
    mb = np.pad(mb, (0, max(0, len(voice) - len(mb))))[:len(voice)]
    mix = (voice + sfx + mb * 0.07) * 0.9
    mix = np.clip(mix, -1, 1)
    wav_path = os.path.join(vo_dir, "mix.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())

    # 3) captions srt
    def ts(x):
        h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    with open(os.path.join(ROOT, "captions", slug + ".srt"), "w", encoding="utf-8") as f:
        for i, (a, b, c, _) in enumerate(caps, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{' '.join(c)}\n\n")

    # 4) frames
    bgs = {}
    ff = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav_path, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                           "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest",
                           os.path.join(ROOT, "renders", season_dir, slug + ".mp4")], stdin=subprocess.PIPE)
    base = gradient((36, 22, 100), (150, 50, 165))
    hdr_f, tag_f = font(34), font(30, False)
    n = int(total * FPS)
    cover_done = False
    for fi in range(n):
        tt = fi / FPS
        sc = next((s for s in scenes_tl if s[1] <= tt < s[2]), scenes_tl[-1])
        lt = tt - sc[1]
        frame = base.copy()
        bg_fx(frame, tt)
        # header + progress + talking mascot (inside safe area)
        hl_ = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(hl_, "RGBA")
        d.text((70, 250), "Z I L L E N I A L   T A L K", font=hdr_f, fill=TEAL + (255,))
        d.text((70, 296), f"SEASON {SEASON_ID}  ·  EPISODE {ep['episode']}", font=tag_f, fill=SOFT + (255,))
        d.rounded_rectangle([70, 350, 70 + 940, 358], 4, fill=(255, 255, 255, 50))
        d.rounded_rectangle([70, 350, 70 + max(8, 940 * tt / total), 358], 4, fill=PINK + (255,))
        draw_mascot(d, 900, 305, tt, float(env[min(fi, len(env) - 1)]))
        frame.alpha_composite(hl_)
        # effects under the visual (light rays)
        ul = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        FX.draw_under(ImageDraw.Draw(ul, "RGBA"), sc[6], lt)
        frame.alpha_composite(ul)
        # scene visual with slide-in + gentle bob
        vl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(vl, "RGBA")
        if sc[0] in VG.CARD_VISUALS:
            VISUALS[sc[0]](d, lt, sc[3], sc[4])
        else:
            VISUALS[sc[0]](d, lt, sc[3])
        a = clamp(lt / 0.35)
        dx, dy = int((1 - a) ** 2 * 220), int(7 * math.sin(tt * 2.2))
        if a < 1:
            vl.putalpha(vl.split()[3].point(lambda v: int(v * a)))
        ps, sdx, sdy = FX.state(sc[6], lt)
        dx, dy = dx + sdx, dy + sdy
        # punch-zoom about the visual's centre (540, 760) + offsets
        vl = vl.transform((W, H), Image.AFFINE, (1 / ps, 0, 540 - 540 / ps - dx, 0, 1 / ps, 760 - 760 / ps - dy))
        frame.alpha_composite(vl)
        # emoji stickers
        for (e, sx, sy, ss, st0) in sc[5]:
            if lt >= st0:
                p = pop(lt, st0, .5)
                blit(frame, emoji_img(e, ss * max(p, .05) * (1 + .05 * math.sin(tt * 4 + sx))), sx, sy + 9 * math.sin(tt * 2.5 + sy))
        # confetti / sparkles above stickers, below captions
        ol = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        FX.draw_over(ImageDraw.Draw(ol, "RGBA"), sc[6], lt)
        frame.alpha_composite(ol)
        # captions on top
        cl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(cl, "RGBA")
        cap = next((c for c in caps if c[0] <= tt < c[1] + 0.12), None)
        if cap:
            draw_caption(d, cap[2], cap[3], tt - cap[0])
        frame = Image.alpha_composite(frame, cl).convert("RGB")
        if tt < 0.3:
            frame = Image.blend(Image.new("RGB", (W, H), NAVY), frame, tt / 0.3)
        if tt > total - 0.5:
            frame = Image.blend(frame, Image.new("RGB", (W, H), NAVY), (tt - (total - 0.5)) / 0.5)
        ff.stdin.write(frame.tobytes())
        if not cover_done and sc[0] == "flow" and lt > 8:
            pass
    ff.stdin.close()
    ff.wait()

    # 5) cover
    cv = base.copy()
    d = ImageDraw.Draw(cv, "RGBA")
    if ep.get("cover_icon", "cat") == "cat":
        cat(d, 540, 640, 260, (255, 170, 90))
    ctext(d, 540, 1000 if ep.get("cover_icon", "cat") == "cat" else 760, ep["publishing"]["thumbnail_text"], font(150), WHITE, stroke=8)
    ctext(d, 540, 1230, "Zillenial Talk · AI From Zero", font(48, False), TEAL)
    cv.convert("RGB").save(os.path.join(ROOT, "thumbnails", slug + ".png"))
    print(f"DONE {total:.1f}s -> renders/{season_dir}/{slug}.mp4")


import visuals_generic as VG  # noqa: E402
VISUALS.update(VG.register(sys.modules[__name__]))
DEFAULT_STICKERS.update(VG.DEFAULT_STICKERS)
FX.DEFAULT_FX.update(VG.DEFAULT_FX)

if __name__ == "__main__":
    main(sys.argv[1])
