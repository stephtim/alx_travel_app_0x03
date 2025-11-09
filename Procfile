web: gunicorn alx_travel_app.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A alx_travel_app worker --loglevel=info
