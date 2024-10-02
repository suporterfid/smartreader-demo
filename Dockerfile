# Dockerfile
FROM python:3.8-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gettext \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better cache utilization
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY src/ /app/

# Compile translation messages
RUN django-admin compilemessages

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Use entrypoint script to determine which command to run
COPY src/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
RUN chmod +x /app/wait-for-it.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]