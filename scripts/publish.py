"""승인된 게시물을 인스타그램에 캐러셀로 발행한다 (Instagram API with Instagram Login).

환경변수
  IG_USER_ID        인스타 프로페셔널 계정 ID
  IG_ACCESS_TOKEN   장기 액세스 토큰
  GITHUB_REPOSITORY owner/repo (Actions가 자동 설정)
  RAW_REF           렌더 이미지가 들어 있는 커밋 SHA
  DRY_RUN=1         실제 호출 없이 계획만 출력
게시 조건: content.json 의 status == "approved", published.json 없음,
          publish_at 이 비어 있거나 현재 시각 이전.
"""
import datetime as dt
import glob, json, os, sys, time
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = os.environ.get('IG_API_HOST', 'https://graph.instagram.com')
VER = os.environ.get('IG_API_VERSION', 'v26.0')
DRY = os.environ.get('DRY_RUN') == '1'
KST = dt.timezone(dt.timedelta(hours=9))


def api(method, path, **params):
    url = f'{HOST}/{VER}/{path}'
    params['access_token'] = os.environ['IG_ACCESS_TOKEN']
    r = requests.request(method, url, params=params, timeout=60)
    try:
        body = r.json()
    except ValueError:
        body = {'raw': r.text}
    if r.status_code >= 400 or 'error' in body:
        raise RuntimeError(f'{method} {path} 실패: {body}')
    return body


def wait_ready(container_id, tries=30):
    for _ in range(tries):
        st = api('GET', container_id, fields='status_code,status').get('status_code')
        if st == 'FINISHED':
            return
        if st in ('ERROR', 'EXPIRED'):
            raise RuntimeError(f'컨테이너 {container_id} 상태 {st}')
        time.sleep(5)
    raise RuntimeError(f'컨테이너 {container_id} 준비 시간 초과')


def due(data, now):
    if data.get('status') != 'approved':
        return False
    when = data.get('publish_at')
    if not when:
        return True
    t = dt.datetime.fromisoformat(when)
    if t.tzinfo is None:
        t = t.replace(tzinfo=KST)  # 시간대 없으면 한국 시간으로 해석
    return t <= now


def publish_post(post, data):
    slug = os.path.basename(post)
    repo, ref = os.environ['GITHUB_REPOSITORY'], os.environ['RAW_REF']
    imgs = sorted(glob.glob(os.path.join(post, 'rendered', '*.jpg')))
    if len(imgs) != len(data['slides']):
        raise RuntimeError(f'{slug}: 렌더 이미지 수({len(imgs)})와 슬라이드 수가 다릅니다')
    urls = [f'https://raw.githubusercontent.com/{repo}/{ref}/posts/{slug}/rendered/{os.path.basename(p)}'
            for p in imgs]
    print(f'[{slug}] {len(urls)}장 발행 시작')
    if DRY:
        for u in urls:
            print('  DRY', u)
        print('  DRY caption:', data.get('caption', '')[:80].replace('\n', ' '), '...')
        return None
    for u in urls:  # 인스타가 가져갈 수 있는 공개 URL인지 먼저 확인
        h = requests.head(u, timeout=30, allow_redirects=True)
        if h.status_code != 200:
            raise RuntimeError(f'이미지 URL 접근 불가({h.status_code}): {u}')
    ig = os.environ['IG_USER_ID']
    children = []
    for u in urls:
        cid = api('POST', f'{ig}/media', image_url=u, is_carousel_item='true')['id']
        wait_ready(cid)
        children.append(cid)
    carousel = api('POST', f'{ig}/media', media_type='CAROUSEL',
                   children=','.join(children), caption=data.get('caption', ''))['id']
    wait_ready(carousel)
    media_id = api('POST', f'{ig}/media_publish', creation_id=carousel)['id']
    info = api('GET', media_id, fields='permalink,timestamp')
    result = {'media_id': media_id, 'permalink': info.get('permalink'),
              'published_at': dt.datetime.now(KST).isoformat(), 'image_ref': ref}
    json.dump(result, open(os.path.join(post, 'published.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f'[{slug}] 발행 완료: {result["permalink"]}')
    return result


def main():
    now = dt.datetime.now(KST)
    failed = 0
    for cfg in sorted(glob.glob(os.path.join(ROOT, 'posts', '*', 'content.json'))):
        post = os.path.dirname(cfg)
        if os.path.exists(os.path.join(post, 'published.json')):
            continue
        data = json.load(open(cfg, encoding='utf-8'))
        if not due(data, now):
            print(f'[{os.path.basename(post)}] 건너뜀 (status={data.get("status")}, publish_at={data.get("publish_at")})')
            continue
        try:
            publish_post(post, data)
        except Exception as e:  # 한 게시물 실패가 다른 게시물을 막지 않도록
            print(f'::error::{os.path.basename(post)}: {e}')
            failed += 1
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
