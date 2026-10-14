"""Genera el Bearer token estático (sin expiración) para consumir el API.

El token se firma con JWT_SECRET_KEY, que debe ser el mismo valor configurado
en las variables de entorno del ambiente de Elastic Beanstalk.

Uso (PowerShell):
    $env:JWT_SECRET_KEY = "<el mismo secreto de Beanstalk>"
    python scripts/generate_token.py
"""
import os
import sys

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

secret = os.environ.get("JWT_SECRET_KEY")
if not secret:
    sys.exit("Defina la variable de entorno JWT_SECRET_KEY antes de generar el token.")

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = secret
JWTManager(app)

with app.app_context():
    print(create_access_token(identity="blacklist-client", expires_delta=False))
