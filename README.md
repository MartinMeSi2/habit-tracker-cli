# 🎯 Habit Tracker CLI

A fully-featured terminal habit tracker built with Python and [Rich](https://github.com/Textualize/rich). Track daily habits, monitor your sleep, write journal entries, set goals, and visualize your consistency — all from your terminal.

![Preview](assets/Captura%20de%20pantalla%202026-04-14%20135202.png)

---

## ✨ Features

- **📋 Habit Dashboard** — Full overview of all your habits grouped by category, with streaks, completion rates and sparklines
- **✅ Multiple habit types** — Boolean (done/not done), Counter (e.g. glasses of water), Rating (1–5 mood), and free-text Notes
- **🗂 Category system** — Group habits by custom categories (Health, Work, Personal, Learning…), collapsible with `Tab`
- **⭐ Star important habits** — Mark priority habits with a star so they stand out visually
- **📅 Monthly calendar** — View your habit completions day by day for any month
- **💤 Sleep tracker** — Log your sleep hours with a visual bar and color-coded quality indicator
- **📓 Journal** — Write a free-text daily note per day, searchable by date
- **🎯 Goals** — Create weekly, monthly or annual goals and track their progress
- **📌 Events** — Add birthdays, parties, free days and recurring yearly events
- **🌡 GitHub-style Heatmap** — Annual activity heatmap per habit, colored by intensity
- **📜 History** — 30-day day-by-day history view for any individual habit
- **🔁 Reorder** — Drag habits and categories into any order you want
- **📤 Export** — Export your data to a readable text report
- **↩ Undo** — Instantly undo the last habit check with `U`
- **🔄 Wrap-around navigation** — Seamless circular scrolling through habits with centered focus
- **📏 Fixed 180×55 layout** — Consistent fixed-width display, auto-resizes your terminal on launch

---

## 🗂 Project Structure

```
habit-tracker-cli/
├── main.py          ← Entry point and main input loop
├── constants.py     ← Colors, layout constants, global console
├── data.py          ← Data loading, saving and all calculations
├── render.py        ← All Rich widgets, panels and layouts
├── screens.py       ← Interactive sub-screens and actions
├── assets/
│   └── screenshot.png
├── requirements.txt
└── .gitignore
```

---

## ⚙️ Requirements

- Python 3.8+
- A terminal with true color support (Windows Terminal, iTerm2, GNOME Terminal, etc.)

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/MartinMeSi2/habit-tracker-cli.git
cd habit-tracker-cli

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

> **Note:** On first run, a `habits_data.json` file will be created automatically with sample habits. This file is excluded from the repository via `.gitignore`.

---

## ⌨️ Keyboard Reference

### Navigation

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate habits and categories (wraps around) |
| `Tab` | Collapse / expand the selected category |
| `Enter` | Check / complete the selected habit |
| `U` | Undo last habit check |
| `Q` | Quit |

### Habit Actions

| Key | Action |
|-----|--------|
| `A` | Add a new habit |
| `E` | Edit the selected habit |
| `D` | Delete the selected habit |
| `*` | Toggle star (highlight) on selected habit |
| `+` / `=` | Increment counter habit by 1 |
| `-` | Decrement counter habit by 1 |
| `H` | View 30-day history of selected habit |

### Screens

| Key | Screen |
|-----|--------|
| `C` | 📅 Monthly calendar |
| `S` | 💤 Sleep tracker |
| `J` | 📓 Journal / diary |
| `G` | 🎯 Goals |
| `V` | 📌 Events |
| `M` | 🌡 Annual heatmap (GitHub-style) |
| `O` | 🔁 Reorder habits and categories |
| `X` | 📤 Export data to text |

---

## 📦 Habit Types

| Type | Description | Example |
|------|-------------|---------|
| `boolean` | Done or not done | Make the bed ✅ |
| `counter` | Numeric counter with optional goal | Glasses of water (goal: 8) 🔢 |
| `rating` | Score from 1 to 5 | Mood rating ⭐ |
| `note` | Free-text daily note | Reflection of the day 📝 |

---

## 🏅 Streak Badges

Keep your streaks alive to earn badges!

| Badge | Name | Streak Required |
|-------|------|----------------|
| 💎 | DIAMOND | 100+ days |
| 🏆 | PLATINUM | 50+ days |
| ⭐ | SILVER | 20+ days |
| 🥉 | BRONZE | 10+ days |
| 🌿 | BEGINNER | 1+ days |
| 🌱 | STARTER | 0 days |

---

## 💾 Data Storage

All data is stored locally in `habits_data.json` in the project directory. This file is excluded from version control. The structure includes:

- **habits** — list of habit definitions
- **logs** — daily log entries keyed by date → habit ID
- **sleep** — sleep hours per date
- **journal** — text notes per date
- **goals** — list of goal objects with progress
- **events** — list of calendar events (birthdays, parties, etc.)
- **categories** — ordered list of category names
- **collapsed_cats** — list of categories currently collapsed in the UI

---

## 🛠 Tech Stack

| Library | Purpose |
|---------|---------|
| [Rich](https://github.com/Textualize/rich) | TUI rendering, panels, tables, live display |
| [readchar](https://github.com/magmax/python-readchar) | Raw keyboard input capture |
| Python stdlib | `json`, `datetime`, `pathlib`, `calendar` |

---

## 📸 Screenshots

![Habit Tracker Main Screen](assets/Captura%20de%20pantalla%202026-04-14%20135202.png)

---

## 📄 License

MIT — feel free to use, fork and adapt.

---

*Built with ❤️ and Python by [MartinMeSi2](https://github.com/MartinMeSi2)*
