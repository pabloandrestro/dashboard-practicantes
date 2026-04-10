"""
Django settings for config project.

Este archivo define la configuración global del proyecto Django:
- Apps instaladas
- Middleware
- Base de datos
- Idioma / zona horaria
- Archivos estáticos y media
- URLs de login/logout, etc.
"""
import dj_database_url
import os
from pathlib import Path

# BASE_DIR apunta a la carpeta raíz del proyecto (donde está manage.py aprox.)
# Se usa para construir rutas de forma portable (Windows/Linux/Mac).
BASE_DIR = Path(__file__).resolve().parent.parent


# =========================
# Seguridad / Entorno
# =========================

# Clave secreta del proyecto.
# IMPORTANTE: en producción debe ir oculta (por ejemplo en variables de entorno),
# porque con esto se firman sesiones, tokens, etc.
SECRET_KEY = 'django-insecure-3i4o$a6+-*!ez3a-nsm*9^v%kd#x2&09j1h8k!jv*ai11aj3kl'

# DEBUG True sirve para desarrollo (muestra errores detallados).
# En producción debe ser False para no exponer información sensible.
DEBUG = True

# Hosts permitidos para servir la app.
# En producción se llena con dominios/IPs (ej: ["tudominio.com", "www.tudominio.com"]).
ALLOWED_HOSTS = [
    '.vercel.app',      
    'localhost', 
    '127.0.0.1'
]


# =========================
# Apps instaladas
# =========================

INSTALLED_APPS = [
    # Apps de Django (admin, auth, sesiones, etc.)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',

    # App propia del proyecto
    # REFACTOR (2026-03-17): uso AppConfig explícito para asegurar que se ejecute
    # CoreConfig.ready() (donde registramos signals del proyecto).
    'core.apps.CoreConfig',
]


# =========================
# Middleware
# =========================
# "Capas" que procesan requests/responses:
# seguridad, sesiones, csrf, auth, mensajes, protección clickjacking, etc.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# Archivo principal de URLs del proyecto (config/urls.py)
ROOT_URLCONF = 'config.urls'


# =========================
# Templates (HTML)
# =========================
TEMPLATES = [
    {
        # Motor de templates de Django
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        # Carpetas extra donde buscar templates.
        # Aquí agregas una carpeta /templates en la raíz del proyecto.
        'DIRS': [BASE_DIR / 'templates'],

        # True = también busca templates dentro de cada app (ej: core/templates/...)
        'APP_DIRS': True,

        'OPTIONS': {
            # Context processors: variables/funciones que se agregan automáticamente
            # al contexto de TODOS los templates.
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                # Context processors propios (según tu proyecto):
                # - navbar_avatar: inyecta la foto/avatar en la navbar
                # - es_controller / es_admin_path: flags/rutas para UI
                'core.context_processors.navbar_avatar',
                'core.context_processors.es_controller',
                'core.context_processors.es_admin_path',

                # NUEVO: Inyecta el contador de sugerencias para el admin
                'core.context_processors.sugerencias_pendientes',
            ],
        },
    },
]


# Configuración para servidores WSGI (deploy clásico)
WSGI_APPLICATION = 'config.wsgi.application'


# =========================
# Base de datos
# =========================
# SQLite para desarrollo (archivo db.sqlite3 dentro del proyecto).
# En producción normalmente se usa Postgres/MySQL, etc.

# DATABASES = {
#     'default': dj_database_url.config(
#         default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}"
#     )
# }

DATABASES = {
    'default': dj_database_url.config(
        # El default solo se usa si NO encuentra DATABASE_URL en el .env
        default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}",
        conn_max_age=600,      # Mantiene la conexión abierta 10 min (más rápido)
        conn_health_checks=True, # Verifica si la conexión sigue viva antes de usarla
    )
}

# =========================
# Validación de contraseñas
# =========================
# Reglas para contraseñas (similitud, longitud mínima, comunes, numéricas, etc.)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =========================
# Internacionalización / Zona horaria
# =========================
LANGUAGE_CODE = 'en-us'  # Idioma base de Django (textos internos, admin, etc.)

# Zona horaria del proyecto, en este caso Chile).
TIME_ZONE = "America/Santiago"

USE_I18N = True  # Activa sistema de traducciones
USE_TZ = True    # Maneja fechas en UTC internamente y las convierte a TIME_ZONE


# =========================
# Archivos estáticos (CSS/JS/Imgs del front)
# =========================
STATIC_URL = '/static/'

# Carpetas adicionales donde Django buscará estáticos en desarrollo
# (además de static/ dentro de apps si existiera).
STATICFILES_DIRS = [
    BASE_DIR / "static"
]


# =========================
# Archivos subidos por usuarios (Media)
# =========================
MEDIA_URL = '/media/'                 # URL pública para acceder a media
MEDIA_ROOT = BASE_DIR / 'media'       # Carpeta física donde se guardan


# =========================
# Auth: URLs de login/logout/redirecciones
# =========================
# A dónde mandar al usuario después de iniciar sesión correctamente
LOGIN_REDIRECT_URL = '/'

# A dónde mandar al usuario después de cerrar sesión
LOGOUT_REDIRECT_URL = '/login/'

# URL de login que usa Django cuando una vista requiere autenticación
LOGIN_URL = '/login/'


# =========================
# Config por defecto de PKs
# =========================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#==========================

# Configuración de Supabase Storage (S3 Compatible)
AWS_ACCESS_KEY_ID = 'mljqhmrwhnotmevvvclb'  # El ID de tu proyecto (está en la URL de Supabase)
AWS_SECRET_ACCESS_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1sanFobXJ3aG5vdG1ldnZ2Y2xiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc1MjI1NiwiZXhwIjoyMDg5MzI4MjU2fQ.aynbEDM1toj0pMmwQICX6C9hfWIWW4Tj3Hai18LsU8M'  # La encuentras en Settings > API (no uses la anon key)
AWS_STORAGE_BUCKET_NAME = 'multimedia'  # El nombre exacto del bucket que creaste
AWS_S3_ENDPOINT_URL = f'https://mljqhmrwhnotmevvvclb.supabase.co/storage/v1/s3'

# Configuración necesaria para que Django use S3
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_S3_REGION_NAME = 'us-east-1' # Supabase usa esta por defecto
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
