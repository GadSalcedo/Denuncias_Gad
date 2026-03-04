"""Django settings for config project (Render-ready).

This settings.py is adapted to work on Render.com:
- SECRET_KEY/DEBUG/ALLOWED_HOSTS/DB/Email keys pulled from environment variables
- WhiteNoise enabled for static files
- Production security headers enabled when DEBUG=False
"""

from pathlib import Path
import os

from decouple import config
import dj_database_url
from dotenv import load_dotenv
import certifi

# ------------------------------------------------------------
# Base paths / env
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Loads .env locally (Render uses Dashboard env vars)
load_dotenv(BASE_DIR / ".env")

# Certificate bundle (helps with SSL in some environments)
os.environ["SSL_CERT_FILE"] = certifi.where()

# ------------------------------------------------------------
# Core security
# ------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY", default="CHANGE_ME_IN_ENV")
DEBUG = config("DEBUG", cast=bool, default=False)

# Comma-separated list: "localhost,127.0.0.1,.onrender.com"
ALLOWED_HOSTS = [h.strip() for h in config(
    "ALLOWED_HOSTS",
    default="192.168.0.189,10.10.80.189,www.salcedo.gob.ec,salcedo.gob.ec,localhost,127.0.0.1"
).split(",") if h.strip()]

# Trusted origins for CSRF (important for IP-based access)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://192.168.0.189:8000,http://10.10.80.189:8000,https://www.salcedo.gob.ec,https://salcedo.gob.ec"
).split(",") if o.strip()]

# ------------------------------------------------------------
# Application definition
# ------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # terceros
    "rest_framework",
    "corsheaders",
    "django_extensions",
    "django_select2",
    "chartkick.django",

    # rutas
    "usuarios_api",
    "denuncias_api",
    "catalogos_api",
    "db",
    "web.apps.WebConfig",

    # librerias
    "crispy_forms",
    #"crispy_bootstrap5",
    "crispy_bootstrap4",

    # notificaciones push
    "notificaciones",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.context_processors.menus_principales",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ------------------------------------------------------------
# Database
# ------------------------------------------------------------
# local y rende rvalen
#DATABASES = {
#    "default": dj_database_url.config(
#        default=config(
#            "DATABASE_URL",
#            default="sqlite:///" + str(BASE_DIR / "db.sqlite3"),
#        ),
#        conn_max_age=600,
#        # Render Postgres uses SSL; keep SSL on in prod
#        ssl_require=not DEBUG,
#    )
#}
# docker
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="bdd_denuncias_publicas"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="5432"),
    }
}
# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", cast=bool, default=True)

# ------------------------------------------------------------
# Password validation
# ------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------
# Internationalization
# ------------------------------------------------------------
DEFAULT_CHARSET = "utf-8"
LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------
# Static & media (WhiteNoise)
# ------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------
# Auth / redirects
# ------------------------------------------------------------
LOGIN_REDIRECT_URL = "web:home"
LOGIN_URL = "web:login"

HANDLER403 = "web.views.permission_denied_view"
HANDLER404 = "web.views.page_not_found_view"
HANDLER500 = "web.views.server_error_view"

# ------------------------------------------------------------
# DRF / JWT
# ------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "usuarios_api.authentication.UsuariosJWTAuthentication",
    ),
}

DEFAULT_DEPARTAMENTO_ID = int(config("DEFAULT_DEPARTAMENTO_ID", default="5"))

from datetime import timedelta
SIMPLE_JWT = {
    "USER_ID_CLAIM": "uid",
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# ------------------------------------------------------------
# django-select2 cache (no Redis)
# ------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}
SELECT2_CACHE_BACKEND = "default"

# ------------------------------------------------------------
# Firebase / OpenAI env
# ------------------------------------------------------------
FIREBASE_SERVICE_ACCOUNT_PATH = config(
    "FIREBASE_SERVICE_ACCOUNT_PATH",
    default=str(BASE_DIR / "serviceAccountKey.json"),
)

OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
OPENAI_MODEL = config("OPENAI_MODEL", default="gpt-5")

# ------------------------------------------------------------
# Email (use env vars on Render; never hardcode secrets)
# ------------------------------------------------------------
#EMAIL_BACKEND = config(
#    "EMAIL_BACKEND",
#    default="django.core.mail.backends.smtp.EmailBackend",
#)
#EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
#EMAIL_PORT = config("EMAIL_PORT", cast=int, default=587)
#EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool, default=True)
#EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
#EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
# ------------------------------------------------------------
# Gmail API (OAuth) - env vars
# ------------------------------------------------------------
GMAIL_CLIENT_ID = config("GMAIL_CLIENT_ID", default="")
GMAIL_CLIENT_SECRET = config("GMAIL_CLIENT_SECRET", default="")
GMAIL_REFRESH_TOKEN = config("GMAIL_REFRESH_TOKEN", default="")
GMAIL_SENDER = config("GMAIL_SENDER", default="")

# ------------------------------------------------------------
# Production security (Render behind proxy)
# ------------------------------------------------------------
if not DEBUG:
    SECURE_HSTS_SECONDS = 30 * 24 * 60 * 60
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # Asegura que las cookies solo se envíen por HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Forzar que el STATIC_URL use HTTPS si se accede por el dominio
    # STATIC_URL = "https://www.salcedo.gob.ec/static/" 
    
    CSRF_TRUSTED_ORIGINS = [
        "https://*.onrender.com",
        "http://www.salcedo.gob.ec",
        "http://salcedo.gob.ec",
        "http://10.10.80.189",
        "http://192.168.0.189:8000",
        "https://www.salcedo.gob.ec",
        "https://salcedo.gob.ec"
    ]
#------------------------------
# para ver erroes en la terminal de render
#------------------------------
#LOGGING = {
#  "version": 1,
#  "disable_existing_loggers": False,
#  "handlers": {"console": {"class": "logging.StreamHandler"}},
#  "loggers": {"django.request": {"handlers": ["console"], "level": "ERROR", "propagate": True}},
#}
LOGGING = {
  "version": 1,
  "disable_existing_loggers": False,
  "handlers": {"console": {"class": "logging.StreamHandler"}},
  "root": {"handlers": ["console"], "level": "INFO"},
  "loggers": {
    "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    "web": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    "denuncias_api": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    "usuarios_api": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
  },
}

#------------------------------
#para ver sitio web
#------------------------------
#PUBLIC_SITE_URL = "https://denuncias-gad.onrender.com/"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
#SESSION_COOKIE_AGE = 60 * 60  # 1 hora (opcional)