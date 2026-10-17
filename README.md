 # Job Tracker API

A REST API to track job applications, built with FastAPI, SQLAlchemy and SQLite.

## Features
- User signup and login with JWT authentication
- Passwords stored hashed (Argon2)
- Each user can only see and edit their own jobs
- Create, read, update and delete job applications
- Filter jobs by status

## Run locally
pip install -r requirements.txt
uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs

## Run tests
python -m pytest -v