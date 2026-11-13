"""연결 점검: 게시 없이 계정 정보와 게시 한도만 조회한다."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import publish as P

ig = os.environ['IG_USER_ID']
print('API host:', P.HOST, P.VER)
try:
    me = P.api('GET', ig, fields='username,name,media_count')
    print('계정 확인:', me.get('username'), '| 게시물 수:', me.get('media_count'))
    lim = P.api('GET', f'{ig}/content_publishing_limit', fields='config,quota_usage')
    print('게시 한도:', lim)
except Exception as e:
    print('::error::', e)
    sys.exit(1)
print('연결 정상')
