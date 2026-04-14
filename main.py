#!/usr/bin/env python3
"""Punto de entrada del Habit Tracker v3 — versión modular."""
import sys
from contextlib import contextmanager
import readchar
from rich.live import Live
from constants import P, console, APP_WIDTH, APP_HEIGHT
from data import load_data, save_data, _today, _build_navigable
from render import build_main_layout
from screens import (form_habit, action_check, action_delete, action_export,
                     screen_calendar, screen_sleep, screen_journal, screen_goals,
                     screen_events, screen_history, screen_heatmap, screen_reorder,
                     _quick_counter)


def _centered_scroll(nav_len, cursor, content_budget):
    """Scroll que deja ``cursor`` centrado en la ventana visible."""
    half = content_budget // 2
    return max(0, min(cursor - half, nav_len - content_budget))


def _resize_terminal():
    """Intenta redimensionar el terminal a APP_WIDTH × APP_HEIGHT.

    Usa la secuencia xterm \033[8;<rows>;<cols>t, soportada por la mayoría
    de emuladores modernos (Windows Terminal, ConEmu, iTerm2, GNOME Terminal…).
    Tras enviarla espera un instante para que el SO aplique el cambio.
    """
    import time
    sys.stdout.write(f"\033[8;{APP_HEIGHT};{APP_WIDTH}t")
    sys.stdout.flush()
    time.sleep(0.15)   # pequeña pausa para que el SO procese el resize


def main():
    _resize_terminal()
    data = load_data()
    cursor   = 0      # índice sobre la lista navegable (CAT + HABIT visibles)
    scroll   = 0      # primer índice visible en la tabla
    last_vis = 0      # último índice visible (actualizado por _render)
    last_undo = None

    with Live(screen=True, auto_refresh=False, console=console) as live:

        def _render():
            nonlocal last_vis
            row_budget = max(5, console.size.height - 20)
            layout, nav, lv = build_main_layout(data, cursor, scroll, row_budget)
            last_vis = lv
            live.update(layout)
            live.refresh()
            return nav

        @contextmanager
        def _subscreen():
            """Pausa Live y corre la sub-pantalla en buffer alternado limpio."""
            live.stop()
            console.set_alt_screen(True)
            try:
                yield
            finally:
                console.set_alt_screen(False)
                live.start(refresh=False)

        def _recenter(nav):
            """Recalcula scroll para centrar ``cursor`` si está fuera de vista."""
            nonlocal scroll
            row_budget     = max(5, console.size.height - 20)
            content_budget = max(2, row_budget - 2)
            if cursor < scroll or cursor > last_vis:
                scroll = _centered_scroll(len(nav), cursor, content_budget)

        nav = _render()

        while True:
            n = len(nav)

            # ── Clamp cursor ─────────────────────────────────────────
            new_cur = max(0, min(cursor, n - 1)) if n > 0 else 0
            if new_cur != cursor:
                cursor = new_cur
                nav = _render()
                n = len(nav)

            key = readchar.readkey()

            # ── ↑ ────────────────────────────────────────────────────
            if key == readchar.key.UP:
                if n:
                    cursor = n - 1 if cursor == 0 else cursor - 1
                    _recenter(nav)
                nav = _render()
                continue

            # ── ↓ ────────────────────────────────────────────────────
            if key == readchar.key.DOWN:
                if n:
                    cursor = 0 if cursor == n - 1 else cursor + 1
                    _recenter(nav)
                nav = _render()
                continue

            # ── Q: salir ─────────────────────────────────────────────
            if key in ("q", "Q"):
                break

            # ── TAB: colapsar / expandir categoría ───────────────────
            elif key == "\t":
                if n and 0 <= cursor < n:
                    kind, cat, h = nav[cursor]
                    # Si estamos en un hábito, buscamos la categoría padre
                    if kind == "HABIT":
                        cat_idx = next(
                            (i for i in range(cursor, -1, -1)
                             if nav[i][0] == "CAT" and nav[i][1] == cat),
                            None)
                        if cat_idx is not None:
                            cursor = cat_idx
                        kind, cat, _ = nav[cursor]
                    if kind == "CAT":
                        collapsed = data.setdefault("collapsed_cats", [])
                        if cat in collapsed:
                            collapsed.remove(cat)
                        else:
                            collapsed.append(cat)
                        save_data(data)
                        nav = _render()
                        n   = len(nav)
                        cursor = max(0, min(cursor, n - 1))
                        _recenter(nav)
                nav = _render()

            # ── * : marcar / desmarcar hábito como destacado ──────────
            elif key == "*":
                if n and 0 <= cursor < n:
                    kind, cat, h = nav[cursor]
                    if kind == "HABIT":
                        h["starred"] = not h.get("starred", False)
                        save_data(data)
                nav = _render()

            # ── U: deshacer ──────────────────────────────────────────
            elif key in ("u", "U"):
                if last_undo:
                    ds, hid, prev = last_undo["ds"], last_undo["hid"], last_undo["prev"]
                    if prev is None:
                        data["logs"].get(ds, {}).pop(hid, None)
                    else:
                        data["logs"][ds][hid] = prev
                    save_data(data)
                last_undo = None
                nav = _render()

            # ── ENTER: check / registrar valor ───────────────────────
            elif key in ("\r", "\n", readchar.key.ENTER):
                last_undo = None
                if n and 0 <= cursor < n:
                    kind, cat, h = nav[cursor]
                    if kind == "HABIT":
                        last_undo = action_check(data, h)
                nav = _render()

            # ── + / - : contador rápido ──────────────────────────────
            elif key in ("+", "="):
                last_undo = None
                if n and 0 <= cursor < n:
                    kind, cat, h = nav[cursor]
                    if kind == "HABIT" and h.get("type") == "counter":
                        _quick_counter(data, h, +1)
                nav = _render()

            elif key == "-":
                last_undo = None
                if n and 0 <= cursor < n:
                    kind, cat, h = nav[cursor]
                    if kind == "HABIT" and h.get("type") == "counter":
                        _quick_counter(data, h, -1)
                nav = _render()

            # ── Sub-pantallas ─────────────────────────────────────────
            elif key in ("a", "A"):
                last_undo = None
                with _subscreen():
                    form_habit(data)
                nav = _render()

            elif key in ("e", "E"):
                last_undo = None
                if n and 0 <= cursor < n:
                    kind, cat, h = nav[cursor]
                    if kind == "HABIT":
                        with _subscreen():
                            form_habit(data, existing=h)
                nav = _render()

            elif key in ("d", "D"):
                last_undo = None
                if n and 0 <= cursor < n:
                    kind, cat, h = nav[cursor]
                    if kind == "HABIT":
                        with _subscreen():
                            deleted = action_delete(data, h)
                        if deleted:
                            cursor = max(0, cursor - 1)
                            nav    = _render()
                            scroll = max(0, min(scroll, cursor))
                nav = _render()

            elif key in ("h", "H"):
                last_undo = None
                if n and 0 <= cursor < n:
                    kind, cat, h = nav[cursor]
                    if kind == "HABIT":
                        with _subscreen():
                            screen_history(data, h)
                nav = _render()

            elif key in ("c", "C"):
                last_undo = None
                with _subscreen():
                    screen_calendar(data)
                nav = _render()

            elif key in ("s", "S"):
                last_undo = None
                with _subscreen():
                    screen_sleep(data)
                nav = _render()

            elif key in ("j", "J"):
                last_undo = None
                with _subscreen():
                    screen_journal(data)
                nav = _render()

            elif key in ("g", "G"):
                last_undo = None
                with _subscreen():
                    screen_goals(data)
                nav = _render()

            elif key in ("v", "V"):
                last_undo = None
                with _subscreen():
                    screen_events(data)
                nav = _render()

            elif key in ("o", "O"):
                last_undo = None
                with _subscreen():
                    screen_reorder(data)
                nav = _render()

            elif key in ("x", "X"):
                last_undo = None
                with _subscreen():
                    action_export(data)
                nav = _render()

            elif key in ("m", "M"):
                last_undo = None
                with _subscreen():
                    screen_heatmap(data)
                nav = _render()

    console.print(f"\n  [bold {P['blue']}]👋  ¡Hasta mañana![/bold {P['blue']}]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f"\n  [dim]Interrumpido.[/dim]\n")
        sys.exit(0)
