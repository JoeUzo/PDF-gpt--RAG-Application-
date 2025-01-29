FROM python:3.10

# Install Tesseract for OCR (Optional, only if needed)
RUN apt update && apt install -y tesseract-ocr

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the application code
COPY . /app
WORKDIR /app

# Run the app
CMD ["python", "app.py"]
