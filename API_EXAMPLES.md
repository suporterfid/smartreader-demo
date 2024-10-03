# API Examples

This document provides examples of how to interact with the SmartReader API using curl commands. These examples are particularly useful for local development with HTTPS.

## Prerequisites

- curl installed on your system
- A valid API key for authentication

## General Notes

- Replace `your_api_key_here` with your actual API key in all examples.
- The `-k` or `--insecure` option is used for local development with self-signed certificates. Remove this option when working with valid SSL certificates in production.

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

## Examples

### List Readers

```bash
curl -k -X GET "https://localhost/api/readers/" \
     -H "X-API-Key: your_api_key_here"
```

### Get Reader Details

```bash
curl -k -X GET "https://localhost/api/readers/READER001/" \
     -H "X-API-Key: your_api_key_here"
```

### List Tag Events

```bash
curl -k -X GET "https://localhost/api/tag-events/" \
     -H "X-API-Key: your_api_key_here"
```

### Send a Command to a Reader

```bash
curl -k -X POST "https://localhost/api/commands/" \
     -H "X-API-Key: your_api_key_here" \
     -H "Content-Type: application/json" \
     -d '{
           "reader_serial_number": "READER001",
           "command_type": "start",
           "details": {}
         }'
```

For more detailed examples and explanations, please refer to the full API documentation.
