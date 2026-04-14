#!/usr/bin/env python3
"""Pantallas interactivas y acciones del Habit Tracker."""
import json, csv, sqlite3, textwrap
from datetime import date, timedelta
from pathlib import Path
from calendar import monthrange
import readchar
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box
from rich.prompt import Prompt, Confirm
from constants import (P, BADGES, SPARKS, SECTION_TYPES, SLEEP_COLORS, PERIODS,
                       PERIOD_UI, EVENT_TYPES, HEAT_COLORS, _DIAS, _MESES,
                       HABIT_COLORS, DEFAULT_CATS, MOODS, console)
from data import (load_data, save_data, _today, _is_done, _find, get_streak, get_rate,
                  get_badge, habit_history, sparkline_vals, make_spark, sleep_color,
                  _build_ordered, _event_matches, _events_for_month, _heat_intensity)
from render import (make_header, make_habits_panel, make_keys_panel,
                    make_mini_calendar, make_today_strip, build_main_layout,
                    sleep_bar_text, pct_bar, _err, _pause, _hr, _section)


def ask_int_range(pt, mn, mx, default=None):
    while True:
        d = str(default) if default is not None else str(mn)
        val = Prompt.ask(pt, default=d)
        try:
            iv = int(val)
            if mn <= iv <= mx:
                return iv
            _err(f"Elige un número entre {mn} y {mx}.")
        except ValueError:
            _err("Introduce un número entero válido.")


def ask_float_range(pt, mn, mx, default=None):
    while True:
        d = str(default) if default is not None else str(mn)
        val = Prompt.ask(pt, default=d)
        try:
            fv = float(val.replace(",", "."))
            if mn <= fv <= mx:
                return fv
            _err(f"Introduce un valor entre {mn} y {mx}.")
        except ValueError:
            _err("Valor inválido. Usa punto o coma decimal (ej. 7.5).")


# ─────────────────────────────────────────── Calendario mensual ──

def screen_calendar(data, year=None, month=None):
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month
    _, n_days = monthrange(year, month)
    console.clear()
    console.print(make_header())
    table = Table(box=box.SIMPLE, show_header=True, header_style=f"bold {P['blue']}",
                  border_style=P["border"], expand=False)
    table.add_column("Hábito", min_width=18, no_wrap=True)
    for d in range(1, n_days + 1):
        is_t = date(year, month, d) == today
        lbl = (f"[bold {P['blue']}]{d:02d}[/bold {P['blue']}]" if is_t else f"[dim]{d:02d}[/dim]")
        table.add_column(lbl, width=3, justify="center")
    for h in data["habits"]:
        row = [h["name"][:18]]
        for d in range(1, n_days + 1):
            ds = date(year, month, d).isoformat()
            val = data["logs"].get(ds, {}).get(str(h["id"]))
            done = _is_done(val, h)
            ht = h.get("type", "boolean")
            if ht == "boolean":
                cell = f"[{P['green']}]✓[/{P['green']}]" if done else "[dim]-[/dim]"
            elif ht == "counter":
                cell = f"[{P['teal']}]{val if val is not None else '-'}[/{P['teal']}]"
            elif ht == "rating":
                cell = f"[{P['yellow']}]{val if val is not None else '-'}[/{P['yellow']}]"
            elif ht == "note":
                cell = f"[{P['purple']}]✎[/{P['purple']}]" if done else "[dim]-[/dim]"
            else:
                cell = f"[{P['green']}]✓[/{P['green']}]" if done else "[dim]-[/dim]"
            row.append(cell)
        table.add_row(*row)
    sleep = data.get("sleep", {})
    sleep_row = [f"[bold {P['purple']}]😴 Sueño[/bold {P['purple']}]"]
    sleep_vals = []
    for d in range(1, n_days + 1):
        ds = date(year, month, d).isoformat()
        hours = sleep.get(ds)
        if hours is not None:
            sleep_vals.append(hours)
            color = sleep_color(hours)
            h_str = f"{hours:.1f}" if hours < 10 else "10"
            sleep_row.append(f"[bold {color}]{h_str}[/bold {color}]")
        else:
            sleep_row.append("[dim]-[/dim]")
    table.add_row(*sleep_row, style=f"on {P['surf']}")
    lbl = f"{_MESES[month-1].upper()} {year}"
    stats_txt = ""
    if sleep_vals:
        avg = sum(sleep_vals) / len(sleep_vals)
        good = sum(1 for h in sleep_vals if h >= 7)
        stats_txt = (f"  [dim]Prom [bold {sleep_color(avg)}]{avg:.1f}h[/bold {sleep_color(avg)}]"
                     f"  ·  Mejor [{P['green']}]{max(sleep_vals):.1f}h[/{P['green']}]"
                     f"  ·  Peor [{P['red']}]{min(sleep_vals):.1f}h[/{P['red']}]"
                     f"  ·  ≥7h [{P['blue']}]{good}/{len(sleep_vals)}[/{P['blue']}][/dim]")
    console.print(Panel(table,
                        title=f"[bold {P['blue']}]📅  CALENDARIO — {lbl}[/bold {P['blue']}]",
                        border_style=P["border"], padding=(0, 1),
                        subtitle=stats_txt if stats_txt else None))
    console.print(make_keys_panel("calendar"))
    console.print(f"\n[dim]  ←  mes anterior  ·  →  mes siguiente  ·  Q  volver[/dim]")
    while True:
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            break
        elif key == readchar.key.LEFT:
            nm, ny = (12, year - 1) if month == 1 else (month - 1, year)
            screen_calendar(data, ny, nm)
            return
        elif key == readchar.key.RIGHT:
            nm, ny = (1, year + 1) if month == 12 else (month + 1, year)
            screen_calendar(data, ny, nm)
            return


# ──────────────────────────────────────────────────── Historial ──

def screen_history(data, habit):
    if habit.get("type") == "note":
        screen_notes_habit(data, habit)
    else:
        _screen_history_regular(data, habit)


def _screen_history_regular(data, habit):
    selected = 0
    while True:
        history = habit_history(data, habit["id"], days=30)
        rate = get_rate(data, habit["id"])
        streak = get_streak(data, habit["id"])
        e_b, n_b, c_b = get_badge(streak)
        htype = habit.get("type", "boolean")
        target = habit.get("target")
        n = len(history)
        console.clear()
        console.print(make_header())
        _section(f"📈  {habit['name'].upper()} — HISTORIAL", P["teal"])
        rc = P["green"] if rate >= 80 else P["yellow"] if rate >= 50 else P["red"]
        summ = Text()
        summ.append(f"\n  ◈ Spark  ", style=P["muted"])
        summ.append(make_spark(sparkline_vals(data, habit["id"], 30)), style=f"bold {P['teal']}")
        summ.append(f"\n  ◈ Tasa   ", style=P["muted"])
        summ.append(f"{rate:.1f}%   ", style=rc)
        summ.append(f"◈ Racha  ", style=P["muted"])
        summ.append(f"🔥{streak}d  {e_b} {n_b}\n", style=f"bold {c_b}")
        console.print(Panel(summ, border_style=P["border"]))
        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {P['blue']}",
                      border_style=P["border"])
        table.add_column("", width=2)
        table.add_column("Fecha", width=12)
        table.add_column("Día", width=5, justify="center")
        table.add_column("Valor", width=12, justify="center")
        table.add_column("Est", width=5, justify="center")
        table.add_column("Visual", min_width=12)
        for idx, (ds, val, done) in enumerate(history):
            day = date.fromisoformat(ds)
            is_sel = (idx == selected)
            is_t = (ds == _today())
            cur = f"[bold {P['blue']}]▶[/bold {P['blue']}]" if is_sel else " "
            dt = Text(ds, style=f"bold {P['blue']}" if is_t else P["text"])
            dow = Text(day.strftime("%a"), style=P["muted"])
            status = f"[{P['green']}]✅[/{P['green']}]" if done else "[dim]⬜[/dim]"
            if htype == "boolean":
                vl = "-" if val is None else ("Sí" if done else "No")
                vis = Text("█" * 10 if done else "░" * 10, style=P["green"] if done else "dim")
            elif htype == "counter":
                v = int(val or 0)
                tgt = target or 10
                b = max(0, min(10, int(v / tgt * 10)))
                vl = "-" if val is None else f"{v}/{tgt}"
                vis = Text("█" * b + "░" * (10 - b), style=P["teal"] if val is not None else "dim")
            elif htype == "rating":
                v = int(val or 0)
                vl = "-" if val is None else ("⭐" * v if v else "-")
                vis = Text("★" * v + "☆" * (5 - v), style=P["yellow"] if val is not None else "dim")
            else:
                vl = "-" if val is None else str(val)
                vis = Text("")
            table.add_row(cur, dt, dow, vl, status, vis,
                          style=f"on {P['sel']}" if is_sel else "")
        console.print(Panel(table, title=f"[bold {P['blue']}]📋  ÚLTIMOS 30 DÍAS[/bold {P['blue']}]",
                            border_style=P["border"]))
        console.print(make_keys_panel("history"))
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            break
        elif key == readchar.key.UP:
            selected = max(0, selected - 1)
        elif key == readchar.key.DOWN:
            selected = min(n - 1, selected + 1)


def screen_notes_habit(data, habit):
    selected = 0
    while True:
        entries = []
        for i in range(30):
            ds = (date.today() - timedelta(days=i)).isoformat()
            val = data["logs"].get(ds, {}).get(str(habit["id"]), "")
            entries.append((ds, val or ""))
        selected = max(0, min(selected, len(entries) - 1))
        console.clear()
        console.print(make_header())
        _section(f"📝  NOTAS — {habit['name'].upper()}", P["purple"])
        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {P['blue']}",
                      border_style=P["border"], expand=True)
        table.add_column("", width=2)
        table.add_column("Fecha", width=12)
        table.add_column("Día", width=4)
        table.add_column("Preview", min_width=46)
        for idx, (ds, val) in enumerate(entries):
            day = date.fromisoformat(ds)
            is_sel = (idx == selected)
            is_t = (ds == _today())
            cur = f"[bold {P['purple']}]▶[/bold {P['purple']}]" if is_sel else " "
            dt = Text(ds, style=f"bold {P['blue']}" if is_t else P["text"])
            dow = Text(day.strftime("%a"), style=P["muted"])
            if val:
                prev = val[:54].replace("\n", " ") + ("…" if len(val) > 54 else "")
                prev_t = Text(prev, style=P["text"])
            else:
                prev_t = Text("── vacío ──", style="dim")
            table.add_row(cur, dt, dow, prev_t, style=f"on {P['sel']}" if is_sel else "")
        console.print(Panel(table, title=f"[bold {P['purple']}]📋  ÚLTIMAS 30 NOTAS[/bold {P['purple']}]",
                            border_style=P["border"]))
        sel_ds, sel_val = entries[selected]
        if sel_val:
            wrapped = textwrap.fill(sel_val, width=76)
            console.print(Panel(Text(f"\n{wrapped}\n", style=P["text"]),
                                title=f"[bold {P['purple']}]📖  {sel_ds}[/bold {P['purple']}]",
                                border_style=P["border"], padding=(0, 2)))
        else:
            console.print(Panel(Text("\n  Sin nota para este día.\n", style="dim"),
                                title=f"[bold {P['purple']}]📖  {sel_ds}[/bold {P['purple']}]",
                                border_style=P["border"], padding=(0, 2)))
        console.print(make_keys_panel("history"))
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            break
        elif key == readchar.key.UP:
            selected = max(0, selected - 1)
        elif key == readchar.key.DOWN:
            selected = min(len(entries) - 1, selected + 1)
        elif key in ("a", "A"):
            _edit_note_entry(data, habit, _today())
        elif key in ("e", "E"):
            _edit_note_entry(data, habit, sel_ds)
        elif key in ("d", "D"):
            if sel_val and Confirm.ask(f"\n  [bold {P['red']}]¿Eliminar nota del {sel_ds}?[/bold {P['red']}]"):
                hid = str(habit["id"])
                if sel_ds in data["logs"] and hid in data["logs"][sel_ds]:
                    del data["logs"][sel_ds][hid]
                    save_data(data)
                    console.print(f"  [{P['green']}]Eliminada.[/{P['green']}]")


def _edit_note_entry(data, habit, ds):
    hid = str(habit["id"])
    current = data["logs"].get(ds, {}).get(hid, "")
    console.print(f"\n  [{P['purple']}]◈  Nota para {ds}[/{P['purple']}]")
    if current:
        console.print(f"  [dim]Actual: {current[:70]}{'…' if len(current) > 70 else ''}[/dim]")
    val = Prompt.ask(f"  [{P['purple']}]Escribe la nota[/{P['purple']}]", default=current)
    if val.strip():
        if ds not in data["logs"]:
            data["logs"][ds] = {}
        data["logs"][ds][hid] = val.strip()
        save_data(data)
        console.print(f"  [{P['green']}]✅ Guardada.[/{P['green']}]")


# ─────────────────────────────────────────────────────── Diario ──

def screen_journal(data):
    journal = data.setdefault("journal", {})
    selected = 0

    def _be():
        return [((date.today() - timedelta(days=i)).isoformat(),
                 journal.get((date.today() - timedelta(days=i)).isoformat(), ""))
                for i in range(30)]

    entries = _be()
    while True:
        selected = max(0, min(selected, len(entries) - 1))
        console.clear()
        console.print(make_header())
        _section("📓  DIARIO PERSONAL", P["pink"])
        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {P['blue']}",
                      border_style=P["border"], expand=True)
        table.add_column("", width=2)
        table.add_column("Fecha", width=12)
        table.add_column("Día", width=4)
        table.add_column("Est", width=4, justify="center")
        table.add_column("Preview", min_width=42)
        for idx, (ds, val) in enumerate(entries):
            day = date.fromisoformat(ds)
            is_sel = (idx == selected)
            is_t = (ds == _today())
            cur = f"[bold {P['pink']}]▶[/bold {P['pink']}]" if is_sel else " "
            dt = Text(ds, style=f"bold {P['blue']}" if is_t else P["text"])
            dow = Text(day.strftime("%a"), style=P["muted"])
            status = f"[{P['green']}]✅[/{P['green']}]" if val else "[dim]—[/dim]"
            if val:
                prev = val[:45].replace("\n", " ") + ("…" if len(val) > 45 else "")
                prev_t = Text(prev, style=P["text"])
            else:
                prev_t = Text("sin entrada", style="dim")
            table.add_row(cur, dt, dow, status, prev_t, style=f"on {P['sel']}" if is_sel else "")
        console.print(Panel(table, title=f"[bold {P['pink']}]📋  ÚLTIMAS 30 ENTRADAS[/bold {P['pink']}]",
                            border_style=P["border"]))
        sel_ds, sel_val = entries[selected]
        if sel_val:
            wrapped = textwrap.fill(sel_val, width=76)
            console.print(Panel(Text(f"\n{wrapped}\n", style=P["text"]),
                                title=f"[bold {P['pink']}]📖  {sel_ds}[/bold {P['pink']}]",
                                border_style=P["border"], padding=(0, 2)))
        else:
            console.print(Panel(Text("\n  Sin entrada para este día.\n", style="dim"),
                                title=f"[bold {P['pink']}]📖  {sel_ds}[/bold {P['pink']}]",
                                border_style=P["border"], padding=(0, 2)))
        console.print(make_keys_panel("journal"))
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            break
        elif key == readchar.key.UP:
            selected = max(0, selected - 1)
        elif key == readchar.key.DOWN:
            selected = min(len(entries) - 1, selected + 1)
        elif key in ("a", "A"):
            _eje(data, _today())
            entries = _be()
        elif key in ("e", "E"):
            _eje(data, sel_ds)
            entries = _be()
        elif key in ("d", "D"):
            if sel_val and Confirm.ask(f"\n  [bold {P['red']}]¿Eliminar entrada del {sel_ds}?[/bold {P['red']}]"):
                journal.pop(sel_ds, None)
                save_data(data)
                entries = _be()


def _eje(data, ds):
    j = data.setdefault("journal", {})
    current = j.get(ds, "")
    console.print(f"\n  [{P['pink']}]◈  Entrada para {ds}[/{P['pink']}]")
    if current:
        console.print(f"  [dim]Actual: {current[:70]}{'…' if len(current) > 70 else ''}[/dim]")
    val = Prompt.ask(f"  [{P['pink']}]Escribe tu entrada[/{P['pink']}]", default=current)
    if val.strip():
        j[ds] = val.strip()
        save_data(data)
        console.print(f"  [{P['green']}]✅ Guardado.[/{P['green']}]")


# ──────────────────────────────────────────────────────── Sueño ──

def screen_sleep(data, year=None, month=None):
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month
    sleep = data.setdefault("sleep", {})
    _, n_days = monthrange(year, month)
    console.clear()
    console.print(make_header())
    lbl = f"{_MESES[month-1].upper()} {year}"
    _section(f"😴  SUEÑO — {lbl}", P["purple"])
    DOW = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
    first_dow = date(year, month, 1).weekday()
    grid = Text()
    grid.append("  ")
    for d in DOW:
        grid.append(d, style=f"bold {P['muted']}")
        grid.append("  ")
    grid.append("\n")
    week = [("    ", "")] * first_dow
    for d in range(1, n_days + 1):
        ds = date(year, month, d).isoformat()
        hours = sleep.get(ds)
        is_t = (date(year, month, d) == today)
        if hours is not None:
            color = sleep_color(hours)
            cell = (f"{hours:3.0f} ", f"bold {color}")
        elif is_t:
            cell = ("  -  ", f"bold {P['blue']}")
        else:
            cell = ("  -  ", "dim")
        week.append(cell)
        if date(year, month, d).weekday() == 6 or d == n_days:
            grid.append("  ")
            for txt, sty in week:
                grid.append(txt, style=sty) if sty else grid.append(txt)
            grid.append("\n")
            week = []
    console.print(Panel(grid,
                        title=f"[bold {P['purple']}]📅  CUADRÍCULA MENSUAL  [dim](horas)[/dim][/bold {P['purple']}]",
                        border_style=P["border"], padding=(0, 2)))
    bars = Text("\n")
    for i in range(13, -1, -1):
        ds = (today - timedelta(days=i)).isoformat()
        hours = sleep.get(ds)
        day = date.fromisoformat(ds)
        is_t = (ds == _today())
        label = f"{'▶' if is_t else ' '}{day.day:02d} {_MESES[day.month-1][:3]}"
        bars.append(f"  {label} ", style=f"bold {P['blue']}" if is_t else P["muted"])
        if hours is not None:
            b = min(10, int(hours / 10 * 10))
            color = sleep_color(hours)
            bars.append("█" * b, style=f"bold {color}")
            bars.append("░" * (10 - b), style="dim")
            warn = " ⚠" if hours < 6 else " ✓" if hours >= 7 else ""
            bars.append(f"  {hours:.1f}h{warn}\n", style=color)
        else:
            bars.append("-\n", style="dim")
    console.print(Panel(bars, title=f"[bold {P['teal']}]🌙  ÚLTIMAS 14 NOCHES[/bold {P['teal']}]",
                        border_style=P["border"]))
    all_m = [sleep.get(date(year, month, d).isoformat()) for d in range(1, n_days + 1)
             if sleep.get(date(year, month, d).isoformat()) is not None]
    stats = Text()
    if all_m:
        avg = sum(all_m) / len(all_m)
        best = max(all_m)
        worst = min(all_m)
        good_pct = sum(1 for h in all_m if h >= 7) / len(all_m) * 100
        stats.append(f"\n  ◈ Promedio  ", style=P["muted"])
        stats.append_text(sleep_bar_text(avg, 8))
        stats.append(f"\n  ◈ Mejor   ", style=P["muted"])
        stats.append(f"{best:.1f}h", style=P["green"])
        stats.append(f"   Peor   ", style=P["muted"])
        stats.append(f"{worst:.1f}h\n", style=P["red"])
        stats.append(f"  ◈ Noches ≥7h  ", style=P["muted"])
        stats.append(f"{good_pct:.0f}%", style=P["blue"])
        stats.append(f"  ({len(all_m)} registradas)\n", style=P["muted"])
    else:
        stats.append("\n  Sin datos este mes.\n", style="dim")
    legend = Text("\n  Leyenda: ")
    for mn, color, label in reversed(SLEEP_COLORS):
        legend.append("■", style=color)
        legend.append(f" {label}  ")
    console.print(Panel(stats + legend, title=f"[bold {P['blue']}]📊  ESTADÍSTICAS[/bold {P['blue']}]",
                        border_style=P["border"]))
    console.print(make_keys_panel("sleep"))
    console.print(f"\n[dim]  ←  mes anterior  ·  →  mes siguiente  ·  L  registrar sueño  ·  Q  volver[/dim]")
    while True:
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            break
        elif key == readchar.key.LEFT:
            nm, ny = (12, year - 1) if month == 1 else (month - 1, year)
            screen_sleep(data, ny, nm)
            return
        elif key == readchar.key.RIGHT:
            nm, ny = (1, year + 1) if month == 12 else (month + 1, year)
            screen_sleep(data, ny, nm)
            return
        elif key in ("l", "L"):
            _log_sleep(data)
            screen_sleep(data, year, month)
            return


def _log_sleep(data):
    console.print(f"\n  [{P['purple']}]😴  Registrar horas de sueño (máx. 10h)[/{P['purple']}]")
    existing = data["sleep"].get(_today())
    hours = ask_float_range(f"  [{P['blue']}]Horas dormidas (0.0 – 10.0)[/{P['blue']}]",
                            0.0, 10.0, default=existing if existing else 7.5)
    data["sleep"][_today()] = hours
    save_data(data)
    c = sleep_color(hours)
    msg = "¡Muy bien! 😴" if hours >= 7 else "Poco sueño ⚠" if hours < 6 else "Podría mejorar"
    console.print(f"  [bold {c}]{hours:.1f}h registradas — {msg}[/bold {c}]")
    _pause()


# ──────────────────────────────────────────────────── Objetivos ──

def screen_goals(data):
    period = "weekly"
    selected = 0
    while True:
        goals = [g for g in data.get("goals", []) if g["type"] == period]
        selected = max(0, min(selected, len(goals) - 1 if goals else 0))
        lbl, clr = PERIOD_UI[period]
        console.clear()
        console.print(make_header())
        _section("🎯  OBJETIVOS", P["orange"])
        tabs = Text("\n  ")
        for p in PERIODS:
            l, c = PERIOD_UI[p]
            nd = sum(1 for g in data.get("goals", []) if g["type"] == p and g["done"])
            nt = sum(1 for g in data.get("goals", []) if g["type"] == p)
            badge = f" {nd}/{nt}" if nt else " 0"
            if p == period:
                tabs.append(f"[ {l}{badge} ]", style=f"bold {c}")
            else:
                tabs.append(f"  {l}{badge}  ", style="dim")
            tabs.append("  ")
        console.print(tabs)
        console.print()
        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {clr}",
                      border_style=P["border"], expand=True)
        table.add_column("", width=2)
        table.add_column("Est", width=4, justify="center")
        table.add_column("Objetivo", min_width=32)
        table.add_column("Creado", width=12)
        table.add_column("Límite", width=12)
        for idx, g in enumerate(goals):
            is_sel = (idx == selected)
            cur = f"[bold {clr}]▶[/bold {clr}]" if is_sel else " "
            if g["done"]:
                status = f"[{P['green']}]✅[/{P['green']}]"
                name_t = Text(g["text"][:44], style=f"dim {P['muted']}")
            else:
                status = f"[{P['yellow']}]⬜[/{P['yellow']}]"
                name_t = Text(g["text"][:44], style=P["text"])
            dl_raw = g.get("deadline")
            if dl_raw and not g["done"] and date.fromisoformat(dl_raw) < date.today():
                dl = Text(dl_raw, style=f"bold {P['red']}")
            else:
                dl = Text(dl_raw or "—", style=P["muted"] if not dl_raw else P["text"])
            table.add_row(cur, status, name_t, g["created"], dl,
                          style=f"on {P['sel']}" if is_sel else "")
        if not goals:
            table.add_row("", "", "[dim]Sin objetivos · A para añadir[/dim]", "", "")
        done = sum(1 for g in goals if g["done"])
        total = len(goals)
        console.print(Panel(table,
                            title=f"[bold {clr}]{lbl}  [dim]({done}/{total} completados)[/dim][/bold {clr}]",
                            border_style=P["border"]))
        if goals and 0 <= selected < len(goals):
            g = goals[selected]
            if g.get("notes"):
                console.print(Panel(Text(f" {g['notes']}", style=P["text"]),
                                    title="[dim]◈  Nota del objetivo[/dim]",
                                    border_style=P["border"], padding=(0, 1)))
        console.print(make_keys_panel("goals"))
        console.print(f"\n[dim]  Tab cambiar período · A añadir · ↵ completar · E editar · D eliminar · Q volver[/dim]")
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            break
        elif key == readchar.key.UP:
            selected = max(0, selected - 1)
        elif key == readchar.key.DOWN:
            selected = min(len(goals) - 1 if goals else 0, selected + 1)
        elif key == "\t":
            period = PERIODS[(PERIODS.index(period) + 1) % len(PERIODS)]
            selected = 0
        elif key in ("\r", "\n", readchar.key.ENTER):
            if goals and 0 <= selected < len(goals):
                goals[selected]["done"] = not goals[selected]["done"]
                save_data(data)
        elif key in ("a", "A"):
            _add_goal(data, period)
        elif key in ("e", "E"):
            if goals and 0 <= selected < len(goals):
                _edit_goal(data, goals[selected])
        elif key in ("n", "N"):
            if goals and 0 <= selected < len(goals):
                _edit_goal_note(data, goals[selected])
        elif key in ("d", "D"):
            if goals and 0 <= selected < len(goals):
                g = goals[selected]
                if Confirm.ask(f"\n  [bold {P['red']}]¿Eliminar objetivo?[/bold {P['red']}]"):
                    data["goals"] = [x for x in data["goals"] if x["id"] != g["id"]]
                    save_data(data)
                    selected = max(0, selected - 1)


def _add_goal(data, period):
    lbl, clr = PERIOD_UI[period]
    console.print(f"\n  [{clr}]◈  Nuevo Objetivo — {lbl}[/{clr}]")
    console.print(_hr())
    text = Prompt.ask(f"  [{P['orange']}]Objetivo[/{P['orange']}]")
    if not text.strip():
        return
    console.print(f"  [dim]Fecha límite: AAAA-MM-DD (Enter para omitir)[/dim]")
    dl = Prompt.ask(f"  [{P['muted']}]Fecha límite[/{P['muted']}]", default="")
    if dl:
        try:
            date.fromisoformat(dl)
        except:
            dl = ""
            _err("Fecha inválida, se omite.")
    notes = Prompt.ask(f"  [{P['muted']}]Nota adicional (opcional)[/{P['muted']}]", default="")
    data["goals"].append({"id": data["next_goal_id"], "text": text.strip(), "type": period,
                          "done": False, "created": _today(), "deadline": dl or None,
                          "notes": notes.strip()})
    data["next_goal_id"] += 1
    save_data(data)
    console.print(f"  [{P['green']}]✅ Objetivo añadido.[/{P['green']}]")
    _pause()


def _edit_goal(data, goal):
    console.print(f"\n  [{P['orange']}]✏️  Editar Objetivo[/{P['orange']}]")
    console.print(_hr())
    console.print(f"  [dim]Confirma qué campos quieres modificar.[/dim]\n")
    console.print(f"  [bold]Texto actual:[/bold] {goal['text']}")
    if Confirm.ask("  ¿Cambiar texto?", default=False):
        nt = Prompt.ask(f"  [{P['orange']}]Nuevo texto[/{P['orange']}]", default=goal["text"])
        if nt.strip():
            goal["text"] = nt.strip()
    console.print(f"  [bold]Fecha límite actual:[/bold] {goal.get('deadline') or '—'}")
    if Confirm.ask("  ¿Cambiar fecha límite?", default=False):
        ndl = Prompt.ask(f"  [{P['muted']}]Nueva fecha (AAAA-MM-DD)[/{P['muted']}]",
                         default=goal.get("deadline", "") or "")
        if ndl:
            try:
                date.fromisoformat(ndl)
                goal["deadline"] = ndl
            except:
                _err("Fecha inválida, no se cambia.")
        else:
            goal["deadline"] = None
    console.print(f"  [bold]Nota actual:[/bold] {goal.get('notes') or '—'}")
    if Confirm.ask("  ¿Cambiar nota?", default=False):
        nn = Prompt.ask(f"  [{P['muted']}]Nueva nota[/{P['muted']}]", default=goal.get("notes", "") or "")
        goal["notes"] = nn.strip()
    done_lbl = "✅ Sí" if goal["done"] else "⬜ No"
    if Confirm.ask(f"  ¿Cambiar estado completado? (actual: {done_lbl})", default=False):
        goal["done"] = not goal["done"]
    save_data(data)
    console.print(f"  [{P['green']}]✅ Objetivo actualizado.[/{P['green']}]")
    _pause()


def _edit_goal_note(data, goal):
    console.print(f"\n  [{P['orange']}]📝  Nota — {goal['text'][:60]}[/{P['orange']}]")
    existing = (goal.get("notes", "") or "").strip()
    if existing:
        console.print(Panel(Text(f"\n{existing}\n", style=P["text"]),
                            title="[dim]◈  Nota actual[/dim]",
                            border_style=P["border"], padding=(0, 2)))
        t = Text("\n  ")
        t.append("[A]", style=f"bold {P['blue']}")
        t.append(" Añadir al final  ·  ", style=P["text"])
        t.append("[R]", style=f"bold {P['yellow']}")
        t.append(" Reemplazar  ·  ", style=P["text"])
        t.append("[D]", style=f"bold {P['red']}")
        t.append(" Borrar  ·  ", style=P["text"])
        t.append("Esc  Cancelar", style="dim")
        console.print(t)
        key = readchar.readkey()
        if key in ("a", "A"):
            addition = Prompt.ask(f"\n  [{P['muted']}]Añadir al final[/{P['muted']}]")
            if addition.strip():
                goal["notes"] = existing + "\n" + addition.strip()
                save_data(data)
                console.print(f"  [{P['green']}]✅ Nota actualizada.[/{P['green']}]")
            else:
                console.print(f"  [dim]Sin cambios.[/dim]")
        elif key in ("r", "R"):
            note = Prompt.ask(f"\n  [{P['muted']}]Nueva nota[/{P['muted']}]", default=existing)
            goal["notes"] = note.strip()
            save_data(data)
            console.print(f"  [{P['green']}]✅ Nota guardada.[/{P['green']}]")
        elif key in ("d", "D"):
            goal["notes"] = ""
            save_data(data)
            console.print(f"  [{P['yellow']}]Nota borrada.[/{P['yellow']}]")
        else:
            console.print(f"  [dim]Cancelado.[/dim]")
    else:
        note = Prompt.ask(f"  [{P['muted']}]Escribe la nota[/{P['muted']}]", default="")
        if note.strip():
            goal["notes"] = note.strip()
            save_data(data)
            console.print(f"  [{P['green']}]✅ Nota guardada.[/{P['green']}]")
        else:
            console.print(f"  [dim]Sin cambios.[/dim]")
    _pause()


# ───────────────────────────────────────────────────── Eventos ──

def _add_event(data):
    console.print(f"\n  [{P['yellow']}]◈  Nuevo Evento[/{P['yellow']}]")
    console.print(_hr())
    console.print(f"\n  Tipos: 1) 🎂 Cumpleaños  2) 📌 Evento  3) 🎉 Fiesta  4) 🏖 Día libre\n")
    t_idx = ask_int_range(f"  [{P['blue']}]Tipo (1-4)[/{P['blue']}]", 1, 4, default=2)
    type_keys = list(EVENT_TYPES.keys())
    etype = type_keys[t_idx - 1]
    ic, lbl_e, col, yearly_def = EVENT_TYPES[etype]
    title = Prompt.ask(f"  [{col}]{ic} Título[/{col}]")
    if not title.strip():
        return
    console.print(f"  [dim]Fecha: AAAA-MM-DD[/dim]")
    dt_str = Prompt.ask(f"  [{P['blue']}]Fecha[/{P['blue']}]", default=_today())
    try:
        date.fromisoformat(dt_str)
    except:
        _err("Fecha inválida.")
        _pause()
        return
    time_str = Prompt.ask(f"  [{P['muted']}]Hora (HH:MM, opcional)[/{P['muted']}]", default="")
    if time_str.strip() and len(time_str.strip()) != 5:
        time_str = ""
    notes = Prompt.ask(f"  [{P['muted']}]Notas (opcional)[/{P['muted']}]", default="")
    yearly = Confirm.ask(f"  ¿Repetir cada año?", default=yearly_def)
    data["events"].append({"id": data["next_event_id"], "title": title.strip(), "date": dt_str,
                           "type": etype, "yearly": yearly, "time": time_str.strip(),
                           "notes": notes.strip()})
    data["next_event_id"] += 1
    save_data(data)
    console.print(f"  [{P['green']}]✅ Evento añadido.[/{P['green']}]")
    _pause()


def _edit_event(data, ev):
    console.print(f"\n  [{P['yellow']}]✏️  Editar Evento[/{P['yellow']}]")
    console.print(_hr())
    ic, _, col, _ = EVENT_TYPES.get(ev["type"], EVENT_TYPES["event"])
    console.print(f"  [bold]Título actual:[/bold] {ev['title']}")
    if Confirm.ask("  ¿Cambiar título?", default=False):
        nt = Prompt.ask(f"  [{col}]Nuevo título[/{col}]", default=ev["title"])
        if nt.strip():
            ev["title"] = nt.strip()
    console.print(f"  [bold]Fecha actual:[/bold] {ev['date']}")
    if Confirm.ask("  ¿Cambiar fecha?", default=False):
        nd = Prompt.ask(f"  [{P['blue']}]Nueva fecha (AAAA-MM-DD)[/{P['blue']}]", default=ev["date"])
        try:
            date.fromisoformat(nd)
            ev["date"] = nd
        except:
            _err("Fecha inválida, no se cambia.")
    console.print(f"  [bold]Hora actual:[/bold] {ev.get('time') or '—'}")
    if Confirm.ask("  ¿Cambiar hora?", default=False):
        nt = Prompt.ask(f"  [{P['muted']}]Nueva hora (HH:MM)[/{P['muted']}]",
                        default=ev.get("time", "") or "")
        ev["time"] = nt.strip()
    console.print(f"  [bold]Notas actuales:[/bold] {ev.get('notes') or '—'}")
    if Confirm.ask("  ¿Cambiar notas?", default=False):
        nn = Prompt.ask(f"  [{P['muted']}]Nuevas notas[/{P['muted']}]",
                        default=ev.get("notes", "") or "")
        ev["notes"] = nn.strip()
    yearly_lbl = "Sí" if ev.get("yearly") else "No"
    if Confirm.ask(f"  ¿Cambiar repetición anual? (actual: {yearly_lbl})", default=False):
        ev["yearly"] = not ev.get("yearly")
    save_data(data)
    console.print(f"  [{P['green']}]✅ Evento actualizado.[/{P['green']}]")
    _pause()


def _render_events_all(data, selected):
    events = data.get("events", [])
    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {P['yellow']}",
                  border_style=P["border"], expand=True)
    table.add_column("", width=2)
    table.add_column("Tipo", width=14)
    table.add_column("Título", min_width=24)
    table.add_column("Fecha", width=12)
    table.add_column("Hora", width=7, justify="center")
    table.add_column("↺", width=3, justify="center")
    table.add_column("Notas", min_width=20)
    for idx, ev in enumerate(events):
        is_sel = (idx == selected)
        cur = f"[bold {P['yellow']}]▶[/bold {P['yellow']}]" if is_sel else " "
        ic, lbl_e, col, _ = EVENT_TYPES.get(ev["type"], EVENT_TYPES["event"])
        tipo = Text(f"{ic} {lbl_e}", style=f"bold {col}")
        yr = Text("↺", style=P["green"]) if ev.get("yearly") else Text("-", style="dim")
        notes_p = ev.get("notes", "")[:28] or "—"
        table.add_row(cur, tipo, ev["title"], ev["date"], ev.get("time") or "—", yr, notes_p,
                      style=f"on {P['sel']}" if is_sel else "")
    if not events:
        table.add_row("", "", "[dim]Sin eventos · A para añadir[/dim]", "", "", "", "")
    console.print(Panel(table,
                        title=f"[bold {P['yellow']}]🗓  TODOS LOS EVENTOS  [dim]({len(events)} total)[/dim][/bold {P['yellow']}]",
                        border_style=P["border"]))
    if events and 0 <= selected < len(events):
        ev = events[selected]
        if ev.get("notes"):
            console.print(Panel(Text(f" {ev['notes']}", style=P["text"]),
                                title="[dim]◈  Notas[/dim]", border_style=P["border"], padding=(0, 1)))
    return events


def _render_events_monthly(data, year, month):
    lbl = f"{_MESES[month-1].upper()} {year}"
    day_evs = _events_for_month(data, year, month)
    t = Text()
    if not day_evs:
        t.append("\n  Sin eventos este mes.\n", style="dim")
    else:
        for d, evs in day_evs:
            dow = _DIAS[date(year, month, d).weekday()][:3].upper()
            is_t = date(year, month, d) == date.today()
            day_style = f"bold {P['blue']}" if is_t else f"bold {P['muted']}"
            t.append(f"\n  {dow} {d:02d}  ", style=day_style)
            for i, ev in enumerate(evs):
                ic, lbl_e, col, _ = EVENT_TYPES.get(ev["type"], EVENT_TYPES["event"])
                yr_tag = " ↺" if ev.get("yearly") else ""
                time_tag = f"  {ev['time']}" if ev.get("time") else ""
                t.append(f"{ic} {ev['title']}{yr_tag}{time_tag}", style=f"bold {col}")
                if ev.get("notes"):
                    t.append(f"  — {ev['notes'][:40]}", style=f"dim {P['muted']}")
                if i < len(evs) - 1:
                    t.append("  ·  ", style=P["border"])
            t.append("\n")
    console.print(Panel(t, title=f"[bold {P['yellow']}]📅  EVENTOS — {lbl}[/bold {P['yellow']}]",
                        border_style=P["border"], padding=(0, 1)))


def _build_yearly_grid(data, year):
    grid = Layout()
    grid.split_column(Layout(name="top", ratio=1), Layout(name="bot", ratio=1))
    grid["top"].split_row(*[Layout(name=f"m{m}") for m in range(1, 7)])
    grid["bot"].split_row(*[Layout(name=f"m{m}") for m in range(7, 13)])
    for m in range(1, 13):
        day_evs = _events_for_month(data, year, m)
        lbl_m = _MESES[m - 1][:3].upper()
        is_cur = (m == date.today().month and year == date.today().year)
        t = Text(justify="center")
        t.append("\n")
        if not day_evs:
            t.append("sin eventos", style=f"dim {P['muted']}")
        else:
            for d, evs in day_evs[:4]:
                ic, _, col, _ = EVENT_TYPES.get(evs[0]["type"], EVENT_TYPES["event"])
                yr_tag = "↺" if evs[0].get("yearly") else ""
                t.append(f"{ic}{yr_tag} {d:02d} {evs[0]['title'][:9]}\n", style=col)
            if len(day_evs) > 4:
                t.append(f"+ {len(day_evs)-4} más…", style=f"dim {P['muted']}")
        border_col = P["blue"] if is_cur else P["border"]
        title_style = f"bold {P['yellow']}" if is_cur else f"bold {P['blue']}"
        panel = Panel(Align.center(t, vertical="middle"),
                      title=f"[{title_style}]{lbl_m}[/{title_style}]",
                      border_style=border_col)
        grid["top" if m <= 6 else "bot"][f"m{m}"].update(panel)
    return grid


def screen_events(data):
    selected = 0
    view = "all"
    year = date.today().year
    month = date.today().month
    VIEWS = ["all", "monthly", "yearly"]
    VIEW_LBL = {"all": "📋 Todos", "monthly": "📅 Mensual", "yearly": "📆 Anual"}

    def _make_tabs(cur_view):
        t = Text("  ")
        for v in VIEWS:
            if v == cur_view:
                t.append(f"[ {VIEW_LBL[v]} ]", style=f"bold {P['yellow']}")
            else:
                t.append(f"  {VIEW_LBL[v]}  ", style=f"dim {P['muted']}")
            t.append("  ")
        if cur_view == "monthly":
            t.append("←→ mes", style=f"dim {P['muted']}")
        elif cur_view == "yearly":
            t.append("←→ año", style=f"dim {P['muted']}")
        return t

    while True:
        events = data.get("events", [])
        selected = max(0, min(selected, len(events) - 1 if events else 0))
        hint_base = "  Tab: cambiar vista  ·  "
        if view == "all":
            hint_str = hint_base + "↑↓ navegar  ·  A añadir  ·  E editar  ·  D eliminar  ·  Q volver"
        else:
            hint_str = hint_base + "←→ navegar  ·  A añadir  ·  Q volver"
        hint_t = Text(hint_str, style=f"dim {P['muted']}")
        if view == "yearly":
            console.clear()
            grid = _build_yearly_grid(data, year)
            outer = Layout()
            outer.split_column(
                Layout(make_header(), name="hdr", size=3),
                Layout(Align.left(_make_tabs(view)), name="tabs", size=1),
                Layout(Align.center(Text(f"📆  EVENTOS — {year}", style=f"bold {P['yellow']}")),
                       name="title", size=1),
                Layout(grid, name="grid", ratio=1),
                Layout(hint_t, name="hint", size=1),
            )
            console.print(outer)
            flat_events = []
        else:
            console.clear()
            console.print(make_header())
            console.print(_make_tabs(view))
            console.print()
            if view == "all":
                flat_events = _render_events_all(data, selected)
            else:
                _render_events_monthly(data, year, month)
                flat_events = []
            console.print(hint_t)
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            break
        elif key == "\t":
            view = VIEWS[(VIEWS.index(view) + 1) % len(VIEWS)]
        elif view == "all":
            if key == readchar.key.UP:
                selected = max(0, selected - 1)
            elif key == readchar.key.DOWN:
                selected = min(len(events) - 1 if events else 0, selected + 1)
            elif key in ("a", "A"):
                _add_event(data)
            elif key in ("e", "E"):
                if events and 0 <= selected < len(events):
                    _edit_event(data, events[selected])
            elif key in ("d", "D"):
                if events and 0 <= selected < len(events):
                    if Confirm.ask(f"\n  [bold {P['red']}]¿Eliminar evento?[/bold {P['red']}]"):
                        data["events"] = [x for x in data["events"] if x["id"] != events[selected]["id"]]
                        save_data(data)
                        selected = max(0, selected - 1)
        elif view == "monthly":
            if key == readchar.key.LEFT:
                month, year = (12, year - 1) if month == 1 else (month - 1, year)
            elif key == readchar.key.RIGHT:
                month, year = (1, year + 1) if month == 12 else (month + 1, year)
            elif key in ("a", "A"):
                _add_event(data)
        elif view == "yearly":
            if key == readchar.key.LEFT:
                year -= 1
            elif key == readchar.key.RIGHT:
                year += 1
            elif key in ("a", "A"):
                _add_event(data)


# ──────────────────────────────────────────────── Heatmap anual ──

def screen_heatmap(data):
    habits = data["habits"]
    if not habits:
        return
    h_idx = 0
    while True:
        habit = habits[h_idx]
        hid = str(habit["id"])
        today = date.today()
        start = today - timedelta(days=363)
        start -= timedelta(days=start.weekday())
        end_sun = today + timedelta(days=6 - today.weekday())
        month_row = Text("    ")
        cur_col = start
        while cur_col <= end_sun:
            if cur_col.day <= 7:
                lbl = _MESES[cur_col.month - 1][:3].upper()
                month_row.append(f"{lbl:<6}", style=f"bold {P['blue']}")
            else:
                month_row.append("      ")
            cur_col += timedelta(weeks=1)
        DOW_LABELS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
        grid = Text()
        grid.append_text(month_row)
        grid.append("\n")
        for row in range(7):
            grid.append(f" {DOW_LABELS[row]} ", style=f"dim {P['muted']}")
            cur = start + timedelta(days=row)
            while cur <= end_sun:
                if cur <= today:
                    ds = cur.isoformat()
                    val = data["logs"].get(ds, {}).get(hid)
                    intensity = _heat_intensity(val, habit)
                    color = HEAT_COLORS[intensity]
                    grid.append("██", style=f"bold {color}")
                else:
                    grid.append("  ")
                cur += timedelta(weeks=1)
                grid.append(" ")
            grid.append("\n")
        legend = Text("\n  ")
        legend.append("Menos  ", style=f"dim {P['muted']}")
        for c in HEAT_COLORS:
            legend.append("██", style=f"bold {c}")
            legend.append(" ")
        legend.append("  Más", style=f"dim {P['muted']}")
        rate = get_rate(data, habit["id"], days=365)
        streak = get_streak(data, habit["id"])
        e_b, n_b, c_b = get_badge(streak)
        stats = Text()
        stats.append(f"\n  ◈ Hábito  ", style=P["muted"])
        stats.append(f"{habit['name']}", style=f"bold {habit.get('color', P['blue'])}")
        stats.append(f"   [{habit.get('type', 'bool')}]", style=f"dim {P['muted']}")
        stats.append(f"\n  ◈ Tasa anual  ", style=P["muted"])
        rc = P["green"] if rate >= 80 else P["yellow"] if rate >= 50 else P["red"]
        stats.append(f"{rate:.1f}%", style=f"bold {rc}")
        stats.append(f"   ◈ Racha  ", style=P["muted"])
        stats.append(f"🔥{streak}d  {e_b} {n_b}", style=f"bold {c_b}")
        n_h = len(habits)
        tab_row = Text("  ")
        for i, h in enumerate(habits):
            nm = h["name"][:12]
            if i == h_idx:
                tab_row.append(f"[{nm}]", style=f"bold {h.get('color', P['blue'])}")
            else:
                tab_row.append(f" {nm} ", style=f"dim {P['muted']}")
            tab_row.append(" ")
        layout = Layout()
        layout.split_column(
            Layout(make_header(), name="hdr", size=3),
            Layout(Panel(stats, border_style=P["border"], padding=(0, 1)), name="stats", size=5),
            Layout(Panel(grid + legend,
                         title=f"[bold {P['green']}]🌡  HEATMAP ANUAL — {habit['name']}[/bold {P['green']}]",
                         border_style=P["border"], padding=(0, 1)), name="grid", ratio=1),
            Layout(Panel(tab_row,
                         title=f"[bold {P['muted']}]Tab / ← → cambiar hábito  ({h_idx+1}/{n_h})  ·  Q volver[/bold {P['muted']}]",
                         border_style=P["border"], padding=(0, 0)), name="hint", size=3),
        )
        console.clear()
        console.print(layout)
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            break
        elif key in ("\t", readchar.key.RIGHT):
            h_idx = (h_idx + 1) % n_h
        elif key == readchar.key.LEFT:
            h_idx = (h_idx - 1) % n_h


# ────────────────────────────────────────────────── Reordenar ──

def screen_reorder(data):
    mode = "habits"
    selected = 0
    while True:
        console.clear()
        console.print(make_header())
        _section("🔀  REORDENAR", P["teal"])
        tabs = Text("\n  ")
        for m, mlbl in [("habits", "Hábitos"), ("categories", "Categorías")]:
            if m == mode:
                tabs.append(f"[ {mlbl} ]", style=f"bold {P['teal']}")
            else:
                tabs.append(f"  {mlbl}  ", style="dim")
            tabs.append("  ")
        tabs.append("  Tab: cambiar modo", style="dim")
        console.print(tabs)
        console.print()
        if mode == "categories":
            items = data.get("categories", DEFAULT_CATS)[:]
            selected = max(0, min(selected, len(items) - 1))
            table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {P['teal']}",
                          border_style=P["border"])
            table.add_column("", width=2)
            table.add_column("#", width=4, justify="right")
            table.add_column("Categoría", min_width=22)
            table.add_column("Hábitos", width=10, justify="center")
            for idx, cat in enumerate(items):
                is_sel = (idx == selected)
                cur = f"[bold {P['teal']}]▶[/bold {P['teal']}]" if is_sel else " "
                n_h = sum(1 for h in data["habits"] if h.get("category") == cat)
                table.add_row(cur, str(idx + 1), cat, str(n_h),
                              style=f"on {P['sel']}" if is_sel else "")
            display_n = len(items)
            habit_items = []
        else:
            habit_items = []
            for cat in data.get("categories", DEFAULT_CATS):
                for h in data["habits"]:
                    if h.get("category") == cat:
                        habit_items.append((cat, h))
            for h in data["habits"]:
                if h.get("category") not in data.get("categories", DEFAULT_CATS):
                    habit_items.append(("Otros", h))
            selected = max(0, min(selected, len(habit_items) - 1 if habit_items else 0))
            table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {P['teal']}",
                          border_style=P["border"])
            table.add_column("", width=2)
            table.add_column("#", width=4, justify="right")
            table.add_column("Categoría", width=13)
            table.add_column("Hábito", min_width=22)
            table.add_column("Tipo", width=8, justify="center")
            for idx, (cat, h) in enumerate(habit_items):
                is_sel = (idx == selected)
                cur = f"[bold {P['teal']}]▶[/bold {P['teal']}]" if is_sel else " "
                table.add_row(cur, str(idx + 1), f"[dim]{cat}[/dim]", h["name"],
                              f"[dim]{h.get('type', 'bool')}[/dim]",
                              style=f"on {P['sel']}" if is_sel else "")
            display_n = len(habit_items)
            items = []
        console.print(Panel(table,
                            title=f"[bold {P['teal']}]🔀  {'CATEGORÍAS' if mode == 'categories' else 'HÁBITOS'}[/bold {P['teal']}]",
                            border_style=P["border"]))
        console.print(make_keys_panel("reorder"))
        if mode == "habits":
            console.print(f"[dim]  Los hábitos solo se mueven dentro de su categoría. Usa E para cambiar de categoría.[/dim]")
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            save_data(data)
            break
        elif key == "\t":
            mode = "categories" if mode == "habits" else "habits"
            selected = 0
        elif key == readchar.key.UP:
            selected = max(0, selected - 1)
        elif key == readchar.key.DOWN:
            selected = min(display_n - 1, selected + 1) if display_n else 0
        elif key in ("w", "W") and selected > 0:
            if mode == "categories":
                cats = data["categories"]
                cats[selected], cats[selected - 1] = cats[selected - 1], cats[selected]
                selected -= 1
            else:
                if not habit_items:
                    continue
                cat_cur, h_cur = habit_items[selected]
                cat_prev, h_prev = habit_items[selected - 1]
                if cat_cur == cat_prev:
                    ic = next(i for i, h in enumerate(data["habits"]) if h["id"] == h_cur["id"])
                    ip = next(i for i, h in enumerate(data["habits"]) if h["id"] == h_prev["id"])
                    data["habits"][ic], data["habits"][ip] = data["habits"][ip], data["habits"][ic]
                    selected -= 1
                else:
                    _err("Solo puedes mover hábitos dentro de su categoría.")
                    _pause()
        elif key in ("s", "S") and display_n and selected < display_n - 1:
            if mode == "categories":
                cats = data["categories"]
                cats[selected], cats[selected + 1] = cats[selected + 1], cats[selected]
                selected += 1
            else:
                if not habit_items:
                    continue
                cat_cur, h_cur = habit_items[selected]
                cat_nxt, h_nxt = habit_items[selected + 1]
                if cat_cur == cat_nxt:
                    ic = next(i for i, h in enumerate(data["habits"]) if h["id"] == h_cur["id"])
                    ix = next(i for i, h in enumerate(data["habits"]) if h["id"] == h_nxt["id"])
                    data["habits"][ic], data["habits"][ix] = data["habits"][ix], data["habits"][ic]
                    selected += 1
                else:
                    _err("Solo puedes mover hábitos dentro de su categoría.")
                    _pause()


# ──────────────────────────────────────── Formulario de hábitos ──

def form_habit(data, existing=None):
    editing = existing is not None
    title = "✏️  Editar Hábito" if editing else "➕  Nuevo Hábito"
    console.clear()
    console.print(make_header())
    _section(title, P["green"])
    if editing:
        console.print(f"\n  [dim]Confirma qué campos quieres modificar. Enter = mantener actual.[/dim]\n")
    cats = data.get("categories", DEFAULT_CATS)
    if editing:
        console.print(f"  [bold]Nombre actual:[/bold] [{P['green']}]{existing['name']}[/{P['green']}]")
        if Confirm.ask("  ¿Cambiar nombre?", default=False):
            nm = Prompt.ask(f"  [{P['green']}]Nuevo nombre[/{P['green']}]")
            if nm.strip():
                existing["name"] = nm.strip()
        name = existing["name"]
    else:
        name = Prompt.ask(f"\n  [{P['green']}]Nombre del hábito[/{P['green']}]")
        if not name.strip():
            _err("Nombre vacío.")
            _pause()
            return
    if editing:
        console.print(f"\n  [bold]Categoría actual:[/bold] [{P['teal']}]{existing.get('category', '—')}[/{P['teal']}]")
        change_cat = Confirm.ask("  ¿Cambiar categoría?", default=False)
    else:
        change_cat = True
    if change_cat:
        console.print(f"\n  [bold]Categorías disponibles:[/bold]")
        for i, c in enumerate(cats, 1):
            console.print(f"    [{P['blue']}]{i}[/{P['blue']}]. {c}")
        console.print(f"    [{P['blue']}]{len(cats)+1}[/{P['blue']}]. [dim]+ Nueva categoría…[/dim]")
        def_ci = (cats.index(existing["category"]) + 1
                  if editing and existing.get("category") in cats else 1)
        ci = ask_int_range(f"  [{P['blue']}]Categoría (1-{len(cats)+1})[/{P['blue']}]",
                           1, len(cats) + 1, default=def_ci)
        if ci == len(cats) + 1:
            nc = Prompt.ask(f"  [{P['teal']}]Nombre de nueva categoría[/{P['teal']}]")
            if nc.strip():
                data["categories"].append(nc.strip())
                category = nc.strip()
            else:
                category = cats[0]
        else:
            category = cats[ci - 1]
        if editing:
            existing["category"] = category
    else:
        category = existing.get("category", cats[0]) if editing else cats[0]
    type_list = list(SECTION_TYPES.items())
    keys_list = list(SECTION_TYPES.keys())
    if editing:
        console.print(f"\n  [bold]Tipo actual:[/bold] [{P['blue']}]{existing.get('type', 'boolean')}[/{P['blue']}]")
        change_type = Confirm.ask("  ¿Cambiar tipo?", default=False)
    else:
        change_type = True
    if change_type:
        console.print(f"\n  [bold]Tipos:[/bold]")
        for i, (k, v) in enumerate(type_list, 1):
            console.print(f"    [{P['blue']}]{i}[/{P['blue']}]. {v}")
        def_ti = (keys_list.index(existing["type"]) + 1
                  if editing and existing.get("type") in keys_list else 1)
        ti = ask_int_range(f"  [{P['blue']}]Tipo (1-{len(type_list)})[/{P['blue']}]",
                           1, len(type_list), default=def_ti)
        htype = type_list[ti - 1][0]
        if editing:
            existing["type"] = htype
    else:
        htype = existing.get("type", "boolean") if editing else "boolean"
    cur_target = existing.get("target") if editing else None
    if htype == "counter":
        if editing:
            console.print(f"\n  [bold]Meta diaria actual:[/bold] [{P['teal']}]{cur_target or '—'}[/{P['teal']}]")
            chg = Confirm.ask("  ¿Cambiar meta?", default=False)
        else:
            chg = True
        if chg:
            target = ask_int_range(f"  [{P['teal']}]Meta diaria[/{P['teal']}]", 1, 99999,
                                   default=cur_target or 8)
            if editing:
                existing["target"] = target
        else:
            target = cur_target
    elif htype == "rating":
        if editing:
            console.print(f"\n  [bold]Escala actual:[/bold] [{P['yellow']}]{cur_target or 5}[/{P['yellow']}]")
            chg = Confirm.ask("  ¿Cambiar escala?", default=False)
        else:
            chg = True
        if chg:
            target = ask_int_range(f"  [{P['yellow']}]Escala máxima (2-10)[/{P['yellow']}]", 2, 10,
                                   default=cur_target or 5)
            if editing:
                existing["target"] = target
        else:
            target = cur_target
    else:
        target = None
    if editing:
        cc = existing.get("color", "")
        cn = next((n for hx, n in HABIT_COLORS if hx == cc), "?")
        console.print(f"\n  [bold]Color actual:[/bold] [{cc}]■[/{cc}] {cn}")
        chg_col = Confirm.ask("  ¿Cambiar color?", default=False)
    else:
        chg_col = True
    if chg_col:
        console.print(f"\n  [bold]Colores:[/bold]")
        for i, (hx, nm) in enumerate(HABIT_COLORS, 1):
            console.print(f"    [{P['blue']}]{i}[/{P['blue']}]. [{hx}]■[/{hx}] {nm}")
        def_col = 3
        if editing:
            for i, (hx, _) in enumerate(HABIT_COLORS, 1):
                if hx == existing.get("color"):
                    def_col = i
                    break
        ci = ask_int_range(f"  [{P['blue']}]Color (1-{len(HABIT_COLORS)})[/{P['blue']}]",
                           1, len(HABIT_COLORS), default=def_col)
        color = HABIT_COLORS[ci - 1][0]
        if editing:
            existing["color"] = color
    else:
        color = existing.get("color", P["blue"]) if editing else P["blue"]
    if not editing:
        data["habits"].append({"id": data["next_id"], "name": name.strip(), "created": _today(),
                               "color": color, "type": htype, "target": target,
                               "category": category})
        data["next_id"] += 1
    save_data(data)
    verb = "actualizado" if editing else f"«{name.strip()}» añadido en {category}"
    console.print(f"\n  [{P['green']}]✅ Hábito {verb}.[/{P['green']}]")
    _pause()


# ──────────────────────────────────── Acciones: check / borrar / exportar ──

def action_check(data, habit, silent=False):
    ds = _today()
    hid = str(habit["id"])
    htype = habit.get("type", "boolean")
    tgt = habit.get("target")
    if ds not in data["logs"]:
        data["logs"][ds] = {}
    val = data["logs"][ds].get(hid)
    done = _is_done(val, habit)
    if not silent:
        console.print(f"\n  [{P['teal']}]◈  {habit['name']}[/{P['teal']}]")
        console.print(_hr())
    if htype == "boolean":
        prev_val = data["logs"][ds].get(hid)
        data["logs"][ds][hid] = not done
        save_data(data)
        return {"ds": ds, "hid": hid, "prev": prev_val}
    elif htype == "counter":
        console.print(f"  [dim]Meta: {tgt or '?'}   Actual: {val or 0}[/dim]")
        v = ask_int_range(f"  [{P['teal']}]Cantidad[/{P['teal']}]", 0, 99999, default=int(val or 0))
        data["logs"][ds][hid] = v
        color = P["green"] if (tgt and v >= tgt) else P["yellow"] if tgt else P["teal"]
        console.print(f"  [bold {color}]🔢 {v}/{tgt or '?'}[/bold {color}]")
        _pause()
    elif htype == "rating":
        max_r = tgt or 5
        scale = "  ".join(f"{i}{'⭐'*i}" for i in range(1, max_r + 1))
        console.print(f"  {scale}")
        v = ask_int_range(f"  [{P['yellow']}]Valoración (1-{max_r})[/{P['yellow']}]", 1, max_r,
                          default=int(val or 1))
        data["logs"][ds][hid] = v
        console.print(f"  [{P['green']}]{'⭐'*v} guardado.[/{P['green']}]")
        _pause()
    elif htype == "note":
        current = val or ""
        if current:
            console.print(f"  [dim]Actual: {current[:60]}{'…' if len(current) > 60 else ''}[/dim]")
        v = Prompt.ask(f"  [{P['purple']}]Nota de hoy[/{P['purple']}]", default=current)
        if v.strip():
            data["logs"][ds][hid] = v.strip()
            console.print(f"  [{P['green']}]📝 Nota guardada.[/{P['green']}]")
        _pause()
    save_data(data)


def screen_mood_history(data):
    """Pantalla de historial de estado de ánimo — estilo heatmap + selector."""
    WEEKS = 20
    DOW_LABELS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]

    def _render_mood_screen():
        console.clear()
        console.print(make_header())
        _section("💭  ESTADO DE ÁNIMO", P["purple"])

        today = date.today()
        # Inicio: lunes de hace WEEKS semanas
        start = today - timedelta(days=today.weekday()) - timedelta(weeks=WEEKS - 1)
        end_sun = today + timedelta(days=6 - today.weekday())
        mood_data = data.get("mood", {})

        # ── Cabecera de meses ───────────────────────────────────────
        month_row = Text("     ")
        cur_col = start
        while cur_col <= end_sun:
            if cur_col.day <= 7:
                lbl = _MESES[cur_col.month - 1][:3].upper()
                month_row.append(f"{lbl:<5}", style=f"bold {P['blue']}")
            else:
                month_row.append("     ")
            cur_col += timedelta(weeks=1)

        # ── Grid de heatmap ─────────────────────────────────────────
        grid = Text()
        grid.append_text(month_row)
        grid.append("\n")
        for row in range(7):
            grid.append(f" {DOW_LABELS[row]} ", style=f"dim {P['muted']}")
            cur = start + timedelta(days=row)
            while cur <= end_sun:
                if cur <= today:
                    ds = cur.isoformat()
                    idx = mood_data.get(ds)
                    if idx is not None and 0 <= idx < len(MOODS):
                        _, _, _, color = MOODS[idx]
                        grid.append("██", style=f"bold {color}")
                    else:
                        grid.append("░░", style=f"dim {P['border']}")
                else:
                    grid.append("  ")
                cur += timedelta(weeks=1)
                grid.append(" ")
            grid.append("\n")

        console.print(Panel(grid,
                            title=f"[bold {P['purple']}]📅  Últimas {WEEKS} semanas[/bold {P['purple']}]",
                            border_style=P["border"], padding=(0, 1)))

        # ── Leyenda de moods ────────────────────────────────────────
        legend = Text("\n  ")
        for i, (emoji, nombre, _, color) in enumerate(MOODS):
            legend.append(f"  [{i+1}] ", style=f"dim {P['muted']}")
            legend.append("██ ", style=f"bold {color}")
            legend.append(f"{emoji} {nombre}  ", style=color)
        console.print(legend)

        # ── Estado de hoy y stats ───────────────────────────────────
        console.print()
        today_idx = mood_data.get(today.isoformat())
        if today_idx is not None:
            em, nm, desc, cl = MOODS[today_idx]
            console.print(f"  Hoy: ", end="")
            console.print(f"{em}  {nm}", style=f"bold {cl}", end="")
            console.print(f"  —  {desc}", style=f"dim {P['text']}")
        else:
            console.print(f"  [dim {P['muted']}]Hoy sin registrar · pulsa 1-5 o ↵ para añadir[/dim {P['muted']}]")

        # ── Stats rápidas ───────────────────────────────────────────
        all_moods = [v for v in mood_data.values() if isinstance(v, int) and 0 <= v < len(MOODS)]
        if all_moods:
            from collections import Counter
            most = Counter(all_moods).most_common(1)[0][0]
            em_m, nm_m, _, cl_m = MOODS[most]
            console.print(f"  [dim {P['muted']}]Más frecuente: [/dim {P['muted']}]", end="")
            console.print(f"{em_m} {nm_m}", style=f"bold {cl_m}", end="")
            console.print(f"  [dim {P['muted']}]({len(all_moods)} días registrados)[/dim {P['muted']}]")

        console.print(f"\n  [dim]↵ / 1-5 Añadir de hoy  ·  Q Volver[/dim]")

    while True:
        _render_mood_screen()
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            break
        elif key in "12345":
            idx = int(key) - 1
            data.setdefault("mood", {})[_today()] = idx
            save_data(data)
            em, nm, _, cl = MOODS[idx]
            console.print(f"\n  [{cl}]{em}  {nm} — guardado.[/{cl}]")
            import time; time.sleep(0.6)
        elif key in ("\r", "\n", readchar.key.ENTER):
            # Abrir selector interactivo
            screen_mood(data)


def screen_mood(data):
    """Pantalla de selección de estado de ánimo."""
    selected = 0
    # Pre-seleccionar el estado de hoy si ya existe
    today_mood = data.get("mood", {}).get(_today())
    if today_mood is not None:
        selected = today_mood
    while True:
        console.clear()
        console.print(make_header())
        _section("💭  ESTADO DE ÁNIMO", P["purple"])
        console.print()
        for i, (emoji, nombre, desc, color) in enumerate(MOODS):
            is_sel = (i == selected)
            cur = f"[bold {color}] ▶ [/bold {color}]" if is_sel else "   "
            bg = f" on {P['sel']}" if is_sel else ""
            line = Text()
            line.append(cur)
            line.append(f" {emoji}  ", style=color + bg)
            line.append(f"{nombre:<14}", style=f"bold {color}{bg}")
            line.append(f"  {desc}", style=f"dim {P['text']}{bg}")
            console.print(line)
            console.print()
        # Mostrar el registrado hoy si existe
        if today_mood is not None:
            em, nm, _, cl = MOODS[today_mood]
            console.print(f"  [dim]Hoy: [{cl}]{em} {nm}[/{cl}][/dim]\n")
        console.print(f"  [dim {P['muted']}]↑↓ Navegar  ·  ↵ Guardar  ·  Q Volver sin guardar[/dim {P['muted']}]")
        key = readchar.readkey()
        if key in ("q", "Q", "\x1b"):
            break
        elif key == readchar.key.UP:
            selected = (selected - 1) % len(MOODS)
        elif key == readchar.key.DOWN:
            selected = (selected + 1) % len(MOODS)
        elif key in ("\r", "\n", readchar.key.ENTER):
            data.setdefault("mood", {})[_today()] = selected
            save_data(data)
            today_mood = selected
            em, nm, _, cl = MOODS[selected]
            console.print(f"\n  [{cl}]{em}  {nm} — guardado.[/{cl}]")
            import time; time.sleep(0.7)
            break
        # Teclas numéricas 1-5 para selección rápida
        elif key in "12345":
            idx = int(key) - 1
            selected = idx
            data.setdefault("mood", {})[_today()] = selected
            save_data(data)
            today_mood = selected
            em, nm, _, cl = MOODS[selected]
            console.print(f"\n  [{cl}]{em}  {nm} — guardado.[/{cl}]")
            import time; time.sleep(0.7)
            break


def action_delete(data, habit):
    if Confirm.ask(f"\n  [bold {P['red']}]¿Eliminar «{habit['name']}»?[/bold {P['red']}]"):
        data["habits"] = [h for h in data["habits"] if h["id"] != habit["id"]]
        save_data(data)
        console.print(f"  [{P['green']}]Eliminado.[/{P['green']}]")
        _pause()
        return True
    return False


def _quick_counter(data, habit, delta):
    ds = _today()
    hid = str(habit["id"])
    if ds not in data["logs"]:
        data["logs"][ds] = {}
    val = max(0, int(data["logs"][ds].get(hid) or 0) + delta)
    data["logs"][ds][hid] = val
    save_data(data)


def action_export(data):
    console.clear()
    console.print(make_header())
    _section("💾  EXPORTAR DATOS", P["purple"])
    console.print(f"\n  [{P['blue']}]1[/{P['blue']}]. JSON\n  [{P['blue']}]2[/{P['blue']}]. CSV"
                  f"\n  [{P['blue']}]3[/{P['blue']}]. SQLite\n  [{P['blue']}]0[/{P['blue']}]. Cancelar\n")
    choice = ask_int_range(f"  [{P['purple']}]Formato (0-3)[/{P['purple']}]", 0, 3)
    if choice == 0:
        return
    names = {1: "habits_export.json", 2: "habits_export.csv", 3: "habits_export.db"}
    path = Prompt.ask(f"  [{P['purple']}]Nombre de archivo[/{P['purple']}]", default=names[choice])
    try:
        if choice == 1:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            p = path
        elif choice == 2:
            hmap = {str(h["id"]): h["name"] for h in data["habits"]}
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Fecha", "Habit ID", "Hábito", "Tipo", "Valor"])
                for ds, entries in sorted(data["logs"].items()):
                    for hid, val in entries.items():
                        h = next((x for x in data["habits"] if str(x["id"]) == hid), {})
                        w.writerow([ds, hid, hmap.get(hid, "?"), h.get("type", "boolean"), val])
            p = path
        else:
            conn = sqlite3.connect(path)
            c = conn.cursor()
            for ddl in [
                "CREATE TABLE IF NOT EXISTS habits(id INT,name TEXT,created TEXT,color TEXT,type TEXT,target TEXT,category TEXT)",
                "CREATE TABLE IF NOT EXISTS logs(date TEXT,habit_id INT,value TEXT)",
                "CREATE TABLE IF NOT EXISTS sleep(date TEXT,hours REAL)",
                "CREATE TABLE IF NOT EXISTS journal(date TEXT,entry TEXT)",
                "CREATE TABLE IF NOT EXISTS goals(id INT,text TEXT,type TEXT,done INT,created TEXT,deadline TEXT,notes TEXT)",
            ]:
                c.execute(ddl)
            for tbl in ("habits", "logs", "sleep", "journal", "goals"):
                c.execute(f"DELETE FROM {tbl}")
            for h in data["habits"]:
                c.execute("INSERT INTO habits VALUES(?,?,?,?,?,?,?)",
                          (h["id"], h["name"], h.get("created", ""), h.get("color", ""),
                           h.get("type", "boolean"), str(h.get("target", "")), h.get("category", "")))
            for ds, entries in data["logs"].items():
                for hid, val in entries.items():
                    c.execute("INSERT INTO logs VALUES(?,?,?)", (ds, int(hid), str(val)))
            for ds, hours in data.get("sleep", {}).items():
                c.execute("INSERT INTO sleep VALUES(?,?)", (ds, hours))
            for ds, entry in data.get("journal", {}).items():
                c.execute("INSERT INTO journal VALUES(?,?)", (ds, entry))
            for g in data.get("goals", []):
                c.execute("INSERT INTO goals VALUES(?,?,?,?,?,?,?)",
                          (g["id"], g["text"], g["type"], int(g["done"]), g["created"],
                           g.get("deadline", ""), g.get("notes", "")))
            conn.commit()
            conn.close()
            p = path
        console.print(f"\n  [{P['green']}]✅ Exportado → {Path(p).resolve()}[/{P['green']}]")
    except Exception as err:
        _err(str(err))
    _pause()
