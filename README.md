# Campus Parking Tracker

A simple college mini-project for managing campus vehicle parking, built with **Flask + SQLite**.

## Overview

The Campus Parking Tracker simulates a real college campus parking system. Users can record
vehicle entry and exit, view live parking availability across parking areas and slots,
and browse parking history with search and filters.

## Features

- **Dashboard** — total / occupied / available spaces, occupancy %, per-area cards,
  occupancy chart (Chart.js), and recent vehicle activity. Auto-refreshes every 5 seconds
  by polling `/api/dashboard`.
- **Vehicle Entry** (`/entry`) — form with validation; prevents duplicate active vehicles
  and double-booking of occupied slots; auto-generates entry time.
- **Vehicle Exit** (`/exit`) — lists active vehicles with vehicle-number search; records
  exit time and frees the slot.
- **Parking Areas** (`/areas`) — capacity, occupied/available counts, occupancy progress bars.
- **Parking Slots** (`/slots`) — visual slot grid (green = Available, red = Occupied);
  occupied slots show the parked vehicle info.
- **Parking History** (`/history`) — completed records with search by vehicle number and
  filters by vehicle type and parking area.
- **JSON APIs** — `/api/dashboard` (live stats), `/api/available_slots` (free slots per area).

## Technology Stack

- Python, Flask, Jinja2 templates
- SQLite (Python built-in `sqlite3`)
- HTML, CSS, JavaScript, Chart.js (CDN)

## Project Structure

```text
app.py            # Flask app, routes, startup (PORT/SECRET_KEY via env)
database.py       # SQLite helpers + init_db() seed logic
requirements.txt  # Flask, gunicorn
templates/        # base.html, index.html, entry.html, exit.html,
                  # areas.html, slots.html, history.html
static/           # style.css, script.js
parking.db        # auto-created at startup (not committed to git)
```

## Database

SQLite file `parking.db` is created automatically next to `app.py` on startup.

- `parking_areas(id, name, capacity)` — Parking Area A (20), B (20), C (10)
- `parking_slots(id, area_id, slot_number, status)` — A-01..A-20, B-01..B-20, C-01..C-10;
  status `Available` / `Occupied`
- `parking_records(id, vehicle_number, vehicle_type, person_type, person_name,
  area_id, slot_id, entry_time, exit_time, status)` — status `Active` / `Completed`

`init_db()` creates tables if missing and seeds areas + slots only once (no duplicate
sample data). All queries use parameterized SQL.

## Installation

```bash
git clone <YOUR_REPOSITORY_URL>
cd campus-parking-tracker
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

Then open http://127.0.0.1:5000

Environment variables (optional):

| Variable      | Default                     | Purpose                          |
|---------------|-----------------------------|----------------------------------|
| `PORT`        | `5000`                      | Port to listen on                |
| `SECRET_KEY`  | dev key                     | Flask session/flash signing key  |
| `FLASK_DEBUG` | off (`"1"` enables)         | Debug mode for local development |

## Screenshots

> Add screenshots here after running the app locally.

- `screenshots/dashboard.png` — Dashboard with stats and chart
- `screenshots/entry.png` — Vehicle entry form
- `screenshots/slots.png` — Parking slot grid

## Deployment (Render)

Build Command:

```text
pip install -r requirements.txt
```

Start Command:

```text
gunicorn app:app
```

Render sets `PORT` automatically; the app binds `0.0.0.0:$PORT`.
The SQLite database is created on startup; note that Render's filesystem is
ephemeral, so parked-vehicle data resets on redeploy/restart (fine for a demo).

## Future Scope

- YOLO-based vehicle detection / automatic occupancy detection
- License plate recognition
- Parking demand and peak-hour prediction
- User authentication and a cloud database
- Mobile application
