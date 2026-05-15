# GeekMagic SmallTV-Ultra HTTP API Protocol

- **Model**: SmallTV-Ultra
- **Firmware**: Ultra-V9.0.41
- **Base URL**: `http://10.10.10.4`
- **인증**: 없음 (인증 불필요)

## 공통 규칙

- 모든 읽기 API: `GET` + JSON 응답
- 모든 쓰기 API: `GET` + query string 파라미터, 성공 시 응답 본문 `OK`
- 파일 업로드만 `POST` + `multipart/form-data`
- 파일 목록 API(`/filelist`): HTML `<table>` 응답

---

## 테마 번호

| 번호 | 테마 이름 |
|------|-----------|
| 0 | Weather Clock Today (시간 + 오늘 날씨) |
| 1 | Weather Forecast (날씨 예보) |
| 2 | Photo Album (이미지/GIF 슬라이드쇼) |
| 3 | Time Style 1 |
| 4 | Time Style 2 |
| 5 | Time Style 3 |
| 6 | Simple Weather Clock (시간 + 간단 날씨) |

---

## 읽기 API (GET → JSON)

### 기기 정보

```
GET /v.json
```
```json
{"m": "SmallTV-Ultra", "v": "Ultra-V9.0.41"}
```

### 현재 활성 테마

```
GET /app.json
```
```json
{"theme": 6}
```
- `theme`: 0~6, 현재 표시 중인 테마 번호

### 자동 테마 전환 설정

```
GET /theme_list.json
```
```json
{"list": "0,0,1,0,0,1,0", "sw_en": "1", "sw_i": "10"}
```
- `list`: 7개 테마 각각의 활성 여부 (`1`=포함, `0`=제외), 쉼표 구분
- `sw_en`: 자동 전환 활성화 (`"1"`=켜짐, `"0"`=꺼짐)
- `sw_i`: 전환 간격 (초)

### 야간 모드 / 밝기 설정

```
GET /timebrt.json
```
```json
{"en": 1, "t1": 22, "t2": 7, "b2": 20}
```
- `en`: 야간 모드 활성화 (`1`=켜짐)
- `t1`: 야간 모드 시작 시각 (0~23, 시 단위)
- `t2`: 야간 모드 종료 시각 (0~23, 시 단위)
- `b2`: 야간 밝기 (0~100)

### 시간 표시 형식

```
GET /hour12.json
```
```json
{"h": 1}
```
- `h`: `1`=12시간제, `0`=24시간제

### 스토리지 용량

```
GET /space.json
```
```json
{"total": 3121152, "free": 327180}
```
- 단위: bytes

### 이미지 자동 표시 설정

```
GET /album.json
```
```json
{"autoplay": 0, "i_i": 5}
```
- `autoplay`: `1`=자동 표시 켜짐, `0`=꺼짐
- `i_i`: 이미지 전환 간격 (초)

### 날씨 도시 설정

```
GET /city.json
```
```json
{"ct": "Namyangju", "t": "9", "mt": "0", "cd": "Namyangju", "loc": "Namyangju,KR"}
```
- `ct`: 도시명
- `t`: 날씨 업데이트 간격 (분)
- `cd`: 도시 코드 / 검색어
- `loc`: `도시,국가코드` 형식

### Wi-Fi 설정 조회

```
GET /config.json
```
```json
{"a": "AP404", "p": "****"}
```
- `a`: 연결된 SSID
- `p`: 비밀번호 (마스킹됨)

### Wi-Fi 네트워크 스캔

```
GET /wifi.json?q=1
```
```json
{
  "aps": [
    {"c": "6", "ss": "MyWiFi", "e": 1, "r": 68},
    {"c": "10", "ss": "OtherNet", "e": 1, "r": 33}
  ]
}
```
- `ss`: SSID
- `r`: 신호 강도 (%)
- `e`: 암호화 여부 (`1`=있음)
- `c`: 채널 번호

---

## 파일 관리 API

### 이미지 목록 조회

```
GET /filelist?dir=/image/
```

HTML `<table>` 응답. 각 행에 파일명, 크기(KB), Delete 버튼, Set 버튼 포함.

```
GET /filelist?dir=/gif
```

날씨 테마용 GIF 목록 조회.

### 파일 업로드

```
POST /doUpload?dir=/image/
Content-Type: multipart/form-data

[파일 바이너리]
```
- 지원 형식: JPG, GIF
- GIF는 240×240px으로 리사이즈 후 업로드 권장
- `dir` 파라미터: `/image/` (이미지 앨범용) 또는 `/gif` (날씨 테마용)

```bash
curl -X POST "http://10.10.10.4/doUpload?dir=/image/" \
  -F "file=@my_animation.gif"
```

### 파일 삭제

```
GET /delete?file=<경로>
```

```bash
curl "http://10.10.10.4/delete?file=/image/my_animation.gif"
```

### 전체 파일 삭제

```
GET /set?clear=image   # /image/ 디렉토리 전체 삭제
GET /set?clear=gif     # /gif 디렉토리 전체 삭제
```

---

## 쓰기 API (GET → `OK`)

### 테마 변경

```
GET /set?theme=<0-6>
```

```bash
curl "http://10.10.10.4/set?theme=2"   # Photo Album으로 전환
```

### 자동 테마 전환 설정

```
GET /set?theme_list=<csv>&sw_en=<0|1>&theme_interval=<초>
```

- `theme_list`: 7자리 쉼표 구분 값 (`0` 또는 `1`), 인덱스 = 테마 번호
- `sw_en`: `1`=켜짐, `0`=꺼짐
- `theme_interval`: 전환 간격 (초)

```bash
# Photo Album(2)과 Time Style 1(3) 번갈아 표시, 30초 간격
curl "http://10.10.10.4/set?theme_list=0,0,1,1,0,0,0&sw_en=1&theme_interval=30"
```

### 표시할 이미지 지정 (Photo Album 테마)

```
GET /set?img=<경로>
```

```bash
curl "http://10.10.10.4/set?img=/image/my_animation.gif"
```

### 표시할 GIF 지정 (날씨 테마용)

```
GET /set?gif=<경로>
```

```bash
curl "http://10.10.10.4/set?gif=/gif/rainbow.gif"
```

### 이미지 자동 표시 설정

```
GET /set?i_i=<초>&autoplay=<0|1>
```

```bash
curl "http://10.10.10.4/set?i_i=10&autoplay=1"   # 10초 간격 자동 표시 켜기
curl "http://10.10.10.4/set?i_i=5&autoplay=0"    # 자동 표시 끄기
```

### 밝기 / 야간 모드

```
GET /set?brt=<0-100>
```

```
GET /set?t1=<시작시각>&t2=<종료시각>&b1=<낮밝기>&b2=<밤밝기>&en=<0|1>
```

```bash
curl "http://10.10.10.4/set?t1=22&t2=7&b1=80&b2=20&en=1"
```

### 날씨 설정

```
GET /set?cd1=<도시명>        # 날씨 도시 변경
GET /set?key=<API키>         # OpenWeatherMap API 키
GET /set?fkey=<API키>        # 날씨 예보 API 키
GET /set?w_u=<단위>          # 온도 단위 (metric / imperial)
GET /set?w_i=<분>            # 날씨 업데이트 간격 (분)
```

### 시간 설정

```
GET /set?hour=<0|1>          # 0=24시간제, 1=12시간제
GET /set?ntp=<서버주소>      # NTP 서버
GET /set?time_interval=<초>  # 시간 동기화 간격
GET /set?day=<형식>          # 날짜 표시 형식
GET /set?hc=<색상>           # 시 색상 (hex)
GET /set?font=<폰트명>       # 폰트
GET /set?colon=<0|1>         # 점멸 콜론
GET /set?dst=<0|1>           # 일광절약시간
```

### Wi-Fi 설정

```
GET /wifisave?s=<SSID>&p=<비밀번호>
GET /set?delay=<밀리초>      # Wi-Fi 연결 대기 시간
```

### 시스템

```
GET /set?reset=1    # 공장 초기화 (업로드 파일 유지)
GET /set?reboot=1   # 재부팅
POST /update        # 펌웨어 업데이트 (multipart/form-data)
```

---

## 시나리오별 사용법

### 1. 시간과 특정 이미지를 번갈아 표시

Time Style과 Photo Album 테마를 자동 전환하고, 표시할 이미지를 지정한다.

```bash
# 1) Photo Album(2)과 Time Style 1(3)을 30초 간격으로 번갈아 표시
curl "http://10.10.10.4/set?theme_list=0,0,1,1,0,0,0&sw_en=1&theme_interval=30"

# 2) Photo Album에서 표시할 이미지 지정
curl "http://10.10.10.4/set?img=/image/my_animation.gif"
```

### 2. 저장된 이미지 목록 확인

```bash
curl "http://10.10.10.4/filelist?dir=/image/"
```

응답은 HTML 테이블. 각 행에 `#`, 파일명(링크), 크기(KB), Delete, Set 버튼 포함.

### 3. 이미지 저장 가능 용량 확인

```bash
curl "http://10.10.10.4/space.json"
# {"total":3121152,"free":327180}
```

- `free / 1024` = 가용 KB
- `(free / total) * 100` = 가용률 %

### 4. GIF 이미지 업로드

GIF는 반드시 **240×240px**으로 리사이즈 후 업로드.

```bash
curl -X POST "http://10.10.10.4/doUpload?dir=/image/" \
  -F "file=@/path/to/my_animation.gif"
```

업로드 후 목록 확인:
```bash
curl "http://10.10.10.4/filelist?dir=/image/"
```

### 5. 이미지 1개만 표시 (GIF 단독 모드)

```bash
# 1) Photo Album 테마 활성화
curl "http://10.10.10.4/set?theme=2"

# 2) 자동 표시(슬라이드쇼) 끄기
curl "http://10.10.10.4/set?i_i=5&autoplay=0"

# 3) 표시할 이미지 지정
curl "http://10.10.10.4/set?img=/image/my_animation.gif"
```

### 6. 시간 + 날씨 표시 모드

**Simple Weather Clock** (시계 + 현재 날씨 정보):
```bash
curl "http://10.10.10.4/set?theme=6"
```

**Weather Clock Today** (시계 + 오늘 날씨 상세):
```bash
curl "http://10.10.10.4/set?theme=0"
```

**Weather Forecast** (날씨 예보 중심):
```bash
curl "http://10.10.10.4/set?theme=1"
```

날씨 도시 변경이 필요한 경우:
```bash
curl "http://10.10.10.4/set?cd1=Seoul"
```
