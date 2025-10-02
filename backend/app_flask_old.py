from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "recruitify.db")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Database models
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "created_at": self.created_at.isoformat()
        }

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    resume = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "resume": self.resume,
            "created_at": self.created_at.isoformat()
        }

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidate.id"), nullable=False)
    cover_letter = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    job = db.relationship("Job")
    candidate = db.relationship("Candidate")

    def to_dict(self):
        return {
            "id": self.id,
            "job": self.job.to_dict() if self.job else None,
            "candidate": self.candidate.to_dict() if self.candidate else None,
            "cover_letter": self.cover_letter,
            "created_at": self.created_at.isoformat()
        }

# Routes
@app.route("/")
def root():
    return send_from_directory("static", "index.html")

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return jsonify([j.to_dict() for j in jobs])

@app.route("/api/jobs", methods=["POST"])
def create_job():
    data = request.get_json() or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "title is required"}), 400
    job = Job(title=title, description=data.get("description"), location=data.get("location"))
    db.session.add(job)
    db.session.commit()
    return jsonify(job.to_dict()), 201

@app.route("/api/candidates", methods=["GET"])
def get_candidates():
    cands = Candidate.query.order_by(Candidate.created_at.desc()).all()
    return jsonify([c.to_dict() for c in cands])

@app.route("/api/candidates", methods=["POST"])
def create_candidate():
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    if not (name and email):
        return jsonify({"error": "name and email are required"}), 400
    existing = Candidate.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "candidate with this email already exists"}), 409
    cand = Candidate(name=name, email=email, resume=data.get("resume"))
    db.session.add(cand)
    db.session.commit()
    return jsonify(cand.to_dict()), 201

@app.route("/api/apply", methods=["POST"])
def apply_job():
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    job_id = data.get("job_id")
    cover_letter = data.get("cover_letter", "")
    resume = data.get("resume", "")

    if not (name and email and job_id):
        return jsonify({"error": "name, email and job_id are required"}), 400

    job = Job.query.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404

    candidate = Candidate.query.filter_by(email=email).first()
    if not candidate:
        candidate = Candidate(name=name, email=email, resume=resume)
        db.session.add(candidate)
        db.session.commit()

    application = Application(job_id=job.id, candidate_id=candidate.id, cover_letter=cover_letter)
    db.session.add(application)
    db.session.commit()
    return jsonify(application.to_dict()), 201

@app.route("/api/applications", methods=["GET"])
def get_applications():
    apps = Application.query.order_by(Application.created_at.desc()).all()
    return jsonify([a.to_dict() for a in apps])

def seed_jobs_if_empty():
    if Job.query.count() == 0:
        sample = [
            {"title": "Junior Backend Engineer", "description": "Work on APIs and data.", "location": "Remote"},
            {"title": "Frontend Developer", "description": "Build user-facing features.", "location": "Lagos"},
            {"title": "Data Analyst Intern", "description": "Assist with data cleaning and reports.", "location": "Onsite"}
        ]
        for s in sample:
            db.session.add(Job(title=s["title"], description=s["description"], location=s["location"]))
        db.session.commit()
        print("Seeded sample jobs.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_jobs_if_empty()
    app.run(host="127.0.0.1", port=5000, debug=True)
