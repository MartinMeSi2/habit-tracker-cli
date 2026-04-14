# 🎯 Habit Tracker CLI

Un rastreador de hábitos de terminal completo construido con Python y [Rich](https://github.com/Textualize/rich). Registra tus hábitos diarios, monitoriza tu sueño, escribe entradas de diario, establece objetivos y visualiza tu constancia — todo desde la terminal.

![Vista previa](assets/preview.png)

---

## ✨ Funcionalidades

- **📋 Panel de hábitos** — Vista completa de todos tus hábitos agrupados por categoría, con rachas, tasas de completado y minigráficos
- **✅ Múltiples tipos de hábito** — Booleano (hecho/no hecho), Contador (p.ej. vasos de agua), Valoración (estado de ánimo 1–5) y Notas de texto libre
- **🗂 Sistema de categorías** — Agrupa hábitos en categorías personalizadas (Salud, Trabajo, Personal, Aprendizaje…), colapsables con `Tab`
- **⭐ Hábitos destacados** — Marca los hábitos más importantes con una estrella para que destaquen visualmente
- **📅 Calendario mensual** — Visualiza tus completados día a día para cualquier mes junto con los eventos del mes
- **💤 Registro de sueño** — Anota tus horas de sueño con barra visual e indicador de calidad por colores
- **📓 Diario personal** — Escribe una nota libre por día, navegable por fecha
- **🎯 Objetivos** — Crea metas semanales, mensuales o anuales con seguimiento de progreso y notas acumulables
- **📌 Eventos** — Añade cumpleaños, fiestas, días libres y eventos recurrentes anuales
- **😶 Estado de ánimo** — Registra cómo te sientes cada día con 5 opciones y visualiza tu historial en un heatmap de 20 semanas
- **🌡 Heatmap estilo GitHub** — Mapa de calor anual por hábito, coloreado según la intensidad
- **📜 Historial** — Vista de los últimos 30 días para cualquier hábito individual
- **🔁 Reordenar** — Mueve hábitos y categorías al orden que quieras
- **📤 Exportar** — Exporta tus datos a un informe de texto legible
- **↩ Deshacer** — Deshaz el último registro de un hábito al instante con `U`
- **📏 Diseño fijo 180×55** — Visualización consistente de ancho fijo, redimensiona el terminal automáticamente al arrancar

---

## 🗂 Estructura del proyecto

```
habit-tracker-cli/
├── main.py          ← Punto de entrada y bucle principal de entrada
├── constants.py     ← Colores, constantes de layout y consola global
├── data.py          ← Carga/guardado de datos y todos los cálculos
├── render.py        ← Todos los widgets Rich, paneles y layouts
├── screens.py       ← Sub-pantallas interactivas y acciones
├── assets/
│   └── preview.png
├── requirements.txt
└── .gitignore
```

---

## ⚙️ Requisitos

- Python 3.8+
- Terminal con soporte de color verdadero (Windows Terminal, iTerm2, GNOME Terminal, etc.)

---

## 🚀 Instalación

```bash
# Clonar el repositorio
git clone https://github.com/MartinMeSi2/habit-tracker-cli.git
cd habit-tracker-cli

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python main.py
```

> **Nota:** En la primera ejecución se creará automáticamente un archivo `habits_data.json` donde se guardarán todos tus datos. Este archivo está excluido del repositorio mediante `.gitignore`, por lo que tus datos son completamente privados.

---

## ⌨️ Referencia de teclas

### Navegación principal

| Tecla | Acción |
|-------|--------|
| `↑` / `↓` | Navegar entre hábitos y categorías (circular) |
| `Tab` | Colapsar / expandir la categoría seleccionada |
| `Enter` | Marcar / completar el hábito seleccionado |
| `+` / `=` / `-` | Incrementar o decrementar un contador en 1 |
| `*` | Marcar/desmarcar hábito como destacado |
| `U` | Deshacer el último registro |
| `Q` | Salir (con opción de guardar) |

### Acciones sobre hábitos

| Tecla | Acción |
|-------|--------|
| `A` | Añadir un nuevo hábito |
| `E` | Editar el hábito seleccionado |
| `D` | Eliminar el hábito seleccionado |
| `H` | Ver historial de 30 días del hábito seleccionado |

### Pantallas

| Tecla | Pantalla |
|-------|---------|
| `C` | 📅 Calendario mensual con eventos |
| `S` | 💤 Registro y estadísticas de sueño |
| `J` | 📓 Diario personal |
| `G` | 🎯 Objetivos (semanal / mensual / anual) |
| `V` | 📌 Eventos del calendario |
| `N` | 😶 Estado de ánimo — registro e historial |
| `M` | 🌡 Heatmap anual estilo GitHub |
| `O` | 🔁 Reordenar hábitos y categorías |
| `X` | 📤 Exportar datos a texto |

---

## 📦 Tipos de hábito

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `boolean` | Completado o no | Hacer la cama ✅ |
| `counter` | Contador numérico con meta opcional | Vasos de agua (meta: 8) 🔢 |
| `rating` | Puntuación del 1 al 5 | Estado de ánimo ⭐ |
| `note` | Nota de texto libre diaria | Reflexión del día 📝 |

---

## 😶 Estado de ánimo

Registra cómo te sientes cada día eligiendo entre 5 opciones:

| Emoji | Nombre | Descripción |
|-------|--------|-------------|
| 💫 | Radiante | Productivo, inspirado, alegre |
| 💚 | Tranquilo | Agradecido, en paz, equilibrado |
| 🩵 | Melancólico | Cansado, reflexivo, solitario |
| 🔥 | Estresado | Irritable, ansioso, frustrado |
| 😶‍🌫️ | Apático | En piloto automático, vacío |

El historial se muestra como un heatmap de 20 semanas con estadísticas de tendencia.

---

## 🏅 Insignias de racha

¡Mantén tu racha para conseguir insignias!

| Insignia | Nombre | Racha necesaria |
|----------|--------|----------------|
| 💎 | DIAMOND | 100+ días |
| 🏆 | PLATINUM | 50+ días |
| ⭐ | SILVER | 20+ días |
| 🥉 | BRONZE | 10+ días |
| 🌿 | BEGINNER | 1+ días |
| 🌱 | STARTER | 0 días |

---

## 💾 Almacenamiento de datos

Todos los datos se guardan localmente en `habits_data.json` en el directorio del proyecto. Este archivo está excluido del control de versiones — tus datos no se suben nunca a ningún servidor. La estructura incluye:

- **habits** — lista de definiciones de hábitos
- **logs** — registros diarios indexados por fecha → ID de hábito
- **sleep** — horas de sueño por fecha
- **journal** — notas de texto por fecha
- **goals** — lista de objetivos con progreso y notas
- **events** — lista de eventos del calendario
- **mood** — estado de ánimo diario indexado por fecha
- **categories** — lista ordenada de categorías
- **collapsed_cats** — categorías actualmente colapsadas en la interfaz

---

## 🛠 Tecnologías utilizadas

| Librería | Uso |
|----------|-----|
| [Rich](https://github.com/Textualize/rich) | Renderizado TUI, paneles, tablas y pantalla en vivo |
| [readchar](https://github.com/magmax/python-readchar) | Captura de teclado en crudo |
| Stdlib de Python | `json`, `datetime`, `pathlib`, `calendar` |

---

## 📄 Licencia

MIT — siéntete libre de usar, hacer fork y adaptar.

---

*Construido con ❤️ y Python por [MartinMeSi2](https://github.com/MartinMeSi2)*
