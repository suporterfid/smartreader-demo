# Dockerfile
FROM python:3.8-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN apt-get update && apt-get install -y gettext
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/

RUN django-admin compilemessages

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]