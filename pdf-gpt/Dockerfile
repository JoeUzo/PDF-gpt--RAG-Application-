# Using a lightweight Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy requirements 
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the app 
EXPOSE 7860

# Run the app
CMD ["python", "app.py"]
