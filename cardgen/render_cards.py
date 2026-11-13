"""사주 카드뉴스 렌더러: content.json -> 1080x1080 PNG 세트.
사용: python3 render_cards.py content.json outdir
"""
import json, re, sys, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, '..', 'fonts')
ASSET = os.path.join(HERE, '..', 'assets')
HANJA_FONT = os.environ.get('HANJA_FONT', '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc')
HANJA_IDX = 1  # KR face inside the ttc (fallback-safe for hanja)

W = H = 1080
RED = (240, 72, 56)  # 도장 심볼과 어울리는 주홍
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
ELEM = {  # 오행 색
    '木': ((46, 158, 91), WHITE), '火': ((251, 84, 89), WHITE),
    '土': ((224, 169, 59), (20, 20, 20)), '金': ((225, 225, 225), (20, 20, 20)),
    '水': ((47, 95, 214), WHITE),
}
GAN_EL = dict(zip('甲乙丙丁戊己庚辛壬癸', '木木火火土土金金水水'))
ZHI_EL = dict(zip('子丑寅卯辰巳午未申酉戌亥', '水土木木土火火土金金土水'))


def F(weight, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, f'Paperlogy-{weight}.ttf'), size)


def HJ(size):
    try:
        return ImageFont.truetype(HANJA_FONT, size, index=HANJA_IDX)
    except Exception:
        return ImageFont.truetype(HANJA_FONT, size)


def font_for(ch, base_font, size):
    # Paperlogy에 한자가 없으면 세리프 한자 폰트로 대체
    if '一' <= ch <= '鿿':
        return HJ(int(size * 0.95))
    return base_font


# ---------- rich text (**강조**) ----------
def parse_rich(text):
    out = []
    for i, part in enumerate(re.split(r'\*\*', text)):
        for ch in part:
            out.append((ch, i % 2 == 1))
    return out


def wrap_rich(chars, font, size, max_w, tracking=0):
    lines, cur, cur_w, last_space = [], [], 0, -1
    for item in chars:
        ch = item[0]
        if ch == '\n':
            lines.append(cur); cur, cur_w, last_space = [], 0, -1; continue
        f = font_for(ch, font, size)
        w = f.getlength(ch) + tracking
        if cur_w + w > max_w and cur:
            if ch == ' ':
                lines.append(cur); cur, cur_w, last_space = [], 0, -1; continue
            if last_space > 0:
                lines.append(cur[:last_space]); cur = cur[last_space + 1:]
            else:
                lines.append(cur); cur = []
            cur_w = sum(font_for(c[0], font, size).getlength(c[0]) + tracking for c in cur)
            last_space = max((i for i, c in enumerate(cur) if c[0] == ' '), default=-1)
        if ch == ' ':
            last_space = len(cur)
        cur.append(item); cur_w += w
    if cur:
        lines.append(cur)
    return lines


def line_width(line, font, size, tracking=0):
    return sum(font_for(c[0], font, size).getlength(c[0]) + tracking for c in line)


def draw_rich(d, x, y, line, font, size, base=WHITE, hi=RED, tracking=0, anchor='ls', shadow=True):
    for ch, emph in line:
        f = font_for(ch, font, size)
        if shadow:
            d.text((x + 2, y + 2), ch, font=f, fill=(0, 0, 0), anchor=anchor)
        d.text((x, y), ch, font=f, fill=hi if emph else base, anchor=anchor)
        x += f.getlength(ch) + tracking


# ---------- backgrounds ----------
def hanja_bg(chars, seed=0, glow=RED, photo=None, crop=None, fit=None):
    if photo and os.path.exists(photo) and fit == 'top':
        # 가로 사진을 자르지 않고 위쪽에 통째로 배치, 아래는 검정으로 페이드
        ph = Image.open(photo).convert('RGB')
        if crop:
            ph = ph.crop(tuple(crop))
        ph = ph.resize((W, round(ph.height * W / ph.width)), Image.LANCZOS)
        bg = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        fade = Image.new('L', (1, ph.height))
        for y in range(ph.height):
            fade.putpixel((0, y), 255 if y < ph.height * 0.7 else int(255 * (1 - (y - ph.height * 0.7) / (ph.height * 0.3))))
        ph = ph.convert('RGBA'); ph.putalpha(fade.resize((W, ph.height)))
        bg.alpha_composite(ph, (0, 0))
        return bg
    if photo and os.path.exists(photo):
        im = Image.open(photo).convert('RGB')
        if crop:
            im = im.crop(tuple(crop))
        s = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1))
        l, t = (im.width - W) // 2, max(0, (im.height - H) // 3)
        return im.crop((l, t, l + W, t + H)).convert('RGBA')
    rnd = random.Random(seed)
    bg = Image.new('RGBA', (W, H), (12, 12, 12, 255))
    # 붉은 은은한 광원
    glow_l = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_l)
    cx, cy = rnd.randint(300, 780), rnd.randint(180, 380)
    gd.ellipse((cx - 420, cy - 320, cx + 420, cy + 320), fill=glow + (45,))
    bg.alpha_composite(glow_l.filter(ImageFilter.GaussianBlur(160)))
    # 큰 한자
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    n = len(chars)
    size = 620 if n == 1 else 470
    f = HJ(size)
    total = size * n * 0.92
    x0 = (W - total) / 2 + size * 0.46
    for i, ch in enumerate(chars):
        ld.text((x0 + i * size * 0.92, 330), ch, font=f, fill=(255, 255, 255, 26), anchor='mm')
    bg.alpha_composite(layer)
    # 결 노이즈
    import numpy as np  # 시드 고정 노이즈: 매번 같은 이미지가 나오도록
    arr = np.random.RandomState(seed).normal(128, 28, (H, W)).clip(0, 255).astype('uint8')
    noise = Image.fromarray(arr, 'L')
    nl = Image.new('RGBA', (W, H), (255, 255, 255, 0)); nl.putalpha(noise.point(lambda v: int(v * 0.06)))
    bg.alpha_composite(nl)
    return bg


def bottom_gradient(im, start=410, full=820, base_dark=0):
    g = Image.new('L', (1, H), 0)
    for y in range(H):
        a = 0 if y < start else min(255, int(255 * ((y - start) / (full - start)) ** 1.15))
        g.putpixel((0, y), a)
    g = g.resize((W, H))
    black = Image.new('RGBA', (W, H), (0, 0, 0, 255)); black.putalpha(g)
    if base_dark:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, base_dark)))
    im.alpha_composite(black)


def logo(im, x, y, center=False):
    lg = Image.open(os.path.join(ASSET, 'logo.png'))
    if center:
        x = (W - lg.width) // 2
    im.alpha_composite(lg, (int(x), int(y)))
    return lg.height


def brand_top(im, h=44, y=30):
    """모든 카드 공통: 상단 중앙 고정 로고 (본문 레이아웃과 분리)"""
    shade = Image.new('L', (1, 150))
    for i in range(150):
        shade.putpixel((0, i), int(150 * (1 - i / 150) ** 1.6))
    top = Image.new('RGBA', (W, 150), (0, 0, 0, 255)); top.putalpha(shade.resize((W, 150)))
    im.alpha_composite(top, (0, 0))
    lg = Image.open(os.path.join(ASSET, 'logo.png')).convert('RGBA')
    lg = lg.resize((round(lg.width * h / lg.height), h), Image.LANCZOS)
    im.alpha_composite(lg, ((W - lg.width) // 2, y))


def handle(d, text='@pigbosal_saju'):
    d.text((W / 2, 1059), text, font=F('3Light', 28), fill=GRAY, anchor='ms')


# ---------- slide types ----------
def slide_cover(s, c):
    im = hanja_bg(s.get('bg_hanja', ''), 1, photo=s.get('photo'), crop=s.get('crop'), fit=s.get('fit'))
    g0, g1 = s.get('grad', [330, 680])
    bottom_gradient(im, g0, g1, base_dark=s.get('dark', 40))
    d = ImageDraw.Draw(im)
    f = F('9Black', 74)
    lines = s['title']  # list of rich strings
    y_end = 960
    lh = 92
    y = y_end - lh * (len(lines) - 1)
    pass  # 로고는 brand_top()에서 상단 중앙 고정
    for ln in lines:
        draw_rich(d, 55, y, parse_rich(ln), f, 74, base=WHITE, hi=RED)
        y += lh
    if s.get('kicker'):
        d.text((57, y - lh + 50), s['kicker'], font=F('4Regular', 28), fill=GRAY, anchor='ls')
    handle(d)
    return im


def slide_body(s, c, idx):
    im = hanja_bg(s.get('bg_hanja', ''), idx, photo=s.get('photo'), crop=s.get('crop'), fit=s.get('fit'))
    g0, g1 = s.get('grad', [200, 520])
    bottom_gradient(im, g0, g1, base_dark=s.get('dark', 60))
    d = ImageDraw.Draw(im)
    size, lh = 36, 52
    f = F('5Medium', size)
    lines = []
    for para in s['body']:
        lines += wrap_rich(parse_rich(para), f, size, W - 57 * 2)
        lines.append(None)  # 문단 간격
    lines = lines[:-1]
    text_h = sum(lh if l else 18 for l in lines)
    y = 1005 - text_h
    if s.get('heading'):
        y -= 64
        hy = y
    y_logo = (hy - 22) if s.get('heading') else (y - 20)
    pass  # 로고는 brand_top()에서 상단 중앙 고정
    if s.get('heading'):
        draw_rich(d, 55, hy + 30, parse_rich(s['heading']), F('9Black', 44), 44, base=RED, hi=WHITE)
        y = hy + 64
    y += 34
    for ln in lines:
        if ln is None:
            y += 18; continue
        draw_rich(d, 57, y, ln, f, size, tracking=-0.5)
        y += lh
    handle(d)
    return im


def pillar_box(im, d, x, y, sz, ch, el):
    if ch == '?':
        d.rounded_rectangle((x, y, x + sz, y + sz), 14, outline=(110, 110, 110), width=3)
        d.text((x + sz / 2, y + sz / 2), '?', font=F('9Black', int(sz * 0.55)), fill=(140, 140, 140), anchor='mm')
        return
    bgc, fg = ELEM[el]
    d.rounded_rectangle((x, y, x + sz, y + sz), 14, fill=bgc)
    d.text((x + sz / 2, y + sz / 2 + 4), ch, font=HJ(int(sz * 0.62)), fill=fg, anchor='mm')
    d.text((x + sz - 12, y + sz - 10), el, font=HJ(22), fill=fg + (200,) if len(fg) == 3 else fg, anchor='rs')


def slide_chart(s, c, idx):
    im = Image.new('RGBA', (W, H), (12, 12, 12, 255))
    d = ImageDraw.Draw(im)
    pass  # 로고는 brand_top()에서 상단 중앙 고정
    d.text((57, 170), s['title'], font=F('9Black', 52), fill=WHITE, anchor='ls')
    d.text((57, 218), s['sub'], font=F('4Regular', 27), fill=GRAY, anchor='ls')
    cols = ['시주', '일주', '월주', '년주']
    p = c['pillars']  # hour, day, month, year  e.g. "??", "辛卯"
    sz, gap = 190, 28
    x0 = (W - (sz * 4 + gap * 3)) / 2
    y_head, y_g, y_z = 290, 330, 330 + sz + 20
    for i, name in enumerate(cols):
        x = x0 + i * (sz + gap)
        d.text((x + sz / 2, y_head), name + (' (나)' if i == 1 else ''), font=F('7Bold', 28),
               fill=RED if i == 1 else WHITE, anchor='ms')
        g, z = p[i][0], p[i][1]
        pillar_box(im, d, x, y_g, sz, g, GAN_EL.get(g))
        pillar_box(im, d, x, y_z, sz, z, ZHI_EL.get(z))
        tg, tz = c['tengods'][i]
        d.text((x + sz / 2, y_g - 0 - 8 + 0), '', font=F('4Regular', 1))
        d.text((x + sz / 2, y_z + sz + 36), tz, font=F('5Medium', 26), fill=GRAY, anchor='ms')
        # 천간 십신은 박스 위 머리글 아래 작은 라벨
        if tg:
            d.text((x + 14, y_g + 32), tg, font=F('5Medium', 22),
                   fill=(20, 20, 20) if GAN_EL.get(g) in ('土', '金') else WHITE, anchor='ls')
    # 오행 분포
    y = 860
    d.text((57, y), '오행 분포', font=F('7Bold', 28), fill=WHITE, anchor='ls')
    counts = c['five']
    bx = 230
    for el in '木火土金水':
        n = counts.get(el, 0)
        bgc, fg = ELEM[el]
        d.rounded_rectangle((bx, y - 30, bx + 140, y + 10), 10, fill=bgc if n else (40, 40, 40))
        d.text((bx + 70, y - 2), f'{el} {n}', font=HJ(28) if False else F('7Bold', 26),
               fill=(fg if n else (120, 120, 120)), anchor='ms')
        bx += 160
    # 한자 오행 글자는 Paperlogy에 없으므로 덮어쓰기
    bx = 230
    for el in '木火土金水':
        n = counts.get(el, 0); bgc, fg = ELEM[el]
        d.rounded_rectangle((bx, y - 30, bx + 140, y + 10), 10, fill=bgc if n else (40, 40, 40))
        col = fg if n else (120, 120, 120)
        d.text((bx + 52, y - 10), el, font=HJ(28), fill=col, anchor='mm')
        d.text((bx + 92, y - 10), str(n), font=F('9Black', 28), fill=col, anchor='mm')
        bx += 160
    d.text((57, 940), s['note'], font=F('4Regular', 27), fill=GRAY, anchor='ls')
    handle(d)
    return im


def slide_daeun(s, c, idx):
    im = Image.new('RGBA', (W, H), (12, 12, 12, 255))
    d = ImageDraw.Draw(im)
    pass  # 로고는 brand_top()에서 상단 중앙 고정
    draw_rich(d, 55, 170, parse_rich(s['heading']), F('9Black', 50), 50, base=RED, hi=WHITE)
    du = c['daeun']  # [[age, '癸丑'], ...]
    n = len(du); bw, gap = 112, 10
    x0 = (W - (bw * n + gap * (n - 1))) / 2
    hl = set(s.get('highlight', []))
    nxt = s.get('next', -1)
    for i, (age, gz) in enumerate(du):
        x = x0 + i * (bw + gap); y = 260
        d.text((x + bw / 2, y), f'{age}세', font=F('6SemiBold', 24),
               fill=RED if age == nxt else (WHITE if age in hl else GRAY), anchor='ms')
        for j, ch in enumerate(gz):
            el = (GAN_EL if j == 0 else ZHI_EL)[ch]
            bgc, fg = ELEM[el]
            yy = y + 18 + j * (bw + 8)
            dim = age not in hl and age != nxt
            fill = tuple(int(v * 0.35 + 12 * 0.65) for v in bgc) if dim else bgc
            d.rounded_rectangle((x, yy, x + bw, yy + bw), 10, fill=fill)
            d.text((x + bw / 2, yy + bw / 2 + 3), ch, font=HJ(66),
                   fill=(fg if not dim else (150, 150, 150)), anchor='mm')
        if age in hl or age == nxt:
            col = WHITE if age in hl else RED
            d.rounded_rectangle((x - 5, y + 13, x + bw + 5, y + 18 + bw * 2 + 8 + 5), 14, outline=col, width=4)
    # 라벨
    hl_idx = [i for i, (a, _) in enumerate(du) if a in hl]
    if hl_idx:
        xa = x0 + hl_idx[0] * (bw + gap); xb = x0 + hl_idx[-1] * (bw + gap) + bw
        d.text(((xa + xb) / 2, 560), s['hl_label'], font=F('7Bold', 28), fill=WHITE, anchor='ms')
    ni = [i for i, (a, _) in enumerate(du) if a == nxt]
    if ni:
        xn = x0 + ni[0] * (bw + gap) + bw / 2
        d.text((xn, 560), s['next_label'], font=F('7Bold', 28), fill=RED, anchor='ms')
    # 본문
    size, lh = 35, 51
    f = F('5Medium', size)
    y = 680
    for para in s['body']:
        for ln in wrap_rich(parse_rich(para), f, size, W - 57 * 2):
            draw_rich(d, 57, y, ln, f, size, tracking=-0.5); y += lh
        y += 18
    handle(d)
    return im


def slide_closing(s, c, idx):
    im = hanja_bg(s.get('bg_hanja', ''), idx, photo=s.get('photo'), crop=s.get('crop'), fit=s.get('fit'))
    im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, 185)))
    d = ImageDraw.Draw(im)
    d.text((W / 2, 400), s['question'], font=F('5Medium', 46), fill=WHITE, anchor='ms')
    y = 700
    for ln in s['answer']:
        d.text((W / 2, y), ln, font=F('7Bold', 40), fill=RED, anchor='ms'); y += 60
    pass  # 로고는 brand_top()에서 상단 중앙 고정
    if s.get('disclaimer'):
        d.text((W / 2, 1000), s['disclaimer'], font=F('3Light', 22), fill=(130, 130, 130), anchor='ms')
    handle(d)
    return im


def slide_outro(s, c, idx):
    return Image.open(os.path.join(ASSET, 'outro.png')).convert('RGBA')


def main(cfg_path, outdir, fmt='jpg'):
    cfg = json.load(open(cfg_path, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(cfg_path))
    os.makedirs(outdir, exist_ok=True)
    fn = {'cover': lambda s, c, i: slide_cover(s, c), 'body': slide_body, 'chart': slide_chart,
          'daeun': slide_daeun, 'closing': slide_closing, 'outro': slide_outro}
    paths = []
    for i, s in enumerate(cfg['slides'], 1):
        if s.get('photo') and not os.path.isabs(s['photo']):
            s = dict(s, photo=os.path.join(base, s['photo']))
        im = fn[s['type']](s, s.get('saju', cfg.get('saju')), i).convert('RGBA')
        if s['type'] != 'outro':
            brand_top(im)
        im = im.convert('RGB')
        p = os.path.join(outdir, f"{i:02d}.{fmt}")
        if fmt == 'jpg':
            im.save(p, 'JPEG', quality=92, optimize=True)  # 인스타 API는 JPEG만 허용
        else:
            im.save(p)
        paths.append(p)
        print('saved', p)
    return paths


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], *(sys.argv[3:4]))
