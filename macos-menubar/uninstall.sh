#!/bin/bash
PLIST="$HOME/Library/LaunchAgents/com.marat.myip.plist"
launchctl unload "$PLIST" 2>/dev/null; rm -f "$PLIST"
pkill -f my_ip_menubar.py 2>/dev/null
echo "✓ «Мой IP» удалён из автозапуска и остановлен."
