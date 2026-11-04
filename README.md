# 자금전선 작전상황실

내 주식 계좌를 삼국지풍 전장으로 보여주는 앱입니다. 종목 하나가 전장 하나이고, 수익이 나면 적성으로 진격하고 손실이 나면 아군 성이 위급해집니다.

- **입체 전장 / 수묵 전장도:** 성, 창병·기병·궁병 진형, 장수, 날씨(전체 형세), 함락 연출
- **판정:** 종목별 전세(대승~위급), 목표 비중 대비 배치 판정, 손절가·목표가 경보
- **장수 열전:** 관직(전과에 따라 오르내림), 전공 추이, 월간 결산, 무장 대결
- **군 재편성:** 목표 비중대로 다시 나누려면 몇 주를 사고팔아야 하는지 계산하고, 군령장(매도 → 매수 순서)으로 정리
- **출정 일지:** 진격·후퇴·승진·함락이 자동으로 기록됨
- **연병(모의전):** 가상 자금으로 24개월 투자 전쟁

> 이 앱은 **잔고 조회만** 합니다. 주문 기능은 없습니다. 판정과 계산은 단순한 규칙이며 투자 조언이 아닙니다.

## 어떻게 동작하나요

```
[내 PC]  실행 파일(로컬 서버, 127.0.0.1)  ──API 키──▶  증권사 Open API
              │  잔고(종목·수량·평단·현재가·예수금)
              ▼
         브라우저 화면 (게임)
```

- 실행 파일을 켜면 내 컴퓨터 안에서만 접속되는 작은 서버가 뜨고 브라우저가 자동으로 열립니다.
- 증권사 API 키는 **내 PC의 설정 파일**(`홈 폴더/.jageum-jeonseon/config.json`, 본인만 읽기 가능)에만 저장됩니다. 증권사 서버 말고 어디에도 보내지 않습니다.
- 실행할 때마다 새 접속 토큰을 만들어서, 실행기가 띄운 주소로 연 화면만 API를 쓸 수 있습니다. 다른 웹사이트가 내 PC의 실행기를 몰래 호출하는 것을 막습니다.
- 출정 기록(일지·전공 추이 등)도 같은 폴더의 `state.json`에 저장됩니다.

## 지원 증권사

| 증권사 | 필요한 것 | 비고 |
|---|---|---|
| 키움증권 | REST API App Key, Secret Key | 실전/모의투자 키가 따로 있음 |
| 토스증권 | Open API Client ID, Client Secret | **허용 IP 등록 필수**. 미국 주식은 환율로 원화 환산 |
| 한국투자증권 | KIS App Key, App Secret, 계좌번호 | 모의투자 계좌 지원 |
| 데모 | 없음 | 가상 잔고로 체험 |

### 키 발급 방법

**키움증권**
1. [키움 REST API 포털](https://openapi.kiwoom.com)에 로그인
2. API 사용 신청 → App Key와 Secret Key 발급 (실전/모의 각각)
3. 포털에서 접속 IP 등록을 요구하면 이 PC의 공인 IP를 등록

**토스증권**
1. 토스증권 PC 웹(WTS) → 설정 → Open API
2. Client ID와 Client Secret 발급
3. 허용 IP에 이 PC의 공인 IP 등록 (등록하지 않으면 403 오류)
4. 계좌가 여러 개면 「계좌 번호표(accountSeq)」를 넣고, 비워 두면 첫 계좌를 씁니다

**한국투자증권**
1. [KIS Developers](https://apiportal.koreainvestment.com)에서 App Key/App Secret 발급
2. 계좌번호는 `12345678-01` 형식

## 설치와 실행

### 실행 파일 (권장)
1. 이 저장소의 **Releases**에서 내 운영체제용 파일을 받습니다.
   - Windows: `jageum-jeonseon-windows.exe`
   - macOS: `jageum-jeonseon-macos`
   - Linux: `jageum-jeonseon-linux`
2. 실행하면 브라우저가 열립니다. 오른쪽 「계좌 연결」 패널에서 증권사와 키를 넣고 **저장하고 연결 시험** → **지금 동기화**.
3. 「자동」에서 1·5·15분마다 자동 동기화를 켤 수 있습니다.

처음 실행할 때 경고가 나올 수 있습니다. 코드 서명이 없는 실행 파일이라서 그렇습니다.
- **Windows:** "Windows의 PC 보호" → 추가 정보 → 실행
- **macOS:** 파일 우클릭 → 열기, 또는 터미널에서 `chmod +x jageum-jeonseon-macos && xattr -d com.apple.quarantine jageum-jeonseon-macos`

### 파이썬으로 직접 실행
파이썬 3.9 이상이면 추가 설치 없이 됩니다.
```bash
python3 server/warroom.py
```
옵션: `--port 8787`, `--no-browser`, `--print-balance kiwoom` (서버 없이 잔고 JSON만 출력)

### 웹 체험판
GitHub Pages에 올라간 체험판은 계좌 연결 없이 예시 데이터·붙여넣기·모의전만 됩니다. 계좌 연결은 실행 파일에서만 됩니다(브라우저만으로는 API 키를 안전하게 숨길 수 없기 때문).

## 개발

```bash
python3 tests/test_brokers.py   # 가짜 증권사 서버로 키움·토스 응답 변환 시험
```
- `server/warroom.py` — 로컬 서버와 증권사 연동 (표준 라이브러리만 사용)
- `app/index.html` — 게임 화면 (단일 파일)
- `.github/workflows/release.yml` — `v*` 태그를 올리면 Windows/macOS/Linux 실행 파일을 빌드해 Releases에 올림
- `.github/workflows/pages.yml` — `app/`을 GitHub Pages 체험판으로 배포

새 버전 배포:
```bash
git tag v0.1.0 && git push origin v0.1.0
```

## 주의

- API 키는 계좌 조회 권한이 있는 비밀번호와 같습니다. 남에게 보여주거나 저장소에 올리지 마세요.
- 증권사 API 이용약관과 호출 한도를 지켜 주세요. 자동 동기화는 최소 1분 간격입니다.
- 이 앱이 보여주는 판정·계산은 투자 조언이 아니며, 실제 투자 판단과 주문은 본인 책임입니다.
