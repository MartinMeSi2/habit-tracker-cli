#!/usr/bin/env python3
"""Punto de entrada del Habit Tracker v3 — versión modular."""
import sys
import readchar
from rich.live import Live
from constants import P, console
from data import load_data, save_data, _today
from render import build_main_layout
from screens import (form_habit, action_check, action_delete, action_export,
                     screen_calendar, screen_sleep, screen_journal, screen_goals,
                     screen_events, screen_history, screen_heatmap, screen_reorder,
                     _quick_counter)


def main():
    data = load_data()
    selected = 0
    last_undo = None
    with Live(screen=True, auto_refresh=False, console=console) as live:
        def _render():
            layout, hl = build_main_layout(data, selected)
            live.update(layout)
            live.refresh()
            return hl
        habit_list = _render()
        while True:
            n = len(habit_list)
            key = readchar.readkey()
            if key == readchar.key.UP:
                if n:
                    selected = max(0, selected - 1)
                habit_list = _render()
                continue
            if key == readchar.key.DOWN:
                if n:
                    selected = min(n - 1, selected + 1)
                habit_list = _render()
                continue
            if key in ("q", "Q"):
                break
            elif key in ("u", "U"):
                if last_undo:
                    ds, hid, prev = last_undo["ds"], last_undo["hid"], last_undo["prev"]
                    if prev is None:
                        data["logs"].get(ds, {}).pop(hid, None)
                    else:
                        data["logs"][ds][hid] = prev
                    save_data(data)
                last_undo = None
                habit_list = _render()
            elif key in ("\r", "\n", readchar.key.ENTER):
                last_undo = None
                if habit_list and 0 <= selected < n:
                    last_undo = action_check(data, habit_list[selected])
                habit_list = _render()
            elif key in ("+", "="):
                last_undo = None
                if habit_list and 0 <= selected < n and habit_list[selected].get("type") == "counter":
                    _quick_counter(data, habit_list[selected], +1)
                habit_list = _render()
            elif key == "-":
                last_undo = None
                if habit_list and 0 <= selected < n and habit_list[selected].get("type") == "counter":
                    _quick_counter(data, habit_list[selected], -1)
                habit_list = _render()
            elif key in ("a", "A"):
                last_undo = None
                form_habit(data)
                habit_list = _render()
            elif key in ("e", "E"):
                last_undo = None
                if habit_list and 0 <= selected < n:
                    form_habit(data, existing=habit_list[selected])
                habit_list = _render()
            elif key in ("d", "D"):
                last_undo = None
                if habit_list and 0 <= selected < n:
                    if action_delete(data, habit_list[selected]):
                        selected = max(0, selected - 1)
                habit_list = _render()
            elif key in ("h", "H"):
                last_undo = None
                if habit_list and 0 <= selected < n:
                    screen_history(data, habit_list[selected])
                habit_list = _render()
            elif key in ("c", "C"):
                last_undo = None
                screen_calendar(data)
                habit_list = _render()
            elif key in ("s", "S"):
                last_undo = None
                screen_sleep(data)
                habit_list = _render()
            elif key in ("j", "J"):
                last_undo = None
                screen_journal(data)
                habit_list = _render()
            elif key in ("g", "G"):
                last_undo = None
                screen_goals(data)
                habit_list = _render()
            elif key in ("v", "V"):
                last_undo = None
                screen_events(data)
                habit_list = _render()
            elif key in ("o", "O"):
                last_undo = None
                screen_reorder(data)
                habit_list = _render()
            elif key in ("x", "X"):
                last_undo = None
                action_export(data)
                habit_list = _render()
            elif key in ("m", "M"):
                last_undo = None
                screen_heatmap(data)
                habit_list = _render()
    console.print(f"\n  [bold {P['blue']}]👋  ¡Hasta mañana![/bold {P['blue']}]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f"\n  [dim]Interrumpido.[/dim]\n")
        sys.exit(0)
