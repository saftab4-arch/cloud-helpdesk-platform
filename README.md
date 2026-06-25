# Cloud Help Desk Platform

A production-style Help Desk Ticket System built with Flask, PostgreSQL, Nginx, Gunicorn, Docker, Docker Compose, GitHub Actions, AWS ECR, and manual CD deployment testing.

This project was built as a real DevOps workflow:

```text
Local Development
    ↓
Docker Compose Dev Stack
    ↓
GitHub Actions CI
    ↓
Python Matrix Testing
    ↓
Ruff Linting
    ↓
Artifact Upload
    ↓
Docker Image Build
    ↓
Push Image to AWS ECR
    ↓
Production Compose Pulls Image from ECR
```

---

# Project Architecture

## Local Development Architecture

```text
Browser
   ↓
localhost:8080
   ↓
Nginx Reverse Proxy Container
   ↓
Gunicorn
   ↓
Flask Help Desk App Container
   ↓
PostgreSQL Container
   ↓
Docker Named Volume
```

## CI/CD Architecture

```text
GitHub Push / Pull Request
        ↓
GitHub Actions
        ↓
Matrix Test: Python 3.12 and 3.13
        ↓
pytest
        ↓
ruff
        ↓
Upload Test Artifacts
        ↓
Build Docker Image
        ↓
Login to AWS ECR
        ↓
Push Image to ECR
```

## Production Image Flow

```text
AWS ECR
   ↓
docker-compose.prod.yml
   ↓
Pulls ECR Image
   ↓
Runs Web Container
   ↓
Nginx Routes Traffic to Flask
```

---

# Technologies Used

* Python Flask
* Gunicorn
* PostgreSQL
* Nginx
* Docker
* Docker Compose
* GitHub Actions
* AWS ECR
* IAM Access Keys for GitHub Actions
* pytest
* ruff
* Git
* GitHub

---

# Final Project Structure

```text
cloud-helpdesk-platform/
│
├── app/
│   ├── app.py
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   └── requirements-dev.txt
│
├── nginx/
│   └── default.conf
│
├── tests/
│   └── test_app.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
└── README.md
```

---

# What the App Does

This is a simple Help Desk Ticket System.

Users can create support tickets with:

* Ticket title
* Description
* Priority
* Status

The ticket is stored in PostgreSQL and displayed on the web page.

Example ticket:

```text
ID: 1
Title: Printer Issue
Description: Cannot print from library
Priority: High
Status: Open
```

---

# Application Code

## `app/app.py`

```python
from flask import Flask, request, redirect
import os
import psycopg2

app = Flask(__name__)


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open'
        );
        """
    )
    conn.commit()
    cur.close()
    conn.close()


@app.route("/health")
def health():
    return "healthy", 200


@app.route("/", methods=["GET", "POST"])
def tickets():
    init_db()

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        priority = request.form["priority"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tickets (title, description, priority) VALUES (%s, %s, %s)",
            (title, description, priority),
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, description, priority, status FROM tickets ORDER BY id DESC")
    tickets = cur.fetchall()
    cur.close()
    conn.close()

    ticket_rows = ""
    for ticket in tickets:
        ticket_rows += f"""
        <tr>
            <td>{ticket[0]}</td>
            <td>{ticket[1]}</td>
            <td>{ticket[2]}</td>
            <td>{ticket[3]}</td>
            <td>{ticket[4]}</td>
        </tr>
        """

    return f"""
    <h1>Help Desk Ticket System</h1>

    <form method="POST">
        <input name="title" placeholder="Ticket title" required><br><br>
        <textarea name="description" placeholder="Ticket description" required></textarea><br><br>
        <select name="priority">
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
        </select><br><br>
        <button type="submit">Create Ticket</button>
    </form>

    <h2>Tickets</h2>
    <table border="1" cellpadding="8">
        <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Description</th>
            <th>Priority</th>
            <th>Status</th>
        </tr>
        {ticket_rows}
    </table>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

---

# Python Dependencies

## `app/requirements.txt`

Production dependencies only:

```text
Flask==3.1.1
gunicorn==23.0.0
psycopg2-binary==2.9.10
redis==6.2.0
```

## `app/requirements-dev.txt`

Testing and linting dependencies:

```text
-r requirements.txt

pytest==8.4.1
ruff==0.12.0
```

Why separate files?

```text
requirements.txt       → used inside production Docker image
requirements-dev.txt   → used by GitHub Actions for testing/linting
```

This keeps the production image cleaner.

---

# Dockerfile

## `app/Dockerfile`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN useradd -m appuser

USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

## Dockerfile Explanation

```dockerfile
FROM python:3.13-slim
```

Uses a smaller Python base image instead of a full Ubuntu image.

```dockerfile
WORKDIR /app
```

Sets `/app` as the working directory inside the container.

```dockerfile
COPY requirements.txt .
```

Copies only the dependency file first to improve Docker layer caching.

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

Installs only production dependencies.

```dockerfile
COPY app.py .
```

Copies the Flask application code.

```dockerfile
RUN useradd -m appuser
USER appuser
```

Creates and runs the app as a non-root user.

```dockerfile
EXPOSE 5000
```

Documents that the container listens on port `5000`.

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

Runs the Flask app using Gunicorn instead of the Flask development server.

---

# Docker Ignore

## `app/.dockerignore`

```text
__pycache__
*.pyc
.env
.git
```

This prevents unnecessary files from being copied into the Docker image.

---

# Environment Variables

## `.env.example`

```env
POSTGRES_USER=helpdesk
POSTGRES_PASSWORD=helpdeskpass
POSTGRES_DB=helpdeskdb
POSTGRES_HOST=db
```

Create your local `.env` file:

```bash
cp .env.example .env
```

The `.env` file is ignored by Git.

---

# Nginx Reverse Proxy

## `nginx/default.conf`

```nginx
server {
    listen 80;

    location / {
        proxy_pass http://web:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Nginx receives traffic on port `80` inside the container and forwards it to:

```text
web:5000
```

`web` is the Docker Compose service name for the Flask app.

---

# Docker Compose Development File

## `docker-compose.dev.yml`

```yaml
services:

  nginx:
    image: nginx:1.27-alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - web
    networks:
      - frontend

  web:
    build: ./app
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    networks:
      - frontend
      - backend

  db:
    image: postgres:16-alpine
    env_file:
      - .env
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U helpdesk -d helpdeskdb"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

networks:
  frontend:
  backend:

volumes:
  postgres-data:
```

## Development Compose Flow

```text
Browser
   ↓
localhost:8080
   ↓
nginx container
   ↓
web container
   ↓
db container
```

## Why Two Docker Networks?

This project uses two networks:

```text
frontend
backend
```

### Frontend Network

```text
nginx ↔ web
```

### Backend Network

```text
web ↔ db
```

Nginx does not need direct access to PostgreSQL, so PostgreSQL stays on the backend network only.

This mimics real AWS tiered architecture:

```text
Public Tier
   ↓
Application Tier
   ↓
Database Tier
```

---

# Docker Compose Production File

## `docker-compose.prod.yml`

```yaml
services:

  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - web
    networks:
      - frontend

  web:
    image: 218908193290.dkr.ecr.us-east-1.amazonaws.com/helpdesk-ticket-system:latest
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    networks:
      - frontend
      - backend

  db:
    image: postgres:16-alpine
    env_file:
      - .env
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U helpdesk -d helpdeskdb"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

networks:
  frontend:
  backend:

volumes:
  postgres-data:
```

## Difference Between Dev and Prod Compose

### Dev Compose

```yaml
web:
  build: ./app
```

This builds the image locally from the Dockerfile.

### Prod Compose

```yaml
web:
  image: 218908193290.dkr.ecr.us-east-1.amazonaws.com/helpdesk-ticket-system:latest
```

This pulls the image from AWS ECR.

---

# Healthcheck

PostgreSQL healthcheck:

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U helpdesk -d helpdeskdb"]
  interval: 10s
  timeout: 5s
  retries: 5
```

This checks whether PostgreSQL is ready before Flask starts.

Without this, Flask might start before the database is ready and fail with connection errors.

Flow:

```text
Start PostgreSQL
   ↓
Run pg_isready
   ↓
Database healthy?
   ↓
Start Flask app
```

---

# Local Development Commands

## 1. Clone Repository

```bash
git clone git@github.com:saftab4-arch/cloud-helpdesk-platform.git
cd cloud-helpdesk-platform
```

## 2. Create Environment File

```bash
cp .env.example .env
```

## 3. Start Development Stack

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

## 4. Check Containers

```bash
docker compose -f docker-compose.dev.yml ps
```

Expected:

```text
db       healthy
web      running
nginx    running
```

## 5. Open App

```text
http://localhost:8080
```

## 6. Create Test Ticket

Example:

```text
Title: Printer Issue
Description: Cannot print from library
Priority: High
```

Expected result:

```text
ID: 1
Printer Issue
Cannot print from library
High
Open
```

---

# Database Persistence Test

Stop the stack:

```bash
docker compose -f docker-compose.dev.yml down
```

Start it again:

```bash
docker compose -f docker-compose.dev.yml up -d
```

Refresh:

```text
http://localhost:8080
```

The ticket should still exist.

Why?

Because PostgreSQL data is stored inside a Docker named volume:

```yaml
volumes:
  postgres-data:
```

The container can be removed and recreated, but the database files remain.

---

# Local Testing Before GitHub Actions

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Install test dependencies:

```bash
pip install -r app/requirements-dev.txt
```

Run tests:

```bash
pytest
```

Expected:

```text
1 passed
```

Run linting:

```bash
ruff check .
```

Expected:

```text
All checks passed!
```

---

# Test File

## `tests/test_app.py`

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app import app


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.data == b"healthy"
```

This test verifies that the Flask health endpoint works.

---

# Git Ignore

## `.gitignore`

```gitignore
venv/
__pycache__/
*.pyc
.env
.pytest_cache/
.ruff_cache/
```

This prevents local virtual environments, cache files, and secrets from being committed.

---

# GitHub Actions CI/CD Workflow

## `.github/workflows/ci.yml`

```yaml
name: CI Build Push

on:
  push:
    branches:
      - main

  pull_request:
    branches:
      - main

jobs:

  test:
    name: Test and Lint
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version:
          - "3.12"
          - "3.13"

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r app/requirements-dev.txt

      - name: Run tests
        run: pytest

      - name: Run Ruff
        run: ruff check .

      - name: Upload test artifacts
        uses: actions/upload-artifact@v4
        with:
          name: test-artifacts-python-${{ matrix.python-version }}
          path: tests/

  build-and-push:
    name: Build and Push to ECR
    runs-on: ubuntu-latest
    needs: test

    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build Docker image
        run: |
          docker build -t ${{ secrets.ECR_REPOSITORY }}:latest ./app

      - name: Tag Docker image for ECR
        run: |
          docker tag ${{ secrets.ECR_REPOSITORY }}:latest ${{ steps.login-ecr.outputs.registry }}/${{ secrets.ECR_REPOSITORY }}:latest

      - name: Push Docker image to ECR
        run: |
          docker push ${{ steps.login-ecr.outputs.registry }}/${{ secrets.ECR_REPOSITORY }}:latest
```

---

# GitHub Actions Explanation

## Pull Request Behavior

On pull requests:

```text
pytest
ruff
artifact upload
```

Only testing happens.

## Push to Main Behavior

On push to main:

```text
pytest
ruff
artifact upload
docker build
docker tag
docker push to ECR
```

The image is only pushed to ECR when code reaches `main`.

This is controlled by:

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

This prevents unmerged pull request code from being pushed as a production image.

---

# GitHub Secrets Required

In GitHub:

```text
Repository → Settings → Secrets and variables → Actions
```

Create these repository secrets:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
ECR_REPOSITORY
```

Example values:

```text
AWS_REGION=us-east-1
ECR_REPOSITORY=helpdesk-ticket-system
```

Do not commit AWS keys into GitHub.

---

# AWS ECR Setup

## 1. Create ECR Repository

AWS Console:

```text
ECR → Private Registry → Repositories → Create repository
```

Repository name:

```text
helpdesk-ticket-system
```

Repository URI:

```text
218908193290.dkr.ecr.us-east-1.amazonaws.com/helpdesk-ticket-system
```

## 2. IAM User for GitHub Actions

Create IAM user:

```text
github-actions-ecr-helpdesk
```

Attach permission:

```text
AmazonEC2ContainerRegistryPowerUser
```

Create access key and save it in GitHub Secrets.

---

# ECR Authentication Explained

ECR is private.

Docker cannot pull from ECR unless it logs in first.

The command:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 218908193290.dkr.ecr.us-east-1.amazonaws.com
```

means:

```text
AWS CLI gets temporary ECR password
   ↓
Password is passed to Docker
   ↓
Docker logs into ECR
   ↓
Docker can pull or push images
```

Docker does not understand IAM directly.

AWS CLI translates IAM permission into a temporary Docker login token.

---

# Manual CD Test from ECR

After GitHub Actions pushes the image to ECR, test pulling it locally.

## 1. Login to ECR

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 218908193290.dkr.ecr.us-east-1.amazonaws.com
```

Expected:

```text
Login Succeeded
```

## 2. Stop Dev Stack

```bash
docker compose -f docker-compose.dev.yml down
```

## 3. Pull ECR Image

```bash
docker pull 218908193290.dkr.ecr.us-east-1.amazonaws.com/helpdesk-ticket-system:latest
```

## 4. Run Production Compose

```bash
docker compose -f docker-compose.prod.yml up -d
```

## 5. Verify Running Containers

```bash
docker ps
```

Expected:

```text
nginx:1.27-alpine
218908193290.dkr.ecr.us-east-1.amazonaws.com/helpdesk-ticket-system:latest
postgres:16-alpine
```

## 6. Open App

```text
http://localhost
```

or if mapped differently:

```text
http://localhost:80
```

---

# Commands Used During This Project

## Create Project

```bash
mkdir cloud-helpdesk-platform
cd cloud-helpdesk-platform
git init

mkdir app nginx tests .github .github/workflows

touch app/app.py
touch app/requirements.txt
touch app/requirements-dev.txt
touch app/Dockerfile
touch app/.dockerignore

touch nginx/default.conf
touch tests/test_app.py

touch docker-compose.dev.yml
touch docker-compose.prod.yml
touch .env.example
touch README.md
touch .github/workflows/ci.yml
```

## Create Environment File

```bash
cp .env.example .env
```

## Start Dev Stack

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

## Check Status

```bash
docker compose -f docker-compose.dev.yml ps
docker ps
```

## Check Logs

```bash
docker compose -f docker-compose.dev.yml logs web
docker compose -f docker-compose.dev.yml logs nginx
docker compose -f docker-compose.dev.yml logs db
```

## Stop Dev Stack

```bash
docker compose -f docker-compose.dev.yml down
```

## Run Tests Locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r app/requirements-dev.txt
pytest
ruff check .
```

## Git Cleanup After Accidentally Adding venv

```bash
git reset --soft HEAD^
```

Create `.gitignore`:

```bash
nano .gitignore
```

Then remove tracked venv files:

```bash
git rm -r --cached venv
git rm --cached .env
```

Commit clean version:

```bash
git add .
git commit -m "Remove venv and add gitignore"
git push
```

Verify venv is no longer tracked:

```bash
git ls-files | grep venv
```

Expected:

```text
no output
```

## ECR Login

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 218908193290.dkr.ecr.us-east-1.amazonaws.com
```

## Pull ECR Image

```bash
docker pull 218908193290.dkr.ecr.us-east-1.amazonaws.com/helpdesk-ticket-system:latest
```

## Run Prod Compose

```bash
docker compose -f docker-compose.prod.yml up -d
```

---

# Troubleshooting

## Problem: `venv/` accidentally committed

### Cause

The virtual environment was created before adding `.gitignore`.

### Fix

```bash
git reset --soft HEAD^
nano .gitignore
git rm -r --cached venv
git add .
git commit -m "Remove venv and add gitignore"
```

---

## Problem: AWS CLI not found

Error:

```text
Command 'aws' not found
```

### Fix on Ubuntu

```bash
sudo snap install aws-cli --classic
```

Verify:

```bash
aws --version
```

---

## Problem: `password is empty` during Docker login

### Cause

AWS CLI was not installed or AWS credentials were not configured.

### Fix

```bash
aws configure
aws sts get-caller-identity
```

Then retry:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 218908193290.dkr.ecr.us-east-1.amazonaws.com
```

---

## Problem: Flask starts before PostgreSQL

### Cause

The database container may be running but not ready.

### Fix

Use Compose healthcheck:

```yaml
depends_on:
  db:
    condition: service_healthy
```

---

## Problem: Local works but GitHub Actions fails

### Troubleshooting Steps

Run locally:

```bash
pytest
ruff check .
```

Check file paths:

```bash
ls app
ls tests
```

Check dependency file:

```bash
cat app/requirements-dev.txt
```

---

# Cleanup Commands

## Stop Containers

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.prod.yml down
```

## Delete Local Image

```bash
docker rmi 218908193290.dkr.ecr.us-east-1.amazonaws.com/helpdesk-ticket-system:latest
```

## Delete ECR Repository

AWS Console:

```text
ECR → Repositories → helpdesk-ticket-system → Delete
```

## Delete IAM User

AWS Console:

```text
IAM → Users → github-actions-ecr-helpdesk → Delete access key → Delete user
```

## Remove Local AWS Credentials

Only do this if these credentials were only used for this lab:

```bash
rm ~/.aws/credentials
rm ~/.aws/config
```

---

# What Was Verified

* Flask application runs
* Gunicorn starts the app
* Nginx reverse proxy routes traffic to Flask
* PostgreSQL stores tickets
* Docker Compose creates frontend and backend networks
* PostgreSQL healthcheck works
* PostgreSQL named volume preserves data
* pytest passes
* ruff passes
* GitHub Actions matrix build works
* GitHub Actions uploads artifacts
* GitHub Actions builds Docker image
* GitHub Actions pushes image to AWS ECR
* Local machine pulls image from ECR
* Production Compose runs using ECR image

---

# Resume Bullet Points

* Built a containerized Help Desk Ticket System using Flask, PostgreSQL, Nginx, Gunicorn, Docker, and Docker Compose.
* Designed a multi-network Docker Compose architecture separating frontend and backend traffic.
* Implemented PostgreSQL healthchecks and persistent named volumes for reliable database startup and data durability.
* Built a GitHub Actions CI pipeline with Python matrix testing, pytest, ruff linting, and artifact uploads.
* Integrated AWS ECR as a private container registry and automated Docker image build, tag, and push workflows.
* Tested manual CD by pulling production images from AWS ECR and running the application using a production Docker Compose file.
* Practiced secure secret handling using GitHub Actions repository secrets and AWS IAM access keys.

---

# Next Phase

The next version of this project will replace manual AWS steps with Terraform.

Terraform will create:

```text
VPC
Subnets
Internet Gateway
Route Tables
Security Groups
IAM Role
EC2
ECR
ALB
Target Group
Listener
```

The application workflow will remain:

```text
GitHub Actions
   ↓
Build Docker Image
   ↓
Push to ECR
   ↓
EC2 Pulls Image
   ↓
Docker Compose Runs App
```

This project is the baseline for the Terraform version.
