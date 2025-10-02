const API_URL = "http://127.0.0.1:5000/api";

// Load jobs from backend
async function loadJobs() {
  const res = await fetch(`${API_URL}/jobs`);
  const jobs = await res.json();
  const jobsList = document.getElementById("jobs-list");
  const jobSelect = document.getElementById("job-select");
  jobsList.innerHTML = "";
  jobSelect.innerHTML = "<option value=''>Select a job</option>";
  jobs.forEach(job => {
    const li = document.createElement("li");
    li.textContent = `${job.title} (${job.location})`;
    jobsList.appendChild(li);

    const option = document.createElement("option");
    option.value = job.id;
    option.textContent = job.title;
    jobSelect.appendChild(option);
  });
}

// Submit job application
document.getElementById("application-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("name").value;
  const email = document.getElementById("email").value;
  const resume = document.getElementById("resume").value;
  const job_id = document.getElementById("job-select").value;
  const cover_letter = document.getElementById("cover-letter").value;

  const res = await fetch(`${API_URL}/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, resume, job_id, cover_letter })
  });

  if (res.ok) {
    alert("Application submitted!");
    loadApplications();
  } else {
    const err = await res.json();
    alert("Error: " + err.error);
  }
});

// Load applications
async function loadApplications() {
  const res = await fetch(`${API_URL}/applications`);
  const apps = await res.json();
  const list = document.getElementById("applications-list");
  list.innerHTML = "";
  apps.forEach(app => {
    const li = document.createElement("li");
    li.textContent = `${app.candidate.name} applied for ${app.job.title}`;
    list.appendChild(li);
  });
}

// Load everything when page opens
loadJobs();
loadApplications();
