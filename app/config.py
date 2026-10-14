import os

from sqlalchemy.engine import URL


def database_uri():
    """URI de la base de datos a partir de las variables de entorno.

    Prioridad: DATABASE_URL completa, o las variables RDS_* (convención de
    Elastic Beanstalk). Con RDS_* la contraseña se escapa correctamente aunque
    tenga caracteres especiales.
    """
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    if os.environ.get("RDS_HOSTNAME"):
        return URL.create(
            "postgresql+psycopg2",
            username=os.environ.get("RDS_USERNAME"),
            password=os.environ.get("RDS_PASSWORD"),
            host=os.environ["RDS_HOSTNAME"],
            port=int(os.environ.get("RDS_PORT", "5432")),
            database=os.environ.get("RDS_DB_NAME"),
        ).render_as_string(hide_password=False)

    return None


def load_config():
    return {
        "SQLALCHEMY_DATABASE_URI": database_uri(),
        "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY"),
        # Detrás del balanceador de Beanstalk hay 2 proxies (ALB + nginx).
        # En un ambiente "Single instance" (solo nginx) usar PROXY_X_FOR=1.
        "PROXY_X_FOR": int(os.environ.get("PROXY_X_FOR", "2")),
        # Necesario para que los errores de Flask-JWT-Extended (401) no los
        # convierta Flask-RESTful en un 500.
        "PROPAGATE_EXCEPTIONS": True,
        # Respuestas con tildes legibles ("Envía" en vez de "Envía").
        "RESTFUL_JSON": {"ensure_ascii": False},
    }
