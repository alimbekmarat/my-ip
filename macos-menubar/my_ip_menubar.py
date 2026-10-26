"""Мой IP в строке меню macOS.

- код страны и IP в строке меню, проверка раз в минуту и по кнопке
- история смен IP
- при смене IP — флаг страны и IP на весь экран (время показа настраивается)
- свой звук для каждой страны
"""
import json
import os
import ssl
import subprocess
import threading
import time
import urllib.request

import rumps
from AppKit import (
    NSApp, NSBackingStoreBuffered, NSColor, NSEvent, NSFont, NSFontWeightBold, NSFontWeightMedium,
    NSMakeRect, NSScreen, NSTextAlignmentCenter, NSTextField, NSView, NSWindow,
    NSWindowCollectionBehaviorCanJoinAllSpaces, NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowStyleMaskBorderless,
)
from PyObjCTools import AppHelper

INTERVAL = 60  # секунд

# Python с python.org на Mac не видит системные сертификаты — берём их из certifi
try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CTX = ssl.create_default_context()

PROVIDERS = [
    ("https://ipwho.is/", lambda d: (d.get("ip"), d.get("country_code"),
        " · ".join(x for x in [d.get("city"), d.get("country"), (d.get("connection") or {}).get("isp")] if x))),
    ("https://ipapi.co/json/", lambda d: (d.get("ip"), d.get("country_code"),
        " · ".join(x for x in [d.get("city"), d.get("country_name"), d.get("org")] if x))),
    ("https://api.ipify.org?format=json", lambda d: (d.get("ip"), None, "")),
]

# Страны со своим звуком (код → название). Всё остальное — «Другие страны».
COUNTRIES = [
    ("US", "США"), ("CN", "Китай"), ("KZ", "Казахстан"), ("GB", "Великобритания"),
    ("RU", "Россия"), ("DE", "Германия"), ("NL", "Нидерланды"), ("HK", "Гонконг"),
    ("SG", "Сингапур"),
]
OTHER = "OTHER"
COUNTRY_NAMES = dict(COUNTRIES, **{
    "FI": "Финляндия", "FR": "Франция", "TR": "Турция", "AE": "ОАЭ", "JP": "Япония", "KR": "Корея",
    "PL": "Польша", "SE": "Швеция", "CH": "Швейцария", "CA": "Канада", "LV": "Латвия", "LT": "Литва",
    "EE": "Эстония", "GE": "Грузия", "AM": "Армения", "BY": "Беларусь", "UA": "Украина", "UZ": "Узбекистан",
    "KG": "Киргизия", "RS": "Сербия", "IT": "Италия", "ES": "Испания", "IN": "Индия", "TH": "Таиланд",
    "VN": "Вьетнам", "IL": "Израиль", "CY": "Кипр", "AT": "Австрия", "CZ": "Чехия", "BG": "Болгария",
})

SYSTEM_SOUNDS = ["Basso", "Blow", "Bottle", "Frog", "Funk", "Glass", "Hero", "Morse",
                 "Ping", "Pop", "Purr", "Sosumi", "Submarine", "Tink"]
NO_SOUND = "Без звука"
DEFAULT_SOUNDS = {"US": "Hero", "CN": "Ping", "KZ": "Submarine", "GB": "Morse", "RU": "Glass",
                  "DE": "Purr", "NL": "Pop", "HK": "Funk", "SG": "Tink", OTHER: "Blow"}

# Время показа полноэкранного флага
OVERLAY_MODES = [("off", "Не показывать"), ("0.5", "0,5 секунды"), ("1", "1 секунда"),
                 ("2", "2 секунды"), ("3", "3 секунды"), ("touch", "Пока не трону мышь или клавиатуру")]

DATA_DIR = os.path.expanduser("~/Library/Application Support/MyIP")
DATA_FILE = os.path.join(DATA_DIR, "history.json")


def load_data():
    try:
        with open(DATA_FILE) as f:
            d = json.load(f)
    except Exception:
        d = {}
    sounds = dict(DEFAULT_SOUNDS)
    sounds.update(d.get("sounds") or {})
    return {
        "history": d.get("history", []),
        "sound": d.get("sound", True),
        "sounds": sounds,
        "overlay": d.get("overlay", "2"),
    }


def save_data(data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        data["history"] = data["history"][:20]
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def flag(cc):
    if not cc or len(cc) != 2:
        return "🌐"
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in cc.upper())


def play(name):
    if name and name != NO_SOUND:
        subprocess.Popen(["afplay", f"/System/Library/Sounds/{name}.aiff"])


def fetch():
    for url, parse in PROVIDERS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "my-ip-menubar"})
            with urllib.request.urlopen(req, timeout=6, context=SSL_CTX) as r:
                ip, cc, geo = parse(json.loads(r.read().decode()))
            if ip:
                return ip, cc, geo
        except Exception:
            continue
    return None, None, ""


# ---------- Полноэкранный флаг ----------

class OverlayWindow(NSWindow):
    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return True


def make_label(text, font, color, y, h, w):
    lbl = NSTextField.labelWithString_(text)
    lbl.setFont_(font)
    lbl.setTextColor_(color)
    lbl.setAlignment_(NSTextAlignmentCenter)
    lbl.setFrame_(NSMakeRect(0, y, w, h))
    return lbl


class Overlay:
    EVENTS_MASK = (1 << 10) | (1 << 12) | (1 << 5) | (1 << 6) | (1 << 7) | (1 << 1) | (1 << 3) | (1 << 22) | (1 << 25)
    # keyDown, flagsChanged, mouseMoved, leftDragged, rightDragged, leftDown, rightDown, scroll, otherDown

    def __init__(self):
        self.windows = []
        self.monitors = []
        self.token = 0

    def show(self, ip, cc, geo, mode):
        self.close()
        self.token += 1
        token = self.token
        code = (cc or "").upper()
        name = COUNTRY_NAMES.get(code, code or "Страна неизвестна")
        hint = "Нажми любую клавишу или пошевели мышью" if mode == "touch" else ""

        for screen in NSScreen.screens():
            fr = screen.frame()
            w, h = fr.size.width, fr.size.height
            win = OverlayWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                fr, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
            win.setLevel_(1000)  # над всеми окнами, включая полноэкранные
            win.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces
                                       | NSWindowCollectionBehaviorFullScreenAuxiliary)
            win.setOpaque_(False)
            win.setBackgroundColor_(NSColor.colorWithCalibratedWhite_alpha_(0.04, 0.9))
            win.setAcceptsMouseMovedEvents_(True)
            win.setReleasedWhenClosed_(False)

            view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
            white = NSColor.whiteColor()
            soft = NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.6)
            view.addSubview_(make_label(flag(cc), NSFont.systemFontOfSize_(h * 0.36), white, h * 0.34, h * 0.52, w))
            view.addSubview_(make_label(name, NSFont.systemFontOfSize_weight_(h * 0.06, NSFontWeightMedium), white, h * 0.25, h * 0.09, w))
            view.addSubview_(make_label(ip, NSFont.monospacedSystemFontOfSize_weight_(h * 0.075, NSFontWeightBold), white, h * 0.14, h * 0.1, w))
            if geo:
                view.addSubview_(make_label(geo, NSFont.systemFontOfSize_(h * 0.025), soft, h * 0.09, h * 0.045, w))
            if hint:
                view.addSubview_(make_label(hint, NSFont.systemFontOfSize_(h * 0.02), soft, h * 0.03, h * 0.04, w))
            win.setContentView_(view)

            win.setAlphaValue_(0.0)
            win.makeKeyAndOrderFront_(None)
            win.animator().setAlphaValue_(1.0)
            self.windows.append(win)

        NSApp.activateIgnoringOtherApps_(True)

        if mode == "touch":
            # небольшая пауза, чтобы случайное дрожание мыши сразу не закрыло флаг
            AppHelper.callLater(0.7, lambda: self._arm(token))
        else:
            AppHelper.callLater(float(mode), lambda: self.close(token))

    def _arm(self, token):
        if token != self.token or not self.windows:
            return

        def local(event):
            AppHelper.callAfter(self.close, token)
            return None  # нажатие не уходит дальше в другие программы

        def glob(event):
            AppHelper.callAfter(self.close, token)

        self.monitors.append(NSEvent.addLocalMonitorForEventsMatchingMask_handler_(self.EVENTS_MASK, local))
        # мышь/трекпад ловим и глобально (не требует особых разрешений)
        m = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(self.EVENTS_MASK, glob)
        if m is not None:
            self.monitors.append(m)

    def close(self, token=None):
        if token is not None and token != self.token:
            return
        for m in self.monitors:
            try:
                NSEvent.removeMonitor_(m)
            except Exception:
                pass
        self.monitors = []
        had = bool(self.windows)
        for w in self.windows:
            w.orderOut_(None)
        self.windows = []
        if had:
            NSApp.hide_(None)  # вернуть фокус программе, в которой работал


# ---------- Приложение в строке меню ----------

class MyIp(rumps.App):
    def __init__(self):
        super().__init__("Мой IP", title="IP…", quit_button=None)
        self.ip, self.cc, self.geo, self.checked, self.error = None, None, "", None, False
        self.show_ip = True
        self.busy = False
        self.data = load_data()
        self.overlay = Overlay()

        self.ip_item = rumps.MenuItem("IP: —", callback=self.copy)
        self.geo_item = rumps.MenuItem("Местоположение: —")
        self.time_item = rumps.MenuItem("Проверено: —")
        self.hist_menu = rumps.MenuItem("История IP")
        self.hist_menu.add(rumps.MenuItem("Пока пусто"))

        # Полноэкранный флаг: время показа
        self.overlay_menu = rumps.MenuItem("Флаг на весь экран при смене IP")
        self.overlay_items = {}
        for key, label in OVERLAY_MODES:
            it = rumps.MenuItem(label, callback=lambda _, k=key: self.set_overlay(k))
            it.state = int(self.data["overlay"] == key)
            self.overlay_items[key] = it
            self.overlay_menu.add(it)
        self.overlay_menu.add(None)
        self.overlay_menu.add(rumps.MenuItem("Показать сейчас (проверка)", callback=self.test_overlay))

        # Звуки по странам
        self.sound_toggle = rumps.MenuItem("Звук при смене страны", callback=self.toggle_sound)
        self.sound_toggle.state = int(self.data["sound"])
        self.sounds_menu = rumps.MenuItem("Звуки стран")
        self.sound_items = {}
        for code, name in COUNTRIES + [(OTHER, "Другие страны")]:
            sub = rumps.MenuItem(f"{flag(code) if code != OTHER else '🌐'} {name}")
            self.sound_items[code] = {}
            for snd in [NO_SOUND] + SYSTEM_SOUNDS:
                it = rumps.MenuItem(snd, callback=lambda _, c=code, s=snd: self.set_sound(c, s))
                it.state = int(self.data["sounds"].get(code) == snd)
                self.sound_items[code][snd] = it
                sub.add(it)
            if code == OTHER:
                self.sounds_menu.add(None)
            self.sounds_menu.add(sub)

        self.toggle_item = rumps.MenuItem("Показывать IP в строке меню", callback=self.toggle)
        self.toggle_item.state = 1

        self.menu = [
            self.ip_item, self.geo_item, self.time_item, None,
            rumps.MenuItem("Обновить сейчас", callback=lambda _: self.check(), key="r"),
            self.hist_menu, None,
            self.overlay_menu, self.sound_toggle, self.sounds_menu, None,
            self.toggle_item, None,
            rumps.MenuItem("Выход", callback=lambda _: rumps.quit_application(), key="q"),
        ]
        self.render_history()
        self.timer = rumps.Timer(lambda _: self.check(), INTERVAL)
        self.timer.start()
        self.check()

    # --- проверка ---
    def check(self):
        if self.busy:
            return
        self.busy = True
        if not self.ip:
            self.title = "IP…"
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        ip, cc, geo = fetch()
        AppHelper.callAfter(self._apply, ip, cc, geo)

    def _apply(self, ip, cc, geo):
        self.busy = False
        self.checked = time.strftime("%H:%M:%S")
        if ip:
            old, old_cc = self.ip, self.cc
            if cc is None and ip == old:
                cc, geo = self.cc, geo or self.geo
            self.ip, self.cc, self.geo, self.error = ip, cc, geo, False

            hist = self.data["history"]
            if not hist or hist[0]["ip"] != ip:
                hist.insert(0, {"ip": ip, "cc": cc, "geo": geo, "t": time.strftime("%d.%m %H:%M")})
                save_data(self.data)

            if old and old != ip:
                if self.data["overlay"] != "off":
                    self.overlay.show(ip, cc, geo, self.data["overlay"])
                try:
                    rumps.notification("IP сменился", f"{old} → {ip}", geo or "")
                except Exception:
                    pass
            if self.data["sound"] and old_cc and cc and old_cc != cc:
                play(self.sound_for(cc))
        else:
            self.error = True
        self.render()

    def sound_for(self, cc):
        code = (cc or "").upper()
        return self.data["sounds"].get(code if code in dict(COUNTRIES) else OTHER)

    # --- отрисовка меню ---
    def render(self):
        if self.error and not self.ip:
            self.title = "IP ⚠︎"
        else:
            mark = f"{flag(self.cc)} {(self.cc or '?').upper()}"
            self.title = f"{mark} {self.ip}" if self.show_ip else mark
            if self.error:
                self.title += " ⚠︎"
        self.ip_item.title = f"IP: {self.ip or '—'}   (нажми, чтобы скопировать)"
        self.geo_item.title = self.geo or "Местоположение неизвестно"
        self.time_item.title = f"Проверено: {self.checked}" + (
            "  — нет ответа, показан прошлый IP" if self.error and self.ip else "")
        self.render_history()

    def render_history(self):
        self.hist_menu.clear()
        hist = self.data["history"]
        if not hist:
            self.hist_menu.add(rumps.MenuItem("Пока пусто"))
            return
        for h in hist[:10]:
            label = f"{flag(h.get('cc'))} {(h.get('cc') or '?').upper()}  {h['ip']}  —  {h['t']}"
            self.hist_menu.add(rumps.MenuItem(label, callback=lambda _, ip=h["ip"]: self.copy_text(ip)))
        self.hist_menu.add(None)
        self.hist_menu.add(rumps.MenuItem("Очистить историю", callback=self.clear_history))

    # --- действия меню ---
    def set_overlay(self, key):
        self.data["overlay"] = key
        for k, it in self.overlay_items.items():
            it.state = int(k == key)
        save_data(self.data)

    def test_overlay(self, _):
        mode = self.data["overlay"] if self.data["overlay"] != "off" else "2"
        self.overlay.show(self.ip or "0.0.0.0", self.cc, self.geo, mode)
        if self.data["sound"]:
            play(self.sound_for(self.cc))

    def set_sound(self, code, snd):
        self.data["sounds"][code] = snd
        for s, it in self.sound_items[code].items():
            it.state = int(s == snd)
        save_data(self.data)
        play(snd)

    def toggle_sound(self, item):
        self.data["sound"] = not self.data["sound"]
        item.state = int(self.data["sound"])
        save_data(self.data)

    def clear_history(self, _):
        self.data["history"] = self.data["history"][:1]
        save_data(self.data)
        self.render_history()

    def toggle(self, item):
        self.show_ip = not self.show_ip
        item.state = int(self.show_ip)
        self.render()

    def copy(self, _):
        if self.ip:
            self.copy_text(self.ip)

    def copy_text(self, text):
        subprocess.run(["pbcopy"], input=text.encode())
        try:
            rumps.notification("Скопировано", text, "")
        except Exception:
            pass


if __name__ == "__main__":
    MyIp().run()
