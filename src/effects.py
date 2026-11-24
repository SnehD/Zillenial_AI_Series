"""Procedural, original visual effects for Zillenial Talk (no third-party assets, no license concerns).

Effects are triggered per scene from episode.json ("fx": [...]) or DEFAULT_FX below.
Trigger spec: {"type": "confetti|rays|sparkle|punch|shake", "at": 1.5 | "p1" | "p1+0.5", "x": 540, "y": 700}
"""
import math, random
from PIL import ImageDraw

TEAL, YELLOW, PINK, WHITE, CORAL = (46, 230, 197), (255, 209, 102), (255, 120, 200), (255, 255, 255), (255, 107, 107)
PALETTE = [TEAL, YELLOW, PINK, WHITE, CORAL, (140, 120, 255)]

DEFAULT_FX = {
    "spam": [{"type": "punch", "at": "p2"}, {"type": "sparkle", "at": "p2", "x": 800, "y": 520}],
    "cats": [{"type": "sparkle", "at": "p0+0.8", "x": 540, "y": 1070}, {"type": "confetti", "at": "p2+1.0", "x": 740, "y": 960}],
    "flow": [{"type": "punch", "at": "p1"}, {"type": "sparkle", "at": "p1+3.4", "x": 540, "y": 950}, {"type": "punch", "at": "p2"}],
    "breaks": [{"type": "shake", "at": "p1+0.5"}],
    "takeaway": [{"type": "rays", "at": 0.1, "x": 540, "y": 760}, {"type": "confetti", "at": "p2", "x": 540, "y": 800}],
    "endcard": [{"type": "rays", "at": 0.1, "x": 540, "y": 700}, {"type": "confetti", "at": 0.3, "x": 540, "y": 650}],
    "jargon": [{"type": "shake", "at": "p2"}],
    "roadmap": [{"type": "sparkle", "at": 8.0, "x": 500, "y": 990}, {"type": "punch", "at": 0.1}],
    "card": [{"type": "sparkle", "at": 1.2, "x": 540, "y": 700}],
    "recipe": [{"type": "sparkle", "at": 0.9, "x": 540, "y": 700}],
    "chef": [{"type": "sparkle", "at": 1.0, "x": 540, "y": 700}, {"type": "punch", "at": 0.1}],
}


def resolve(spec, offs):
    if isinstance(spec, (int, float)):
        return float(spec)
    base, _, plus = spec.partition("+")
    i = int(base[1:])
    return offs[min(i, len(offs) - 1)] + (float(plus) if plus else 0.0)


def resolve_all(fx_list, offs):
    return [dict(f, t0=resolve(f["at"], offs)) for f in fx_list]


def star(d, cx, cy, r, col):
    d.polygon([(cx, cy - r), (cx + r * .22, cy - r * .22), (cx + r, cy), (cx + r * .22, cy + r * .22),
               (cx, cy + r), (cx - r * .22, cy + r * .22), (cx - r, cy), (cx - r * .22, cy - r * .22)], fill=col)


def rays(d, cx, cy, age):
    a = min(1.0, age / .5) * (0.16 + 0.04 * math.sin(age * 3))
    rot = age * .35
    for i in range(14):
        ang = rot + i * (2 * math.pi / 14)
        w = .09
        pts = [(cx, cy)] + [(cx + math.cos(ang + k) * 1500, cy + math.sin(ang + k) * 1500) for k in (-w, w)]
        d.polygon(pts, fill=(255, 255, 255, int(255 * a)))


def confetti(d, cx, cy, age, seed=1):
    rnd = random.Random(seed)
    for i in range(46):
        ang = rnd.uniform(-math.pi, 0) + rnd.uniform(-.3, .3)
        sp = rnd.uniform(380, 900)
        vx, vy = math.cos(ang) * sp, math.sin(ang) * sp
        x = cx + vx * age
        y = cy + vy * age + 0.5 * 1500 * age * age
        life = 2.2
        if age > life or y > 1900:
            continue
        al = int(255 * min(1, (life - age) / .6))
        sz = rnd.uniform(11, 22)
        rot = rnd.uniform(0, 6.3) + age * rnd.uniform(-9, 9)
        col = PALETTE[i % len(PALETTE)] + (al,)
        w, h = sz, sz * .55 * abs(math.cos(rot * .7)) + 3
        pts = [(x + math.cos(rot) * px - math.sin(rot) * py, y + math.sin(rot) * px + math.cos(rot) * py)
               for px, py in [(-w, -h), (w, -h), (w, h), (-w, h)]]
        d.polygon(pts, fill=col)


def sparkle(d, cx, cy, age, seed=2):
    rnd = random.Random(seed)
    for i in range(7):
        ox, oy = rnd.uniform(-130, 130), rnd.uniform(-110, 110)
        delay = i * .09
        t = age - delay
        if t < 0 or t > .9:
            continue
        r = 40 * math.sin(math.pi * t / .9) * rnd.uniform(.6, 1.1)
        star(d, cx + ox, cy + oy, max(1, r), (255, 255, 255, 235) if i % 2 else YELLOW + (235,))


def state(fx, lt):
    """Return (punch_scale, shake_dx, shake_dy) for the visual layer at scene time lt."""
    s, dx, dy = 1.0, 0, 0
    for f in fx:
        a = lt - f["t0"]
        if f["type"] == "punch" and 0 <= a < .6:
            s *= 1 + .07 * math.exp(-a * 7) * math.cos(a * 18) ** 2
        if f["type"] == "shake" and 0 <= a < .5:
            k = math.exp(-a * 7) * 14
            dx += int(k * math.sin(a * 70))
            dy += int(k * math.cos(a * 55))
    return s, dx, dy


def draw_under(d, fx, lt):
    for f in fx:
        if f["type"] == "rays" and lt >= f["t0"]:
            rays(d, f.get("x", 540), f.get("y", 760), lt - f["t0"])


def draw_over(d, fx, lt):
    for n, f in enumerate(fx):
        a = lt - f["t0"]
        if a < 0:
            continue
        if f["type"] == "confetti":
            confetti(d, f.get("x", 540), f.get("y", 760), a, seed=n + 7)
        elif f["type"] == "sparkle":
            sparkle(d, f.get("x", 540), f.get("y", 760), a, seed=n + 3)
