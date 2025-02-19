# Using a lightweight Python base image
FROM python:3.12-alpine3.20

# Set the working directory in the container
WORKDIR /app

# Create the directory for Gradio temporary files
RUN mkdir -p /tmp

# Copy requirements 
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Expose the app 
EXPOSE 5000

ENV GRADIO_TEMP_DIR="/tmp"

# Run the app
CMD ["python", "app.py"]
