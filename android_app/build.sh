#!/usr/bin/env bash
# 重新打包 APK（改完 web/ 后：先同步资源，再编译签名）
# 用法: bash android_app/build.sh
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
T=/root/workspace/phone-apk-toolchain

# 1) 同步 web → assets
rm -rf "$HERE/app/src/main/assets"/* 
cp "$ROOT"/web/index.html "$ROOT"/web/app.js "$ROOT"/web/engine.js "$ROOT"/web/styles.css "$HERE/app/src/main/assets/"
cp -r "$ROOT"/web/vendor "$HERE/app/src/main/assets/vendor"
cp -r "$ROOT"/web/img "$HERE/app/src/main/assets/img"
mkdir -p "$HERE/app/src/main/assets/data"
cp "$ROOT"/web/data/ggen.db "$HERE/app/src/main/assets/data/ggen.db"

# 2) 编译 + 签名 (中间产物导出到临时目录, 不进 Download)
source /etc/profile.d/android-build-env.sh
export APK_EXPORT_DIR=/tmp/ggen_apk_export
rm -rf "$APK_EXPORT_DIR"; mkdir -p "$APK_EXPORT_DIR"
bash $T/build-apk.sh "$HERE" release
bash $T/sign-apk.sh "$HERE/app/build/outputs/apk/release/app-release-unsigned.apk"
OUT="/sdcard/Download/SD高达永恒助手-v0.110.apk"
mv -f "$HERE/app/build/outputs/apk/release/app-release-signed.apk" "$OUT" 2>/dev/null || true
# 3) 清理历史中间产物(只保留最终命名的 APK)
rm -rf "$APK_EXPORT_DIR"
rm -f /sdcard/Download/android_app-release-*.apk /sdcard/Download/app-release-signed.apk 2>/dev/null || true
rm -f /sdcard/Download/永恒助手-*.apk 2>/dev/null || true
echo "==> 完成: $OUT"
