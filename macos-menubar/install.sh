#!/bin/bash
# Установка «Мой IP» в строку меню + автозапуск при входе в систему
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.marat.myip.plist"

# Ищем уже установленный Python (Homebrew, python.org), системный /usr/bin/python3 — только если есть инструменты Apple
PY=""
for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3 $(which -a python3 2>/dev/null); do
  [ -x "$c" ] || continue
  if [ "$c" = "/usr/bin/python3" ] && ! xcode-select -p >/dev/null 2>&1; then continue; fi
  if "$c" -c "import venv" >/dev/null 2>&1; then PY="$c"; break; fi
done

if [ -z "$PY" ]; then
  echo "Python не найден. Сейчас откроется установка инструментов разработчика Apple — нажми «Установить», дождись конца и запусти этот скрипт ещё раз."
  xcode-select --install
  exit 1
fi
echo "→ Использую Python: $PY"

echo "→ Готовлю окружение Python…"
"$PY" -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q --upgrade pip
"$DIR/.venv/bin/pip" install -q rumps certifi

echo "→ Настраиваю автозапуск…"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.marat.myip</string>
  <key>ProgramArguments</key><array>
    <string>$DIR/.venv/bin/python</string><string>$DIR/my_ip_menubar.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
</dict></plist>
PL
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "✓ Готово: смотри справа вверху в строке меню."
