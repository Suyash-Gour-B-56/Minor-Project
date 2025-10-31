# app.py
from flask import Flask, jsonify, render_template, send_file, make_response
from db_config import get_connection
from scheduler import generate_timetable
import pandas as pd
from fpdf import FPDF
from io import BytesIO

app = Flask(__name__, template_folder="templates")

# Home / dashboard HTML
@app.route('/')
def home():
    return render_template('dashboard.html')

# Generate timetable
@app.route('/generate')
def generate():
    try:
        count = generate_timetable()
        return jsonify({"status":"success","message":"Timetable generated automatically","count":count})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# Timetable JSON data (used by front-end)
@app.route('/timetable_data')
def timetable_data():
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.year, c.section, s.subject_name, f.name AS faculty_name,
                   r.room_name, t.day_of_week, t.start_time, t.end_time
            FROM Timetable t
            LEFT JOIN Class c ON t.class_id = c.class_id
            LEFT JOIN Subject s ON t.subject_id = s.subject_id
            LEFT JOIN Faculty f ON t.faculty_id = f.faculty_id
            LEFT JOIN Room r ON t.room_id = r.room_id
            ORDER BY FIELD(t.day_of_week, 'Mon','Tue','Wed','Thu','Fri','Sat'), t.start_time
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # stringify times for JSON
        for r in rows:
            if r.get('start_time') is not None:
                r['start_time'] = str(r['start_time'])
            if r.get('end_time') is not None:
                r['end_time'] = str(r['end_time'])
        if not rows:
            return jsonify({"status":"empty","message":"No timetable generated yet."})
        return jsonify(rows)
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# Timetable page (HTML)
@app.route('/timetable')
def timetable_page():
    return render_template('timetable.html')

# Analytics JSON
@app.route('/analytics_data')
def analytics_data():
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT f.name AS faculty_name, COUNT(t.timetable_id) AS classes
            FROM Faculty f
            LEFT JOIN Timetable t ON f.faculty_id = t.faculty_id
            GROUP BY f.faculty_id
        """)
        faculty_workload = cur.fetchall()

        cur.execute("""
            SELECT r.room_name, COUNT(t.timetable_id) AS usage_count
            FROM Room r
            LEFT JOIN Timetable t ON r.room_id = t.room_id
            GROUP BY r.room_id
        """)
        room_usage = cur.fetchall()

        cur.execute("""
            SELECT day_of_week, COUNT(timetable_id) AS total_classes
            FROM Timetable
            GROUP BY day_of_week
        """)
        daily_load = cur.fetchall()

        cur.close()
        conn.close()
        return jsonify({
            "status":"success",
            "faculty_workload":faculty_workload,
            "room_usage":room_usage,
            "daily_load":daily_load
        })
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# Analytics HTML page
@app.route('/analytics')
def analytics_page():
    return render_template('analytics.html')

# Export Excel (download)
@app.route('/export/excel')
def export_excel():
    try:
        conn = get_connection()
        df = pd.read_sql("""
            SELECT c.year AS Year, c.section AS Section, s.subject_name AS Subject,
                   f.name AS Faculty, r.room_name AS Room, t.day_of_week AS Day,
                   t.start_time AS Start, t.end_time AS End
            FROM Timetable t
            LEFT JOIN Class c ON t.class_id = c.class_id
            LEFT JOIN Subject s ON t.subject_id = s.subject_id
            LEFT JOIN Faculty f ON t.faculty_id = f.faculty_id
            LEFT JOIN Room r ON t.room_id = r.room_id
            ORDER BY FIELD(t.day_of_week, 'Mon','Tue','Wed','Thu','Fri','Sat'), t.start_time
        """, conn)
        conn.close()

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Timetable')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name="Timetable_Report.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

# Export PDF (download)
@app.route('/export/pdf')
def export_pdf():
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.year AS year, c.section AS section, s.subject_name AS subject_name,
                   f.name AS faculty_name, r.room_name AS room_name,
                   t.day_of_week AS day_of_week, t.start_time AS start_time, t.end_time AS end_time
            FROM Timetable t
            LEFT JOIN Class c ON t.class_id = c.class_id
            LEFT JOIN Subject s ON t.subject_id = s.subject_id
            LEFT JOIN Faculty f ON t.faculty_id = f.faculty_id
            LEFT JOIN Room r ON t.room_id = r.room_id
            ORDER BY FIELD(t.day_of_week, 'Mon','Tue','Wed','Thu','Fri','Sat'), t.start_time
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        pdf = FPDF('L', 'mm', 'A4')
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Generated Timetable", ln=True, align="C")
        pdf.ln(6)

        pdf.set_font("Arial", "B", 10)
        headers = ["Year","Section","Subject","Faculty","Room","Day","Start","End"]
        col_w = 30
        for h in headers:
            pdf.cell(col_w, 8, h, border=1, align="C")
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        for r in rows:
            pdf.cell(col_w, 8, str(r.get('year','')), border=1)
            pdf.cell(col_w, 8, str(r.get('section','')), border=1)
            pdf.cell(col_w, 8, str(r.get('subject_name',''))[:20], border=1)
            pdf.cell(col_w, 8, str(r.get('faculty_name',''))[:20], border=1)
            pdf.cell(col_w, 8, str(r.get('room_name',''))[:15], border=1)
            pdf.cell(col_w, 8, str(r.get('day_of_week','')), border=1)
            pdf.cell(col_w, 8, str(r.get('start_time','')), border=1)
            pdf.cell(col_w, 8, str(r.get('end_time','')), border=1)
            pdf.ln()

        # ✅ fpdf2 returns bytes directly; don’t encode
        pdf_bytes = pdf.output(dest='S').encode('latin1') if isinstance(pdf.output(dest='S'), str) else pdf.output(dest='S')
        return send_file(BytesIO(pdf_bytes), as_attachment=True, download_name="Timetable_Report.pdf", mimetype="application/pdf")

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT c.year AS year, c.section AS section, s.subject_name AS subject_name,
                   f.name AS faculty_name, r.room_name AS room_name,
                   t.day_of_week AS day_of_week, t.start_time AS start_time, t.end_time AS end_time
            FROM Timetable t
            LEFT JOIN Class c ON t.class_id = c.class_id
            LEFT JOIN Subject s ON t.subject_id = s.subject_id
            LEFT JOIN Faculty f ON t.faculty_id = f.faculty_id
            LEFT JOIN Room r ON t.room_id = r.room_id
            ORDER BY FIELD(t.day_of_week, 'Mon','Tue','Wed','Thu','Fri','Sat'), t.start_time
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        pdf = FPDF('L', 'mm', 'A4')
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Generated Timetable", ln=True, align="C")
        pdf.ln(6)

        pdf.set_font("Arial", "B", 10)
        headers = ["Year","Section","Subject","Faculty","Room","Day","Start","End"]
        col_w = 30
        for h in headers:
            pdf.cell(col_w, 8, h, border=1, align="C")
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        for r in rows:
            pdf.cell(col_w, 8, str(r.get('year','')), border=1)
            pdf.cell(col_w, 8, str(r.get('section','')), border=1)
            pdf.cell(col_w, 8, str(r.get('subject_name',''))[:20], border=1)
            pdf.cell(col_w, 8, str(r.get('faculty_name',''))[:20], border=1)
            pdf.cell(col_w, 8, str(r.get('room_name',''))[:15], border=1)
            pdf.cell(col_w, 8, str(r.get('day_of_week','')), border=1)
            pdf.cell(col_w, 8, str(r.get('start_time','')), border=1)
            pdf.cell(col_w, 8, str(r.get('end_time','')), border=1)
            pdf.ln()

        pdf_output = BytesIO(pdf.output(dest='S').encode('latin1'))
        return send_file(pdf_output, as_attachment=True, download_name="Timetable_Report.pdf", mimetype="application/pdf")
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@app.route('/clear')
def clear_timetable():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM Timetable")
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status":"success","message":"Timetable cleared successfully"})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
