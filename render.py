#!/usr/bin/env python3
"""Funciones de renderizado: panels, widgets y layouts de la pantalla principal."""
from datetime import date, timedelta
from calendar import monthrange
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.rule import Rule
from rich import box
from constants import (P, BADGES, SPARKS, HABIT_COLORS, SLEEP_COLORS, EVENT_TYPES,
                       HEAT_COLORS, _DIAS, _MESES, console)
from data import (overall_today, weekly_stats, get_streak, get_rate, get_badge,
                  sparkline_vals, make_spark, sleep_color, _build_ordered, _is_done,
                  _event_matches, _period_rate, _avg_rate_month, _heat_intensity)


def _hr(c=None):
    return Rule(style=c or P["border"], characters="─")


def _err(m):
    console.print(f"  [{P['red']}]⚠  {m}[/{P['red']}]")


def _pause():
    console.input(f"\n[dim]  ↵ Enter para continuar…[/dim]")


def _section(title, color=None):
    c = color or P["blue"]
    console.print(Rule(f"[bold {c}] ◈  {title}  ◈ [/bold {c}]", style=P["border"], characters="─"))


def sleep_bar_text(hours, width=10):
    filled = min(width, int(hours / 10 * width))
    color = sleep_color(hours)
    t = Text()
    t.append("█" * filled, style=f"bold {color}")
    t.append("░" * (width - filled), style="dim")
    t.append(f" {hours:.1f}h", style=color)
    return t


def pct_bar(pct, width=10):
    filled = int(pct / 100 * width)
    color = P["green"] if pct >= 80 else P["yellow"] if pct >= 50 else P["red"]
    t = Text()
    t.append("█" * filled, style=f"bold {color}")
    t.append("░" * (width - filled), style="dim")
    t.append(f" {pct:4.0f}%", style=color)
    return t


def mini_ring(pct):
    filled = int(pct / 10)
    color = P["green"] if pct >= 80 else P["yellow"] if pct >= 50 else P["red"]
    t = Text()
    t.append("●" * filled, style=f"bold {color}")
    t.append("○" * (10 - filled), style="dim")
    return t


def make_header():
    today = date.today()
    fecha = f"{_DIAS[today.weekday()]}, {today.day:02d} {_MESES[today.month-1]} {today.year}".upper()
    t = Text()
    t.append("┤ ", style=P["border"])
    t.append("🎯  HABIT TRACKER  v3", style="bold white")
    t.append(" ├── ", style=P["border"])
    t.append(fecha, style=f"bold {P['blue']}")
    t.append(" ──", style=P["border"])
    return Panel(Align.center(t), style=P["blue"], box=box.DOUBLE_EDGE, padding=(0, 1))


def _today_str():
    return date.today().isoformat()


def make_today_strip(data):
    from data import _today
    comp, total, pct = overall_today(data)
    c = P["green"] if pct >= 80 else P["yellow"] if pct >= 50 else P["red"]
    sl_h = data.get("sleep", {}).get(_today())
    gd = sum(1 for g in data.get("goals", []) if g["done"] and g["type"] == "weekly")
    gt = sum(1 for g in data.get("goals", []) if g["type"] == "weekly")
    j = bool(data.get("journal", {}).get(_today()))
    t = Text()
    t.append(f" 📋 {comp}/{total} ({pct:.0f}%)", style=f"bold {c}")
    t.append("  ┃  ", style=P["border"])
    sl_str = f"{sl_h:.1f}h" if sl_h else "—"
    sc = sleep_color(sl_h) if sl_h else P["muted"]
    t.append(f"😴 {sl_str}", style=f"bold {sc}")
    t.append("  ┃  ", style=P["border"])
    t.append(f"🎯 {gd}/{gt} sem", style=P["orange"])
    t.append("  ┃  ", style=P["border"])
    t.append(f"📓 {'✅' if j else '⬜'} diario", style=P["pink"])
    if total == 0:
        msg = "  Sin hábitos · A para añadir"
    elif pct == 100:
        msg = "  🎉  ¡Todos completados! ¡Gran día!"
    elif pct >= 50:
        msg = f"  💪  {total-comp} pendiente(s) — ¡Sigue así!"
    elif comp > 0:
        msg = f"  🔥  {total-comp} pendiente(s) — ¡Aún puedes lograrlo!"
    else:
        msg = f"  🌅  {total} hábito(s) por completar — ¡Empieza el día!"
    t.append(f"\n{msg}", style=f"bold {c}")
    return Panel(Align.center(t), border_style=P["border"], padding=(0, 0))


def make_habits_panel(data, selected_idx, scroll=0, row_budget=None):
    """Renderiza el panel de hábitos con scroll virtual.

    ``row_budget`` es el nº total de filas disponibles para el contenido
    de la tabla (hábitos + cabeceras de categoría + indicadores de scroll).
    Cada fila —sea hábito o cabecera de categoría— consume 1 unidad del
    presupuesto, por lo que el resultado nunca desbordará el espacio del panel.
    """
    from data import _today
    ds = _today()
    ordered = _build_ordered(data)

    # ── Presupuesto de filas ────────────────────────────────────────
    total_habits = sum(1 for k, _, _ in ordered if k == "HABIT")
    if row_budget is None:
        row_budget = total_habits + 50          # sin límite efectivo
    scroll = max(0, scroll)

    # Reservamos 1 fila para el indicador ↓ (puede que no se use,
    # pero así garantizamos que nunca sobrepasamos el presupuesto).
    content_budget = max(2, row_budget - 1)
    if scroll > 0:
        content_budget -= 1                     # 1 fila para el indicador ↑

    # Pre-pase: qué hábitos e índices entran en la ventana visible
    # Cada nueva categoría cuesta 1 fila (cabecera); cada hábito cuesta 1.
    visible_idxs: list[int] = []
    seen_cats_pass: dict = {}
    hi = 0
    rows_used = 0
    for kind, cat, h in ordered:
        if kind != "HABIT":
            continue
        if hi < scroll:
            hi += 1
            continue
        cat_cost = 1 if cat not in seen_cats_pass else 0
        if rows_used + cat_cost + 1 > content_budget:
            break
        seen_cats_pass[cat] = True
        rows_used += cat_cost + 1
        visible_idxs.append(hi)
        hi += 1

    visible_set = set(visible_idxs)
    last_visible_idx = visible_idxs[-1] if visible_idxs else scroll - 1

    # ── Construcción de la tabla ────────────────────────────────────
    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style=f"bold {P['blue']}",
                  border_style=P["border"], expand=True)
    table.add_column("", width=2)
    table.add_column("Hábito", min_width=17)
    table.add_column("Cat", width=9, no_wrap=True)
    table.add_column("Tipo", width=6, justify="center")
    table.add_column("Hoy", width=8, justify="center")
    table.add_column("🔥", width=4, justify="center")
    table.add_column("Badge", width=12, justify="center")
    table.add_column("Spark", width=22)
    table.add_column("Tasa", width=11)
    type_lbl = {
        "boolean": f"[{P['blue']}]bool[/{P['blue']}]",
        "counter": f"[{P['teal']}]cnt[/{P['teal']}]",
        "rating": f"[{P['yellow']}]rate[/{P['yellow']}]",
        "note": f"[{P['purple']}]note[/{P['purple']}]",
    }

    # Indicador scroll ↑
    if scroll > 0:
        table.add_row("", f"[dim]  ↑  {scroll} hábito(s) más arriba[/dim]",
                      "", "", "", "", "", "", "")

    habit_list, habit_idx = [], 0
    for kind, cat, h in ordered:
        if kind == "CAT":
            if cat in seen_cats_pass:
                n_cat = sum(1 for k, c, _ in ordered if k == "HABIT" and c == cat)
                lbl = (f"[bold {P['teal']}]╸ {cat.upper()}[/bold {P['teal']}]"
                       f" [dim]({n_cat})[/dim]")
                table.add_row("", lbl, "", "", "", "", "", "", "",
                              style=f"on {P['surf']}")
        else:
            if habit_idx in visible_set:
                is_sel = (habit_idx == selected_idx)
                val = data["logs"].get(ds, {}).get(str(h["id"]))
                done = _is_done(val, h)
                streak = get_streak(data, h["id"])
                rate = get_rate(data, h["id"])
                e_b, n_b, c_b = get_badge(streak)
                sparks = make_spark(sparkline_vals(data, h["id"]))
                htype = h.get("type", "boolean")
                target = h.get("target")
                if htype == "boolean":
                    tv = "✅" if done else "⬜"
                elif htype == "counter":
                    tv = f"{val or 0}/{target or '?'}"
                elif htype == "rating":
                    tv = "⭐" * int(val or 0) or "—"
                elif htype == "note":
                    tv = "📝" if done else "—"
                else:
                    tv = str(val or "—")
                cursor = f"[bold {P['blue']}]▶[/bold {P['blue']}]" if is_sel else " "
                rs = f"on {P['sel']}" if is_sel else ""
                sc_t = Text(str(streak),
                            style=f"bold {P['orange']}" if streak >= 10
                            else f"{P['yellow']}" if streak > 0 else "dim")
                table.add_row(
                    cursor, h["name"], f"[dim]{h.get('category', '')[:8]}[/dim]",
                    type_lbl.get(htype, htype), tv, sc_t,
                    Text(f"{e_b} {n_b}", style=f"bold {c_b}"),
                    Text(sparks, style=P["teal"] if done else P["muted"]),
                    pct_bar(rate, 8), style=rs)
            # habit_list recoge TODOS para mantener los índices correctos en main.py
            habit_list.append(h)
            habit_idx += 1

    # Indicador scroll ↓
    remaining = total_habits - (last_visible_idx + 1)
    if remaining > 0:
        table.add_row("", f"[dim]  ↓  {remaining} hábito(s) más abajo[/dim]",
                      "", "", "", "", "", "", "")

    if not data["habits"]:
        table.add_row("", "[dim]Sin hábitos · A para añadir[/dim]",
                      "", "", "", "", "", "", "")

    return (Panel(table, title=f"[bold {P['blue']}]📋  HÁBITOS DIARIOS[/bold {P['blue']}]",
                  border_style=P["border"], padding=(0, 1)),
            habit_list,
            last_visible_idx)


def make_charts_panel(data):
    comp_t, total_t, pct_t = overall_today(data)
    weekly = weekly_stats(data)
    t = Text(justify="center")
    c = P["green"] if pct_t >= 80 else P["yellow"] if pct_t >= 50 else P["red"]
    t.append(f"\n  ◈ HOY  ", style=f"bold {P['muted']}")
    t.append(f"{comp_t}/{total_t}  ", style=f"bold {P['blue']}")
    t.append(f"{pct_t:.0f}%\n  ", style=f"bold {c}")
    t.append_text(mini_ring(pct_t))
    t.append("\n\n")
    t.append("  ◈ SEMANA\n", style=f"bold {P['muted']}")
    for day_l, comp, total in weekly:
        pct = comp / total * 100 if total > 0 else 0
        filled = int(pct / 100 * 12)
        color = P["green"] if pct >= 80 else P["yellow"] if pct >= 50 else P["red"]
        is_tod = day_l == date.today().strftime("%a")
        t.append(f"  {'▶' if is_tod else ' '}{day_l} ",
                 style=f"bold {P['blue']}" if is_tod else P["muted"])
        t.append("█" * filled, style=f"bold {color}")
        t.append("░" * (12 - filled), style="dim")
        t.append(f" {pct:3.0f}%\n", style=color)
    from data import _today
    sl = (data.get("sleep", {}).get(_today()) or
          data.get("sleep", {}).get((date.today() - timedelta(days=1)).isoformat()))
    t.append(f"\n  ◈ SUEÑO\n", style=f"bold {P['muted']}")
    if sl:
        t.append("  ")
        t.append_text(sleep_bar_text(sl, 10))
        t.append("\n")
    else:
        t.append(f"  [dim]Sin registro · S[/dim]\n")
    t.append(f"\n  ◈ TOP RACHAS\n", style=f"bold {P['muted']}")
    top4 = sorted(data["habits"], key=lambda h: get_streak(data, h["id"]), reverse=True)[:4]
    for h in top4:
        s = get_streak(data, h["id"])
        e_b, _, _ = get_badge(s)
        t.append(f"  {e_b} ")
        t.append(f"{h['name'][:13]:<13} ", style=P["text"])
        t.append(f"🔥{s}\n", style=f"bold {P['orange']}" if s > 0 else "dim")
    # Comparativa semanal/mensual
    this_w = _period_rate(data, 0, 6)
    prev_w = _period_rate(data, 7, 13)
    dw = this_w - prev_w
    aw = "↑" if dw > 0 else "↓" if dw < 0 else "→"
    cw = P["green"] if dw >= 0 else P["red"]
    today = date.today()
    pm = (today.month - 2) % 12 + 1
    py = today.year if today.month > 1 else today.year - 1
    this_m = _avg_rate_month(data, today.year, today.month)
    prev_m = _avg_rate_month(data, py, pm)
    dm = this_m - prev_m
    am = "↑" if dm > 0 else "↓" if dm < 0 else "→"
    cm = P["green"] if dm >= 0 else P["red"]
    t.append(f"\n  ◈ COMPARATIVA\n", style=f"bold {P['muted']}")
    t.append(f"  Semana  ", style=P["muted"])
    t.append(f"{this_w:.0f}%", style=P["text"])
    t.append(f"  {aw}", style=f"bold {cw}")
    t.append(f"{abs(dw):.0f}%\n", style=cw)
    t.append(f"  Mes     ", style=P["muted"])
    t.append(f"{this_m:.0f}%", style=P["text"])
    t.append(f"  {am}", style=f"bold {cm}")
    t.append(f"{abs(dm):.0f}%\n", style=cm)
    return Panel(t, title=f"[bold {P['yellow']}]📊  CHARTS[/bold {P['yellow']}]",
                 border_style=P["border"])


def make_keys_panel(screen="main"):
    keys = {"main": [
        [("↑↓", "Navegar"), ("↵", "Check/valor"), ("+/-", "Contador ±1"), ("U", "Deshacer")],
        [("A", "Añadir"), ("E", "Editar"), ("D", "Eliminar"), ("H", "Historial")],
        [("C", "Calendario"), ("S", "Sueño"), ("J", "Diario"), ("G", "Objetivos")],
        [("V", "Eventos"), ("M", "Heatmap"), ("O", "Reordenar"), ("X", "Exportar")],
        [("Q", "Salir"), ("", ""), ("", ""), ("", "")],
    ],
        "calendar": [("←→", "Mes ant/sig"), ("Q", "Volver")],
        "sleep": [("←→", "Mes ant/sig"), ("L", "Registrar sueño"), ("Q", "Volver")],
        "history": [("↑↓", "Navegar"), ("A", "Añadir/editar hoy"), ("E", "Editar selec."), ("D", "Eliminar"), ("Q", "Volver")],
        "journal": [("↑↓", "Navegar"), ("A", "Escribir hoy"), ("E", "Editar selec."), ("D", "Eliminar"), ("Q", "Volver")],
        "goals": [("↑↓", "Navegar"), ("Tab", "Período"), ("↵", "Completar"), ("A", "Añadir"), ("E", "Editar"), ("N", "Nota"), ("D", "Eliminar"), ("Q", "Volver")],
        "reorder": [("↑↓", "Cursor"), ("W", "Subir"), ("S", "Bajar"), ("Tab", "Hábitos/Categ."), ("Q", "Guardar y salir")],
        "events": [("↑↓", "Navegar"), ("A", "Añadir"), ("E", "Editar"), ("D", "Eliminar"), ("Q", "Volver")],
        "heatmap": [("Tab/←→", "Cambiar hábito"), ("Q", "Volver")],
    }
    if screen == "main":
        col_headers = ["Navegación", "Hábitos", "Pantallas", "Sistema"]
        cols = keys["main"]
        tbl = Table(box=None, expand=True, show_header=True, padding=(0, 2))
        for h in col_headers:
            tbl.add_column(h, header_style=f"bold {P['muted']}", ratio=1)
        n_rows = max(len(c) for c in cols)
        for r in range(n_rows):
            row = []
            for col in cols:
                if r < len(col):
                    k, v = col[r]
                    cell = Text()
                    if k:
                        cell.append(f"[{k}] ", style=f"bold {P['blue']}")
                        cell.append(v, style=P["text"])
                else:
                    cell = Text()
                row.append(cell)
            tbl.add_row(*row)
        return Panel(tbl, title=f"[bold {P['purple']}]⌨  TECLAS[/bold {P['purple']}]",
                     border_style=P["border"], padding=(0, 0))
    t = Text("\n")
    for k, v in keys.get(screen, []):
        if k.startswith("─"):
            t.append(f"  {k}\n", style=f"dim {P['border']}")
        else:
            t.append(f"  [{k}] ", style=f"bold {P['blue']}")
            t.append(f"{v}\n", style=P["text"])
    return Panel(t, title=f"[bold {P['purple']}]⌨  TECLAS[/bold {P['purple']}]",
                 border_style=P["border"])


def make_mini_calendar(data, year=None, month=None):
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month
    _, n_days = monthrange(year, month)
    first_dow = date(year, month, 1).weekday()
    events = data.get("events", [])
    ev_days = {}
    for ev in events:
        for d in range(1, n_days + 1):
            if _event_matches(ev, year, month, d):
                ev_days.setdefault(d, []).append(ev)
    t = Text("\n ", justify="center")
    for d in ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]:
        t.append(f" {d}", style=f"bold {P['muted']}")
    t.append("\n")
    start = date(year, month, 1) - timedelta(days=first_dow)
    for week in range(6):
        cur = start + timedelta(weeks=week)
        if cur > date(year, month, n_days):
            break
        t.append(" ")
        for off in range(7):
            d = cur + timedelta(days=off)
            evs = ev_days.get(d.day, []) if d.month == month else []
            if d == today and evs:
                ic, _, col, _ = EVENT_TYPES.get(evs[0]["type"], EVENT_TYPES["event"])
                t.append(f" {d.day:2d}", style=f"bold {col} on {P['red']}")
            elif d == today:
                t.append(f" {d.day:2d}", style=f"bold white on {P['red']}")
            elif evs and d.month == month:
                ic, _, col, _ = EVENT_TYPES.get(evs[0]["type"], EVENT_TYPES["event"])
                t.append(f" {d.day:2d}", style=f"bold {col}")
            elif d.month == month:
                t.append(f" {d.day:2d}", style=P["text"])
            else:
                t.append(f" {d.day:2d}", style=f"dim {P['muted']}")
        t.append("\n")
    if ev_days:
        t.append("\n")
        for day_num in sorted(ev_days.keys()):
            for ev in ev_days[day_num]:
                ic, _, col, _ = EVENT_TYPES.get(ev["type"], EVENT_TYPES["event"])
                yr_tag = "↺ " if ev.get("yearly") else ""
                t.append(f" {ic}{yr_tag}{day_num:02d} {ev['title'][:15]}\n", style=col)
    lbl = f"{_MESES[month-1]} {year}"
    return Panel(t, title=f"[bold {P['blue']}]📅  {lbl}[/bold {P['blue']}]",
                 border_style=P["border"], padding=(0, 1))


def build_main_layout(data, selected, scroll=0, row_budget=None):
    habits_panel, habit_list, last_vis = make_habits_panel(data, selected, scroll, row_budget)
    today = date.today()
    _, n_days = monthrange(today.year, today.month)
    ev_count = sum(1 for ev in data.get("events", [])
                   if any(_event_matches(ev, today.year, today.month, d) for d in range(1, n_days + 1)))
    cal_size = 11 + min(ev_count, 5)
    layout = Layout()
    layout.split_column(
        Layout(make_header(), name="header", size=3),
        Layout(make_today_strip(data), name="strip", size=4),
        Layout(name="top", ratio=1),
        Layout(make_keys_panel("main"), name="keys", size=9),
    )
    layout["top"].split_row(Layout(habits_panel, name="main", ratio=3), Layout(name="side", ratio=1))
    layout["top"]["side"].split_column(
        Layout(make_charts_panel(data), name="charts", ratio=2),
        Layout(make_mini_calendar(data), name="minical", size=cal_size),
    )
    return layout, habit_list, last_vis
