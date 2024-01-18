#!/bin/bash
FLASK_ENV=$1
if [ "$FLASK_ENV" == "development" ]; then
    python -m flask --app 'api:create_app(instance_path="/api/instance")' run --host=0.0.0.0
else 
    sudo -u app python -m gunicorn -w 4 'api:create_app(instance_path="/api/instance", environment="production")' &
    sleep 5
    until curl localhost:8000; do
        sleep 1
    done
    nginx -g 'daemon off;'
fi
