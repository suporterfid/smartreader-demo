# Django MQTT Demo Application

This Django application demonstrates communication with the SmartReader on-reader application using MQTT. Follow these instructions to set up a local development environment.

## Table of Contents

- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Running the Application](#running-the-application)
- [MQTT Topics](#mqtt-topics)
- [API Access](#api-access)
- [Development Notes](#development-notes)
- [Contributing](#contributing)
- [Legal](#legal)

## Requirements

- Python 3.9+
- Docker
- Docker Compose
- MQTT Broker (e.g., Mosquitto)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/suporterfid/smartreader-demo.git
   cd smartreader-demo
   ```

2. Set up the environment:
   ```bash
   cp .env.example .env
   docker-compose up --build
   ```

3. Create a superuser:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

4. Access the application at `https://localhost:8000/readers/`

## Detailed Setup

### 1. Environment Setup

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_SSL_REQUIRE=False
SECURE_SSL_REDIRECT=False
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0 
MQTT_PORT=1883
MQTT_BROKER=test.mosquitto.org
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 2. Local HTTPS Setup

Generate self-signed SSL certificates:

```bash
mkdir -p ssl
docker run --rm -v ${PWD}/ssl:/certificates --entrypoint openssl alpine/openssl \
req -x509 -nodes -days 365 -newkey rsa:2048 \
-keyout /certificates/localhost.key -out /certificates/localhost.crt \
-subj "/C=US/ST=State/L=City/O=Organization/OU=Department/CN=localhost"
```

### 3. Database Setup

Run migrations:

```bash
docker-compose exec web python manage.py migrate
```

### 4. Create Superuser

```bash
docker-compose exec web python manage.py createsuperuser
```

### 5. Static Files (Optional for production)

```bash
docker-compose exec web python manage.py collectstatic
```

## Running the Application

### Using Docker Compose

1. Start the application:
   ```bash
   docker-compose up -d
   ```

2. Access the application at `https://localhost:8000/readers/`

### Running Locally (Alternative)

1. Set up a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

2. Start the MQTT broker:
   ```bash
   docker run -it -p 1883:1883 -p 9001:9001 eclipse-mosquitto
   ```

3. Run the Django server:
   ```bash
   python manage.py runserver
   ```

## MQTT Topics

The application uses the following MQTT topics for communication with R700 readers:

1. `smartreader/{Reader Serial Number}/manage`: Management commands
2. `smartreader/{Reader Serial Number}/control`: Control commands
3. `smartreader/{Reader Serial Number}/manageResult`: Command responses
4. `smartreader/{Reader Serial Number}/tagEvents`: RFID tag reads
5. `smartreader/{Reader Serial Number}/event`: Detailed status events
6. `smartreader/{Reader Serial Number}/metrics`: Performance metrics
7. `smartreader/{Reader Serial Number}/lwt`: Last Will and Testament

## API Access

The application provides a RESTful API for integration. To use the API:

1. Generate an API key:
   ```bash
   docker-compose exec web python manage.py generate_api_key your_username
   ```

2. Use the API key in requests:
   ```bash
   curl -H "X-API-Key: your_api_key_here" https://localhost/api/readers/
   ```

For detailed API documentation, visit `/api/docs/` in the application.

## Development Notes

- Authentication is required to access the application.
- The readers list is the home page after login.
- Ensure correct configuration of the MQTT broker and reader serial numbers.
- Tag event data can be exported to CSV from the tag event list page.

For more information on the SmartReader application, visit the [smartreader project documentation](https://suporte-rfid-organization.gitbook.io/smartreader-doc).

## Contributing

Contributions are welcome. Please follow coding standards and include tests for new features.

## Legal

### Warranty Disclaimer

This software is provided "as is" without any warranties. All warranties, express or implied, are disclaimed.

### Limitation of Liability

The developers' liability is limited to the amount paid for the software (zero in this case). They are not liable for any indirect, incidental, special, or consequential damages.

This project is licensed under the MIT License. See the LICENSE file for details.
