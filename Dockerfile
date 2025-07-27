FROM python:3.11-slim

# Working directory
WORKDIR /app

# Update system packages and install necessary tools
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and copy requirements.txt
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Install Playwright browser
RUN playwright install chromium
RUN playwright install-deps

# Copy application code
COPY . .

# Create pdf, html, markdown directories (mount points)
RUN mkdir -p /app/pdf /app/html /app/markdown /app/extracted_images

# Suppress log for MCP stdio communication
ENV PYTHONWARNINGS=ignore

# MCP server communicates via stdio, so no port is needed

# Run the application
CMD ["python", "main.py"] 