from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# -----------------------
# MODELS
# -----------------------
class Job(BaseModel):
    id: int
    title: str
    description: str
    company: str

class User(BaseModel):
    id: int
    name: str
    email: str

# -----------------------
# IN-MEMORY STORAGE (like fake database for now)
# -----------------------
jobs: List[Job] = []
users: List[User] = []

# -----------------------
# JOB ROUTES
# -----------------------
@app.get("/jobs", response_model=List[Job])
def get_jobs():
    return jobs

@app.post("/jobs", response_model=Job)
def create_job(job: Job):
    jobs.append(job)
    return job

@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: int):
    for job in jobs:
        if job.id == job_id:
            return job
    raise HTTPException(status_code=404, detail="Job not found")

@app.delete("/jobs/{job_id}")
def delete_job(job_id: int):
    global jobs
    jobs = [j for j in jobs if j.id != job_id]
    return {"message": "Job deleted"}

# -----------------------
# USER ROUTES
# -----------------------
@app.get("/users", response_model=List[User])
def get_users():
    return users

@app.post("/users", response_model=User)
def create_user(user: User):
    users.append(user)
    return user
