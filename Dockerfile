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

COPY application.py .
COPY app/ app/

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Detrás del ALB de Fargate hay un solo proxy: PROXY_X_FOR=1 (se define en la tarea de ECS).
# --preload crea la app (y las tablas) una sola vez antes de levantar los workers.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--preload", "--access-logfile", "-", "application:application"]
