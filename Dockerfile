# AI Real Estate Assistant - Docker Image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in stages for better compatibility
# Install critical packages with C extensions first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir "numpy>=1.26.4,<2.0.0" && \
    pip install --no-cache-dir "pydantic-core>=2.14.0,<3.0.0" && \
    pip install --no-cache-dir "pandas>=2.2.3,<2.3.0" && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for persistent data
RUN mkdir -p chroma_db .preferences .notifications .sessions

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Set environment variables
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run the application
CMD ["streamlit", "run", "app_modern.py", "--server.port=8501", "--server.address=0.0.0.0"]
