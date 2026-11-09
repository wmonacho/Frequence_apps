import math
def gear_path(cx, cy, r_out, r_root, teeth, tip=0.40, root=0.56):
    pts, step = [], 2*math.pi/teeth
    for i in range(teeth):
        a0 = i*step - math.pi/2
        for a, r in [(a0-step*root/2, r_root), (a0-step*tip/2, r_out), (a0+step*tip/2, r_out), (a0+step*root/2, r_root)]:
            pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
def svg(bg, fg):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 432 432" width="432" height="432"><g id="bg">{bg}</g><g id="fg">{fg}</g></svg>'

def rouille():
    g = gear_path(216, 216, 124, 102, 12)
    bg = '<rect width="432" height="432" fill="#2a211c"/>'
    fg = f'''<path d="{g} M216 146 a70 70 0 1 0 0.1 0 Z" fill-rule="evenodd" fill="#e9783c"/>
<circle cx="216" cy="216" r="88" fill="none" stroke="#c45a24" stroke-width="6"/>
<path d="M196 258 V204 Q196 180 222 176 Q236 174 247 179" fill="none" stroke="#f6e7d8" stroke-width="28" stroke-linecap="round" stroke-linejoin="round"/>'''
    return svg(bg, fg)

def bitabit():
    cx, cy, R, t = 192, 216, 120, 44
    hp = lambda r: [(cx + r*math.cos(math.radians(a)), cy + r*math.sin(math.radians(a))) for a in (-30, 30, 90, 150, 210, 270)]
    o, i = hp(R), hp(R - t)
    L = lambda a, b, k: (a[0] + (b[0]-a[0])*k, a[1] + (b[1]-a[1])*k)
    outer = [L(o[5], o[0], .62), o[5], o[4], o[3], o[2], L(o[2], o[1], .62)]
    inner = [L(i[2], i[1], .5), i[2], i[3], i[4], i[5], L(i[5], i[0], .5)]
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in outer + inner) + " Z"
    def plus(x, y, s):
        w = s*0.34
        return f'<rect x="{x-w/2:.1f}" y="{y-s/2:.1f}" width="{w:.1f}" height="{s}" rx="4" fill="#5fe3c6"/><rect x="{x-s/2:.1f}" y="{y-w/2:.1f}" width="{s}" height="{w:.1f}" rx="4" fill="#5fe3c6"/>'
    bg = '<rect width="432" height="432" fill="#13203b"/>'
    fg = f'<path d="{d}" fill="#2a56b8" transform="translate(0 12)"/><path d="{d}" fill="#5b93f5"/>{plus(302, 216, 44)}{plus(356, 216, 44)}'
    return svg(bg, fg)

def dodiese():
    bg = '<rect width="432" height="432" fill="#271944"/>'
    def sharp(fill, dx=0, dy=0):
        return (f'<g fill="{fill}" transform="translate({dx} {dy})">'
                '<rect x="178" y="104" width="22" height="230" rx="11"/><rect x="234" y="90" width="22" height="230" rx="11"/>'
                '<path d="M128 214 L306 176 Q318 174 318 186 L318 206 Q318 216 306 219 L128 257 Q116 259 116 247 L116 227 Q116 217 128 214 Z"/>'
                '<path d="M128 284 L306 246 Q318 244 318 256 L318 276 Q318 286 306 289 L128 327 Q116 329 116 317 L116 297 Q116 287 128 284 Z"/></g>')
    fg = sharp("#7650d6", 0, 10) + sharp("#c7a6ff") + '<ellipse cx="336" cy="128" rx="16" ry="11.5" transform="rotate(-22 336 128)" fill="#f2c46b"/><path d="M349 124 V70 Q366 76 373 94" stroke="#f2c46b" stroke-width="6" fill="none" stroke-linecap="round"/>'
    return svg(bg, fg)

def miseenprod():
    bg = '<rect width="432" height="432" fill="#0e2a30"/>'
    fg = '''<path d="M146 154 L96 204 L146 254" stroke="#34d399" stroke-width="20" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M286 154 L336 204 L286 254" stroke="#34d399" stroke-width="20" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M200 300 Q216 354 232 300 Z" fill="#f6c453"/>
<path d="M186 262 L160 298 L162 314 L192 294 Z" fill="#1fb88a"/><path d="M246 262 L272 298 L270 314 L240 294 Z" fill="#1fb88a"/>
<path d="M216 88 C250 116 256 162 250 212 L244 296 L188 296 L182 212 C176 162 182 116 216 88 Z" fill="#effcf7"/>
<path d="M216 88 C231 100 241 116 246 134 L186 134 C191 116 201 100 216 88 Z" fill="#34d399"/>
<rect x="195" y="162" width="42" height="48" rx="12" fill="#0e2a30"/>
<path d="M210 176 l-8 10 l8 10 M222 176 l8 10 l-8 10" stroke="#34d399" stroke-width="4.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'''
    return svg(bg, fg)

for n, f in [("rouille", rouille), ("bitabit", bitabit), ("dodiese", dodiese), ("miseenprod", miseenprod)]:
    s = f(); open(f"/home/claude/logos/{n}.svg", "w").write(s)
    a = s.replace('<g id="fg">', '<g id="fg"><g transform="translate(216 216) scale(0.62) translate(-216 -216)">', 1).replace('</g></svg>', '</g></g></svg>')
    open(f"/home/claude/logos/{n}_android.svg", "w").write(a)
