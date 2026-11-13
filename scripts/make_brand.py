"""브랜드 에셋 생성: 도장 심볼 → 투명 배경 seal.png, 로고 logo.png, 아웃트로 outro.png"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'assets')
F = lambda w, s: ImageFont.truetype(os.path.join(ROOT, 'fonts', f'Paperlogy-{w}.ttf'), s)
ACCENT = (240, 72, 56)
HANDLE = '@pigbosal_saju'


def seal():
    im = Image.open(os.path.join(A, 'src', 'seal_original.png')).convert('RGBA')
    w, h = im.size
    # 바깥 밝은 배경만 지우기: 모서리에서 flood fill (안쪽 흰 글씨는 붉은 테두리에 막혀 보존)
    mask = Image.new('L', (w + 2, h + 2), 0)
    rgb = im.convert('RGB')
    light = Image.new('L', (w, h))
    light.putdata([255 if (r > 200 and g > 170) else 0 for r, g, b in rgb.getdata()])
    pad = Image.new('L', (w + 2, h + 2), 255); pad.paste(light, (1, 1))
    ImageDraw.floodfill(pad, (0, 0), 128)
    outside = pad.crop((1, 1, w + 1, h + 1)).point(lambda v: 255 if v == 128 else 0)
    outside = outside.filter(ImageFilter.MaxFilter(3))  # 경계 흰 테두리 정리
    alpha = Image.eval(outside, lambda v: 255 - v).filter(ImageFilter.GaussianBlur(0.6))
    im.putalpha(alpha)
    im = im.crop(im.getbbox())
    im.save(os.path.join(A, 'seal.png'))
    return im


def logo(s):
    sz = 58
    sm = s.resize((sz, round(s.height * sz / s.width)), Image.LANCZOS)
    f = F('9Black', 38)
    tw = int(f.getlength('강남돼지보살'))
    lg = Image.new('RGBA', (sz + 14 + tw + 4, sm.height), (0, 0, 0, 0))
    lg.alpha_composite(sm, (0, 0))
    ImageDraw.Draw(lg).text((sz + 14, sm.height / 2 + 2), '강남돼지보살', font=f, fill='white', anchor='lm')
    lg.save(os.path.join(A, 'logo.png'))


def outro(s):
    W = 1080
    im = Image.new('RGBA', (W, W), (12, 12, 12, 255))
    glow = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((190, 60, 890, 700), fill=ACCENT + (55,))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(150)))
    big = s.resize((380, round(s.height * 380 / s.width)), Image.LANCZOS)
    im.alpha_composite(big, ((W - big.width) // 2, 150))
    d = ImageDraw.Draw(im)
    d.text((W / 2, 640), '유명인의 사주,', font=F('9Black', 56), fill='white', anchor='ms')
    d.text((W / 2, 715), '돼지보살이 풀어드립니다', font=F('9Black', 56), fill=ACCENT, anchor='ms')
    # 팔로우 버튼
    bw, bh, by = 520, 92, 790
    d.rounded_rectangle(((W - bw) / 2, by, (W + bw) / 2, by + bh), bh / 2, fill=ACCENT)
    d.text((W / 2, by + bh / 2 + 2), f'{HANDLE}  팔로우', font=F('7Bold', 36), fill='white', anchor='mm')
    d.text((W / 2, 945), '다음 사주풀이를 가장 먼저 받아보세요', font=F('4Regular', 30), fill=(200, 200, 200), anchor='ms')
    d.text((W / 2, 1059), HANDLE, font=F('3Light', 28), fill=(200, 200, 200), anchor='ms')
    im.convert('RGB').save(os.path.join(A, 'outro.png'))


if __name__ == '__main__':
    s = seal(); logo(s); outro(s); print('brand assets ok')
