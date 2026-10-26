# Мой IP

Набор виджетов, которые показывают ваш внешний IP-адрес и страну, сами проверяют его раз в минуту и сразу сообщают, когда IP меняется. Удобно, если вы часто переключаете VPN.

*English summary below.*

## Что внутри

| Папка | Что это | Где работает |
| --- | --- | --- |
| `macos-menubar/` | Флаг, код страны и IP в строке меню | macOS |
| `browser-extension/` | Расширение с кодом страны на значке | Chrome, Яндекс Браузер, Edge |
| `claude-mod/` | Строка с IP над полем ввода в Claude Code | Claude Code |
| `tray/` | Значок в трее | Windows, Linux |
| `my-ip.html` | Страница: просто открыть в браузере | Любой браузер |

## macOS: строка меню

- флаг, код страны и IP в строке меню, проверка раз в минуту и по `⌘R`;
- история последних IP, клик копирует адрес;
- **флаг на весь экран при смене IP**: на 0,5 / 1 / 2 / 3 секунды или пока не тронешь мышь или клавиатуру;
- **свой звук для каждой страны**: США, Китай, Казахстан, Великобритания, Россия, Германия, Нидерланды, Гонконг, Сингапур и отдельно для остальных.

Установка (нужен Python 3; если его нет, скрипт предложит поставить инструменты Apple):

```bash
git clone https://github.com/alimbekmarat/my-ip.git ~/my-ip
bash ~/my-ip/macos-menubar/install.sh
```

Скрипт сам включает автозапуск при входе в систему. Удаление: `bash ~/my-ip/macos-menubar/uninstall.sh`.

> Если вместо флага видите `IP ⚠︎` и стоит Python с python.org, выполните `"/Applications/Python 3.x/Install Certificates.command"`.

## Расширение для браузера

1. Откройте `chrome://extensions` (в Яндексе `browser://extensions`).
2. Включите «Режим разработчика».
3. Нажмите «Загрузить распакованное» и выберите папку `browser-extension`.

На значке показан код страны: зелёный для России, синий для остальных стран. По клику открывается полный IP, город, провайдер и история.

## Claude Code

Мод показывает строку `IP: … · город [Обновить]` над полем ввода и добавляет команду `/ip`.

```bash
claude --plugin-dir ~/my-ip/claude-mod
```

Чтобы мод загружался всегда, в том числе в приложении Claude, добавьте путь к папке в `~/.claude/settings.json`:

```json
{ "env": { "CLAUDE_CODE_PLUGIN_DIRS": "/Users/<ваше-имя>/my-ip/claude-mod" } }
```

## Windows / Linux: трей

```bash
pip install -r tray/requirements.txt
python tray/my_ip_tray.py
```

На Windows можно просто запустить `tray/run_windows.bat`.

## Откуда берётся IP

Запросы идут по очереди к публичным сервисам [ipwho.is](https://ipwho.is), [ipapi.co](https://ipapi.co) и [ipify](https://www.ipify.org). Если один не ответил, используется следующий. Никакие данные никуда больше не отправляются.

---

## English

**My IP** shows your public IP address and country and checks it every minute. It alerts you when the IP changes, which is handy if you switch VPNs often.

- **macOS menu bar app**: flag, country code and IP; IP history; a full-screen flag on IP change (0.5–3 s or until you touch the mouse or keyboard); a custom sound per country.
- **Browser extension** (Chromium): country code on the toolbar badge.
- **Claude Code mod**: an IP line above the prompt plus a `/ip` command.
- **Tray app** for Windows and Linux, and a standalone HTML page.

Install the macOS app with `bash macos-menubar/install.sh`. MIT licensed.
