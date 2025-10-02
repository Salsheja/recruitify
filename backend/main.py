# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional, Generator
from datetime import datetime

# --- Config ---
DB_FILE = "recruitify_fastapi.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"

# create engine (SQLite)
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

app = FastAPI(title="Recruitify (FastAPI backend)")

# allow frontend access during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # during dev; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from ./static (so http://127.0.0.1:8000/ returns static/index.html)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# --- Database models ---
class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Candidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    resume: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    candidate_id: int = Field(foreign_key="candidate.id")
    cover_letter: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    role: Optional[str] = "recruiter"
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- DB helpers ---
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def seed_jobs_if_empty():
    with Session(engine) as session:
        statement = select(Job)
        first_job = session.exec(statement).first()
        if not first_job:
            sample = [
                {"title": "Junior Backend Engineer", "description": "Work on APIs and data.", "location": "Remote"},
                {"title": "Frontend Developer", "description": "Build user-facing features.", "location": "Lagos"},
                {"title": "Data Analyst Intern", "description": "Assist with data cleaning and reports.", "location": "Onsite"}
            ]
            for s in sample:
                session.add(Job(title=s["title"], description=s["description"], location=s["location"]))
            session.commit()
            print("Seeded sample jobs.")

# --- Startup ---
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed_jobs_if_empty()

# --- API endpoints (prefixed with /api) ---

# JOBS
@app.get("/api/jobs")
def list_jobs(session: Session = Depends(get_session)):
    return session.exec(select(Job).order_by(Job.created_at.desc())).all()

@app.post("/api/jobs", status_code=201)
def create_job(job: Job, session: Session = Depends(get_session)):
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

@app.get("/api/jobs/{job_id}")
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    session.delete(job)
    session.commit()
    return {"detail": "Job deleted"}

# CANDIDATES
@app.get("/api/candidates")
def list_candidates(session: Session = Depends(get_session)):
    return session.exec(select(Candidate).order_by(Candidate.created_at.desc())).all()

@app.post("/api/candidates", status_code=201)
def create_candidate(candidate: Candidate, session: Session = Depends(get_session)):
    found = session.exec(select(Candidate).where(Candidate.email == candidate.email)).first()
    if found:
        raise HTTPException(status_code=409, detail="Candidate with this email already exists")
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return candidate

# APPLICATIONS
@app.post("/api/apply", status_code=201)
def apply(payload: dict, session: Session = Depends(get_session)):
    name = payload.get("name")
    email = payload.get("email")
    job_id = payload.get("job_id")
    resume = payload.get("resume")
    cover_letter = payload.get("cover_letter", "")

    if not (name and email and job_id):
        raise HTTPException(status_code=400, detail="name, email and job_id are required")

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    candidate = session.exec(select(Candidate).where(Candidate.email == email)).first()
    if not candidate:
        candidate = Candidate(name=name, email=email, resume=resume)
        session.add(candidate)
        session.commit()
        session.refresh(candidate)

    application = Application(job_id=job.id, candidate_id=candidate.id, cover_letter=cover_letter)
    session.add(application)
    session.commit()
    session.refresh(application)

    return {
        "id": application.id,
        "created_at": application.created_at,
        "cover_letter": application.cover_letter,
        "job": {"id": job.id, "title": job.title},
        "candidate": {"id": candidate.id, "name": candidate.name, "email": candidate.email}
    }

@app.get("/api/applications")
def list_applications(session: Session = Depends(get_session)):
    apps = session.exec(select(Application).order_by(Application.created_at.desc())).all()
    results = []
    for a in apps:
        job = session.get(Job, a.job_id)
        candidate = session.get(Candidate, a.candidate_id)
        results.append({
            "id": a.id,
            "created_at": a.created_at,
            "cover_letter": a.cover_letter,
            "job": {"id": job.id, "title": job.title} if job else None,
            "candidate": {"id": candidate.id, "name": candidate.name, "email": candidate.email} if candidate else None
        })
    return results

# USERS (simple CRUD for recruiters/admins)
@app.get("/api/users")
def list_users(session: Session = Depends(get_session)):
    return session.exec(select(User).order_by(User.created_at.desc())).all()

@app.post("/api/users", status_code=201)
def create_user(user: User, session: Session = Depends(get_session)):
    found = session.exec(select(User).where(User.email == user.email)).first()
    if found:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.get("/api/users/{user_id}")
def get_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user)
    session.commit()
    return {"detail": "User deleted"}
