# Use official lightweight Python image
FROM python:3.11-slim

# Set system-level environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (build-essential, and LaTeX compilation engines)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    texlive-latex-base \
    texlive-fonts-recommended \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Install Python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase to the container workspace
COPY . /app/

# Expose Django development/production port
EXPOSE 8000

# Start Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
