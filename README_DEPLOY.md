Deployment notes
================

This document contains steps to deploy the Django project, configure Celery with RabbitMQ, enable Swagger at `/swagger/`, and how to test endpoints including email notifications.

Environment variables (minimum)
- DJANGO_SECRET_KEY
- DJANGO_DEBUG (True/False)
- DJANGO_ALLOWED_HOSTS (comma-separated)
- DATABASE_URL (optional, recommended: postgres)
- CELERY_BROKER_URL (e.g. amqp://guest:guest@rabbitmq:5672//)
- CELERY_RESULT_BACKEND (optional, default django-db)
- CHAPA_SECRET_KEY
- DEFAULT_FROM_EMAIL
- EMAIL_BACKEND
- EMAIL_HOST
- EMAIL_PORT
- EMAIL_HOST_USER
- EMAIL_HOST_PASSWORD
- EMAIL_USE_TLS


Quick local run (Docker Compose)

1. Edit the `.env` file in the project root to set your secrets and config.

2. Build and start services:

```powershell
docker-compose build
docker-compose up -d
```

3. Run migrations and create superuser (in separate terminal):

```powershell
docker-compose run web python manage.py migrate
docker-compose run web python manage.py createsuperuser
```

4. Open Swagger at http://localhost:8000/swagger/

Deploy to Render (high level)
1. Create a Web Service in Render using Docker (connect GitHub repo) or use the Build & Deploy with Dockerfile.
2. Add a Background Worker on Render for the Celery worker command: `celery -A alx_travel_app worker --loglevel=info`.
3. Add a RabbitMQ instance (Render does not provide RabbitMQ as a service directly). Use a hosted RabbitMQ provider or run RabbitMQ in a private service (e.g., Docker on another host), and set `CELERY_BROKER_URL` to it.
4. Add all environment variables in Render dashboard.

Deploy to PythonAnywhere (notes)
- PythonAnywhere does not easily support RabbitMQ — recommended to use an external RabbitMQ provider or switch to Redis as broker.
- Configure WSGI entry to point to `alx_travel_app.wsgi`.
- Configure virtualenv with the provided `requirements.txt`.

Verifying Celery and email in production
1. Ensure RabbitMQ broker URL is reachable by the worker service.
2. Start worker (Render worker service, systemd on VM, or Docker container).
3. Trigger a task via an API endpoint that uses `send_payment_confirmation_email.delay(...)`.
4. Monitor logs for the worker and web processes.

Swagger
- Swagger UI is available at `/swagger/` (drf-yasg is installed and routes configured in `alx_travel_app/urls.py`).

Notes and next steps
- Replace SQLite with Postgres for production by setting `DATABASE_URL`.
- Use a secrets manager or render's environment variables for secret keys.
- Add HTTPS configuration / ensure host has valid domain and SSL.
