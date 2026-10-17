from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from typing import Optional

from . import models
from .auth import (
    hash_password, verify_password, create_access_token, get_current_user,
)
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Tracker API")

@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/docs")

class UserIn(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)

class UserOut(BaseModel):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)

class JobIn(BaseModel):
    company: str
    role: str
    status: str = "applied"
    notes: Optional[str] = None

class Job(JobIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

@app.post("/signup", response_model=UserOut, status_code=201)
def signup(data: UserIn, db: Session = Depends(get_db)):
    exists = db.query(models.UserDB).filter(
        models.UserDB.username == data.username
    ).first()
    if exists:
        raise HTTPException(400, "Username already taken")
    user = models.UserDB(
        username=data.username, hashed_password=hash_password(data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(models.UserDB).filter(
        models.UserDB.username == form.username
    ).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Wrong username or password")
    return {"access_token": create_access_token(user.username), "token_type": "bearer"}

def find_job(db: Session, job_id: int, user: models.UserDB):
    job = db.query(models.JobDB).filter(
        models.JobDB.id == job_id, models.JobDB.owner_id == user.id
    ).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job

@app.post("/jobs", response_model=Job, status_code=201)
def create_job(
    data: JobIn,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    job = models.JobDB(**data.model_dump(), owner_id=user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

@app.get("/jobs", response_model=list[Job])
def list_jobs(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    query = db.query(models.JobDB).filter(models.JobDB.owner_id == user.id)
    if status:
        query = query.filter(models.JobDB.status == status)
    return query.all()

@app.get("/jobs/{job_id}", response_model=Job)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    return find_job(db, job_id, user)

@app.put("/jobs/{job_id}", response_model=Job)
def update_job(
    job_id: int,
    data: JobIn,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    job = find_job(db, job_id, user)
    for key, value in data.model_dump().items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return job

@app.delete("/jobs/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.UserDB = Depends(get_current_user),
):
    job = find_job(db, job_id, user)
    db.delete(job)
    db.commit()