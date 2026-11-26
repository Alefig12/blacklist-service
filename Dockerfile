# Imagen del microservicio para AWS Fargate.
# La base viene del mirror de Docker Hub en Amazon ECR Public para evitar el límite
# de descargas anónimas de Docker Hub en CodeBuild.
FROM public.ecr.aws/docker/library/python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Solo dependencias de ejecución: las pruebas corren en CodeBuild antes de construir la imagen.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY application.py newrelic.ini ./
COPY app/ app/

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Agente APM de New Relic: se configura con variables de entorno (NEW_RELIC_LICENSE_KEY y
# NEW_RELIC_APP_NAME las pone docker-compose o la tarea de ECS). Sin licencia el agente
# no se activa y la aplicación funciona igual. newrelic.ini solo trae lo que no admite
# variables de entorno (los errores esperados).
ENV NEW_RELIC_CONFIG_FILE=/app/newrelic.ini \
    NEW_RELIC_LOG=stdout \
    NEW_RELIC_LOG_LEVEL=info

# Detrás del ALB de Fargate hay un solo proxy: PROXY_X_FOR=1 (se define en la tarea de ECS).
# --preload crea la app (y las tablas) una sola vez antes de levantar los workers.
CMD ["newrelic-admin", "run-program", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--preload", "--access-logfile", "-", "application:application"]
