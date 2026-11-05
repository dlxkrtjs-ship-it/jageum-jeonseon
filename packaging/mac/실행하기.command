#!/bin/bash
# 자금전선 작전상황실 실행기 (Mac) — 이 파일을 더블클릭하면 실행됩니다.
cd "$(dirname "$0")" || exit 1
xattr -dr com.apple.quarantine . 2>/dev/null
chmod +x ./jageum-jeonseon
echo "자금전선 작전상황실을 켭니다. 이 창을 닫으면 꺼집니다."
./jageum-jeonseon
