"""Мой IP в трее: значок с последним октетом IP, проверка раз в минуту и по клику."""
import json
import threading
import time
import urllib.request

import pystray
from PIL import Image, ImageDraw, ImageFont

INTERVAL = 60  # секунд

PROVIDERS = [
    ("https://ipwho.is/", lambda d: (d.get("ip"), ", ".join(x for x in [d.get("city"), d.get("country")] if x))),
    ("https://ipapi.co/json/", lambda d: (d.get("ip"), ", ".join(x for x in [d.get("city"), d.get("country_name")] if x))),
    ("https://api.ipify.org?format=json", lambda d: (d.get("ip"), "")),
]

state = {"ip": None, "geo": "", "checked": None, "error": None}
lock = threading.Lock()


def fetch_ip():
    for url, parse in PROVIDERS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "my-ip-tray"})
            with urllib.request.urlopen(req, timeout=6) as r:
                ip, geo = parse(json.loads(r.read().decode()))
            if ip:
                return ip, geo
        except Exception:
            continue
    return None, ""


def make_icon(ip, error):
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = (192, 57, 43) if error else (15, 123, 108)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=14, fill=color)
    text = "!" if error else ("v6" if ip and ":" in ip else (ip.split(".")[-1] if ip else "…"))
    font = None
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(name, 34 if len(text) < 3 else 26)
            break
        except OSError:
            pass
    font = font or ImageFont.load_default()
    box = d.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((size - w) / 2 - box[0], (size - h) / 2 - box[1]), text, font=font, fill="white")
    return img


def check(icon):
    with lock:
        ip, geo = fetch_ip()
        old = state["ip"]
        state["checked"] = time.strftime("%H:%M:%S")
        if ip:
            state.update(ip=ip, geo=geo, error=None)
            if old and old != ip:
                try:
                    icon.notify(f"{old} → {ip}", "IP сменился")
                except Exception:
                    pass
        else:
            state["error"] = "нет ответа"
        icon.icon = make_icon(state["ip"], state["error"] and not ip)
        label = state["ip"] or "IP неизвестен"
        icon.title = f"{label}\n{state['geo']}\nпроверено {state['checked']}"[:127]
        icon.update_menu()


def copy_ip(icon, _item):
    if not state["ip"]:
        return
    try:
        import tkinter
        r = tkinter.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(state["ip"])
        r.update()
        r.destroy()
        icon.notify(state["ip"], "Скопировано")
    except Exception:
        pass


def loop(icon):
    icon.visible = True
    while True:
        check(icon)
        time.sleep(INTERVAL)


icon = pystray.Icon(
    "my-ip",
    make_icon(None, False),
    "Мой IP",
    menu=pystray.Menu(
        pystray.MenuItem(lambda _: f"IP: {state['ip'] or '—'} (копировать)", copy_ip, default=True),
        pystray.MenuItem(lambda _: state["geo"] or "местоположение неизвестно", None, enabled=False),
        pystray.MenuItem(lambda _: f"Проверено: {state['checked'] or '—'}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Обновить сейчас", lambda i, _: threading.Thread(target=check, args=(i,), daemon=True).start()),
        pystray.MenuItem("Выход", lambda i, _: i.stop()),
    ),
)

if __name__ == "__main__":
    icon.run(setup=loop)
