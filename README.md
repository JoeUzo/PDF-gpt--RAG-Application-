# PDF-GPT (RAG Application)

**PDF-GPT** is a Retrieval-Augmented Generation (RAG) application that lets users upload PDFs and chat with an AI model (GPT-3.5-turbo) enhanced by document context. The application also integrates (or will integrate) with Pinecone for vector storage, AWS S3 for chat history storage, and (upcoming) Terraform/Kubernetes for infrastructure automation.

## Table of Contents

- [Overview](#overview)  
- [Features](#features)  
- [Tech Stack](#tech-stack)  
- [Project Structure](#project-structure)  
- [Setup & Installation](#setup--installation)  
  - [Local Environment](#local-environment)  
  - [Docker](#docker)  
- [Usage](#usage)  
- [Environment Variables](#environment-variables)  
- [Roadmap / Future Plans](#roadmap--future-plans)  
- [Contributing](#contributing)  
- [License](#license)  
- [Contact](#contact)

---

## Overview

This repository demonstrates how to build a **PDF-centric ChatGPT** application using **RAG (Retrieval-Augmented Generation)**. Users can upload a PDF, the text is extracted and turned into embeddings, which are stored in Pinecone. At query time, the relevant chunks from the user’s PDF are retrieved and fed into OpenAI’s GPT-3.5-turbo model to provide contextual answers. 

Currently, the app runs in a **Gradio** interface. The application also supports user sessions (via a simple username), with future plans to add:

- **Secure User Authentication**  
- **Chat History Storage** in AWS S3  
- **Infrastructure as Code** with Terraform  
- **Continuous Deployment** on Kubernetes  

---

## Features

1. **PDF Upload**: Users can upload a PDF file; the text is parsed and stored in Pinecone vector index.  
2. **Contextual Chat**: Users ask questions, and the AI retrieves relevant chunks from the PDF to inform the answer.  
3. **General Knowledge**: The AI can also leverage its general training if the question goes beyond the PDF scope.  
4. **Namespace-based Storage**: Each user’s vectors are stored under a unique namespace in Pinecone, preventing data overlap.  
5. **Dockerized**: There is a GitHub workflow that builds and pushes the Docker image to a public registry.  

---

## Tech Stack

- **Python**  
- **Gradio** for the interactive chat UI  
- **OpenAI GPT-3.5-turbo** for language generation  
- **Pinecone** for vector embeddings storage  
- **(Planned) AWS S3** for user chat history  
- **(Planned) Terraform** for cloud infrastructure provisioning  
- **(Planned) Kubernetes** for container orchestration  

---

## Project Structure

A simplified overview of key files:

```
PDF-gpt--RAG-Application-
│
├── .github/workflows/docker-image.yml   # CI workflow to build & push Docker images
├── .env.example                         # Example of environment variables (for local use)
├── Dockerfile                           # Docker build instructions
├── app.py                               # Main Gradio app with RAG pipeline
├── pdf.py                               # PDFLoader class for reading PDF content
├── requirements.txt                     # Python dependencies
├── README.md                            # This README
└── ...
```

- **`.env.example`** – Template for environment variables.  
- **`app.py`** – Core application logic using Gradio, Pinecone, and OpenAI.  
- **`pdf.py`** – Contains the `PDFLoader` class for extracting text from PDF files.

---

## Setup & Installation

### Local Environment

1. **Clone the Repository**  
   ```bash
   git clone https://github.com/JoeUzo/PDF-gpt--RAG-Application-.git
   cd PDF-gpt--RAG-Application-
   ```
2. **Create a Virtual Environment (Optional but Recommended)**  
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
   - Copy `.env.example` to `.env` and fill in your credentials. (See [Environment Variables](#environment-variables) below.)
5. **Run the App**  
   ```bash
   python app.py
   ```
   The Gradio interface will start on `http://localhost:7860`.

### Docker

1. **Pull the Public Image** (if you don’t want to build locally):  
   ```bash
   docker pull joeuzo/pdf-gpt:latest
   ```
2. **Run the Container**  
   ```bash
   docker run -it --rm -p 7860:7860 \
     -e OPENAI_API_KEY=<your-openai-key> \
     -e PINECONE_API_KEY=<your-pinecone-key> \
     -e INDEX_NAME=<your-pinecone-index> \
     -e BUCKET_NAME=<your-s3-bucket> \ 
     joeuzo/pdf-gpt:latest
   ```
   Then access the app at `http://localhost:7860`.

---

## Usage

1. **Enter Username**: Provide a username (this will be your Pinecone namespace).  
2. **Upload PDF**: Attach a PDF file.  
3. **Ask Questions**: Type your question in the chat box. The AI will retrieve relevant context from the PDF to answer.  
4. **Multiple or New PDFs**: The code is designed such that each new PDF can replace or augment what’s in your Pinecone namespace. (See `replace_pdf_in_pinecone` logic for a “replace” option.)

---

## Environment Variables

The following variables are used in `.env` or Docker environment:

| Variable          | Description                                               |
|-------------------|-----------------------------------------------------------|
| `OPENAI_API_KEY`  | Your OpenAI API key to use GPT-3.5-turbo.                |
| `PINECONE_API_KEY`| Your Pinecone API key.                                   |
| `INDEX_NAME`      | Name of the Pinecone index storing vectors.              |
| `BUCKET_NAME`     | (Future) AWS S3 bucket for storing chat history logs.    |

> **Note**: The S3 logic is **not yet** implemented. Once you create the Terraform scripts and S3 bucket, you’ll integrate the code to store/retrieve chat logs.

---

## Roadmap / Future Plans

- **Terraform**: Automate infrastructure provisioning (creating S3 bucket, IAM roles, etc.).  
- **Kubernetes (K8s)**: Container orchestration for scalable deployments.  
- **User Authentication**: Possibly integrate Flask or another method for secure login.  
- **Full Chat History Storage**: Upload chat transcripts to S3 under `BUCKET_NAME`, retrieve them on user login.  
- **Delete / Replace Vectors**: Provide a straightforward UI to remove or replace old PDFs from a user’s namespace.

---

## Contributing

1. **Fork** the repo on GitHub  
2. **Create** your feature branch (`git checkout -b feature/my-new-feature`)  
3. **Commit** your changes (`git commit -m 'Add some feature'`)  
4. **Push** to the branch (`git push origin feature/my-new-feature`)  
5. **Open a Pull Request** on GitHub

All contributions—bug reports, feature requests, and PRs—are welcome!

---

## License

This project is available under the **MIT License**. See the [LICENSE](LICENSE) file for details. *(If you haven’t added a LICENSE file yet, consider adding one.)*

---

## Contact

- **Author**: [JoeUzo](https://github.com/JoeUzo)  
- **Repository**: [GitHub: PDF-gpt--RAG-Application-](https://github.com/JoeUzo/PDF-gpt--RAG-Application-)

Feel free to open an issue if you have questions, or reach out via GitHub.
