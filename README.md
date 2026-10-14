# Blacklist Service

Microservicio de **lista negra global de emails** — Proyecto DevOps MISO, Entrega 1.

## Equipo

| Nombre | Correo |
|---|---|
| Fernando Lozano | f.lozanor@uniandes.edu.co |
| Alex Figueroa | a.figueroa@uniandes.edu.co |
| Marcela Hernandez | mv.hernandezl1@uniandes.edu.co |
| Jorge Cepeda | j.cepeday@uniandes.edu.co |

Stack: Python, Flask, Flask-SQLAlchemy, Flask-RESTful, Flask-Marshmallow, Flask-JWT-Extended, Werkzeug y PostgreSQL (AWS RDS), desplegado manualmente en AWS Elastic Beanstalk.

## Endpoints

Todos excepto `/ping` requieren el header `Authorization: Bearer <token>`.

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/blacklists` | Agrega un email a la lista negra global |
| `GET` | `/blacklists/<email>` | Indica si un email está en la lista negra y el motivo |
| `GET` | `/ping` (y `/`) | Health check: estado, versión desplegada e instancia que respondió |

### POST /blacklists

```json
{
  "email": "cliente@correo.com",
  "app_uuid": "6f1c2b9e-3a4d-4c5e-9f00-112233445566",
  "blocked_reason": "Envía spam"
}
```

- `email`: obligatorio, formato válido (se guarda en minúsculas).
- `app_uuid`: obligatorio, UUID válido.
- `blocked_reason`: opcional, máximo 255 caracteres.
- El servicio guarda además la **IP de origen** de la solicitud y la **fecha/hora**.

| Código | Cuándo |
|---|---|
| 201 | Email agregado. La respuesta incluye el registro guardado (con `request_ip` y `created_at`) |
| 400 | Datos inválidos (el detalle viene en `errors`) |
| 401 | Token ausente o inválido |
| 409 | El email ya está en la lista negra |

### GET /blacklists/&lt;email&gt;

```json
{ "email": "cliente@correo.com", "is_blacklisted": true, "blocked_reason": "Envía spam" }
```

Si el email no está en la lista: `"is_blacklisted": false` y `"blocked_reason": null`.

## Configuración (variables de entorno)

| Variable | Descripción |
|---|---|
| `RDS_HOSTNAME`, `RDS_PORT`, `RDS_DB_NAME`, `RDS_USERNAME`, `RDS_PASSWORD` | Conexión a PostgreSQL |
| `DATABASE_URL` | Alternativa a las `RDS_*`: URI completa (`postgresql://usuario:clave@host:5432/db`) |
| `JWT_SECRET_KEY` | Secreto con el que se firma y valida el token |
| `PROXY_X_FOR` | Número de proxies delante de la app. Por defecto `2` (ALB + nginx). Usar `1` en un ambiente *Single instance* |

## Desarrollo local

Requisitos: Python 3.14 y Docker Desktop (para PostgreSQL).

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt

# Tests (usan SQLite en memoria, no necesitan Docker)
pytest

# PostgreSQL local
docker compose up -d

$env:DATABASE_URL   = "postgresql://postgres:postgres@localhost:5432/blacklist"
$env:JWT_SECRET_KEY = "un-secreto-local-de-al-menos-32-caracteres"
python application.py          # http://127.0.0.1:5000/ping

# Token para probar
python scripts/generate_token.py
```

## Generar el token del API

El token es estático (no expira) y está firmado con `JWT_SECRET_KEY`. Debe generarse con **el mismo secreto** configurado en Beanstalk:

```powershell
$env:JWT_SECRET_KEY = "<mismo valor que en Beanstalk>"
python scripts/generate_token.py
```

## Empaquetar para Beanstalk

```powershell
python scripts/build_zip.py     # -> dist/blacklist-service-v<VERSION>.zip
```

No comprimir con el "Enviar a > Carpeta comprimida" de Windows: genera rutas con `\` que fallan en Linux. La versión sale de `app/version.py`.

---

## Despliegue manual en AWS Elastic Beanstalk

### 1. Rol IAM para las instancias (Tutorial 1, Actividad 1)

IAM → Roles → **Create role** → *AWS service* → caso de uso **EC2** → políticas:
`AWSElasticBeanstalkWebTier`, `AWSElasticBeanstalkWorkerTier`, `AWSElasticBeanstalkMulticontainerDocker` → nombre `aws-elasticbeanstalk-ec2-role`.

### 2. Security group para las instancias de la app

EC2 → Security Groups → **Create security group**: nombre `blacklist-app-sg`, VPC por defecto, **sin reglas de entrada** (Beanstalk crea las suyas para el balanceador). Este grupo solo sirve para darle permiso a la base de datos.

### 3. Base de datos en RDS 📸

RDS → **Create database**:

- *Standard create* → **PostgreSQL** (versión por defecto) → plantilla **Free tier** (o *Sandbox*, la de menor costo).
- DB instance identifier: `blacklist-db` · Master username: `postgres` · *Self managed* · contraseña (**guardarla**).
- Instance class `db.t3.micro` o `db.t4g.micro` · Storage 20 GiB · desmarcar *storage autoscaling*.
- Connectivity: *Don't connect to an EC2 compute resource* · VPC por defecto · **Public access: No** · VPC security group: *Create new* → `blacklist-db-sg`.
- *Additional configuration* → **Initial database name: `blacklist`**. Desactivar Performance Insights y Enhanced monitoring.
- Create (tarda 5–10 min). Copiar el **Endpoint** (pestaña *Connectivity & security*).

Luego, EC2 → Security Groups → `blacklist-db-sg` → **Edit inbound rules**: dejar solo la regla *PostgreSQL / TCP 5432* con origen **`blacklist-app-sg`**.

### 4. Secreto JWT y paquete

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT_SECRET_KEY, guardarlo
python scripts/build_zip.py
```

### 5. Crear la aplicación y el ambiente en Beanstalk 📸

Elastic Beanstalk → **Create application**:

1. **Configure environment**: *Web server environment* · Application name `blacklist-service` · Environment name `blacklist-env` · Platform **Python**, rama *Python 3.14 running on 64bit Amazon Linux 2023* · Application code: **Upload your code**, version label `v1.0.0`, archivo local `dist/blacklist-service-v1.0.0.zip` · Presets: **High availability**.
2. **Service access**: Service role → crear/usar `aws-elasticbeanstalk-service-role` · EC2 instance profile → `aws-elasticbeanstalk-ec2-role` · key pair opcional.
3. **Networking, database and tags**: VPC por defecto · **Public IP address: Activated** · seleccionar las subredes (instancias y balanceador) excepto `us-east-1e`. **No** habilitar la base de datos aquí (usamos la RDS del paso 3).
4. **Instance traffic and scaling**:
   - EC2 security groups: marcar **`blacklist-app-sg`**.
   - Capacity: *Load balanced* · **Min 3 / Max 6** · On-Demand · instance types **solo `t3.micro`**.
   - Load balancer: *Application load balancer*, dedicado · listener HTTP 80.
   - **Processes** → `default` → Edit → **Health check path: `/ping`** 📸 (health checks de la app).
5. **Updates, monitoring and logging**:
   - Health reporting: *Enhanced* · Managed platform updates: **desactivado**.
   - Rolling updates and deployments: deployment policy **All at once** (para el primer despliegue).
   - **Environment properties**: `RDS_HOSTNAME` (endpoint), `RDS_PORT=5432`, `RDS_DB_NAME=blacklist`, `RDS_USERNAME=postgres`, `RDS_PASSWORD`, `JWT_SECRET_KEY`.
6. **Review → Submit**. Esperar a que *Health* quede en **Ok** (5–10 min).

### 6. Verificar

- Abrir `http://<dominio-del-ambiente>/ping`. Al recargar varias veces cambia `host`: el balanceador reparte entre las 3 instancias.
- Generar el token (sección *Generar el token del API*) y probar `POST` y `GET` desde Postman.
- Verificar que el `request_ip` del POST sea su IP pública (compárenla con https://checkip.amazonaws.com).

### Solución de problemas

- **Health en Severe / errores 502**: Logs → *Request logs* → *Last 100 lines*, revisar `web.stdout.log`. Si falta una variable de entorno, la app lo dice explícitamente al arrancar.
- **Error de conexión o *timeout* a la base**: revisar la regla de `blacklist-db-sg` y que las instancias tengan `blacklist-app-sg`. Una vez corregido, ejecutar *Actions → Restart app server(s)* para que se creen las tablas.
- **`request_ip` muestra una IP 172.31.x.x**: el número de proxies no coincide; ajustar `PROXY_X_FOR`.

## Nuevas versiones (estrategias de despliegue)

1. Cambiar `VERSION` en `app/version.py` (`1.0.1`, `1.0.2`, …) y ejecutar `python scripts/build_zip.py`.
2. En Beanstalk: Configuration → *Rolling updates and deployments* → elegir la política (All at once, Rolling, Rolling with additional batch, Immutable, Traffic splitting).
3. **Upload and deploy** con el zip nuevo y la etiqueta `v<VERSION>`.
4. Mientras despliega, consultar `/ping` en bucle para ver qué instancias responden con la versión vieja y cuáles con la nueva:

```powershell
while ($true) { (Invoke-RestMethod http://<dominio>/ping) | ConvertTo-Json -Compress; Start-Sleep 1 }
```
