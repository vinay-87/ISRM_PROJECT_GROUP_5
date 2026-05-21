CREATE DATABASE IF NOT EXISTS student_db_secure;
USE student_db_secure;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    CHECK (role IN ('admin', 'user'))
);

CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL,
    course VARCHAR(120) NOT NULL,
    year INT NOT NULL
);

TRUNCATE TABLE students;
DELETE FROM users;
ALTER TABLE users AUTO_INCREMENT = 1;
ALTER TABLE students AUTO_INCREMENT = 1;

INSERT INTO users (username, password, role) VALUES
('admin', '$2b$12$SNDUiGS/W/KFjPHwRgDobeRsUumUQHxKrmqeIGJqbF29shovlQZUW', 'admin'),
('student', '$2b$12$fn0Dqd4OeZvuFpsyMfE2L.ZTZ8u4klX9iuU7sCzijjh3NkrzI5gEa', 'user');

INSERT INTO students (name, email, course, year) VALUES
('Asha Mehta', 'asha.mehta@example.edu', 'Information Security', 3),
('Rohan Singh', 'rohan.singh@example.edu', 'Data Science', 2),
('Mira Kapoor', 'mira.kapoor@example.edu', 'Software Engineering', 4);
