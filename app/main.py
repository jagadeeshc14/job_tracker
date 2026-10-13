from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from typing import Optional

from . import models
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Tracker API")

class JobIn(BaseModel):
    company: str
    role: str
    status: str = "applied"
    notes: Optional[str] = None

class Job(JobIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

def find_job(db: Session, job_id: int):
    job = db.get(models.JobDB, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

@app.post("/jobs", response_model=Job, status_code=201)
def create_job(data: JobIn, db: Session = Depends(get_db)):
    job = models.JobDB(**data.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

@app.get("/jobs", response_model=list[Job])
def list_jobs(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.JobDB)
    if status:
        query = query.filter(models.JobDB.status == status)
    return query.all()

@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return find_job(db, job_id)

@app.put("/jobs/{job_id}", response_model=Job)
def update_job(job_id: int, data: JobIn, db: Session = Depends(get_db)):
    job = find_job(db, job_id)
    for key, value in data.model_dump().items():
        setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return job

@app.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = find_job(db, job_id)
    db.delete(job)
    db.commit()