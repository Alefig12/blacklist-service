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

## Postman

**Documentación publicada:** https://documenter.getpostman.com/view/7736655/2sBYHSxLCX

En [`postman/`](postman/) están la colección y dos environments (`AWS` y `Local`):

- **16 escenarios** agrupados por endpoint: casos exitosos, email duplicado (409), validaciones (400) y token ausente o inválido (401). Cada uno tiene tests (`pm.test`) y un ejemplo de respuesta guardado para la documentación.
- Los emails de prueba se generan en los pre-request scripts, así que la colección se puede ejecutar varias veces sin conflictos.
- Importar la colección y el environment, asignar el token a la variable `token` y ejecutar la colección completa con el *Collection Runner*, **en orden**.

Desde la terminal (con [Newman](https://www.npmjs.com/package/newman)):

```powershell
npx newman run postman/blacklist-service.postman_collection.json `
  -e postman/blacklist-service-aws.postman_environment.json --env-var "token=<TOKEN>"
```

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

EC2 → Security Groups → **Create security group**: nombre `blacklist-app-sg` (descripción *Blacklist App*), VPC por defecto, **sin reglas de entrada** (Beanstalk crea las suyas para el balanceador). Este grupo solo sirve para darle permiso a la base de datos.

### 3. Base de datos en RDS 📸

Aurora and RDS → **Create database**:

| Campo | Valor |
|---|---|
| Creation method | *Full configuration* |
| Engine | **PostgreSQL 18.3-R2** |
| DB instance identifier | `blacklist-db` |
| Credentials | Master username `postgres` · *Self managed* · contraseña propia |
| Instance class | Burstable · **`db.t4g.micro`** |
| Storage | General Purpose SSD (gp2) · **20 GiB** · storage autoscaling desactivado |
| Compute resource | *Don't connect to an EC2 compute resource* |
| VPC / DB subnet group | VPC por defecto · `default-vpc-…` |
| Public access | **No** |
| VPC security group | *Create new* → `blacklist-db-sg` |
| Availability Zone | *No preference* |
| Initial database name | **`blacklist`** |
| DB parameter group | `default.postgres18` |
| Encryption | Activado (`aws/rds`) |
| Backup | Automated backup activado · retención 1 día |

Luego, EC2 → Security Groups → `blacklist-db-sg` → **Edit inbound rules**: dejar solo la regla *PostgreSQL / TCP 5432* con origen **`blacklist-app-sg`**.

### 4. Secreto JWT y paquete

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT_SECRET_KEY, guardarlo
python scripts/build_zip.py
```

### 5. Crear el ambiente en Beanstalk 📸

Elastic Beanstalk → **Create environment**:

| Sección | Campo | Valor |
|---|---|---|
| Deployment mode | | **Standard** |
| Environment details | Application name / Environment name | `blacklist-service` / `blacklist-env` |
| Platform details | Platform · branch · version | Python · *Python 3.14 running on 64bit Amazon Linux 2023* · 4.13.10 |
| Application code | | *Local file* → `blacklist-service-v1.0.0.zip` · version label `v1.0.0` |
| Environment properties | | `RDS_HOSTNAME` (endpoint de RDS) · `RDS_PORT=5432` · `RDS_DB_NAME=blacklist` · `RDS_USERNAME=postgres` · `RDS_PASSWORD` · `JWT_SECRET_KEY` |
| Platform-specific options | Proxy server | nginx |
| Service access | Service role | `aws-elasticbeanstalk-service-role` |
| | EC2 instance profile | `aws-elasticbeanstalk-ec2-role` |
| Infrastructure | Environment tier | Web server environment |
| | Environment type | **Load balanced** · Min **3** / Max **6** |
| | Architecture · instance types | x86_64 · **solo `t3.micro`** |
| | IMDSv1 | Disable |
| Networking | VPC · instance subnets | VPC por defecto · `us-east-2a`, `us-east-2b`, `us-east-2c` |
| | EC2 security groups | **`blacklist-app-sg`** |
| | Load balancer | Application Load Balancer · Dedicated · Public · Listener 80 |
| | Process `default` → Health check 📸 | HTTP code `200` · **Health check path `/ping`** · timeout 5 · interval 15 · deregistration delay 20 · healthy threshold 3 · unhealthy threshold 5 |
| | Load balancer subnets | `us-east-2a`, `us-east-2b`, `us-east-2c` |
| | Instance public IP address | **Enabled** |
| Monitoring and updates | Monitoring | Enhanced · 5 minutes |
| | Deployment policy | **All at once** |
| | Additional deployment settings | Rolling update type *Disabled* · Enable health check · Health threshold *Ok* · Command timeout 600 |
| | Managed platform updates | Desactivado |

**Create**. Esperar a que *Health* quede en **Ok** (5–10 min).

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
