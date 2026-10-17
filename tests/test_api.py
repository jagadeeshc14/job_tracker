import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False)

def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def auth_headers(username="alice", password="secret123"):
    client.post("/signup", json={"username": username, "password": password})
    r = client.post("/login", data={"username": username, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

def add_job(headers, company="Google", role="Intern", status="applied"):
    return client.post(
        "/jobs",
        json={"company": company, "role": role, "status": status},
        headers=headers,
    )

def test_signup_ok():
    r = client.post("/signup", json={"username": "alice", "password": "secret123"})
    assert r.status_code == 201
    assert r.json()["username"] == "alice"

def test_duplicate_signup_rejected():
    client.post("/signup", json={"username": "alice", "password": "secret123"})
    r = client.post("/signup", json={"username": "alice", "password": "secret123"})
    assert r.status_code == 400

def test_login_wrong_password():
    client.post("/signup", json={"username": "alice", "password": "secret123"})
    r = client.post("/login", data={"username": "alice", "password": "wrongpass"})
    assert r.status_code == 401

def test_jobs_require_login():
    assert client.get("/jobs").status_code == 401

def test_create_and_list_job():
    h = auth_headers()
    assert add_job(h).status_code == 201
    jobs = client.get("/jobs", headers=h).json()
    assert len(jobs) == 1
    assert jobs[0]["company"] == "Google"

def test_filter_by_status():
    h = auth_headers()
    add_job(h, status="applied")
    add_job(h, company="TCS", status="interview")
    r = client.get("/jobs?status=interview", headers=h)
    assert len(r.json()) == 1
    assert r.json()[0]["company"] == "TCS"

def test_update_job():
    h = auth_headers()
    job_id = add_job(h).json()["id"]
    r = client.put(
        f"/jobs/{job_id}",
        json={"company": "Google", "role": "Intern", "status": "offer"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "offer"

def test_delete_job():
    h = auth_headers()
    job_id = add_job(h).json()["id"]
    assert client.delete(f"/jobs/{job_id}", headers=h).status_code == 204
    assert client.get("/jobs", headers=h).json() == []

def test_user_cannot_see_other_users_jobs():
    alice = auth_headers("alice", "secret123")
    bob = auth_headers("bobby", "secret123")
    job_id = add_job(alice).json()["id"]
    assert client.get("/jobs", headers=bob).json() == []
    assert client.get(f"/jobs/{job_id}", headers=bob).status_code == 404