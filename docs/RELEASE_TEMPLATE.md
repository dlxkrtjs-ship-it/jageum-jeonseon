## 어떤 파일을 받나요?

| 내 컴퓨터 | 받을 파일 | 실행 방법 |
|---|---|---|
| 🪟 **Windows** | [**JageumJeonseon-Windows.exe**](https://github.com/dlxkrtjs-ship-it/jageum-jeonseon/releases/download/__VER__/JageumJeonseon-Windows.exe) | 더블클릭 → 파란 경고창이 뜨면 「추가 정보」 → 「실행」 |
| 🍎 **Mac** (권장) | 터미널에 한 줄 붙여넣기 ↓ | 다음부터는 바탕화면 「자금전선 실행」 더블클릭 |
| 🍎 Mac (M 칩) zip | [JageumJeonseon-Mac-AppleSilicon.zip](https://github.com/dlxkrtjs-ship-it/jageum-jeonseon/releases/download/__VER__/JageumJeonseon-Mac-AppleSilicon.zip) | 경고가 뜨면 아래 참고 |
| 🍎 Mac (인텔) zip | [JageumJeonseon-Mac-Intel.zip](https://github.com/dlxkrtjs-ship-it/jageum-jeonseon/releases/download/__VER__/JageumJeonseon-Mac-Intel.zip) | 경고가 뜨면 아래 참고 |
| 🐧 Linux | [JageumJeonseon-Linux](https://github.com/dlxkrtjs-ship-it/jageum-jeonseon/releases/download/__VER__/JageumJeonseon-Linux) | `chmod +x JageumJeonseon-Linux && ./JageumJeonseon-Linux` |

### 🍎 Mac 한 줄 설치 (권장)
터미널(Spotlight에서 "터미널")을 열고 붙여넣기 → 엔터:
```bash
curl -fsSL https://raw.githubusercontent.com/dlxkrtjs-ship-it/jageum-jeonseon/main/install.sh | bash
```

**Mac 칩 확인:** 화면 왼쪽 위 사과(🍎) 메뉴 → 「이 Mac에 관하여」 → 칩이 "Apple M…"이면 M 칩, "Intel"이면 인텔.

**zip으로 받았는데 「악성 코드가 없음을 확인할 수 없습니다」 경고가 뜨면:** 「완료」(휴지통 말고) → 시스템 설정 → 개인정보 보호 및 보안 → 아래쪽 「그래도 열기」. 또는 위의 한 줄 설치를 쓰세요.

### 실행하면
1. 검은 창(터미널)이 뜨고 브라우저가 자동으로 열립니다. **쓰는 동안 검은 창은 닫지 마세요.**
2. 오른쪽 「계좌 연결」에서 데모로 먼저 둘러보거나, 증권사(키움·토스·한국투자)와 API 키를 넣고 「저장하고 연결 시험」.
3. 자세한 설명: [README](https://github.com/dlxkrtjs-ship-it/jageum-jeonseon#readme)

> API 키는 내 PC에만 저장되고 증권사 말고는 어디에도 보내지 않습니다. 이 앱은 잔고 조회만 하며 주문하지 않습니다.

---
