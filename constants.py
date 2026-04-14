#!/usr/bin/env python3
"""Constantes globales del Habit Tracker."""
from pathlib import Path
from rich.console import Console

P = {
    "bg":"#0d1117","surf":"#161b22","border":"#30363d",
    "text":"#c9d1d9","muted":"#8b949e","blue":"#4d96ff",
    "green":"#6bcb77","yellow":"#ffd93d","orange":"#ff922b",
    "red":"#ff6b6b","purple":"#cc5de8","teal":"#20c997",
    "pink":"#f06595","sel":"#1c2d3f",
}
HABIT_COLORS=[("#ff6b6b","Rojo"),("#ffd93d","Amarillo"),("#6bcb77","Verde"),
              ("#4d96ff","Azul"),("#ff922b","Naranja"),("#cc5de8","Morado"),
              ("#20c997","Teal"),("#f06595","Rosa")]
BADGES=[(100,"💎","DIAMOND","#b9f2ff"),(50,"🏆","PLATINUM","#e5e5e5"),
        (20,"⭐","SILVER","#c0c0c0"),(10,"🥉","BRONZE","#cd7f32"),
        (1,"🌿","BEGINNER","#6bcb77"),(0,"🌱","STARTER","#8b949e")]
SECTION_TYPES={"boolean":"✅  Sí/No — hábito completado o no",
               "counter":"🔢  Contador — vasos de agua, páginas…",
               "rating":"⭐  Valoración — estado de ánimo 1–5",
               "note":"📝  Nota — texto libre diario"}
SLEEP_COLORS=[(9.0,"#cc5de8","Mucho"),(7.5,"#6bcb77","Ideal"),
              (6.5,"#20c997","OK"),(6.0,"#ffd93d","Poco"),(0.0,"#ff6b6b","Mal")]
PERIODS=["weekly","monthly","annual"]
PERIOD_UI={"weekly":("📅 SEMANAL","#4d96ff"),"monthly":("🗓 MENSUAL","#6bcb77"),"annual":("📆 ANUAL","#ff922b")}
SPARKS="▁▂▃▄▅▆▇█"
EVENT_TYPES={"birthday":("🎂","Cumpleaños","#f06595",True),"event":("📌","Evento","#4d96ff",False),
             "party":("🎉","Fiesta","#ffd93d",False),"free":("🏖","Día libre","#6bcb77",False)}
HEAT_COLORS=["#161b22","#0e4429","#006d32","#26a641","#39d353"]
_DIAS=["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
_MESES=["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
DATA_FILE=Path("habits_data.json")
DEFAULT_CATS=["Salud","Trabajo","Personal","Aprendizaje"]
APP_WIDTH  = 180      # ancho fijo de la aplicación (columnas)
APP_HEIGHT = 55       # alto mínimo recomendado (filas)
console=Console(width=APP_WIDTH, legacy_windows=False)
