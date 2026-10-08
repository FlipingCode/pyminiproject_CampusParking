from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import os
import sqlite3
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "campus-parking-secret-key")  # needed for flash messages

init_db()  # ensure DB/tables exist on import too (needed for gunicorn)

VEHICLE_TYPES = ["Car", "Motorcycle", "Scooter", "Other"]
PERSON_TYPES = ["Student", "Faculty", "Staff", "Visitor"]


def get_dashboard_stats():
    """Calculate total, occupied, available and occupancy % from live DB data."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(capacity), 0) AS total FROM parking_areas")
    total = cur.fetchone()["total"] or 0
    cur.execute("SELECT COUNT(*) AS c FROM parking_slots WHERE status = 'Occupied'")
    occupied = cur.fetchone()["c"] or 0
    available = total - occupied
    occupancy = round((occupied / total * 100) if total > 0 else 0, 1)
    conn.close()
    return {"total": total, "occupied": occupied,
            "available": available, "occupancy_percentage": occupancy}


def get_area_stats():
    """Per-area stats: capacity, occupied, available, occupancy %."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM parking_areas ORDER BY id")
    areas = cur.fetchall()
    result = []
    for a in areas:
        cur.execute(
            "SELECT COUNT(*) AS c FROM parking_slots WHERE area_id = ? AND status = 'Occupied'",
            (a["id"],),
        )
        occupied = cur.fetchone()["c"] or 0
        capacity = a["capacity"]
        available = capacity - occupied
        occupancy = round((occupied / capacity * 100) if capacity else 0, 1)
        result.append({
            "id": a["id"], "name": a["name"], "capacity": capacity,
            "occupied": occupied, "available": available,
            "occupancy": occupancy,
        })
    conn.close()
    return result


@app.route("/")
def index():
    stats = get_dashboard_stats()
    area_stats = get_area_stats()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.*, a.name AS area_name, s.slot_number
        FROM parking_records r
        JOIN parking_areas a ON r.area_id = a.id
        JOIN parking_slots s ON r.slot_id = s.id
        ORDER BY r.entry_time DESC LIMIT 8
    """)
    recent = cur.fetchall()
    conn.close()
    return render_template("index.html", stats=stats,
                           areas=area_stats, recent=recent)


@app.route("/entry", methods=["GET", "POST"])
def entry():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM parking_areas ORDER BY id")
    areas = cur.fetchall()

    if request.method == "POST":
        vehicle_number = request.form.get("vehicle_number", "").strip().upper()
        vehicle_type = request.form.get("vehicle_type", "").strip()
        person_type = request.form.get("person_type", "").strip()
        person_name = request.form.get("person_name", "").strip()
        area_id = request.form.get("area_id", "").strip()
        slot_id = request.form.get("slot_id", "").strip()

        # 1. Empty field check
        if not all([vehicle_number, vehicle_type, person_type,
                    person_name, area_id, slot_id]):
            flash("All fields are required.", "error")
            conn.close()
            return render_template("entry.html", areas=areas,
                                   vehicle_types=VEHICLE_TYPES,
                                   person_types=PERSON_TYPES)

        if vehicle_type not in VEHICLE_TYPES or person_type not in PERSON_TYPES:
            flash("Invalid vehicle type or person type.", "error")
            conn.close()
            return render_template("entry.html", areas=areas,
                                   vehicle_types=VEHICLE_TYPES,
                                   person_types=PERSON_TYPES)

        try:
            # 2. Duplicate active vehicle check
            cur.execute(
                "SELECT id FROM parking_records WHERE UPPER(vehicle_number) = ? AND status = 'Active'",
                (vehicle_number,),
            )
            if cur.fetchone():
                flash(f"Vehicle {vehicle_number} is already parked inside.", "error")
                conn.close()
                return render_template("entry.html", areas=areas,
                                       vehicle_types=VEHICLE_TYPES,
                                       person_types=PERSON_TYPES)

            # 3. Slot exists + belongs to area + available check
            cur.execute("SELECT * FROM parking_slots WHERE id = ?", (slot_id,))
            slot = cur.fetchone()
            if not slot:
                flash("Selected parking slot does not exist.", "error")
                conn.close()
                return render_template("entry.html", areas=areas,
                                       vehicle_types=VEHICLE_TYPES,
                                       person_types=PERSON_TYPES)
            if str(slot["area_id"]) != str(area_id):
                flash("Slot does not belong to the selected parking area.", "error")
                conn.close()
                return render_template("entry.html", areas=areas,
                                       vehicle_types=VEHICLE_TYPES,
                                       person_types=PERSON_TYPES)
            if slot["status"] != "Available":
                flash(f"Slot {slot['slot_number']} is already occupied.", "error")
                conn.close()
                return render_template("entry.html", areas=areas,
                                       vehicle_types=VEHICLE_TYPES,
                                       person_types=PERSON_TYPES)

            # 4. Insert record + occupy slot
            entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""
                INSERT INTO parking_records
                (vehicle_number, vehicle_type, person_type, person_name,
                 area_id, slot_id, entry_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')
            """, (vehicle_number, vehicle_type, person_type, person_name,
                  area_id, slot_id, entry_time))
            cur.execute("UPDATE parking_slots SET status = 'Occupied' WHERE id = ?",
                        (slot_id,))
            conn.commit()
            conn.close()
            flash(f"Vehicle {vehicle_number} parked at {slot['slot_number']}.", "success")
            return redirect(url_for("index"))
        except sqlite3.Error:
            conn.rollback()
            conn.close()
            flash("Database error. Please try again.", "error")
            return render_template("entry.html", areas=areas,
                                   vehicle_types=VEHICLE_TYPES,
                                   person_types=PERSON_TYPES)

    conn.close()
    return render_template("entry.html", areas=areas,
                           vehicle_types=VEHICLE_TYPES,
                           person_types=PERSON_TYPES)


@app.route("/exit", methods=["GET", "POST"])
def exit_vehicle():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        record_id = request.form.get("record_id", "").strip()
        if not record_id:
            flash("Please select a vehicle.", "error")
        else:
            try:
                cur.execute("""
                    SELECT r.*, s.slot_number FROM parking_records r
                    JOIN parking_slots s ON r.slot_id = s.id
                    WHERE r.id = ? AND r.status = 'Active'
                """, (record_id,))
                rec = cur.fetchone()
                if not rec:
                    flash("Vehicle not found or already exited.", "error")
                else:
                    exit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cur.execute(
                        "UPDATE parking_records SET exit_time = ?, status = 'Completed' WHERE id = ?",
                        (exit_time, record_id),
                    )
                    cur.execute("UPDATE parking_slots SET status = 'Available' WHERE id = ?",
                                (rec["slot_id"],))
                    conn.commit()
                    flash(f"Vehicle {rec['vehicle_number']} exited from {rec['slot_number']}.", "success")
                    conn.close()
                    return redirect(url_for("index"))
            except sqlite3.Error:
                conn.rollback()
                flash("Database error. Please try again.", "error")
        conn.close()
        return redirect(url_for("exit_vehicle"))

    # GET: list active vehicles, optional search
    search = request.args.get("search", "").strip().upper()
    if search:
        cur.execute("""
            SELECT r.*, a.name AS area_name, s.slot_number
            FROM parking_records r
            JOIN parking_areas a ON r.area_id = a.id
            JOIN parking_slots s ON r.slot_id = s.id
            WHERE r.status = 'Active' AND UPPER(r.vehicle_number) LIKE ?
            ORDER BY r.entry_time DESC
        """, (f"%{search}%",))
    else:
        cur.execute("""
            SELECT r.*, a.name AS area_name, s.slot_number
            FROM parking_records r
            JOIN parking_areas a ON r.area_id = a.id
            JOIN parking_slots s ON r.slot_id = s.id
            WHERE r.status = 'Active'
            ORDER BY r.entry_time DESC
        """)
    active = cur.fetchall()
    conn.close()
    return render_template("exit.html", active=active, search=request.args.get("search", ""))


@app.route("/areas")
def areas():
    return render_template("areas.html", areas=get_area_stats())


@app.route("/slots")
def slots():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM parking_areas ORDER BY id")
    areas = cur.fetchall()
    grouped = []
    for a in areas:
        cur.execute("SELECT * FROM parking_slots WHERE area_id = ? ORDER BY slot_number",
                    (a["id"],))
        slot_list = []
        for s in cur.fetchall():
            vehicle = None
            if s["status"] == "Occupied":
                cur.execute("""
                    SELECT vehicle_number, vehicle_type, person_name, entry_time
                    FROM parking_records
                    WHERE slot_id = ? AND status = 'Active' LIMIT 1
                """, (s["id"],))
                vehicle = cur.fetchone()
            slot_list.append({"slot": s, "vehicle": vehicle})
        grouped.append({"area": a, "slots": slot_list})
    conn.close()
    return render_template("slots.html", grouped=grouped)


@app.route("/history")
def history():
    search = request.args.get("search", "").strip()
    vtype = request.args.get("vehicle_type", "").strip()
    area_id = request.args.get("area_id", "").strip()

    query = """
        SELECT r.*, a.name AS area_name, s.slot_number
        FROM parking_records r
        JOIN parking_areas a ON r.area_id = a.id
        JOIN parking_slots s ON r.slot_id = s.id
        WHERE r.status = 'Completed'
    """
    params = []
    if search:
        query += " AND UPPER(r.vehicle_number) LIKE ?"
        params.append(f"%{search.upper()}%")
    if vtype in VEHICLE_TYPES:
        query += " AND r.vehicle_type = ?"
        params.append(vtype)
    if area_id.isdigit():
        query += " AND r.area_id = ?"
        params.append(area_id)
    query += " ORDER BY r.exit_time DESC"

    conn = get_db()
    cur = conn.cursor()
    cur.execute(query, params)
    records = cur.fetchall()
    cur.execute("SELECT * FROM parking_areas ORDER BY id")
    areas = cur.fetchall()
    conn.close()
    return render_template("history.html", records=records,
                           areas=areas, vehicle_types=VEHICLE_TYPES,
                           search=search, vtype=vtype, area_id=area_id)


@app.route("/api/dashboard")
def api_dashboard():
    return jsonify(get_dashboard_stats())


@app.route("/api/available_slots")
def api_available_slots():
    """Return available slots for a given area (used by entry form)."""
    area_id = request.args.get("area_id", "")
    conn = get_db()
    cur = conn.cursor()
    if area_id.isdigit():
        cur.execute(
            "SELECT id, slot_number FROM parking_slots WHERE area_id = ? AND status = 'Available' ORDER BY slot_number",
            (area_id,),
        )
    else:
        cur.execute(
            "SELECT id, slot_number FROM parking_slots WHERE status = 'Available' ORDER BY slot_number",
        )
    rows = [{"id": r["id"], "slot_number": r["slot_number"]} for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
