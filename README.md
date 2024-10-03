
# Django MQTT Demo Application

This is a Django application demonstrating how to communicate with the SmartReader on-reader application using MQTT. This README provides instructions for setting up a local environment for development and testing purposes, as well as information on the adopted MQTT topic structure.

## Table of Contents

- [Requirements](#requirements)
- [Setup Instructions](#setup-instructions)
- [MQTT Topics](#mqtt-topics)
- [Running the Application](#running-the-application)
- [Accessing the Application](#accessing-the-application)
- [Development Notes](#development-notes)

## Requirements

- Python 3.9+
- Docker
- Docker Compose
- MQTT Broker (e.g., Mosquitto)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/suporterfid/smartreader-demo.git
cd smartreader-demo
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scriptsctivate`
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Local HTTPS Setup

For local development with HTTPS, we use self-signed SSL certificates. Follow these steps to generate the certificates using Docker:

1. Ensure you're in the project root directory.

2. Create a directory for the SSL certificates:
   ```bash
   mkdir -p ssl
   ```

3. Run the following command to generate the self-signed certificates using Docker:
   ```bash
   docker run --rm -v ${PWD}/ssl:/certificates --entrypoint openssl alpine/openssl \
   req -x509 -nodes -days 365 -newkey rsa:2048 \
   -keyout /certificates/localhost.key -out /certificates/localhost.crt \
   -subj "/C=US/ST=State/L=City/O=Organization/OU=Department/CN=localhost"
   ```

   This command does the following:
   - Uses the `alpine/openssl` Docker image to run OpenSSL.
   - Mounts the local `ssl` directory to `/certificates` in the container.
   - Generates a self-signed certificate valid for 365 days.
   - Creates `localhost.key` (private key) and `localhost.crt` (certificate) in the `ssl` directory.
   - Sets default values for certificate information (you can modify these as needed).

4. Verify that the certificates were created:
   ```bash
   ls ssl
   ```
   You should see `localhost.key` and `localhost.crt` in the output.

5. Ensure that your `nginx.conf` file is configured to use these certificates:
   ```nginx
   ssl_certificate /etc/nginx/ssl/localhost.crt;
   ssl_certificate_key /etc/nginx/ssl/localhost.key;
   ```

6. Update your `docker-compose.yml` file to mount the `ssl` directory to the Nginx container:
   ```yaml
   nginx:
     # ... other configurations ...
     volumes:
       - ./nginx.conf:/etc/nginx/nginx.conf:ro
       - ./ssl:/etc/nginx/ssl:ro
   ```

7. Restart your Docker services:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

Now your local development environment should be set up with HTTPS using self-signed certificates.

Note: Browsers will show a security warning when accessing your site because the certificate is self-signed. This is normal for local development and doesn't affect the encryption of data.

Remember to add the `ssl/` directory to your `.gitignore` file to avoid committing the certificates to your repository.

### 5. Setup Environment Variables

Create a `.env` file in the project root and set up the following environment variables:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_SSL_REQUIRE=False
SECURE_SSL_REDIRECT = False
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0 
MQTT_PORT=1883
MQTT_BROKER=test.mosquitto.org
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 6. Configure MQTT Broker

You can use the public test broker from Mosquitto (`test.mosquitto.org`). Alternatively, you can set up a local broker using Docker:

```bash
docker run -it -p 1883:1883 -p 9001:9001 eclipse-mosquitto
```

### 7. Migrate Database

```bash
python manage.py migrate
```
or
```bash
docker-compose exec web python manage.py migrate
```


### 8. Create a Superuser

```bash
python manage.py createsuperuser
```
or
```bash
docker-compose exec web python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('$superuser', '$email', '$password')"
```

### 9. Collect Static Files (Optional for production)

```bash
python manage.py collectstatic
```

## MQTT Topics

### Standard Topics for SmartReader R700 Readers

The following MQTT topics are used to communicate with the R700 readers:

1. **Management Commands**
   - **Topic:** `smartreader/{Reader Serial Number}/manage`
   - **Purpose:** To send management commands like "status-detailed" to the reader.

2. **Control Commands**
   - **Topic:** `smartreader/{Reader Serial Number}/control`
   - **Purpose:** To send control commands such as "start", "stop", or "mode".

3. **Management Command Response**
   - **Topic:** `smartreader/{Reader Serial Number}/manageResult`
   - **Purpose:** To receive responses from management commands sent to the reader.

4. **Tag Events**
   - **Topic:** `smartreader/{Reader Serial Number}/tagEvents`
   - **Purpose:** To receive RFID tag reads from the reader.

5. **Reader Events**
   - **Topic:** `smartreader/{Reader Serial Number}/event`
   - **Purpose:** To receive detailed status events from the reader.

6. **Metrics**
   - **Topic:** `smartreader/{Reader Serial Number}/metrics`
   - **Purpose:** To receive performance metrics from the reader.

7. **LWT (Last Will and Testament)**
   - **Topic:** `smartreader/{Reader Serial Number}/lwt`
   - **Purpose:** To detect disconnections or failures from the reader.

Each reader is identified by its serial number, and this number must be properly configured when communicating with readers via MQTT. Ensure the correct serial number is being used for each reader.

## API Access

The SmartReader demo application now provides a RESTful API for integrating with other systems. The API allows you to:

- List and retrieve reader information
- Access tag event data
- Send commands to readers

For detailed API documentation, please visit the `/api/docs/` endpoint in the application.

To use the API, you need to obtain an API key. Please contact the system administrator to get your API key.

## Generating and Using API Keys

To use the API, you need to generate an API key. Follow these steps to create and use an API key:

1. Ensure you have a user account in the system. If not, create one using the Django admin interface or the `createsuperuser` command.

2. Generate an API key for your user by running the following command:

   ```bash
   docker-compose exec web python manage.py generate_api_key your_username
   ```

   Replace `your_username` with your actual username.

3. The command will output your API key. Make sure to copy and save this key securely.

4. To use the API key in requests, include it in the `X-API-Key` header. For example:

   ```bash
   curl -H "X-API-Key: your_api_key_here" https://localhost/api/readers/
   ```

   Replace `your_api_key_here` with the actual API key you generated.

Remember to keep your API key secure and don't share it publicly. Each user should have their own unique API key.

Note: If you need to regenerate an API key for a user, simply run the `generate_api_key` command again with the same username. This will create a new key, invalidating the old one.

## Running the Application

### Using Docker Compose

1. **Build and Run Docker Containers**

   ```bash
   docker-compose up --build
   ```

2. **Access the Application**

   Open your browser and go to:

   ```
   http://localhost:8000/readers/
   ```

   Login using the superuser credentials you created.

### Running Locally without Docker

1. **Start MQTT Broker**

   If you're using a local MQTT broker, ensure it's running. You can run a Mosquitto broker using Docker:

   ```bash
   docker run -it -p 1883:1883 -p 9001:9001 eclipse-mosquitto
   ```

2. **Run Django Development Server**

   ```bash
   python manage.py runserver
   ```

3. **Run the MQTT Client**

   The MQTT client is started when the application is running, and it listens to the specified topics for communication with the readers.

## Accessing the Application

After the application is running, you can log in using the credentials created for the superuser.

The application provides a list of readers, tag events, and detailed status events, allowing you to interact with the readers using the management and control commands.

## Development Notes

- **Authentication:** The application is protected using Django's built-in authentication system. You must log in to access any pages.
- **Readers List:** The readers list is the home page of the application. You will be redirected here after login.
- **MQTT Communication:** Ensure that your MQTT broker is properly configured, and the reader's serial numbers match the ones used in the MQTT topics.
- **Exports:** You can export filtered tag event data to a CSV file using the export button available in the tag event list page.
  
For more information on how the SmartReader application works, refer to the [smartreader project](https://suporte-rfid-organization.gitbook.io/smartreader-doc).

## Contributing

Contributions to the project are welcome. Please ensure you follow the coding standards and write tests for new features.

## WARRANTY DISCLAIMER

This software is provided “as is” without quality check, and there is no warranty that the software will operate without error or interruption or meet any performance standard or other expectation. All warranties, express or implied, including the implied warranties of merchantability, non-infringement, quality, accuracy, and fitness for a particular purpose are expressly disclaimed. The developers of this software are not obligated in any way to provide support or other maintenance with respect to this software.

## LIMITATION OF LIABILITY

The total liability arising out of or related to the use of this software will not exceed the total amount paid by the user for this software, which in this case is zero as the software is provided free of charge. In no event will the developers have liability for any indirect, incidental, special, or consequential damages, even if advised of the possibility of these damages. These limitations will apply notwithstanding any failure of essential purpose of any limited remedy provided.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
