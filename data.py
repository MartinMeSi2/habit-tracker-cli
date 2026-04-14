#!/usr/bin/env python3
"""Lógica de carga, guardado y cálculos de datos."""
import json
from datetime import date, timedelta
from calendar import monthrange
from constants import (P, BADGES, SPARKS, DEFAULT_CATS, DATA_FILE, SLEEP_COLORS,
                       HEAT_COLORS, _MESES, console)


def _today():
    return date.today().isoformat()


def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            d = json.load(f)
        for h in d.get("habits", []):
            h.setdefault("category", "Personal")
            h.setdefault("type", "boolean")
            h.setdefault("target", None)
            h.setdefault("color", P["blue"])
        d.setdefault("categories", DEFAULT_CATS[:])
        d.setdefault("next_id", max((h["id"] for h in d["habits"]), default=0) + 1)
        d.setdefault("sleep", {})
        d.setdefault("journal", {})
        d.setdefault("goals", [])
        d.setdefault("next_goal_id", 1)
        d.setdefault("events", [])
        d.setdefault("next_event_id", 1)
        d.setdefault("collapsed_cats", [])
        for h in d.get("habits", []):
            h.setdefault("starred", False)
        return d
    s = {"events": [], "next_event_id": 1, "habits": [
        {"id": 1, "name": "Despertar a las 6am", "created": _today(), "color": "#ffd93d", "type": "boolean", "target": None, "category": "Salud"},
        {"id": 2, "name": "Hacer la cama", "created": _today(), "color": "#6bcb77", "type": "boolean", "target": None, "category": "Salud"},
        {"id": 3, "name": "Entrenar 30 min", "created": _today(), "color": "#4d96ff", "type": "boolean", "target": None, "category": "Salud"},
        {"id": 4, "name": "Deep work 2h", "created": _today(), "color": "#ff922b", "type": "boolean", "target": None, "category": "Trabajo"},
        {"id": 5, "name": "Leer 20 páginas", "created": _today(), "color": "#cc5de8", "type": "boolean", "target": None, "category": "Aprendizaje"},
        {"id": 6, "name": "Vasos de agua", "created": _today(), "color": "#20c997", "type": "counter", "target": 8, "category": "Salud"},
        {"id": 7, "name": "Estado de ánimo", "created": _today(), "color": "#f06595", "type": "rating", "target": 5, "category": "Personal"},
        {"id": 8, "name": "Nota del día", "created": _today(), "color": "#cc5de8", "type": "note", "target": None, "category": "Personal"},
        {"id": 9, "name": "Caminar 10k", "created": _today(), "color": "#4d96ff", "type": "counter", "target": 10000, "category": "Salud"},
    ], "logs": {}, "next_id": 10, "categories": DEFAULT_CATS[:],
        "sleep": {}, "journal": {}, "goals": [], "next_goal_id": 1,
        "collapsed_cats": []}
    save_data(s)
    return s


def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def _is_done(val, habit):
    if val is None or val is False:
        return False
    t = habit.get("type", "boolean")
    if t == "boolean":
        return bool(val)
    if t == "counter":
        try:
            return int(val) >= (habit.get("target") or 1)
        except:
            return False
    if t == "rating":
        try:
            return int(val) >= 1
        except:
            return False
    if t == "note":
        return bool(str(val).strip())
    return bool(val)


def _find(data, hid):
    return next((h for h in data["habits"] if h["id"] == hid), None)


def get_streak(data, hid):
    h = _find(data, hid)
    if not h:
        return 0
    streak, day = 0, date.today()
    while True:
        val = data["logs"].get(day.isoformat(), {}).get(str(hid))
        if _is_done(val, h):
            streak += 1
            day -= timedelta(days=1)
        else:
            break
    return streak


def get_rate(data, hid, days=30):
    h = _find(data, hid)
    if not h:
        return 0.0
    created = date.fromisoformat(h.get("created", _today()))
    start = max(date.today() - timedelta(days=days - 1), created)
    total = (date.today() - start).days + 1
    if total <= 0:
        return 0.0
    comp = sum(1 for i in range(total) if _is_done(
        data["logs"].get((start + timedelta(days=i)).isoformat(), {}).get(str(hid)), h))
    return comp / total * 100


def get_badge(streak):
    for t, e, n, c in BADGES:
        if streak >= t:
            return e, n, c
    return "🌱", "STARTER", "#8b949e"


def overall_today(data):
    ds = _today()
    habits = data["habits"]
    if not habits:
        return 0, 0, 0.0
    comp = sum(1 for h in habits if _is_done(data["logs"].get(ds, {}).get(str(h["id"])), h))
    return comp, len(habits), comp / len(habits) * 100


def weekly_stats(data):
    result = []
    for i in range(6, -1, -1):
        day = date.today() - timedelta(days=i)
        ds = day.isoformat()
        total = len(data["habits"])
        comp = sum(1 for h in data["habits"] if _is_done(data["logs"].get(ds, {}).get(str(h["id"])), h))
        result.append((day.strftime("%a"), comp, total))
    return result


def _period_rate(data, days_from, days_to):
    """% cumplimiento global para los días entre days_from y days_to atrás (inclusive)."""
    habits = data["habits"]
    if not habits:
        return 0.0
    total = 0
    done = 0
    for i in range(days_from, days_to + 1):
        ds = (date.today() - timedelta(days=i)).isoformat()
        for h in habits:
            total += 1
            if _is_done(data["logs"].get(ds, {}).get(str(h["id"])), h):
                done += 1
    return done / total * 100 if total else 0.0


def _avg_rate_month(data, year, month):
    _, n_days = monthrange(year, month)
    habits = data["habits"]
    if not habits:
        return 0.0
    total = 0
    done = 0
    for d in range(1, n_days + 1):
        ds = date(year, month, d).isoformat()
        for h in habits:
            total += 1
            if _is_done(data["logs"].get(ds, {}).get(str(h["id"])), h):
                done += 1
    return done / total * 100 if total else 0.0


def sparkline_vals(data, hid, days=20):
    h = _find(data, hid)
    if not h:
        return []
    vals = []
    for i in range(days - 1, -1, -1):
        ds = (date.today() - timedelta(days=i)).isoformat()
        val = data["logs"].get(ds, {}).get(str(hid))
        t = h.get("type", "boolean")
        if t in ("counter", "rating"):
            try:
                vals.append(float(val or 0))
            except:
                vals.append(0)
        else:
            vals.append(1 if _is_done(val, h) else 0)
    return vals


def make_spark(vals):
    if not vals:
        return ""
    max_v = max(vals) if max(vals) > 0 else 1
    return "".join(SPARKS[min(7, int(v / max_v * 7))] for v in vals)


def habit_history(data, hid, days=30):
    h = _find(data, hid)
    if not h:
        return []
    result = []
    for i in range(days - 1, -1, -1):
        ds = (date.today() - timedelta(days=i)).isoformat()
        val = data["logs"].get(ds, {}).get(str(hid))
        result.append((ds, val, _is_done(val, h)))
    return result


def _build_ordered(data):
    ordered, seen = [], set()
    for cat in data.get("categories", DEFAULT_CATS):
        group = [h for h in data["habits"] if h.get("category") == cat]
        if group:
            ordered.append(("CAT", cat, None))
            for h in group:
                ordered.append(("HABIT", cat, h))
                seen.add(h["id"])
    others = [h for h in data["habits"] if h["id"] not in seen]
    if others:
        ordered.append(("CAT", "Otros", None))
        for h in others:
            ordered.append(("HABIT", "Otros", h))
    return ordered


def _build_navigable(data):
    """Lista de items navegables: cabeceras de categoría + hábitos no colapsados.

    Cada elemento es ``(kind, cat, h)`` igual que ``_build_ordered``.
    Las categorías en ``data["collapsed_cats"]`` ocultan sus hábitos pero
    mantienen la fila de cabecera para poder volver a expandirlas.
    """
    collapsed = set(data.get("collapsed_cats", []))
    result = []
    for kind, cat, h in _build_ordered(data):
        if kind == "CAT":
            result.append((kind, cat, h))
        elif kind == "HABIT" and cat not in collapsed:
            result.append((kind, cat, h))
    return result


def sleep_color(hours):
    for mn, color, _ in SLEEP_COLORS:
        if hours >= mn:
            return color
    return "#ff6b6b"


def _heat_intensity(val, habit):
    if val is None or val is False:
        return 0
    t = habit.get("type", "boolean")
    if t == "boolean":
        return 4 if bool(val) else 0
    if t == "counter":
        tgt = habit.get("target") or 1
        try:
            return min(4, max(1, int(int(val) / tgt * 4)))
        except:
            return 0
    if t == "rating":
        mx = habit.get("target") or 5
        try:
            return min(4, max(1, int(int(val) / mx * 4)))
        except:
            return 0
    if t == "note":
        return 3 if str(val).strip() else 0
    return 0


def _event_matches(ev, year, month, day):
    try:
        ed = date.fromisoformat(ev["date"])
    except:
        return False
    if ev.get("yearly"):
        return ed.month == month and ed.day == day
    return ed.year == year and ed.month == month and ed.day == day


def _events_for_month(data, year, month):
    _, n_days = monthrange(year, month)
    result = []
    for d in range(1, n_days + 1):
        day_evs = [ev for ev in data.get("events", []) if _event_matches(ev, year, month, d)]
        if day_evs:
            result.append((d, day_evs))
    return result
