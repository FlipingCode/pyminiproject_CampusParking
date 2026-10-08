import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "parking.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and insert sample data only once."""
    conn = get_db()
    cur = conn.cursor()

    # Tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS parking_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            capacity INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS parking_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area_id INTEGER NOT NULL,
            slot_number TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'Available',
            FOREIGN KEY (area_id) REFERENCES parking_areas(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS parking_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            person_type TEXT NOT NULL,
            person_name TEXT NOT NULL,
            area_id INTEGER NOT NULL,
            slot_id INTEGER NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY (area_id) REFERENCES parking_areas(id),
            FOREIGN KEY (slot_id) REFERENCES parking_slots(id)
        )
    """)
    conn.commit()

    # Insert sample data only if areas table is empty
    cur.execute("SELECT COUNT(*) AS c FROM parking_areas")
    if cur.fetchone()["c"] == 0:
        areas = [
            ("Parking Area A", 20, "A"),
            ("Parking Area B", 20, "B"),
            ("Parking Area C", 10, "C"),
        ]
        for name, capacity, prefix in areas:
            cur.execute(
                "INSERT INTO parking_areas (name, capacity) VALUES (?, ?)",
                (name, capacity),
            )
            area_id = cur.lastrowid
            for i in range(1, capacity + 1):
                slot_number = f"{prefix}-{i:02d}"
                cur.execute(
                    "INSERT INTO parking_slots (area_id, slot_number, status) VALUES (?, ?, 'Available')",
                    (area_id, slot_number),
                )
        conn.commit()
        print("Sample parking areas and slots created.")
    else:
        print("Database already initialized.")

    conn.close()


if __name__ == "__main__":
    init_db()
