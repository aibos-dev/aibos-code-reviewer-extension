# LLM Code Reviewer API

This repository hosts a **FastAPI** application supporting **asynchronous** job-based code reviews (new `/v2/jobs` model).

## **Features**

- **Hybrid Synchronous & Asynchronous** code reviews
- **In-Memory Job Queue** for asynchronous tasks
- **Ollama** as the LLM backend (DeepSeek R1, etc.)
- **PostgreSQL** database with SQLAlchemy ORM
- **Comprehensive Logging & Error Handling**
- **Python-dotenv** for environment variable management
- **Docker Support** for containerized deployment

---

## **Table of Contents**

1. [Requirements](#requirements)
2. [Installation & Setup](#installation--setup)
   - [1. Clone Repo](#1-clone-repo)
   - [2. Create .env File](#2-create-env-file)
   - [3. Install Dependencies](#3-install-dependencies)
   - [4. Prepare the Database](#4-prepare-the-database)
   - [5. Run the App](#5-run-the-app)
3. [Development Environment Setup](#development-environment-setup)
4. [Downloading and Managing LLM Models](#downloading-and-managing-llm-models)
5. [API Endpoints](#api-endpoints)
   - [Synchronous Code Review](#synchronous-code-review)
   - [Asynchronous Job-Based Review](#asynchronous-job-based-review)
6. [Sample curl Commands](#sample-curl-commands)
7. [Local Development](#local-development)
   - [Running Tests](#running-tests)
   - [Docker Usage (Optional)](#docker-usage-optional)
8. [Performance Benchmarks](#performance-benchmarks)
9. [FAQ / Troubleshooting](#faq--troubleshooting)

---

## **Getting Started in 5 Minutes** 🚀

1. **Clone & Setup:**
   ```bash
   git clone https://github.com/aibos-dev/llm-code-reviewer-api.git
   cd llm-code-reviewer-api
   ```

2. **Configure & Run:**
   ```bash
   # Create minimal .env file
   echo "POSTGRES_USER=postgres\nPOSTGRES_PASSWORD=postgres\nPOSTGRES_DB=llm_review_db\nPOSTGRES_HOST=localhost\nPOSTGRES_PORT=5432" > .env
   
   # Install dependencies
   uv sync
   
   # Create database
   psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE llm_review_db;"
   
   # Run database migrations
   alembic upgrade head
   
   # Start the API
   uvicorn src.main:app --reload
   ```

3. **Test with a simple API call:**
   ```bash
   curl -X POST "http://localhost:8000/v2/jobs" \
     -H "Content-Type: application/json" \
     -d '{"language":"Python","sourceCode":"print(\"Hello, world!\")","diff":"","options":{}}'
   ```

## **Docker Compose Usage**

You can easily run the entire application stack (API, database, Ollama) using Docker Compose:

### **Starting the Application Stack**

```bash
# Build and start all services in detached mode
docker-compose -f docker-compose.yml up --build -d
```

This command:
- Builds all necessary containers
- Starts PostgreSQL, the FastAPI application, and Ollama
- Runs everything in detached mode (background)

### **Stopping and Cleaning Up**

```bash
# Stop all services and remove volumes
docker-compose -f docker-compose.yml down -v
```

This command:
- Stops all running containers
- Removes all created containers
- Deletes associated volumes (-v flag)
- Cleans up the environment completely

---

## **Requirements**

- **Python 3.12** or later
- **PostgreSQL** (14 or later)
- **[Ollama](https://ollama.ai/)** for local LLM inference
- **Docker** and **Docker Compose** for containerized development
- **NVIDIA GPU** (optional, but recommended for better performance)

---

## **Installation & Setup**

### **1. Clone Repo**

```bash
git clone https://github.com/aibos-dev/llm-code-reviewer-api.git
cd llm-code-reviewer-api
```

### **2. Create .env File**

Create a `.env` file in the root directory:

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=llm_review_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

> If using Docker, set `POSTGRES_HOST=postgres`.

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

Run the database migrations:

```bash
alembic upgrade head
```

### **5. Run the App**

```bash
# Option 1: Run directly
uvicorn src.main:app --reload

# Option 2: Run via CLI
python src/main.py --host 0.0.0.0 --port 8000 --debug True
```

Now your API is live at `http://localhost:8000`.

The docs are also available at `http://localhost:8000/docs`.

---

## **Development Environment Setup**

1. **Prerequisites:**

   - Install **Docker**: [https://www.docker.com/](https://www.docker.com/)
   - Install your preferred code editor or IDE

2. **Setting Up Development Environment:**

   - Clone the repository and navigate to the project directory
   - Set up the environment variables as described in the installation section
   - Install the development dependencies

3. **Accessing the Development Environment:**

   - Open a terminal in your project directory
   - Run the API: `uvicorn src.main:app --reload`
   - Access the API at `http://localhost:8000`

---

## **Downloading and Managing LLM Models**

### **1. Adding a Custom Model to Ollama**

To introduce a new model to Ollama, follow these steps:

1. Ensure the model is compatible with Ollama
2. Use the command `ollama pull <model-name>` to download the model
3. Update `llm_engines/ollama_engine.py` to include the new model
4. Restart the API service to apply changes

Default models that come pre-installed with Ollama:
- `llama2`
- `codellama`
- `mistral`
- `orca-mini`

### **2. Downloading the DeepSeek Model**

Run the following command to fetch the required LLM model:
```bash
./download_model.sh
```

### **3. Managing the prompt in the `config.json`**

The prompt used for code reviews can be customized in the `config.json` file:

```json
{
  "prompt": "Provide detailed feedback on the given code snippet...",
  "categories": ["Security", "Performance", "Readability", "Best Practices"]
}
```

After modifying the `config.json` file, you need to restart the API service for the changes to take effect:

```bash
# If running directly
# Press Ctrl+C to stop the current process, then restart:
uvicorn src.main:app --reload

# If running with Docker Compose
docker-compose restart app
```

### **4. Listing Available Models in Ollama**
Check available models:
```bash
ollama list
```

---

## **API Endpoints**

The API provides both synchronous and asynchronous code review endpoints, making it suitable for integration with various clients including IDE extensions, CI/CD pipelines, or standalone applications.

### **Synchronous Code Review**

#### **1. POST `/v2/review`**
**Request Body:**
```json
{
  "language": "Python",
  "sourceCode": "def example():\n    return True",
  "fileName": "example.py",
  "diff": "...",
  "options": {}
}
```
**Response:**
```json
{
  "reviewId": "<uuid>",
  "reviews": [
    { "category": "General Feedback", "message": "..." },
    { "category": "Code Readability", "message": "..." }
  ]
}
```

#### **2. POST `/v2/review/feedback`**  
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


#### **3. PUT `/v2/jobs/{jobId}`**  
**Request Body:**
```json
{
  "status": "canceled"
}

```
**Response:**
```json
{
    "detail": "Job canceled."
}
```

---

## **Performance Benchmarks**

### **Performance on NVIDIA RTX A6000 GPU**

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

## **Feedback Extraction**
**Command Line Arguments:**

- **--output**: Specify output filename
- **--days**: Number of days of data to extract
- **--format**: Choose between CSV or JSON output
- **--include-code**: Option to include source code (warning: large files)

---

### **Usage Examples**

### **Basic usage (exports last 30 days of feedback to CSV):**
```bash
python feedback_extractor.py
```

### **Export last 90 days of feedback to a specific file:**
```bash
python feedback_extractor.py --days 90 --output quarterly_feedback.csv
```

### **Export to JSON format:**
```bash
python feedback_extractor.py --format json --output feedback_data.json
```

### **Include source code in the export (caution: large file):**
```bash
python feedback_extractor.py --include-code
```
---

## **Error Handling & Response Codes**

### **Common Error Codes**

| HTTP Status | Meaning |
|------------|---------|
| 400 | Bad Request - Invalid input provided |
| 401 | Unauthorized - Authentication failed |
| 403 | Forbidden - Access denied |
| 404 | Not Found - Requested resource not available |
| 422 | Unprocessable Entity - Validation errors |
| 500 | Internal Server Error - Unexpected issue |

---

## **Integration with Client Applications**

This API is designed to be integrated with various client applications:

- **IDE Extensions**: Can be integrated with extensions for Visual Studio, Visual Studio Code, JetBrains IDEs, etc.
- **CI/CD Pipelines**: Can be used in automated code review workflows
- **Web Applications**: Can provide code review capabilities in web-based platforms
- **CLI Tools**: Can be integrated with command-line tools for development workflows

The API provides a standardized interface that makes it easy to build various tools and extensions that require code review functionality.

---

## **FAQ / Troubleshooting**

### **Common Issues**

1. **Database connection errors**: Ensure PostgreSQL is running and the connection details in `.env` file are correct

2. **Ollama model not found**: Run `ollama pull <model-name>` to download the required model

3. **API startup failures**: Check the logs for detailed error messages and ensure all dependencies are installed

4. **Slow response times**: For large code files, the LLM processing can take significant time. Consider using the asynchronous endpoints for better user experience

### **Advanced Configuration**

For advanced configuration options, check the `config.json` file and the environment variables documented in the installation section.

---

**Happy Coding!** Contributions, issues, and PRs are welcome.