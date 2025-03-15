"""
main.py
================
Main Entry Point
================
"""

import logging
import sys
import os
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api import router as review_router
from .database import engine
from .models_db import Base
from .schemas import CliArgs

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s : %(message)s")

# Create tables if they do not already exist
Base.metadata.create_all(bind=engine)

# Set up static files and templates directories
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

# Create directories if they don't exist
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

# Create CSS file for custom documentation
custom_css_path = static_dir / "custom.css"
if not custom_css_path.exists():
    with open(custom_css_path, "w") as f:
        f.write("""
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        pre {
            background-color: #f5f5f5;
            padding: this 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        code {
            font-family: 'Courier New', Courier, monospace;
        }
        .endpoint {
            margin-bottom: 30px;
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
        }
        .toggle-container {
            position: fixed;
            top: 10px;
            right: 20px;
            background-color: #fff;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            z-index: 1000;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f5f5f5;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .btn {
            display: inline-block;
            padding: 8px 12px;
            background-color: #4a6cf7;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
        }
        """)

# Create HTML template for custom documentation
custom_docs_path = templates_dir / "custom_docs.html"
if not custom_docs_path.exists():
    # Create custom documentation HTML template using the markdown content
    with open(custom_docs_path, "w") as f:
        f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Code Review API Documentation</title>
    <link rel="stylesheet" href="{{ url_for('static', path='/custom.css') }}">
</head>
<body>
    <div class="toggle-container">
        <a href="/swagger-docs" class="btn">Switch to Swagger UI</a>
    </div>
    
    <h1>LLM Code Review API Documentation</h1>
    
    <p>This documentation provides details on endpoints, request/response formats, and examples for the LLM-powered code review API.</p>
    
    <h2>Base URL</h2>
    <pre><code>http://35.221.116.53:8000</code></pre>
    
    <h2>Authentication</h2>
    <p>Currently, the API does not require authentication.</p>
    
    <h2>Endpoints</h2>
    
    <div class="endpoint">
        <h3>1. Synchronous Code Review</h3>
        <p>Performs a synchronous code review and returns results immediately.</p>
        
        <p><strong>Endpoint:</strong> <code>POST /v2/review</code></p>
        
        <p><strong>Request Body:</strong></p>
        <pre><code>{
  "language": "string",          // Required: Programming language of the code
  "sourceCode": "string",        // Required: The source code to review
  "fileName": "string",          // Optional: Name of the file
  "diff": "string",              // Optional: Git diff output if applicable
  "options": {}                  // Optional: Additional configuration options
}</code></pre>
        
        <p><strong>Response:</strong></p>
        <pre><code>{
  "reviewId": "string",          // UUID of the review
  "reviews": [                   // Array of review categories
    {
      "category": "string",      // Category name (e.g., "General Feedback", "Security")
      "message": "string"        // Detailed feedback message
    }
  ]
}</code></pre>
        
        <p><strong>Example:</strong></p>
        <pre><code>curl -X POST "http://35.221.116.53:8000/v2/review" \\
  -H "Content-Type: application/json" \\
  -d '{
    "language": "Python",
    "sourceCode": "def process_data(data):\\n    return data.process()",
    "fileName": "processor.py",
    "diff": "",
    "options": {}
  }'</code></pre>
    </div>
    
    <div class="endpoint">
        <h3>2. Submit Review Feedback</h3>
        <p>Allows users to provide feedback on a review.</p>
        
        <p><strong>Endpoint:</strong> <code>POST /v2/review/feedback</code></p>
        
        <p><strong>Request Body:</strong></p>
        <pre><code>{
  "reviewId": "string",        // Required: UUID of the review
  "feedbacks": [               // Required: Array of feedback items
    {
      "category": "string",    // Category name that received feedback
      "feedback": "string"     // Feedback value (e.g., "Good", "Bad")
    }
  ]
}</code></pre>
        
        <p><strong>Response:</strong></p>
        <pre><code>{
  "status": "success",
  "message": "Feedback saved."
}</code></pre>
        
        <p><strong>Example:</strong></p>
        <pre><code>curl -X POST "http://35.221.116.53:8000/v2/review/feedback" \\
  -H "Content-Type: application/json" \\
  -d '{
    "reviewId": "550e8400-e29b-41d4-a716-446655440000",
    "feedbacks": [
      { "category": "General Feedback", "feedback": "Good" },
      { "category": "Security", "feedback": "Bad" }
    ]
  }'</code></pre>
    </div>
    
    <div class="endpoint">
        <h3>3. Create Asynchronous Review Job</h3>
        <p>Creates a new code review job to be processed asynchronously.</p>
        
        <p><strong>Endpoint:</strong> <code>POST /v2/jobs</code></p>
        
        <p><strong>Request Body:</strong></p>
        <pre><code>{
  "language": "string",        // Required: Programming language of the code
  "sourceCode": "string",      // Required: The source code to review
  "fileName": "string",        // Optional: Name of the file
  "diff": "string",            // Optional: Git diff output if applicable
  "options": {}                // Optional: Additional configuration options
}</code></pre>
        
        <p><strong>Response:</strong></p>
        <pre><code>{
  "jobId": "string",           // UUID of the created job
  "status": "queued",          // Status of the job
  "message": "Job accepted. Check status via GET /v2/jobs/{jobId}"
}</code></pre>
        
        <p><strong>Example:</strong></p>
        <pre><code>curl -X POST "http://35.221.116.53:8000/v2/jobs" \\
  -H "Content-Type: application/json" \\
  -d '{
    "language": "JavaScript",
    "sourceCode": "function calculateTotal(items) {\\n  return items.reduce((acc, item) => acc + item.price, 0);\\n}",
    "fileName": "calculator.js",
    "diff": "",
    "options": {}
  }'</code></pre>
    </div>
    
    <div class="endpoint">
        <h3>4. Check Job Status</h3>
        <p>Retrieves the status and results of an asynchronous review job.</p>
        
        <p><strong>Endpoint:</strong> <code>GET /v2/jobs/{jobId}</code></p>
        
        <p><strong>Path Parameters:</strong></p>
        <ul>
            <li><code>jobId</code>: UUID of the job to check</li>
        </ul>
        
        <p><strong>Response:</strong></p>
        <pre><code>{
  "jobId": "string",           // UUID of the job
  "status": "string",          // Status: "queued", "in_progress", "completed", "canceled", or "error"
  "reviewId": "string",        // UUID of the review (if completed)
  "reviews": [                 // Array of review categories (if completed)
    {
      "category": "string",    // Category name
      "message": "string"      // Detailed feedback message
    }
  ]
}</code></pre>
        
        <p><strong>Example:</strong></p>
        <pre><code>curl -X GET "http://35.221.116.53:8000/v2/jobs/550e8400-e29b-41d4-a716-446655440000"</code></pre>
    </div>
    
    <div class="endpoint">
        <h3>5. Cancel Job</h3>
        <p>Cancels an in-progress job.</p>
        
        <p><strong>Endpoint:</strong> <code>PUT /v2/jobs/{jobId}</code></p>
        
        <p><strong>Path Parameters:</strong></p>
        <ul>
            <li><code>jobId</code>: UUID of the job to cancel</li>
        </ul>
        
        <p><strong>Request Body:</strong></p>
        <pre><code>{
  "status": "canceled"
}</code></pre>
        
        <p><strong>Response:</strong></p>
        <pre><code>{
  "jobId": "string",           // UUID of the job
  "status": "canceled",        // Updated status
  "message": "Job has been canceled."
}</code></pre>
        
        <p><strong>Example:</strong></p>
        <pre><code>curl -X PUT "http://35.221.116.53:8000/v2/jobs/550e8400-e29b-41d4-a716-446655440000" \\
  -H "Content-Type: application/json" \\
  -d '{"status": "canceled"}'</code></pre>
    </div>
    
    <h2>Status Codes</h2>
    
    <table>
        <tr>
            <th>Status Code</th>
            <th>Description</th>
        </tr>
        <tr>
            <td>200</td>
            <td>Successful operation</td>
        </tr>
        <tr>
            <td>400</td>
            <td>Bad request (e.g., invalid input)</td>
        </tr>
        <tr>
            <td>404</td>
            <td>Resource not found</td>
        </tr>
        <tr>
            <td>409</td>
            <td>Conflict (e.g., trying to cancel a completed job)</td>
        </tr>
        <tr>
            <td>422</td>
            <td>Validation error</td>
        </tr>
        <tr>
            <td>500</td>
            <td>Internal server error</td>
        </tr>
    </table>
    
    <h2>Review Categories</h2>
    
    <p>The API returns feedback in multiple categories, including:</p>
    
    <ul>
        <li>General Feedback</li>
        <li>Memory Management</li>
        <li>Performance</li>
        <li>Null Check</li>
        <li>Security</li>
        <li>Coding Standard</li>
        <li>Error Handling</li>
        <li>Code Readability</li>
        <li>Concurrency Issues</li>
        <li>Scalability</li>
    </ul>
    
    <h2>Example Full Response</h2>
    
    <p>Here's an example response from a completed code review:</p>
    
    <pre><code>{
  "reviewId": "550e8400-e29b-41d4-a716-446655440000",
  "reviews": [
    {
      "category": "General Feedback",
      "message": "The code is generally well-structured but lacks error handling for edge cases. Consider adding input validation and appropriate exception handling."
    },
    {
      "category": "Security",
      "message": "Line 15: The function `process_user_input` doesn't sanitize user input before processing, which could lead to injection attacks. Consider using a validation library or implementing input sanitization."
    },
    {
      "category": "Performance",
      "message": "Line 27-35: The nested loops have O(n²) time complexity which may cause performance issues with large datasets. Consider using a more efficient algorithm or data structure."
    }
  ]
}</code></pre>
    
    <h2>Setting Up Environment</h2>
    
    <p>For local development, ensure you have:</p>
    
    <ol>
        <li>PostgreSQL database configured</li>
        <li>Ollama service running with the required model</li>
        <li>Correct environment variables set in <code>.env</code> file</li>
    </ol>
    
    <h2>Environment Variables</h2>
    
    <p>Key environment variables include:</p>
    
    <ul>
        <li><code>POSTGRES_USER</code>: Database username</li>
        <li><code>POSTGRES_PASSWORD</code>: Database password</li>
        <li><code>POSTGRES_DB</code>: Database name</li>
        <li><code>POSTGRES_HOST</code>: Database host</li>
        <li><code>POSTGRES_PORT</code>: Database port</li>
        <li><code>OLLAMA_HOST</code>: URL for Ollama service</li>
        <li><code>OLLAMA_MODEL</code>: Model name to use for code reviews</li>
    </ul>
    
    <h2>Docker Support</h2>
    
    <p>The API supports containerized deployment using Docker and Docker Compose. See the README for details on setting up with Docker.</p>
</body>
</html>
        """)

# Create FastAPI app with metadata
app = FastAPI(
    title="LLM Code Review API",
    description="LLM-powered code review API with synchronous and asynchronous options",
    version="1.0",
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable ReDoc
)

app.include_router(review_router)

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Default route redirects to custom docs
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

# Custom documentation endpoint
@app.get("/docs", include_in_schema=False)
async def custom_docs(request: Request):
    return templates.TemplateResponse("custom_docs.html", {"request": request})

# Swagger UI documentation endpoint
@app.get("/swagger-docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        swagger_ui_parameters={"docExpansion": "list", "defaultModelsExpandDepth": 1},
        init_oauth=None,
    )


def main() -> None:
    try:
        from tap import Tap  # typed-argument-parser
    except ImportError:
        logger.exception("Tap module not installed. Please `pip install typed-argument-parser`.")
        sys.exit(1)

    class ArgsParser(Tap):
        host: str = "127.0.0.1"
        port: int = 8000
        debug: bool = False

    parsed_args = ArgsParser().parse_args()
    cli_args = CliArgs(host=parsed_args.host, port=parsed_args.port, debug=parsed_args.debug)

    import uvicorn

    uvicorn.run("src.main:app", host=cli_args.host, port=cli_args.port, reload=cli_args.debug)


if __name__ == "__main__":
    main()