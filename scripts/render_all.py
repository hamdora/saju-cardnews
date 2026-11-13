"""발행 전(published.json 없는) 게시물을 모두 렌더링한다.
사용: python3 scripts/render_all.py
"""
import glob, json, os, sys, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'cardgen'))
from render_cards import main as render  # noqa: E402

MAX_SLIDES = 10  # 인스타 API 캐러셀 최대 장수

errors = 0
for cfg in sorted(glob.glob(os.path.join(ROOT, 'posts', '*', 'content.json'))):
    post = os.path.dirname(cfg)
    slug = os.path.basename(post)
    if os.path.exists(os.path.join(post, 'published.json')):
        continue
    data = json.load(open(cfg, encoding='utf-8'))
    n = len(data['slides'])
    if not 2 <= n <= MAX_SLIDES:
        print(f'::error::{slug}: 슬라이드는 2~{MAX_SLIDES}장이어야 합니다 (현재 {n}장)')
        errors += 1
        continue
    if len(data.get('caption', '')) > 2200:
        print(f'::error::{slug}: 캡션은 2,200자 이하여야 합니다')
        errors += 1
        continue
    out = os.path.join(post, 'rendered')
    shutil.rmtree(out, ignore_errors=True)
    render(cfg, out, 'jpg')
    print(f'rendered {slug}: {n} slides')

sys.exit(1 if errors else 0)
