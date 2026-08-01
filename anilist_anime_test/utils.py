import re
import time

from android_utils import run_on_ui_thread
from client_utils import get_last_fragment
from ui.bulletin import BulletinHelper


def gb(plugin, key, default=True):
    val = plugin.get_setting(key, default)
    return bool(val) if val is not None else default


def gi(plugin, key, default=0, mn=0, mx=None):
    try:
        val = int(plugin.get_setting(key, str(default)))
    except Exception:
        val = default
    val = max(mn, val)
    return min(mx, val) if mx is not None else val


def gs(plugin, key, default=""):
    val = plugin.get_setting(key, default)
    return str(val).strip() or default if val is not None else default


def is_cyrillic(text):
    return bool(text) and any("\u0400" <= ch <= "\u04FF" for ch in text)


def is_already_processed(store, msg_text, window=5, ttl=30):
    if not msg_text:
        return False
    key = hash(msg_text.strip()[:200])
    now = time.time()
    if key in store and now - store[key] < window:
        return True
    store[key] = now
    for k in list(store):
        if now - store[k] > ttl:
            store.pop(k, None)
    return False


def cleanup_old_cache(cache, ttl=1800):
    now = time.time()
    for k in [
        k for k, v in list(cache.items())
        if isinstance(v, tuple) and len(v) > 3 and now - v[-1] > ttl
    ]:
        cache.pop(k, None)


def show_success(text="Отправлено"):
    run_on_ui_thread(lambda: BulletinHelper.show_success(text, get_last_fragment()))


def show_error(message="Не найдено"):
    run_on_ui_thread(lambda: BulletinHelper.show_error(message, get_last_fragment()))


def show_info(message):
    run_on_ui_thread(lambda: BulletinHelper.show_info(message, get_last_fragment()))


def parse_cmd(msg_lower, msg, commands):
    for c in sorted(commands, key=len, reverse=True):
        pat = rf"^{re.escape(c)}"
        if len(msg) > len(c):
            pat += r"\s"
        if re.match(pat, msg_lower):
            return c
    return None