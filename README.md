# LLM Code Review API

This repository hosts a **FastAPI** application supporting **both synchronous** code reviews (legacy `/v2/review` model) and **asynchronous** job-based reviews (new `/v2/jobs` model).

## **Features**

- **Hybrid Synchronous & Asynchronous** code reviews
- **In-Memory Job Queue** for asynchronous tasks
- **Ollama** as the LLM backend (DeepSeek R1, etc.)
- **PostgreSQL** database with SQLAlchemy ORM
- **Comprehensive Logging & Error Handling**
- **Python-dotenv** for environment variable management
- **VS Code Dev Container Support** for seamless development

---

## **Table of Contents**

1. [Requirements](#requirements)
2. [Installation & Setup](#installation--setup)
   - [1. Clone Repo](#1-clone-repo)
   - [2. Create ](#2-create-env-file)[`.env`](#2-create-env-file)[ File](#2-create-env-file)
   - [3. Install Dependencies](#3-install-dependencies)
   - [4. Prepare the Database](#4-prepare-the-database)
   - [5. Run the App](#5-run-the-app)
3. [Development Environment Setup with Dev Containers](#development-environment-setup-with-dev-containers)
4. [Downloading and Managing LLM Models](#downloading-and-managing-llm-models)
5. [API Endpoints](#api-endpoints)
   - [Synchronous Code Review](#synchronous-code-review)
   - [Asynchronous Job-Based Review](#asynchronous-job-based-review)
6. [Sample ](#sample-curl-commands)[`curl`](#sample-curl-commands)[ Commands](#sample-curl-commands)
7. [Local Development](#local-development)
   - [Running Tests](#running-tests)
   - [Docker Usage (Optional)](#docker-usage-optional)
8. [Downloading and Managing LLM Models](#downloading-and-managing-llm-models)
9. [Performance Benchmarks](#performance-benchmarks)
10. [FAQ / Troubleshooting](#faq--troubleshooting)

---

## **Requirements**

- **Python 3.12** or later
- **PostgreSQL** (14 or later)
- **[Ollama](https://ollama.ai/)** for local LLM inference
- **Docker** and **Docker Compose** for containerized development
- **Visual Studio Code** with the **Dev Containers** extension

---

## **Installation & Setup**

### **1. Clone Repo**

```bash
git clone https://github.com/aibos-dev/aibos-code-reviewer-extension.git
cd aibos-code-reviewer-extension
```

### **2. Create ************`.env`************ File**

Create a `.env` file in the root directory:

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=llm_review_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

> If using Docker, set `POSTGRES_HOST=db`.

### **3. Install Dependencies**

#### **Using uv:**

```bash
uv sync
```

### **4. Prepare the Database**

Ensure **PostgreSQL is running**, then create the database:

```bash
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE llm_review_db;"
```

### **5. Run the App**

```bash
# Option 1: Run directly
uvicorn src.main:app --reload

# Option 2: Run via CLI
python src/main.py --host 0.0.0.0 --port 8000 --debug True
```

Now your API is live at `http://localhost:8000`.

---

## **Development Environment Setup with Dev Containers**

1. **Prerequisites:**

   - Install **Docker**: [https://www.docker.com/](https://www.docker.com/)
   - Install **Visual Studio Code**: [https://code.visualstudio.com/](https://code.visualstudio.com/)
   - Install the **Dev Containers** extension in VS Code.

2. **Setting Up the Dev Container:**

   - Open the project in VS Code.
   - Press `F1`, search for **"Reopen in Container"**, and select it.
   - The container will be built and configured automatically.

3. **Accessing the Development Environment:**

   - Open a terminal inside VS Code.
   - Run the API: `uvicorn src.main:app --reload`.
   - Access the API at `http://localhost:8000`.

---

## **Downloading and Managing LLM Models**

### **1. Downloading the DeepSeek Model**
### **1. Introducing a New Model**

To introduce a new model to Ollama, follow these steps:

1. Ensure the model is compatible with Ollama.
2. Use the command `ollama pull <model-name>` to download the model.
3. Update `llm_engines/ollama_engine.py` to include the new model.
4. Restart the API service to apply changes.

### \*\*2. Managing the prompt in the \*\***`config.json`**

The prompt used for code reviews can be customized in the `config.json` file:

```json
{
  "prompt": "Provide detailed feedback on the given code snippet...",
  "categories": ["Security", "Performance", "Readability", "Best Practices"]
}
```

Modify these values as needed.

---

Run the following command to fetch the required LLM model:
```bash
./download_model.sh
```

### **2. Listing Available Models in Ollama**
Check available models:
```bash
ollama list
```

---

## **API Endpoints**

#### **1. POST `/v2/review/feedback`**  
**Request Body:**
```json
{
  "reviewId": "<uuid>",
  "feedbacks": [
    { "category": "General Feedback", "feedback": "Good" }
  ]
}
```
**Response:**
```json
{
  "status": "success",
  "message": "Feedback saved."
}
```

### **Asynchronous Job-Based Review**

#### **1. POST `/v2/jobs`**  
**Request Body:**
```json
{
  "language": "Python",
  "sourceCode": "print(123)",
  "diff": "...",
  "options": {}
}
```
**Response:**
```json
{
  "jobId": "<uuid>",
  "status": "queued",
  "message": "Job accepted. Check status via GET /v2/jobs/<jobId>"
}
```

#### **2. GET `/v2/jobs/{jobId}`**  
**Response (when completed):**
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

## **Performance Benchmarks**

### **Performance on NVIDIA A6000 ADA GPU**

- **Average Task Completion Time:** ~51.05 seconds
- **GPU Usage:** 97% load, 89.7% memory used (only GPU 0 utilized)
- **CPU Usage:** Two threads maxed out at 100% usage

### **Response Time vs. Token Size**

| Input Tokens | Output Tokens | Response Time (s) |
| ------------ | ------------- | ----------------- |
| 512          | 128           | 10.5              |
| 1024         | 256           | 22.3              |
| 2048         | 512           | 48.7              |
| 4096         | 1024          | 120.9             |

### **Memory Consumption**

- **CPU Memory Usage:** 2-4GB depending on token size
- **GPU Memory Usage:** Peaks at ~90% for large inputs

---

## **FAQ / Troubleshooting**

See the documentation for additional troubleshooting tips.

---

**Happy Coding!** Contributions, issues, and PRs are welcome.




