# 책상 위 시계가 Claude의 두뇌 상태를 알려준다
## — GeekMagic SmallTV-Ultra × Claude Code 훅 연동기

---

## 또 멈춰 있었다

Claude Code로 큰 작업을 돌릴 때 버릇이 하나 생겼다.

작업을 걸어두고 자리를 비운다. 커피를 마시거나, 다른 모니터에서 다른 일을 한다. 그러다 5~10분 뒤 터미널 창을 슬쩍 보면 — **또 멈춰 있다.**

```
Do you want to proceed with this action?
❯ Yes  No
```

Claude가 뭔가를 실행하기 전에 내 승인을 기다리고 있었던 것이다. 언제부터 멈춰 있었는지도 모른다. 1분일 수도 있고, 8분일 수도 있다.

알림이 오는 것도 아니고, 소리가 나는 것도 아니다. 그냥 조용히, 내가 돌아오기를 기다리고 있다.

`geekmagic_hook setup` 실행 중이라면 어떻게 알 수 있을까? 도구를 실행하는 중인지, 완료됐는지, 아니면 내 응답을 기다리는지. 매번 터미널 창으로 시선을 옮기는 게 불편했다.

> *"어디서든 한눈에 보이는 무언가가 있으면 좋겠다."*

`[스크린샷①: Claude Code 퍼미션 요청 화면]`

---

## 시계로만 쓰고 있었다

그때 눈에 들어온 게 책상 한쪽에 놓인 **GeekMagic SmallTV-Ultra**였다.

![SmallTV-Ultra 날씨 시계 모드](/Users/eschu/Desktop/weather_clock.png)

남양주, 27°C, 4:15. 날씨와 시간을 보여주는 작은 정사각형 디스플레이. 한동안 시계로만 써왔는데, 문득 이런 생각이 들었다.

> *"이 화면에 Claude 상태를 띄우면 어떨까?"*

찾아보니 이 기기는 단순한 시계가 아니었다.

- **240×240 픽셀** 컬러 디스플레이
- **GIF 애니메이션** 재생 지원
- **와이파이로 HTTP API** 제공 — 로컬 네트워크에서 간단히 제어 가능

API 명세는 공식 문서가 따로 없어서 앱 트래픽을 캡처해 직접 파악했다. 예상보다 훨씬 단순했다.

```bash
# GIF 표시
curl "http://10.10.10.4/set?img=/image//working.gif"
# → OK

# Photo Album 모드로 전환 (GIF 재생 모드)
curl "http://10.10.10.4/set?theme=3"

# GIF 업로드
curl -F "file=@working.gif" "http://10.10.10.4/doUpload?dir=/image/"
```

인증도 없다. 같은 와이파이에 있으면 누구나 제어할 수 있다. 로컬 네트워크 전용이니 보안 문제는 없지만, 덕분에 연동이 극도로 간단해진다.

---

## Claude Code에도 훅이 있었다

API를 파악했으니, 이제 Claude Code와 연결할 방법을 찾아야 했다.

Claude Code 문서를 뒤지다가 **훅(Hook) 시스템**을 발견했다. `~/.claude/settings.json`에 명령어를 등록해두면, Claude Code가 상태를 바꿀 때마다 그 명령어를 자동으로 실행해준다.

![settings.json 훅 등록 화면](https://cdn-images-1.medium.com/max/1600/1*DshFX0407rbiWQi32_c9NQ.png)

이벤트는 6가지다.

| 이벤트 | 발생 시점 |
|--------|----------|
| `UserPromptSubmit` | 내가 프롬프트를 입력했을 때 |
| `PreToolUse` | Claude가 도구(Bash, Read, Edit…)를 실행하기 직전 |
| `PostToolUse` | 도구 실행이 끝났을 때 |
| `Notification` | 알림 발생 시 (레이트 리밋 등) |
| `SubagentStop` | 서브에이전트 작업 완료 시 |
| `Stop` | 응답 완료, 다음 입력 대기 중 |

이 6가지 이벤트가 GeekMagic API의 6가지 GIF와 자연스럽게 맞아떨어진다는 걸 알았다. 퍼즐 조각이 맞춰지는 느낌이었다.

---

## GIF를 만들었다

연결할 수 있다는 확신이 생기고 나서, 먼저 GIF를 만들었다.

7가지 상태 각각에 맞는 애니메이션이 필요했다. 로봇 캐릭터를 직접 제작하고 상황에 맞는 포즈와 동작을 담았다.

`[사진⑤: 7가지 GIF 콜라주]`

| 상태 | GIF | 표시되는 순간 |
|------|-----|--------------|
| `starting` | starting.gif | 세션 첫 시작 |
| `prompt_received` | prompt_received.gif | 두 번째 이후 프롬프트 |
| `calling_tools` | calling_tools.gif | 도구 실행 중 |
| `working` | working.gif | 결과 처리 중 |
| `permission` | permission.gif | 내 승인 필요 |
| `rate_limited` | rate_limited.gif | API 한도 초과 |
| `idle` | waiting.gif | 완료, 대기 중 |

특히 `permission.gif`에는 Allow / Deny 버튼이 화면에 등장하도록 만들었다. 저 화면이 뜨면 내가 뭔가를 결정해야 한다는 뜻이다.

GIF 크기는 240×240 픽셀, 8fps, 64색으로 제한했다. 기기의 저장 공간이 넉넉하지 않아서 최적화가 필요했다.

---

## 훅과 API를 연결하다

이제 실제로 연결할 차례다.

훅이 실행될 때마다 GeekMagic API를 호출하는 스크립트를 Python으로 작성했다. 설계에서 가장 중요하게 생각한 것 두 가지가 있다.

**첫째, Claude Code를 절대 차단하지 않는다.**

훅은 Claude Code의 흐름에 끼어드는 코드다. 만약 GeekMagic 기기가 꺼져있거나, 와이파이가 끊겼거나, 응답이 느리면 — Claude Code 전체가 멈추면 안 된다. HTTP 타임아웃을 1.5초로 고정하고, 어떤 오류가 나더라도 exit 0으로 종료하도록 했다.

**둘째, 중복 호출을 방지한다.**

`PostToolUse`는 도구를 쓸 때마다 발생한다. 상태가 계속 `working`이라면 굳이 API를 반복 호출할 필요가 없다. 마지막 상태를 파일에 기록해두고, 같은 상태가 연속으로 오면 스킵한다.

```
Claude Code
  → 훅 이벤트
    → geekmagic_hook (Python)
      → 상태 변화 있을 때만
        → HTTP GET /set?img=...
          → SmallTV-Ultra
```

설치와 설정은 두 줄이면 끝난다.

```bash
pipx install git+https://github.com/litdemon/geekmagic-hook
geekmagic_hook setup
```

`setup` 명령 하나가 기기를 자동 감지하고, GIF를 업로드하고, 훅을 등록한다.

![Geekmagic Setup Screenshot](/Users/eschu/Desktop/geekmagic_setup.png)

---

## 이제 자리를 비워도 된다

![스크린샷 2026-05-16 오후 8.34.53](/Users/eschu/Desktop/스크린샷 2026-05-16 오후 8.34.53.png)

이제 Claude Code를 돌려두고 다른 일을 해도, 책상 옆 작은 디스플레이를 흘깃 보는 것만으로 상황을 파악할 수 있다.

- 로봇이 터미널 앞에 앉아 바쁘게 작동 중이면 → Claude가 작업하는 중, 기다리면 된다
- Allow / Deny 버튼이 화면에 등장하면 → 내 결정이 필요하다, 터미널로 가야 한다
- 로봇이 조용히 서서 기다리는 모습이면 → 완료됐다, 다음 작업을 시작하면 된다
- 노란색 로봇이 지친 표정이면 → 레이트 리밋, 잠깐 쉬면 된다

10분짜리 작업을 걸어두고 커피를 마시다가, 디스플레이에 `waiting.gif`가 뜨는 순간 "아, 됐구나" 하고 돌아오게 됐다. 매번 터미널 창을 확인하러 가는 습관이 자연스럽게 사라졌다.

---

## 오픈소스로 공개했다

GeekMagic SmallTV-Ultra가 있다면 누구나 쓸 수 있도록 GitHub에 공개했다.

```bash
pipx install git+https://github.com/litdemon/geekmagic-hook
geekmagic_hook setup
# → Claude Code 재시작하면 바로 동작
```

같은 와이파이에 SmallTV-Ultra가 있으면 기기를 자동으로 찾아주고, 5분이면 설정이 끝난다. GIF 테마도 직접 만들어 올릴 수 있도록 변환 스크립트도 함께 공개했다.

Claude Code가 생각보다 훨씬 많은 것과 연결될 수 있다는 걸 이번 프로젝트로 실감했다. 다음엔 다른 디스플레이 기기나 LED 조명과도 연동해보고 싶다는 생각이 든다.

---

**GitHub**: [github.com/litdemon/geekmagic-hook](https://github.com/litdemon/geekmagic-hook)

*GeekMagic SmallTV-Ultra, Claude Code, Python 3.9+, 같은 Wi-Fi 네트워크 필요*
