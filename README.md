# 사주 카드뉴스 자동 발행

`posts/<slug>/content.json` 원고를 push하면 GitHub Actions가 카드를 렌더링하고,
승인된 게시물을 인스타그램에 캐러셀로 발행합니다.

## 흐름

```
원고 작성(Claude) → push (status: draft)
   → Actions: posts/<slug>/rendered/*.jpg 렌더 & 커밋  ← 여기서 미리보기 확인
   → status: approved 로 바꿔 push
   → Actions: 인스타 발행 → posts/<slug>/published.json 기록
```

- `publish_at`에 `"2026-11-14T19:00"`(한국 시간)처럼 적으면 그 시각 이후 매시 7분 점검 때 발행됩니다.
- `published.json`이 있는 게시물은 다시 발행되지 않습니다.
- 캐러셀은 2~10장, 캡션은 2,200자 이하여야 합니다(API 제한).

## content.json 필드

| 필드 | 설명 |
|---|---|
| `status` | `draft`(렌더만) / `approved`(발행) |
| `publish_at` | 예약 시각(선택). 비우면 승인 즉시 발행 |
| `caption` | 인스타 캡션 + 해시태그 |
| `saju` | 명식(pillars, tengods, five, daeun) |
| `slides` | `cover` / `body` / `chart` / `daeun` / `closing` / `outro` |

본문에서 `**강조**`는 빨간색으로 표시됩니다. 사진은 `photos/`에 넣고 `photo`, `crop`으로 지정합니다.

## 최초 설정

1. **인스타 계정**: 설정 → 계정 유형에서 *프로페셔널(비즈니스 또는 크리에이터)*로 전환
2. **Meta 앱**: developers.facebook.com → 앱 만들기 → Instagram API 사용 사례 선택
   → *Instagram 로그인을 통한 API 설정* → 내 인스타 계정 추가 → 액세스 토큰 생성
   (권한: `instagram_business_basic`, `instagram_business_content_publish`)
   - 개발 모드 앱이라도 본인 계정(테스터로 추가된 계정)에는 발행할 수 있습니다.
   - 토큰 화면에 표시되는 인스타 사용자 ID도 함께 복사합니다.
3. **GitHub Secrets** (저장소 Settings → Secrets and variables → Actions)
   - `IG_USER_ID`: 인스타 사용자 ID
   - `IG_ACCESS_TOKEN`: 장기 액세스 토큰(60일)
   - `GH_PAT`(선택): 토큰 자동 갱신용. Fine-grained 토큰, 이 저장소만, *Secrets: Read and write*
4. Actions 탭 → *카드뉴스 렌더 & 인스타 발행* → Run workflow → `dry_run` 체크로 점검

Secrets가 비어 있으면 발행 단계는 자동으로 dry-run(계획만 출력)으로 동작합니다.

## 주의

- 인스타 API는 공개 URL의 JPEG만 가져가므로 이 저장소는 **public**이어야 합니다.
  토큰은 Secrets에만 두고 절대 파일에 적지 마세요.
- 사진은 사용 권리가 있는 것만 올리세요. 저장소가 공개이므로 사진도 공개됩니다.
- 폰트: Paperlogy (SIL Open Font License, `fonts/OFL.txt`).
