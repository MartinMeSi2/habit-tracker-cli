#!/usr/bin/env python3
"""Punto de entrada del Habit Tracker v3 — versión modular."""
import sys
from contextlib import contextmanager
import readchar
from rich.live import Live
from constants import P, console
from data import load_data, save_data, _today, _build_ordered
from render import build_main_layout
from screens import (form_habit, action_check, action_delete, action_export,
                     screen_calendar, screen_sleep, screen_journal, screen_goals,
                     screen_events, screen_history, screen_heatmap, screen_reorder,
                     _quick_counter)


def _scroll_for_last(data, target_idx, content_budget):
    """Devuelve el mínimo `scroll` para que `target_idx` sea el último hábito visible.

    Recorre la lista de hábitos hacia atrás desde `target_idx`, contando el
    coste de cada fila (1 por hábito + 1 extra la primera vez que aparece una
    categoría) hasta agotar el presupuesto de contenido.  El índice donde se
    detiene es el primer hábito visible → ese es el nuevo scroll.
    """
    ordered = _build_ordered(data)
    habits = [(cat, h) for kind, cat, h in ordered if kind == "HABIT"]
    rows = 0
    seen_cats: set = set()
    first = target_idx
    for i in range(target_idx, -1, -1):
        if i >= len(habits):
            continue
        cat = habits[i][0]
        cat_cost = 1 if cat not in seen_cats else 0
        if rows + cat_cost + 1 > content_budget:
            break
        seen_cats.add(cat)
        rows += cat_cost + 1
        first = i
    return first


def main():
    data = load_data()
    selected = 0
    scroll = 0
    last_vis = 0        # último índice de hábito visible (actualizado en _render)
    last_undo = None

    with Live(screen=True, auto_refresh=False, console=console) as live:

        def _render():
            nonlocal last_vis
            # Filas disponibles para el contenido del panel de hábitos:
            # total - header(3) - strip(4) - keys(9) - bordes panel(2) - cabecera tabla(2)
            row_budget = max(5, console.size.height - 20)
            layout, hl, lv = build_main_layout(data, selected, scroll, row_budget)
            last_vis = lv
            live.update(layout)
            live.refresh()
            return hl

        @contextmanager
        def _subscreen():
            """Pausa Live y ejecuta la sub-pantalla en el buffer alternado limpio.

            Así las sub-pantallas no acumulan historial de interacciones en el
            buffer primario del terminal, igual que la pantalla principal.
            """
            live.stop()                    # sale del buffer alternado de Live
            console.set_alt_screen(True)   # entra en buffer alternado limpio
            try:
                yield
            finally:
                console.set_alt_screen(False)  # sale del buffer alternado
                live.start(refresh=False)      # Live vuelve a su buffer alternado

        habit_list = _render()

        while True:
            n = len(habit_list)

            # ── Clamp: selected siempre dentro del rango válido ──────
            new_sel = max(0, min(selected, n - 1)) if n > 0 else 0
            if new_sel != selected:
                selected = new_sel
                habit_list = _render()
                n = len(habit_list)

            key = readchar.readkey()

            # ── Navegación ↑↓ con scroll automático ─────────────────
            if key == readchar.key.UP:
                if n:
                    selected = max(0, selected - 1)
                    if selected < scroll:
                        scroll = selected
                habit_list = _render()
                continue

            if key == readchar.key.DOWN:
                if n:
                    selected = min(n - 1, selected + 1)
                    if selected > last_vis:
                        row_budget = max(5, console.size.height - 20)
                        content_budget = max(2, row_budget - 2)
                        scroll = _scroll_for_last(data, selected, content_budget)
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

            # ── Sub-pantallas: cada una en su propio buffer alternado ─
            elif key in ("a", "A"):
                last_undo = None
                with _subscreen():
                    form_habit(data)
                habit_list = _render()

            elif key in ("e", "E"):
                last_undo = None
                if habit_list and 0 <= selected < n:
                    with _subscreen():
                        form_habit(data, existing=habit_list[selected])
                habit_list = _render()

            elif key in ("d", "D"):
                last_undo = None
                if habit_list and 0 <= selected < n:
                    with _subscreen():
                        deleted = action_delete(data, habit_list[selected])
                    if deleted:
                        selected = max(0, selected - 1)
                        scroll = max(0, min(scroll, selected))
                habit_list = _render()

            elif key in ("h", "H"):
                last_undo = None
                if habit_list and 0 <= selected < n:
                    with _subscreen():
                        screen_history(data, habit_list[selected])
                habit_list = _render()

            elif key in ("c", "C"):
                last_undo = None
                with _subscreen():
                    screen_calendar(data)
                habit_list = _render()

            elif key in ("s", "S"):
                last_undo = None
                with _subscreen():
                    screen_sleep(data)
                habit_list = _render()

            elif key in ("j", "J"):
                last_undo = None
                with _subscreen():
                    screen_journal(data)
                habit_list = _render()

            elif key in ("g", "G"):
                last_undo = None
                with _subscreen():
                    screen_goals(data)
                habit_list = _render()

            elif key in ("v", "V"):
                last_undo = None
                with _subscreen():
                    screen_events(data)
                habit_list = _render()

            elif key in ("o", "O"):
                last_undo = None
                with _subscreen():
                    screen_reorder(data)
                habit_list = _render()

            elif key in ("x", "X"):
                last_undo = None
                with _subscreen():
                    action_export(data)
                habit_list = _render()

            elif key in ("m", "M"):
                last_undo = None
                with _subscreen():
                    screen_heatmap(data)
                habit_list = _render()

    console.print(f"\n  [bold {P['blue']}]👋  ¡Hasta mañana![/bold {P['blue']}]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f"\n  [dim]Interrumpido.[/dim]\n")
        sys.exit(0)
