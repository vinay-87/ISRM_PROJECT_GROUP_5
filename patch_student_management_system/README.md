# Patched Student Management System

This folder contains the MySQL-based secure version used for patch explanation, testing, and CI/CD.

## Database

Database name: `student_db_secure`

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
USE student_db_secure;
SELECT username, role FROM users;
SELECT * FROM students;
```

The password column contains bcrypt hashes, not plaintext.

## Run

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5001`.

## Demo Accounts

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `Admin@123` |
| User | `student` | `Student@123` |

## Main Controls

| Original Issue | Control In This Version |
| --- | --- |
| SQL injection | Parameterized MySQL queries using `%s` placeholders |
| Plaintext passwords | bcrypt hashing |
| Self-selected admin role | Registration always creates `user` |
| Missing authorization | `login_required` and `admin_required` decorators |
| Unsafe upload | Extension allowlist, size limit, safe filename |
| Brute-force risk | Login throttling |
| CSRF risk | CSRF token on POST forms |
| Weak browser defaults | Security headers |
| No accountability | Audit log for role, upload, and student changes |

## Tests

```powershell
python -m pytest -q
```

## CI/CD

The workflow file is:

```text
.github/workflows/ci.yml
```

It starts a MySQL 8 service, seeds `student_db_secure`, installs dependencies, runs tests, runs Bandit, and uploads `bandit-report.json`.
