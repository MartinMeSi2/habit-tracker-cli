# 🎯 Habit Tracker v3 — Versión Modular

Habit Tracker de terminal con interfaz TUI construido en Python con **Rich**. Versión refactorizada en módulos independientes.

## Estructura del proyecto

```
segmentado/
├── main.py         ← Punto de entrada y bucle principal
├── constants.py    ← Colores, constantes y configuración global
├── data.py         ← Carga/guardado de datos y cálculos
├── render.py       ← Widgets visuales y layouts
├── screens.py      ← Pantallas interactivas y acciones
├── requirements.txt
└── .gitignore
```

## Requisitos

- Python 3.7+
- Terminal con soporte para colores

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

## Teclas principales

| Tecla | Acción |
|-------|--------|
| `↑ ↓` | Navegar entre hábitos |
| `Enter` | Registrar / completar hábito |
| `+ / -` | Incrementar/decrementar contador |
| `U` | Deshacer último check |
| `A` | Añadir hábito |
| `E` | Editar hábito seleccionado |
| `D` | Eliminar hábito seleccionado |
| `H` | Historial del hábito |
| `C` | Calendario mensual |
| `S` | Registro de sueño |
| `J` | Diario personal |
| `G` | Objetivos |
| `V` | Eventos |
| `M` | Heatmap anual estilo GitHub |
| `O` | Reordenar hábitos y categorías |
| `X` | Exportar datos |
| `Q` | Salir |

## Tipos de hábitos

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `bool` | Completado o no | Hacer la cama |
| `cnt` | Contador con meta | Vasos de agua (meta: 8) |
| `rate` | Valoración 1–5 | Estado de ánimo |
| `note` | Texto libre diario | Reflexión del día |

## Notas

Los datos se guardan en `habits_data.json` (excluido del repositorio por `.gitignore`).
