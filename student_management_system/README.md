# Original Student Management System

This folder contains the original MySQL-based Flask app used for vulnerability analysis in the follow-up tutorial.

## Database

Database name: `student_db`

Create and seed it:

```powershell
mysql -u root -p < setup_database.sql
```

If the MySQL CLI is not in PATH:

```powershell
python seed_mysql.py
```

Check records:

```sql
USE student_db;
SELECT * FROM users;
SELECT * FROM students;
```

## Run

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Demo Accounts

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `Admin@123` |
| User | `student` | `Student@123` |

## Behaviors To Demonstrate

| Topic | Demonstration |
| --- | --- |
| SQL injection | Use username `admin' -- ` or `admin' #` with any password. |
| Plaintext passwords | Inspect `student_db.users.password`. |
| Missing access control | Login as `student`, then open `/admin`. |
| Role abuse | Register a new account and choose `admin`. |
| Unsafe upload | Upload a file such as `shell.php`. |
| Brute-force risk | Run `python bruteforce.py`. |

## Tests

```powershell
python -m pytest -q
```

These tests verify that the expected original behaviors are present for the report and demonstration.
