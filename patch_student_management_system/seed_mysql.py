import os

import mysql.connector

from app import hash_password, load_local_env


load_local_env()


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "student_db_secure")


def main():
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
    cursor.execute(f"CREATE DATABASE `{DB_NAME}`")
    cursor.execute(f"USE `{DB_NAME}`")
    cursor.execute(
        """
        CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            CHECK (role IN ('admin', 'user'))
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            email VARCHAR(150) NOT NULL,
            course VARCHAR(120) NOT NULL,
            year INT NOT NULL
        )
        """
    )
    cursor.executemany(
        "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
        [
            ("admin", hash_password("Admin@123"), "admin"),
            ("student", hash_password("Student@123"), "user"),
        ],
    )
    cursor.executemany(
        "INSERT INTO students (name, email, course, year) VALUES (%s, %s, %s, %s)",
        [
            ("Asha Mehta", "asha.mehta@example.edu", "Information Security", 3),
            ("Rohan Singh", "rohan.singh@example.edu", "Data Science", 2),
            ("Mira Kapoor", "mira.kapoor@example.edu", "Software Engineering", 4),
        ],
    )
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Created and seeded MySQL database: {DB_NAME}")


if __name__ == "__main__":
    main()
