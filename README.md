# PDF-GPT (RAG Application)

**PDF-GPT** is a Retrieval-Augmented Generation (RAG) application that allows users to upload PDFs and chat with an AI model. The system uses OpenAI GPT models and an in-memory vector store to provide contextual answers from the PDF, supplemented by the AI's general knowledge. User conversation data is persisted in Redis, ensuring session continuity across restarts or multiple replicas.

## Table of Contents

- [Overview](#overview)  
- [Features](#features)  
- [Tech Stack](#tech-stack)  
- [Project Structure](#project-structure)  
- [Setup & Installation](#setup--installation)  
  - [Local Development](#local-development)  
  - [Docker](#docker)  
  - [Kubernetes](#kubernetes)  
    - [Deploying Redis](#deploying-redis)  
- [Usage](#usage)  
- [Environment Variables](#environment-variables)  
- [Roadmap / Future Plans](#roadmap--future-plans)  
- [Contributing](#contributing)  
- [License](#license)  
- [Contact](#contact)

---

## Overview

This repository demonstrates how to build a **PDF-centric ChatGPT** application using **Retrieval-Augmented Generation (RAG)**. Users can upload a PDF, which the system splits and embeds into an **in-memory vector store** for quick retrieval. The user’s conversation data is stored in **Redis**, ensuring that session history remains persistent. The AI can reference the PDF context plus general knowledge, allowing it to be both PDF‐aware and more broadly informative.

The application:
- Runs in a **Gradio** UI on **port 5000** (by default).
- Supports **multiple GPT models**: `gpt-3.5-turbo`, `gpt-4o`, and `gpt-4o-mini`.
- Is containerized for easy deployment, with Kubernetes manifests for production use.

---

## Features

1. **PDF Upload & Extraction**  
   - Users upload a PDF. The file is split into chunks and embedded in memory for retrieval.

2. **Contextual Chat**  
   - Users ask questions in a chat interface. The AI fetches relevant PDF chunks to inform responses, while also leveraging its broader knowledge.

3. **Session Persistence with Redis**  
   - Chat history (conversation text) is stored in Redis, ensuring continuity across app restarts or pod migrations.

4. **Model Selection**  
   - Users can choose among `gpt-3.5-turbo`, `gpt-4o`, and `gpt-4o-mini`.

5. **Kubernetes Manifests**  
   - Includes YAML files for deploying the app (and a script for deploying Redis) on a cluster, plus examples of sticky sessions in the Ingress for multi-replica scenarios.

---

## Tech Stack

- **Python** (Primary language)
- **Gradio** (UI framework for chat)
- **OpenAI GPT Models** (User‐selectable models for generation)
- **DocArrayInMemorySearch** (In-memory vector store)
- **Redis** (Storing conversation states)
- **Kubernetes** (Deployment manifests)
- **(Optional) Terraform** (For IaC in future expansions)
- **AWS EFS** (Storage class for persistent volumes if desired)

---

## Project Structure

A simplified overview of key files:

```
PDF-gpt--RAG-Application-
│
├── app.py                     # Main Gradio application, RAG pipeline logic
├── pdf.py                     # PDFLoader class for extracting text
├── template.py                # Template prompt for the AI
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker build instructions
├── k8s/                       # Kubernetes YAML manifests (Deployment, Service, Ingress, etc.)
└── README.md                  # This README
```

- **`app.py`** – Core application logic (Gradio + retrieval chain).
- **`pdf.py`** – PDFLoader utility for reading/parsing PDF content.
- **`template.py`** – The specialized prompt template for contextual AI responses.
- **`k8s/`** – Example manifests for running the app on Kubernetes (Deployment, Service, Ingress).
- **`deploy-redis.sh`** – Script to install Redis on the cluster using Helm with an EFS-based storage class.

---

## Setup & Installation

### Local Development

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/JoeUzo/PDF-gpt--RAG-Application-.git
   cd PDF-gpt--RAG-Application-
   ```

2. **Create a Virtual Environment (Optional)**  
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**  
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**  
   - Copy `.env.example` to `.env` and fill in your credentials. See [Environment Variables](#environment-variables).

5. **Run the App**  
   ```bash
   python app.py
   ```
   It will start on `http://localhost:5000` by default.

### Docker

1. **Pull or Build the Image**  
   ```bash
   docker pull joeuzo/pdf-gpt:latest
   ```
   or build locally:
   ```bash
   docker build -t pdf-gpt:latest .
   ```

2. **Run the Container**  
   ```bash
   docker run -it --rm -p 5000:5000 \
     -e OPENAI_API_KEY=<your-openai-key> \
     -e REDIS_HOST=<your-redis-host> \
     -e REDIS_PORT=6379 \
     pdf-gpt:latest
   ```
   Access the app at `http://localhost:5000`.

### Kubernetes

1. **Deploy Redis**  
   - Use the provided `deploy-redis.sh` script or Helm directly to install a Redis instance, possibly in a `redis` namespace with EFS storage. Example:
     ```bash
     ./deploy-redis.sh
     ```
   - Confirm Redis is up and running: `kubectl get pods -n redis`

2. **Deploy the App**  
   - Adjust the `k8s/` manifests (Deployment, Service, Ingress) to your environment. Ensure:
     - `REDIS_HOST` is set to your Redis Service DNS (e.g. `my-redis.redis.svc.cluster.local`)
     - `REDIS_PORT` is `6379` (or your chosen port)
   - Apply the manifests:
     ```bash
     kubectl apply -f k8s/
     ```
3. **Expose via Ingress**  
   - By default, the Ingress uses cookie-based sticky sessions to ensure users remain pinned to a single pod if you scale the deployment.  
   - Access the application via your configured domain or Load Balancer address.

---

## Usage

1. **Upload a PDF**: Click “Upload PDF” and pick a file. The system displays a preview of the first page.  
2. **Ask a Question**: Type into the chat box. The AI references the PDF embeddings (and general knowledge if needed) to form an answer.  
3. **Reset Session**: Click “Reset Session” to clear your conversation in Redis and start fresh.  
4. **Model Choice**: Pick among `gpt-3.5-turbo`, `gpt-4o`, or `gpt-4o-mini` from the dropdown.

---

## Environment Variables

| Variable          | Description                                                             |
|-------------------|-------------------------------------------------------------------------|
| `OPENAI_API_KEY`  | Your OpenAI API key                                                     |
| `REDIS_HOST`      | The DNS or IP of your Redis Service (e.g. `my-redis.redis.svc.cluster.local`) |
| `REDIS_PORT`      | Redis port (usually `6379`)                                             |

---

## Roadmap / Future Plans

- **Distributed Vector Store**: If you want multi-replica scaling without sticky sessions, consider moving from in-memory to a shared vector DB.  
- **Advanced Authentication**: Add user accounts or SSO.  
- **Terraform**: Full infrastructure automation, including EFS provisioning, secrets, etc.  
- **Enhanced Logging & Monitoring**: Set up structured logs, Prometheus/Grafana for metrics, etc.  
- **Autoscaling**: HPA-based scaling if the load increases.  
- **Further Model Options**: Possibly integrate GPT-4 or other specialized LLMs.

---

## Contributing

1. **Fork** the repo on GitHub  
2. **Create** your feature branch: `git checkout -b feature/my-new-feature`  
3. **Commit** your changes: `git commit -m 'Add some feature'`  
4. **Push** to the branch: `git push origin feature/my-new-feature`  
5. **Open a Pull Request** on GitHub

All contributions—bug reports, feature requests, and PRs—are welcome!

---

## License

Licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Contact

- **Author**: [JoeUzo](https://github.com/JoeUzo)  
- **Repository**: [PDF-gpt--RAG-Application-](https://github.com/JoeUzo/PDF-gpt--RAG-Application-)
