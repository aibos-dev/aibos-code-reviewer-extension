# LLM Code Review API (v0.2)

This repository hosts a **FastAPI** application that supports **both synchronous** code reviews (legacy `/v1/review` model) and **asynchronous** job-based reviews (new `/v1/jobs` model).

It uses:
- **PostgreSQL** for data storage,
- **SQLAlchemy** for ORM,
- **Ollama** for LLM inference (DeepSeek R1, etc.),
- **Python-dotenv** for environment configuration,
- A simple **in-memory queue** + **background thread** for asynchronous jobs.

---

## **Table of Contents**
1. [Features](#features)  
2. [Requirements](#requirements)  
3. [Installation & Setup](#installation--setup)  
   - [1. Clone Repo](#1-clone-repo)  
   - [2. Create `.env` File](#2-create-env-file)  
   - [3. Install Dependencies](#3-install-dependencies)  
   - [4. Prepare the Database](#4-prepare-the-database)  
   - [5. Run the App](#5-run-the-app)  
4. [API Endpoints](#api-endpoints)  
   - [A. Synchronous (Legacy) Endpoints](#a-synchronous-legacy-endpoints)  
   - [B. Asynchronous (Job-Based) Endpoints](#b-asynchronous-job-based-endpoints)  
5. [Sample `curl` Commands](#sample-curl-commands)  
6. [Local Development](#local-development)  
   - [Running Tests](#running-tests)  
   - [Docker Usage (Optional)](#docker-usage-optional)  
7. [FAQ / Troubleshooting](#faq--troubleshooting)

---

## **Features**
- **Hybrid Synchronous & Asynchronous** code reviews
- **In-Memory Job Queue** for asynchronous tasks
- **Ollama** as the LLM backend (via CLI)
- **PostgreSQL** database with SQLAlchemy models
- **Logging** and error handling
- **Python-dotenv** for environment variable management

---

## **Requirements**
- **Python 3.12** (or compatible)
- **PostgreSQL** (e.g., 14 or 15)
- **[Ollama](https://ollama.ai/)** for local LLM inference
- **pip** or [uv](https://github.com/astral-sh/uv) for dependency management

---

## **Installation & Setup**

### **1. Clone Repo**
```bash
git clone <YOUR_REPO_URL> template_uv
cd template_uv
```

### **2. Create `.env` File**
In `src/.env` (or project root, if you prefer):
```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=llm_review_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```
> If you’re using Docker Compose, set `POSTGRES_HOST=db`.  

### **3. Install Dependencies**
#### **If using [uv](https://github.com/astral-sh/uv):**
```bash
uv sync
```
#### **Otherwise, with pip:**
```bash
pip install -r requirements.txt
```

### **4. Prepare the Database**
Ensure **PostgreSQL is running** on the host/port specified in `.env`. Then the app will automatically create tables on startup:
```bash
# For a local DB:
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE llm_review_db;"
```
(If `llm_review_db` doesn’t already exist.)

### **5. Run the App**
```bash
# Option A: With uvicorn directly
uvicorn src.main:app --reload

# Option B: Using the main.py with Tap-based CLI
python src/main.py --host 0.0.0.0 --port 8000 --debug True
```
Now your API is at `http://localhost:8000`.

---

## **API Endpoints**

### **A. Synchronous (Legacy) Endpoints**
1. **POST `/v1/review`**  
   - **Description**: Generates an immediate code review (no queue).  
   - **Request Body** (`ReviewRequest`):
     ```json
     {
       "language": "Python",
       "sourceCode": "print('Hello World')",
       "fileName": "hello.py",
       "diff": null,
       "options": {}
     }
     ```
   - **Response** (`ReviewResponse`):
     ```json
     {
       "reviewId": "<uuid>",
       "reviews": [
         {
           "category": "General Feedback",
           "message": "Some review text..."
         }
       ]
     }
     ```

2. **POST `/v1/review/feedback`**  
   - **Description**: Submits feedback (Good/Bad) for a completed review.  
   - **Request Body**:
     ```json
     {
       "reviewId": "<uuid>",
       "feedbacks": [
         { "category": "General Feedback", "feedback": "Good" }
       ]
     }
     ```
   - **Response**:
     ```json
     {
       "status": "success",
       "message": "Feedback saved."
     }
     ```

### **B. Asynchronous (Job-Based) Endpoints**
1. **POST `/v1/jobs`**  
   - **Description**: Create a new code review job in the queue.  
   - **Request Body**:
     ```json
     {
       "language": "Python",
       "sourceCode": "print(123)",
       "diff": "...",
       "options": {}
     }
     ```
   - **Response**:
     ```json
     {
       "jobId": "<uuid>",
       "status": "queued",
       "message": "Job accepted. Check status via GET /v1/jobs/<jobId>"
     }
     ```

2. **GET `/v1/jobs/{jobId}`**  
   - **Description**: Get the status of a job, plus review results if completed.  
   - **Response** (when completed):
     ```json
     {
       "jobId": "<uuid>",
       "status": "completed",
       "reviews": [
         { "category": "General Feedback", "message": "..." }
       ]
     }
     ```

---

## **Local Development**

### **Running Tests**
```bash
pytest --maxfail=1 --disable-warnings -q
```

### **Docker Usage (Optional)**
1. **Build**:
   ```bash
   docker build -t llm-review-api .
   ```
2. **Run**:
   ```bash
   docker run -it --rm -p 8000:8000 llm-review-api
   ```

---

## **FAQ / Troubleshooting**
See troubleshooting section in the main documentation for more help.

---

**Happy Coding!** Please open issues or submit PRs for any improvements or bug fixes.
