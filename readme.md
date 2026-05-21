# ISRM Project Group 5

This repository contains **two versions of the same student management web application**:

* **`student_management_system/`** — the original vulnerable Flask + MySQL application used for security analysis.
* **`patch_student_management_system/`** — the patched and secure version with fixes applied.

The repository is designed to demonstrate **secure coding**, **vulnerability analysis**, and **CI/CD security automation** using **GitHub Actions** and **Bandit**.

---

## 1) Project Overview

The goal of this repository is to show how a web application can be improved from an insecure version to a secure version, and how automated security checks can be added to the development pipeline.

The project demonstrates:

* SQL injection in the vulnerable version
* bcrypt password hashing in the patched version
* role-based access control
* secure file upload handling
* login throttling / brute-force protection
* CSRF protection
* security headers
* audit logging
* automated security scanning with GitHub Actions
* report generation as build artifacts

---

## 2) Repository Structure

```text
ISRM_PROJECT_GROUP_5/
├── student_management_system/         # Original vulnerable app
├── patch_student_management_system/   # Patched secure app
├── .github/
│   └── workflows/
│       └── security_scan.yml         # CI/CD security workflow
├── .gitignore
└── README.md
```

---

## 3) Prerequisites

Before running either project, install:

* Python 3.11 or later
* MySQL Server 8+
* `pip`
* Git

Recommended Python packages are listed in each project’s `requirements.txt`.

---

## 4) How to Run the Project from Scratch

### Step 1: Clone the repository

```powershell
git clone https://github.com/<your-username>/ISRM_PROJECT_GROUP_5.git
cd ISRM_PROJECT_GROUP_5
```

### Step 2: Choose a project folder

Open either:

```text
student_management_system/
```

or

```text
patch_student_management_system/
```

### Step 3: Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### Step 4: Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 5: Set up the database

Run the SQL seed file:

```powershell
mysql -u root -p < setup_database.sql
```

If the MySQL CLI is not available in PATH, use the helper script:

```powershell
python seed_mysql.py
```

### Step 6: Start the app

For the vulnerable app:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

For the patched app:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5001
```

---

## 5) Database Information

### Vulnerable version

* Database name: `student_db`

Useful queries:

```sql
USE student_db;
SELECT * FROM users;
SELECT * FROM students;
```

### Patched version

* Database name: `student_db_secure`

Useful queries:

```sql
USE student_db_secure;
SELECT username, role FROM users;
SELECT * FROM students;
```

In the patched version, the password column stores **bcrypt hashes**, not plaintext passwords.

---

## 6) Demo Accounts

Both versions include demo accounts for testing.

| Role  | Username  | Password      |
| ----- | --------- | ------------- |
| Admin | `admin`   | `Admin@123`   |
| User  | `student` | `Student@123` |

---

## 7) What to Demonstrate in the Vulnerable App

The original application is intentionally insecure so it can be used for security analysis and classroom demonstration.

| Topic                  | Demonstration                                                       |
| ---------------------- | ------------------------------------------------------------------- |
| SQL injection          | Use a payload such as `admin' -- ` or `admin' #` with any password. |
| Plaintext passwords    | Inspect `student_db.users.password`.                                |
| Missing access control | Log in as `student` and open `/admin`.                              |
| Role abuse             | Register a new account and choose `admin`.                          |
| Unsafe upload          | Upload a file such as `shell.php`.                                  |
| Brute-force risk       | Run `python bruteforce.py`.                                         |

The vulnerable project is useful for showing how insecure design choices can affect a real application.

---

## 8) What the Patched Version Fixes

The patched application adds security controls that address the issues above.

| Original Issue           | Control in Patched Version                          |
| ------------------------ | --------------------------------------------------- |
| SQL injection            | Parameterized MySQL queries using `%s` placeholders |
| Plaintext passwords      | bcrypt hashing                                      |
| Self-selected admin role | Registration always creates `user`                  |
| Missing authorization    | `login_required` and `admin_required` decorators    |
| Unsafe upload            | Extension allowlist, size limit, safe filename      |
| Brute-force risk         | Login throttling                                    |
| CSRF risk                | CSRF token on POST forms                            |
| Weak browser defaults    | Security headers                                    |
| No accountability        | Audit log for role, upload, and student changes     |

---

## 9) Testing

Run the test suite in either project folder:

```powershell
python -m pytest -q
```

For the vulnerable app, the tests help confirm the original behavior that is being analyzed.

For the patched app, the tests verify that the secure behavior is working as intended.

---

## 10) CI/CD Security Automation

This repository uses **GitHub Actions** to automate security scanning.

Workflow file:

```text
.github/workflows/security_scan.yml
```

The workflow is designed to:

* run on every push and pull request
* install Bandit
* scan both application folders
* generate JSON reports
* upload the reports as artifacts
* enforce a security gate for the vulnerable application

This demonstrates **Shift-Left DevSecOps**, where security is built into the development pipeline instead of being added only at the end.

---

## 11) GitHub Actions Behavior

The workflow does the following:

1. Checks out the repository
2. Sets up Python 3.11
3. Installs Bandit
4. Scans `student_management_system/`
5. Scans `patch_student_management_system/`
6. Generates JSON reports
7. Uploads reports as artifacts
8. Fails the workflow when the vulnerable app contains high-severity issues

The reports can be downloaded from the **Actions** tab in GitHub.

---

## 12) Why This Repository Has Two Versions

This is useful for showing a complete security story:

* the **original version** shows what insecure code looks like
* the **patched version** shows how to fix it properly
* the **CI/CD pipeline** proves that security scanning works automatically

This makes the repository strong for:

* college submission
* security lab demonstration
* DevSecOps explanation
* project viva
* GitHub portfolio presentation

---

## 13) Suggested Demo Flow

1. Show the repository structure.
2. Open the vulnerable app and explain the issues.
3. Open the patched app and explain the fixes.
4. Show the GitHub Actions workflow file.
5. Open the Actions tab and show the scan run.
6. Show the uploaded artifact reports.
7. Explain how the pipeline supports secure development.

---

## 14) Notes

* Do not upload virtual environments, node_modules, or temporary files.
* Keep the root repository as the only Git repository.
* Do not keep nested `.git` folders inside the two project folders.
* If your workflow file name differs, update the path in this README accordingly.

---

## 15) Summary

This repository demonstrates a full security lifecycle:

* insecure application analysis
* secure remediation
* automated CI/CD scanning
* artifact-based reporting
* practical DevSecOps implementation

It is designed to be easy to understand, easy to demo, and easy to extend.
