"""Data-driven visual layouts for Zillenial Talk episodes.

Each visual reads its content from the scene's "card" object in episode.json, so a new episode
needs NO renderer code. Registered into render.VISUALS via register(render_module).
Reveal timing follows the narration: item i appears at phrase i's start when there are enough phrases.
"""
import math


def register(R):
    clamp, pop, ctext, rbox, font = R.clamp, R.pop, R.ctext, R.rbox, R.font
    TEAL, YELLOW, WHITE, SOFT, NAVY, CORAL, PINK = R.TEAL, R.YELLOW, R.WHITE, R.SOFT, R.NAVY, R.CORAL, R.PINK

    def fit(d, s, maxw, size, bold=True):
        while size > 26 and d.textlength(s, font=font(size, bold)) > maxw:
            size -= 2
        return font(size, bold)

    def ft(d, cx, y, s, maxw, size, fill=WHITE, bold=True):
        ctext(d, cx, y, s, fit(d, s, maxw, size, bold), fill)

    def times(n, ph):
        return [max(0.35, ph[i]) if n <= len(ph) else 0.35 + 0.9 * i for i in range(n)]

    def emo(d, ch, cx, cy, size):
        img = R.emoji_img(ch, size)
        x = int(max(0, min(R.W - img.size[0], cx - img.size[0] / 2)))
        y = int(max(0, min(R.H - img.size[1], cy - img.size[1] / 2)))
        d._image.alpha_composite(img, (x, y))

    def wrap(d, s, maxw, f):
        lines, cur = [], ""
        for w in s.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) > maxw and cur:
                lines.append(cur)
                cur = w
            else:
                cur = t
        if cur:
            lines.append(cur)
        return lines

    def arrow(d, x, y, a=1.0):
        d.polygon([(x - 34, y), (x + 34, y), (x, y + 34)], fill=YELLOW + (int(255 * a),))

    def v_steps(d, lt, ph, c):
        steps = c["steps"][:5]
        n = len(steps)
        ts = times(n, ph)
        if c.get("title"):
            ft(d, 540, 410, c["title"], 800, 50, YELLOW)
        gap = 165 if n < 5 else 150
        y0 = 540 if c.get("title") else 500
        for i, s in enumerate(steps):
            p = pop(lt, ts[i], .45)
            cy = y0 + i * gap
            rbox(d, 540, cy, 820, 120, p, fill=(255, 255, 255, 40), outline=(TEAL if i == n - 1 else SOFT), width=5, r=36)
            if p > .6:
                d.ellipse([170, cy - 34, 238, cy + 34], fill=TEAL + (255,))
                ctext(d, 204, cy - 30, str(i + 1), font(46), NAVY)
                ft(d, 590, cy - 30, s, 560, 50)
            if i < n - 1 and lt > ts[i] + .5:
                arrow(d, 540, cy + 62, clamp((lt - ts[i] - .5) / .3))
        if c.get("foot") and n <= 4 and lt > ts[-1] + .8:
            ft(d, 540, y0 + (n - 1) * gap + 110, c["foot"], 860, 42, SOFT, False)

    def v_compare(d, lt, ph, c):
        L, Rr = c["left"], c["right"]
        for k, (side, cx, t0) in enumerate(((L, 290, 0.3), (Rr, 790, max(0.6, ph[1] if len(ph) > 1 else 1.5)))):
            p = pop(lt, t0)
            rbox(d, cx, 740, 450, 560, p, fill=(255, 255, 255, 38), outline=(TEAL if k == 0 else PINK), width=5, r=40)
            if p > .7:
                if side.get("emoji"):
                    emo(d, side["emoji"], cx, 560, 120)
                ft(d, cx, 640, side["title"], 400, 52, YELLOW)
                for i, ln in enumerate(side["lines"][:3]):
                    if lt > t0 + .5 + i * .6:
                        ft(d, cx, 740 + i * 78, ln, 410, 40, WHITE, False)
        if c.get("warn") and lt >= ph[-1]:
            q = pop(lt, ph[-1] + .3, .5)
            rbox(d, 540, 1100, 860, 100, q, fill=(255, 107, 107, 80), outline=CORAL, width=5, r=50)
            if q > .7:
                ft(d, 540, 1070, "! " + c["warn"], 780, 40)

    def v_bigword(d, lt, ph, c):
        p = pop(lt, 0.25, .55)
        if c.get("emoji") and p > .05:
            emo(d, c["emoji"], 540, 520, 200 * p)
        if p > .3:
            ft(d, 540, 610, c["word"], 900, int(190 * clamp(p, .2, 1.05)), TEAL)
        if c.get("sub") and lt > .9:
            ft(d, 540, 860, c["sub"], 900, 56)
        if c.get("sub2") and lt > ph[min(1, len(ph) - 1)] + .3:
            ft(d, 540, 960, c["sub2"], 900, 44, SOFT, False)

    def ring(n, cx, cy, r, start=-90):
        return [(cx + r * math.cos(math.radians(start + i * 360 / n)), cy + r * math.sin(math.radians(start + i * 360 / n))) for i in range(n)]

    def v_loop(d, lt, ph, c):
        nodes = c["nodes"][:5]
        n = len(nodes)
        pts = ring(n, 540, 760, 300)
        ts = times(n, ph)
        for i in range(n):
            if (i < n - 1 and lt >= ts[i + 1]) or (i == n - 1 and lt >= ts[-1] + 1.0):
                a, b = pts[i], pts[(i + 1) % n]
                d.line([a, b], fill=(255, 209, 102, 150), width=6)
                mx, my = a[0] * .4 + b[0] * .6, a[1] * .4 + b[1] * .6
                ang = math.atan2(b[1] - a[1], b[0] - a[0])
                d.polygon([(mx + 26 * math.cos(ang), my + 26 * math.sin(ang)),
                           (mx + 22 * math.cos(ang + 2.5), my + 22 * math.sin(ang + 2.5)),
                           (mx + 22 * math.cos(ang - 2.5), my + 22 * math.sin(ang - 2.5))], fill=YELLOW + (255,))
        p0 = pop(lt, 0.2)
        r0 = 105 * p0
        d.ellipse([540 - r0, 760 - r0, 540 + r0, 760 + r0], fill=TEAL + (255,))
        if p0 > .7:
            ft(d, 540, 735, c.get("center", ""), 190, 44, NAVY)
        for i, (x, y) in enumerate(pts):
            p = pop(lt, ts[i], .45)
            rbox(d, x, y, 300, 92, p, fill=(255, 255, 255, 60), outline=SOFT, width=5, r=46)
            if p > .7:
                ft(d, x, y - 26, nodes[i], 260, 44)

    def v_stack(d, lt, ph, c):
        layers = c["layers"][:5]
        n = len(layers)
        ts = times(n, ph)
        if c.get("title"):
            ft(d, 540, 410, c["title"], 800, 50, YELLOW)
        y0 = 560 if c.get("title") else 520
        gap = 150 if n < 5 else 135
        for i, s in enumerate(layers):
            p = pop(lt, ts[i], .45)
            cy = y0 + i * gap
            rbox(d, 540, cy, 800, 112, p, fill=(255, 255, 255, 40 + 14 * i), outline=(TEAL if i % 2 == 0 else PINK), width=5, r=30)
            if p > .6:
                ft(d, 540, cy - 28, s, 720, 50)

    def v_chat(d, lt, ph, c):
        msgs = c["messages"][:4]
        ts = times(len(msgs), ph)
        f = font(40, False)
        y = 440
        for i, m in enumerate(msgs):
            lines = wrap(d, m["text"], 640, f)[:3]
            h = 60 + len(lines) * 52
            user = m.get("who", "you") == "you"
            x0 = 280 if user else 100
            p = pop(lt, ts[i], .4)
            if p > 0:
                cx = x0 + 350
                rbox(d, cx, y + h / 2, 700, h, p, fill=(46, 230, 197, 235) if user else (255, 255, 255, 235), r=34)
                if p > .7:
                    d.text((x0 + 22, y - 36), "YOU" if user else "AI", font=font(28), fill=SOFT + (255,))
                    for j, ln in enumerate(lines):
                        d.text((x0 + 30, y + 26 + j * 52), ln, font=f, fill=NAVY + (255,))
            y += h + 56

    def v_checklist(d, lt, ph, c):
        items = c["items"][:5]
        ts = times(len(items), ph)
        if c.get("title"):
            ft(d, 540, 410, c["title"], 800, 50, YELLOW)
        y0 = 560 if c.get("title") else 520
        for i, it in enumerate(items):
            p = pop(lt, ts[i], .45)
            cy = y0 + i * 150
            rbox(d, 540, cy, 840, 118, p, fill=(255, 255, 255, 38), outline=(TEAL if it.get("ok", True) else CORAL), width=5, r=34)
            if p > .6:
                emo(d, "✅" if it.get("ok", True) else "❌", 175, cy, 84)
                ft(d, 600, cy - 28, it["text"], 600, 46)

    def v_hub(d, lt, ph, c):
        sp = c["spokes"][:6]
        n = len(sp)
        pts = ring(n, 540, 770, 330)
        ts = times(n, ph)
        for i, (x, y) in enumerate(pts):
            if lt >= ts[i]:
                d.line([(540, 770), (x, y)], fill=(255, 209, 102, 170), width=6)
        p0 = pop(lt, 0.2)
        r0 = 120 * p0
        d.ellipse([540 - r0, 770 - r0, 540 + r0, 770 + r0], fill=TEAL + (255,))
        if p0 > .7:
            ft(d, 540, 740, c.get("center", ""), 210, 52, NAVY)
        for i, (x, y) in enumerate(pts):
            p = pop(lt, ts[i], .45)
            rbox(d, x, y, 270, 88, p, fill=(255, 255, 255, 235), r=44)
            if p > .7:
                ft(d, x, y - 24, sp[i], 230, 40, NAVY)

    return {"steps": v_steps, "compare": v_compare, "bigword": v_bigword, "loop": v_loop,
            "stack": v_stack, "chat": v_chat, "checklist": v_checklist, "hub": v_hub}


DEFAULT_STICKERS = {
    "steps": [("✨", 110, 1230, 80, "p1")],
    "compare": [("🤔", 540, 1230, 90, "p1")],
    "bigword": [("✨", 140, 560, 90, 0.8), ("✨", 940, 700, 80, 1.0)],
    "loop": [("🔄", 130, 1190, 90, "p1")],
    "stack": [("🧱", 130, 1230, 80, "p1")],
    "chat": [("💬", 940, 1220, 90, "p1")],
    "checklist": [("📋", 940, 1230, 90, "p1")],
    "hub": [("🔌", 130, 1220, 90, "p1")],
}
DEFAULT_FX = {
    "steps": [{"type": "punch", "at": 0.35}],
    "compare": [{"type": "punch", "at": 0.3}],
    "bigword": [{"type": "punch", "at": 0.25}, {"type": "sparkle", "at": 0.9, "x": 540, "y": 700}],
    "loop": [{"type": "sparkle", "at": 3.0, "x": 540, "y": 760}],
    "stack": [{"type": "punch", "at": 0.35}],
    "chat": [],
    "checklist": [{"type": "sparkle", "at": 3.0, "x": 540, "y": 800}],
    "hub": [{"type": "sparkle", "at": 3.0, "x": 540, "y": 770}],
}
CARD_VISUALS = {"card", "steps", "compare", "bigword", "loop", "stack", "chat", "checklist", "hub"}
