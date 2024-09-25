
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

### 4. Setup Environment Variables

Create a `.env` file in the project root and set up the following environment variables:

```env
SECRET_KEY=your-secret-key
DEBUG=True
MQTT_BROKER=test.mosquitto.org
MQTT_PORT=1883
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 5. Configure MQTT Broker

You can use the public test broker from Mosquitto (`test.mosquitto.org`). Alternatively, you can set up a local broker using Docker:

```bash
docker run -it -p 1883:1883 -p 9001:9001 eclipse-mosquitto
```

### 6. Migrate Database

```bash
python manage.py migrate
```
or
```bash
docker-compose exec web python manage.py migrate
```


### 7. Create a Superuser

```bash
python manage.py createsuperuser
```
or
```bash
docker-compose exec web python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('$superuser', '$email', '$password')"
```

### 8. Collect Static Files (Optional for production)

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

Contributions to the DPP project are welcome. Please ensure you follow the coding standards and write tests for new features.

## WARRANTY DISCLAIMER

This software is provided “as is” without quality check, and there is no warranty that the software will operate without error or interruption or meet any performance standard or other expectation. All warranties, express or implied, including the implied warranties of merchantability, non-infringement, quality, accuracy, and fitness for a particular purpose are expressly disclaimed. The developers of this software are not obligated in any way to provide support or other maintenance with respect to this software.

## LIMITATION OF LIABILITY

The total liability arising out of or related to the use of this software will not exceed the total amount paid by the user for this software, which in this case is zero as the software is provided free of charge. In no event will the developers have liability for any indirect, incidental, special, or consequential damages, even if advised of the possibility of these damages. These limitations will apply notwithstanding any failure of essential purpose of any limited remedy provided.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
