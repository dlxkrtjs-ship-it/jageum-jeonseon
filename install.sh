#!/bin/bash
# 자금전선 작전상황실 설치·실행 (Mac / Linux)
#
#   curl -fsSL https://raw.githubusercontent.com/dlxkrtjs-ship-it/jageum-jeonseon/main/install.sh | bash
#
# 하는 일
#  1. 내 컴퓨터(Mac M 칩 / Mac 인텔 / Linux)에 맞는 최신 실행 파일을 GitHub Releases에서 받습니다.
#  2. 홈 폴더의 JageumJeonseon 폴더에 넣고, Mac이면 바탕화면에 「자금전선 실행」 아이콘을 만듭니다.
#  3. 바로 실행합니다. (다음부터는 바탕화면 아이콘을 더블클릭)
#
# 터미널로 받은 파일은 macOS가 "인터넷에서 받은 파일"로 표시하지 않아 '악성 코드 확인 불가' 경고 없이 열립니다.
set -euo pipefail

REPO="dlxkrtjs-ship-it/jageum-jeonseon"
DIR="$HOME/JageumJeonseon"
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS-$ARCH" in
  Darwin-arm64)  ASSET="JageumJeonseon-Mac-AppleSilicon.zip"; KIND="Mac (M 칩)" ;;
  Darwin-x86_64) ASSET="JageumJeonseon-Mac-Intel.zip";        KIND="Mac (인텔)" ;;
  Linux-x86_64)  ASSET="JageumJeonseon-Linux";                KIND="Linux" ;;
  *) echo "지원하지 않는 환경입니다: $OS $ARCH"; exit 1 ;;
esac

URL="https://github.com/$REPO/releases/latest/download/$ASSET"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "자금전선 작전상황실 — $KIND 용 최신 버전을 받습니다."
curl -fL --progress-bar -o "$TMP/$ASSET" "$URL"

mkdir -p "$DIR"
if [ "$OS" = "Darwin" ]; then
  ditto -x -k "$TMP/$ASSET" "$TMP/x"
  BIN="$(find "$TMP/x" -type f -name jageum-jeonseon | head -n 1)"
  [ -n "$BIN" ] || { echo "압축 파일에서 실행 파일을 찾지 못했습니다."; exit 1; }
  cp "$BIN" "$DIR/jageum-jeonseon"
else
  cp "$TMP/$ASSET" "$DIR/jageum-jeonseon"
fi
chmod +x "$DIR/jageum-jeonseon"
xattr -dr com.apple.quarantine "$DIR" 2>/dev/null || true

if [ "$OS" = "Darwin" ]; then
  LAUNCH="$HOME/Desktop/자금전선 실행.command"
  cat > "$LAUNCH" <<EOF
#!/bin/bash
# 자금전선 작전상황실 — 더블클릭하면 실행됩니다. 이 창을 닫으면 꺼집니다.
"$DIR/jageum-jeonseon"
EOF
  chmod +x "$LAUNCH"
  echo "설치 완료: $DIR"
  echo "다음부터는 바탕화면의 「자금전선 실행」을 더블클릭하세요."
else
  echo "설치 완료: $DIR/jageum-jeonseon"
fi

if [ "${JJ_NO_RUN:-}" = "1" ]; then exit 0; fi
echo "지금 실행합니다. 브라우저가 열리면 오른쪽 「계좌 연결」에서 시작하세요. 이 창을 닫으면 꺼집니다."
exec "$DIR/jageum-jeonseon"
