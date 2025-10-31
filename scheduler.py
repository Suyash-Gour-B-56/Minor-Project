# scheduler.py
import json
import random
from db_config import get_connection

def parse_availability(avail):
    """
    Accepts a JSON string or dict like {"Mon":["10:00-11:00", ...], ...}
    Returns list of slot dicts: {"day":"Mon","start":"10:00:00","end":"11:00:00"}
    """
    slots = []
    if not avail:
        return slots
    try:
        if isinstance(avail, str):
            avail_obj = json.loads(avail)
        else:
            avail_obj = avail
        for day, times in avail_obj.items():
            if not isinstance(times, list):
                continue
            for t in times:
                parts = t.split("-")
                if len(parts) != 2:
                    continue
                start = parts[0].strip()
                end = parts[1].strip()
                # ensure seconds part for MySQL TIME
                if len(start) == 5:
                    start = start + ":00"
                if len(end) == 5:
                    end = end + ":00"
                slots.append({"day": day, "start": start, "end": end})
    except Exception:
        # bad JSON or format -> ignore availability
        return []
    return slots

def generate_timetable():
    """
    Generate timetable using:
      - Faculty availability (if present)
      - Subjects assigned faculty
      - Room is_lab flag
      - Basic workload (max_hours_per_week)
    Inserts into Timetable table. Returns number of inserted rows.
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # Ensure tables exist (create minimal if missing)
    # (safe-create statements -- no FK constraints to avoid lock issues)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Class (
        class_id INT AUTO_INCREMENT PRIMARY KEY,
        year INT,
        section VARCHAR(10),
        department VARCHAR(100)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Faculty (
        faculty_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        department VARCHAR(100),
        availability JSON,
        max_hours_per_week INT DEFAULT 7
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Subject (
        subject_id INT AUTO_INCREMENT PRIMARY KEY,
        subject_name VARCHAR(150),
        credits INT,
        year INT,
        department VARCHAR(100),
        faculty_id INT,
        is_lab BOOLEAN DEFAULT 0
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Room (
        room_id INT AUTO_INCREMENT PRIMARY KEY,
        room_name VARCHAR(100),
        capacity INT,
        type VARCHAR(50),
        is_lab BOOLEAN DEFAULT 0
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Timetable (
        timetable_id INT AUTO_INCREMENT PRIMARY KEY,
        class_id INT,
        subject_id INT,
        faculty_id INT,
        room_id INT,
        day_of_week VARCHAR(10),
        start_time TIME,
        end_time TIME
    )""")
    conn.commit()

    # Fetch datasets
    cur.execute("SELECT * FROM Class")
    classes = cur.fetchall()

    cur.execute("SELECT * FROM Faculty")
    faculties = cur.fetchall()

    cur.execute("SELECT * FROM Subject")
    subjects = cur.fetchall()

    cur.execute("SELECT * FROM Room")
    rooms = cur.fetchall()

    # If no classes, create a default class (year 4 B Dept)
    if not classes:
        cur.execute("INSERT INTO Class (year, section, department) VALUES (4,'B','Electronics & Computer Science')")
        conn.commit()
        cur.execute("SELECT * FROM Class")
        classes = cur.fetchall()

    # build faculty map and availability slots
    faculty_map = {}
    faculty_slots = {}
    for f in faculties:
        fid = f.get('faculty_id')
        faculty_map[fid] = f
        slots = parse_availability(f.get('availability') or '{}')
        random.shuffle(slots)
        faculty_slots[fid] = slots

    # split rooms by lab/non-lab
    lab_rooms = [r for r in rooms if r.get('is_lab') in (1, True)]
    class_rooms = [r for r in rooms if r.get('is_lab') in (0, False, None)]
    if not rooms:
        # create default rooms if none exist
        cur.execute("INSERT INTO Room (room_name, capacity, type, is_lab) VALUES ('Seminar Hall',100,'classroom',0)")
        cur.execute("INSERT INTO Room (room_name, capacity, type, is_lab) VALUES ('Lab-1',30,'lab',1)")
        conn.commit()
        cur.execute("SELECT * FROM Room")
        rooms = cur.fetchall()
        lab_rooms = [r for r in rooms if r.get('is_lab') in (1, True)]
        class_rooms = [r for r in rooms if r.get('is_lab') in (0, False, None)]

    # Clear old timetable
    cur.execute("DELETE FROM Timetable")
    conn.commit()

    inserted = 0
    assigned = set()  # (faculty_id, day, start) and (room_id, day, start) to avoid conflict
    # Heuristic: assign each subject ~3 lectures/week (2 for labs)
    for cls in classes:
        for subj in subjects:
            # basic year match if subject/year present
            if subj.get('year') and cls.get('year') and subj.get('year') != cls.get('year'):
                continue

            fid = subj.get('faculty_id')
            if not fid:
                # skip if no faculty assigned
                continue

            # choose allowed rooms
            is_lab = int(subj.get('is_lab') or 0)
            allowed_rooms = lab_rooms if is_lab == 1 else class_rooms
            if not allowed_rooms:
                allowed_rooms = rooms

            # pick lecture count
            lectures_needed = 3 if is_lab == 0 else 2

            # if faculty has availability slots use them, else create generic slots
            slots = faculty_slots.get(fid) or []
            if not slots:
                # fallback slots
                fallback = [
                    {"day":d,"start":"10:00:00","end":"11:00:00"} for d in ["Mon","Tue","Wed","Thu","Fri","Sat"]
                ]
                random.shuffle(fallback)
                slots = fallback

            count = 0
            for s in slots:
                if count >= lectures_needed:
                    break
                day = s['day']
                start = s['start']
                end = s['end']
                key_fac = ('F', fid, day, start)
                if key_fac in assigned:
                    continue

                # choose free room for that slot
                room_choice = None
                for r in allowed_rooms:
                    key_room = ('R', r['room_id'], day, start)
                    if key_room not in assigned:
                        room_choice = r
                        break
                if not room_choice:
                    continue

                # check max hours
                max_h = int(faculty_map.get(fid, {}).get('max_hours_per_week') or 7)
                # count current faculty hours from inserted list
                cur.execute("SELECT COUNT(*) AS cnt FROM Timetable WHERE faculty_id = %s", (fid,))
                cnt_row = cur.fetchone()
                current_hours = cnt_row.get('cnt') if cnt_row else 0
                if current_hours >= max_h:
                    continue

                # insert row
                cur.execute("""
                    INSERT INTO Timetable (class_id, subject_id, faculty_id, room_id, day_of_week, start_time, end_time)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (
                    cls.get('class_id'),
                    subj.get('subject_id'),
                    fid,
                    room_choice.get('room_id'),
                    day,
                    start,
                    end
                ))
                conn.commit()
                inserted += 1
                assigned.add(key_fac)
                assigned.add(('R', room_choice.get('room_id'), day, start))
                count += 1

    cur.close()
    conn.close()
    return inserted
