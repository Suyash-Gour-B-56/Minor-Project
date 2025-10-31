-- ================================================================
-- DATABASE: Dynamic Scheduling System for Resource Optimization
-- ================================================================

CREATE DATABASE IF NOT EXISTS scheduling_db;
USE scheduling_db;

-- ================================================================
-- 1. CLASS TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS Class (
    class_id INT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL,
    section VARCHAR(10),
    department VARCHAR(100)
);

-- Sample Data
INSERT INTO Class (year, section, department)
VALUES (4, 'B', 'Electronics & Computer Science');

-- ================================================================
-- 2. FACULTY TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS Faculty (
    faculty_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    availability JSON,  -- store as JSON (e.g., {"Mon":["10:00-11:00"], "Tue":["11:00-12:00"]})
    max_hours_per_week INT DEFAULT 7
);

-- Sample Data
INSERT INTO Faculty (name, department, availability, max_hours_per_week) VALUES
('Prof. N.S. Damle', 'Electronics & CS', '{"Tue":["11:00-12:00"], "Wed":["11:00-12:00","14:00-15:00"]}', 7),
('Prof. S. V. Laddha', 'Electronics & CS', '{"Mon":["14:00-15:00"], "Tue":["14:00-15:00"], "Wed":["10:00-11:00"]}', 7),
('Dr. P. S. Jawarkar', 'Electronics & CS', '{"Mon":["10:00-11:00"], "Tue":["10:00-11:00"], "Wed":["12:00-13:00"]}', 7),
('Prof. P. P. Rane', 'Electronics & CS', '{"Mon":["11:00-12:00"], "Tue":["12:00-13:00"]}', 7),
('Respective Project Guide', 'Electronics & CS', '{"Wed":["15:00-16:00"], "Thu":["10:00-13:00"], "Fri":["10:00-13:00"], "Sat":["10:00-12:00"]}', 7);

-- ================================================================
-- 3. SUBJECT TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS Subject (
    subject_id INT AUTO_INCREMENT PRIMARY KEY,
    subject_name VARCHAR(100) NOT NULL,
    credits INT DEFAULT 4,
    year INT,
    department VARCHAR(100),
    faculty_id INT,
    is_lab BOOLEAN DEFAULT 0,
    FOREIGN KEY (faculty_id) REFERENCES Faculty(faculty_id)
);

-- Sample Data
INSERT INTO Subject (subject_name, credits, year, department, faculty_id, is_lab) VALUES
('System Design', 4, 4, 'Electronics & CS', 1, 0),
('Block Chain', 4, 4, 'Electronics & CS', 2, 0),
('Information Security and Cryptography', 4, 4, 'Electronics & CS', 3, 0),
('Cyber Laws and Ethics', 4, 4, 'Electronics & CS', 4, 0),
('Project-II', 4, 4, 'Electronics & CS', 5, 0),
('Minor Project', 4, 4, 'Electronics & CS', 5, 1);

-- ================================================================
-- 4. ROOM TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS Room (
    room_id INT AUTO_INCREMENT PRIMARY KEY,
    room_name VARCHAR(50),
    capacity INT,
    type VARCHAR(20),
    is_lab BOOLEAN DEFAULT 0
);

-- Sample Data
INSERT INTO Room (room_name, capacity, type, is_lab) VALUES
('Seminar Hall', 100, 'classroom', 0),
('B-1/6', 60, 'classroom', 0),
('B-00/6', 60, 'classroom', 0),
('Lab-1', 30, 'lab', 1),
('Lab-2', 30, 'lab', 1);

-- ================================================================
-- 5. TIMETABLE TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS Timetable (
    timetable_id INT AUTO_INCREMENT PRIMARY KEY,
    class_id INT,
    subject_id INT,
    faculty_id INT,
    room_id INT,
    day_of_week VARCHAR(10),
    start_time TIME,
    end_time TIME,
    FOREIGN KEY (class_id) REFERENCES Class(class_id),
    FOREIGN KEY (subject_id) REFERENCES Subject(subject_id),
    FOREIGN KEY (faculty_id) REFERENCES Faculty(faculty_id),
    FOREIGN KEY (room_id) REFERENCES Room(room_id)
);

-- ================================================================
-- 6. VERIFY TABLES
-- ================================================================
SHOW TABLES;

-- ================================================================
-- 7. TEST SAMPLE SELECT
-- ================================================================
SELECT * FROM Faculty;
SELECT * FROM Subject;
SELECT * FROM Room;
SELECT * FROM Class;
