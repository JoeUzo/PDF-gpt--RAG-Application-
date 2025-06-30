from setuptools import setup, find_packages

with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

setup(
    name="pdf-gpt",
    version="0.1.0",
    author="Joe",
    description="A Retrieval-Augmented Generation (RAG) application for PDF documents using LangChain and OpenAI.",
    author_email="joeuzoproject@gmail.com",
    packages=find_packages(),
    install_requires=requirements,
)