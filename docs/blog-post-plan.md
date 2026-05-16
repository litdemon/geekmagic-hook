# 블로그 포스팅 계획 — Claude Code × GeekMagic SmallTV-Ultra

> **타깃 독자**: Claude Code를 개발 도구로 쓰는 개발자, 픽셀 디스플레이 / 소형 기기 덕후  
> **예상 분량**: 2,000 ~ 2,500 자 (한국어 기준), 사진 6 ~ 8 장  
> **톤**: 문제 해결 실화 + 가볍게 읽히는 기술 블로그

---

## 제목 후보

- **"책상 위 시계가 Claude의 두뇌 상태를 알려준다 — GeekMagic × Claude Code 훅 연동기"**
- "자리 비운 사이 Claude가 멈춰있었다 — 픽셀 디스플레이로 해결한 이야기"
- "SmallTV-Ultra를 시계 대신 Claude Code 상태판으로 쓰기"

---

## 섹션 구성

---

### 1. 도입 — "또 멈춰 있었다"

**핵심 메시지**: 공감을 사는 문제 제시  
**분량**: 200 자

- Claude Code로 긴 작업을 돌려놓고 자리를 비우거나 다른 창에서 작업한다
- 돌아와 보면 퍼미션 요청 대화상자에서 멈춰 있는 일이 반복된다
- 결과물이 나왔는지 아닌지 알 수가 없어 자꾸 터미널 창을 확인하게 된다
- "알림이라도 있으면 좋겠다" 라는 생각

📷 **사진 ① — 스크린샷 필요**
> 터미널 창에 Claude Code가 퍼미션 요청으로 멈춰 있는 화면 스크린샷  
> (텍스트: "Do you want to proceed?" 혹은 tool 허용 요청 다이얼로그가 보이는 상태)

---

### 2. 아이디어의 씨앗 — "시계로만 쓰던 그 녀석"

**핵심 메시지**: 우연한 발견이 해결책이 됨  
**분량**: 200 자

- 책상 한쪽에 GeekMagic SmallTV-Ultra가 놓여 있다 — 그냥 시계로만 쓰고 있었다
- "이 디스플레이에 Claude 상태를 띄울 수 있지 않을까?"
- 240×240 픽셀, GIF 재생 가능, 와이파이로 HTTP API 지원

📷 **사진 ② ✅ 확보**
> 모니터 하단에 SmallTV-Ultra가 날씨 시계(남양주, 4:15, 27°C)를 표시 중  
> 위로 Claude Code 터미널(`accept edits on`)이 살짝 보임  
> → **"항상 시계로만 쓰고 있었다"** 는 문맥에 딱 맞는 구도

---

### 3. GeekMagic API 파헤치기

**핵심 메시지**: 기기 분석 과정, 의외로 단순한 HTTP API  
**분량**: 350 자

- 공식 앱 트래픽을 캡처해 HTTP API를 역엔지니어링
- 핵심 엔드포인트만 3개면 충분함을 발견
  ```
  GET /set?theme=3           → Photo Album 모드 전환
  GET /set?img=/image//x.gif → GIF 표시
  POST /doUpload?dir=/image/ → GIF 업로드
  ```
- 인증 없음, 로컬 와이파이만 있으면 됨
- 1.5초 타임아웃으로 충분히 반응

📷 **사진 ③ — 스크린샷 필요**
> `curl` 명령어로 GeekMagic API를 호출하는 터미널 화면  
> 예: `curl "http://10.10.10.4/set?img=/image//working.gif"` → `OK` 응답

---

### 4. Claude Code 훅 발견

**핵심 메시지**: Claude Code 훅 시스템이 딱 맞는 연결점  
**분량**: 350 자

- Claude Code에 훅(Hook) 시스템이 있음을 문서에서 발견
- `~/.claude/settings.json`에 명령어를 등록하면 각 상태 변화마다 자동 실행
- 6가지 이벤트를 발견하고 각 이벤트가 무엇을 의미하는지 정리

| 이벤트 | 발생 시점 |
|--------|----------|
| UserPromptSubmit | 사용자가 프롬프트를 입력했을 때 |
| PreToolUse | Claude가 도구를 호출하기 직전 |
| PostToolUse | 도구 호출이 끝났을 때 |
| Notification | 알림 발생 시 (레이트 리밋 등) |
| SubagentStop | 서브에이전트 완료 시 |
| Stop | 응답 완료, 다음 입력 대기 |

- "이걸 GeekMagic API와 연결하면 되겠다"

📷 **사진 ④ — 스크린샷 필요**
> `~/.claude/settings.json` 훅 등록 부분을 보여주는 코드 에디터 화면  
> (혹은 터미널에서 `cat ~/.claude/settings.json | jq .hooks` 출력)

---

### 5. GIF 제작

**핵심 메시지**: 상태마다 다른 시각적 표현을 만드는 과정  
**분량**: 250 자

- 7가지 상태에 맞는 GIF 애니메이션을 제작
- 240×240 픽셀, 8fps, 64색으로 최적화 (장치 메모리 제한)
- `.mov` 소스로 촬영 후 직접 만든 컨버터 스크립트로 변환

| 상태 | GIF | 의미 |
|------|-----|------|
| starting | starting.gif | 세션 시작 |
| prompt_received | prompt_received.gif | 프롬프트 수신 |
| calling_tools | calling_tools.gif | 도구 호출 중 |
| working | working.gif | 처리 중 |
| permission | permission.gif | 사용자 승인 필요 |
| rate_limited | rate_limited.gif | API 한도 초과 |
| idle | waiting.gif | 완료, 대기 중 |

📷 **사진 ⑤ ✅ 확보**
> 7가지 상태별 GIF가 재생 중인 SmallTV-Ultra 디스플레이 콜라주  
> 로봇 캐릭터가 각 상태별로 다른 포즈를 취하고 있음:
> - 좌상(大): 터미널 앞에서 작업 중 (`calling_tools` 또는 `working`)
> - 우상: 앞에서 대기하는 자세 (`starting` 또는 `prompt_received`)
> - 우중: 서류/문서를 들고 있는 모습 (`working`)
> - 하단 4컷: 정면 대기 / 퍼미션 요청(Allow·Deny 버튼) / 노트북 작업 / 코드 확인

---

### 6. 개발 — 훅과 API를 연결하다

**핵심 메시지**: 구현의 핵심 아이디어와 설계 결정  
**분량**: 350 자

- Python stdlib만으로 구현 (의존성 없음 — 훅이 항상 실행될 수 있어야 함)
- 1.5초 HTTP 타임아웃: 네트워크 이슈가 있어도 Claude Code를 절대 차단하지 않음
- 상태 중복 호출 방지: `~/.geekmagic_hook/state.json`으로 동일 상태 재전송 스킵
- `pip install -e .` 한 줄로 설치, `geekmagic_hook setup`으로 자동 설정

```
Claude Code → 훅 이벤트 → geekmagic_hook → HTTP GET → GeekMagic 디스플레이
```

- 최종 아키텍처: 9개 모듈로 역할 분리 (OOP)
  - `device.py` — GeekMagic HTTP API 클라이언트
  - `display.py` — 상태 → GIF 매핑
  - `hook_manager.py` — 훅 등록 관리
  - 외 6개

---

### 7. 결과 — 이제 자리를 비워도 된다

**핵심 메시지**: 실제 사용 후기와 효과  
**분량**: 250 자

- Claude가 퍼미션을 요청하면 `permission.gif` 표시 → 즉시 알 수 있다
- 작업이 완료되면 `waiting.gif` → 돌아와도 되는 신호
- 레이트 리밋이 걸리면 `rate_limited.gif` → 커피 한 잔 마시고 오면 됨
- 로봇 캐릭터가 상태에 따라 다른 표정과 포즈를 취하는 것이 직관적

📷 **사진 ⑥ ✅ 확보 — 블로그 대표 이미지**
> 모니터에 Claude Code 한국어 작업 화면(`이전 리뷰 항목`, `billing_status`, `Brewed for 10m 58s`)이 보이고,  
> 그 아래 SmallTV-Ultra에 `calling_tools.gif` (로봇이 터미널 앞에 앉아 작업 중)가 표시됨  
> → **Claude가 실제로 일하는 동안 디스플레이도 함께 반응한다**는 것을 한 장으로 전달

📷 **사진 ⑦ — 스크린샷 필요 (선택)**
> `geekmagic_hook setup` 실행 화면 — 자동 감지, GIF 업로드, 훅 등록 과정이  
> 터미널에 출력되는 스크린샷

---

### 8. 마무리 — 오픈소스로 공개

**핵심 메시지**: 재현 가능하도록 공개, 독자 행동 유도  
**분량**: 150 자

- GitHub에 오픈소스 공개 (MIT)
- `pipx install git+https://github.com/litdemon/geekmagic-hook`
- GeekMagic SmallTV-Ultra가 있다면 5분 안에 설정 완료
- 커스텀 GIF 테마도 직접 만들어 올릴 수 있음
- "다음엔 다른 디스플레이 기기도 지원해보고 싶다"로 마무리

---

## 사진 촬영 체크리스트

| # | 장면 | 상태 |
|---|------|------|
| ① | Claude Code 퍼미션 요청 멈춤 화면 (스크린샷) | ⬜ 필요 |
| ② | SmallTV-Ultra 날씨 시계 모드 실물 | ✅ 확보 |
| ③ | curl API 호출 터미널 화면 (스크린샷) | ⬜ 선택 |
| ④ | settings.json 훅 등록 코드 화면 (스크린샷) | ⬜ 선택 |
| ⑤ | 7가지 GIF 재생 중인 디스플레이 콜라주 | ✅ 확보 |
| ⑥ | 모니터 + SmallTV-Ultra 함께 찍은 메인 사진 | ✅ 확보 |
| ⑦ | setup 명령 터미널 실행 화면 (스크린샷) | ⬜ 선택 |

> **실물 사진 3장(②⑤⑥) 확보 완료** — 스크린샷(①③④⑦)은 포스팅 작성 시 캡처 가능  
> 초안 작성을 시작할 수 있는 상태입니다.

---

## 게시 플랫폼 후보

| 플랫폼 | 특징 |
|--------|------|
| **Velog** | 한국 개발자 커뮤니티, 마크다운 지원 |
| **Medium** | 영문 버전 작성 시 글로벌 노출 |
| **개인 블로그** | 자유도 높음, SEO 직접 관리 |
| **LinkedIn** | 개발자 네트워크에 공유 |

---

*이 계획서는 `/docs/blog-post-plan.md`에 저장됩니다.*
