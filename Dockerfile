# Use PyTorch base image with CUDA support
FROM pytorch/pytorch:2.5.0-cuda12.4-cudnn9-devel

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and conda packages
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install scipy and scikit-image via conda (for compatibility with conda-installed packages)
RUN conda install -y scipy scikit-image -c conda-forge && conda clean -afy

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /mnt/nvme_gds/slides /mnt/nvme_gds/predictions

# Set environment variable for Docker
ENV ENVIRONMENT=docker

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python", "main.py"]