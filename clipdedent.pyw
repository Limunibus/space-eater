"""
ClipDedent - Clipboard indentation cleaner.
Runs in background, cleans indentation when you paste.

Hotkeys:
  Ctrl+Shift+V  - Paste with left indent + trailing whitespace removed
  Ctrl+Shift+Q  - Quit

Zero external dependencies. Uses only Python stdlib + Windows API via ctypes.
Run as .pyw for silent background mode, or with python.exe for console output.
"""

import ctypes
from ctypes import wintypes
import textwrap
import time
import sys

# ── Windows API constants ─────────────────────────────────────────
CF_UNICODETEXT  = 13
GMEM_MOVEABLE   = 0x0002
KEYEVENTF_KEYUP = 0x0002
WM_HOTKEY       = 0x0312
MOD_CONTROL     = 0x0002
MOD_SHIFT       = 0x0004
MOD_ALT         = 0x0001
MOD_NOREPEAT    = 0x4000
HOTKEY_PASTE    = 1
HOTKEY_QUIT     = 2

# ── Windows API handles ──────────────────────────────────────────
user32  = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Clipboard type hints
user32.OpenClipboard.argtypes  = [wintypes.HWND]
user32.OpenClipboard.restype   = wintypes.BOOL
user32.CloseClipboard.restype  = wintypes.BOOL
user32.EmptyClipboard.restype  = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype  = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype  = wintypes.HANDLE
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype  = wintypes.BOOL
kernel32.GlobalLock.argtypes   = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype    = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype  = wintypes.BOOL
kernel32.GlobalAlloc.argtypes  = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype   = wintypes.HGLOBAL

# Hotkey / message loop type hints
user32.RegisterHotKey.argtypes   = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype    = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype  = wintypes.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                               wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype  = wintypes.BOOL

# NOTE: keybd_event and MessageBeep are called WITHOUT argtypes.
# This avoids 64-bit marshaling issues with ULONG_PTR dwExtraInfo.
# ctypes default int marshaling works correctly for both 32 and 64-bit.


# ── Console detection ─────────────────────────────────────────────
def _has_console():
    try:
        if sys.stdout is None:
            return False
        sys.stdout.write('')
        return True
    except Exception:
        return False

HAS_CONSOLE = _has_console()

def log(msg):
    if HAS_CONSOLE:
        print(msg)
        sys.stdout.flush()


# ── Clipboard ─────────────────────────────────────────────────────
def get_clipboard():
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None
    text = None
    if user32.OpenClipboard(0):
        try:
            h = user32.GetClipboardData(CF_UNICODETEXT)
            if h:
                ptr = kernel32.GlobalLock(h)
                if ptr:
                    text = ctypes.wstring_at(ptr)
                    kernel32.GlobalUnlock(h)
        finally:
            user32.CloseClipboard()
    return text


def set_clipboard(text):
    raw = text.encode('utf-16-le') + b'\x00\x00'
    if user32.OpenClipboard(0):
        try:
            user32.EmptyClipboard()
            h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(raw))
            if h:
                ptr = kernel32.GlobalLock(h)
                if ptr:
                    ctypes.memmove(ptr, raw, len(raw))
                    kernel32.GlobalUnlock(h)
                    user32.SetClipboardData(CF_UNICODETEXT, h)
        finally:
            user32.CloseClipboard()


# ── Text processing ───────────────────────────────────────────────
def clean_indentation(text):
    """Remove common leading whitespace and trailing spaces per line."""
    dedented = textwrap.dedent(text)
    lines = dedented.split('\n')
    cleaned = '\n'.join(line.rstrip() for line in lines)
    cleaned = cleaned.strip('\n')
    return cleaned


# ── Key simulation via keybd_event (no argtypes = safe marshaling) ─
def simulate_paste():
    """Release held modifiers, then send Ctrl+V to the foreground window."""
    # Release any physically held modifier keys
    user32.keybd_event(0x10, 0, KEYEVENTF_KEYUP, 0)   # Shift up
    user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)   # Ctrl up
    user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)   # Alt up
    time.sleep(0.15)

    # Ctrl+V: press Ctrl, press V, release V, release Ctrl
    user32.keybd_event(0x11, 0, 0, 0)                  # Ctrl down
    time.sleep(0.03)
    user32.keybd_event(0x56, 0, 0, 0)                  # V down
    time.sleep(0.03)
    user32.keybd_event(0x56, 0, KEYEVENTF_KEYUP, 0)   # V up
    time.sleep(0.03)
    user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)   # Ctrl up


# ── Main loop ─────────────────────────────────────────────────────
def main():
    paste_combo = 'Ctrl+Shift+V'
    ok = user32.RegisterHotKey(None, HOTKEY_PASTE,
                               MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x56)
    if not ok:
        ok = user32.RegisterHotKey(None, HOTKEY_PASTE,
                                   MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 0x56)
        if ok:
            paste_combo = 'Ctrl+Alt+V'
        else:
            log('ERROR: Could not register paste hotkey!')
            if HAS_CONSOLE:
                input('Press Enter to exit...')
            return

    user32.RegisterHotKey(None, HOTKEY_QUIT,
                          MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, 0x51)

    log('=' * 45)
    log('  ClipDedent is running')
    log('=' * 45)
    log(f'  {paste_combo}   = Paste cleaned (no indent)')
    log(f'  Ctrl+Shift+Q   = Quit')
    log('')
    log('  Waiting for hotkey...')
    log('')

    try:
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
            if msg.message == WM_HOTKEY:
                if msg.wParam == HOTKEY_PASTE:
                    text = get_clipboard()
                    if text:
                        cleaned = clean_indentation(text)
                        set_clipboard(cleaned)
                        time.sleep(0.05)
                        simulate_paste()
                        user32.MessageBeep(0)
                        removed = len(text) - len(cleaned)
                        log(f'  Pasted: {len(cleaned)} chars ({removed} ws removed)')
                    else:
                        log('  No text in clipboard.')

                elif msg.wParam == HOTKEY_QUIT:
                    log('Exiting ClipDedent...')
                    break
    finally:
        user32.UnregisterHotKey(None, HOTKEY_PASTE)
        user32.UnregisterHotKey(None, HOTKEY_QUIT)


if __name__ == '__main__':
    main()
