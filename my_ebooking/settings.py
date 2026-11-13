import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY doit être défini en production.")
    SECRET_KEY = "django-insecure-local-development-key-change-before-deployment"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "catalog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "my_ebooking.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "my_ebooking.wsgi.application"
ASGI_APPLICATION = "my_ebooking.asgi.application"

database_url = os.environ.get("DATABASE_URL")
if database_url:
    DATABASES = {
        "default": dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
elif not DEBUG:
    raise ImproperlyConfigured("DATABASE_URL doit pointer vers PostgreSQL en production.")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Abidjan"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_BACKEND = (
    "whitenoise.storage.CompressedStaticFilesStorage"
    if DEBUG
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

# Fichiers téléversés (couvertures et PDF).
# En local, ils sont enregistrés sur le disque dans media/ et private_books/.
# En production, le disque de Render est effacé à chaque redémarrage : les
# fichiers sont donc envoyés vers un stockage objet compatible S3
# (Cloudflare R2, Backblaze B2, Supabase Storage, AWS S3...).
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_BOOK_ROOT = BASE_DIR / "private_books"

STORAGE_BUCKET_NAME = os.environ.get("STORAGE_BUCKET_NAME", "")
if STORAGE_BUCKET_NAME:
    missing = [
        name
        for name in ("STORAGE_ACCESS_KEY_ID", "STORAGE_SECRET_ACCESS_KEY", "STORAGE_ENDPOINT_URL")
        if not os.environ.get(name)
    ]
    if missing:
        raise ImproperlyConfigured(
            "Variables de stockage manquantes : " + ", ".join(missing)
        )
    s3_options = {
        "bucket_name": STORAGE_BUCKET_NAME,
        "access_key": os.environ["STORAGE_ACCESS_KEY_ID"],
        "secret_key": os.environ["STORAGE_SECRET_ACCESS_KEY"],
        "endpoint_url": os.environ["STORAGE_ENDPOINT_URL"],
        "region_name": os.environ.get("STORAGE_REGION", "auto"),
        "signature_version": "s3v4",
        # Le bucket reste privé : chaque lien est signé et expire.
        "default_acl": None,
        "querystring_auth": True,
        "file_overwrite": False,
    }
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {**s3_options, "location": "media", "querystring_expire": 3600},
        },
        "private_books": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {**s3_options, "location": "private_books", "querystring_expire": 300},
        },
        "staticfiles": {"BACKEND": STATICFILES_BACKEND},
    }
elif not DEBUG:
    raise ImproperlyConfigured(
        "STORAGE_BUCKET_NAME doit être défini en production : le disque de Render "
        "ne conserve pas les fichiers téléversés."
    )
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "private_books": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": PRIVATE_BOOK_ROOT},
        },
        "staticfiles": {"BACKEND": STATICFILES_BACKEND},
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ADMIN_ACCESS_CODE_HASH = os.environ.get("ADMIN_ACCESS_CODE_HASH", "")
WHATSAPP_PHONE_NUMBER = os.environ.get("WHATSAPP_PHONE_NUMBER", "")
if not DEBUG and not ADMIN_ACCESS_CODE_HASH:
    raise ImproperlyConfigured("ADMIN_ACCESS_CODE_HASH doit être configuré en production.")
CURRENCY = "FCFA"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if render_hostname:
    CSRF_TRUSTED_ORIGINS.append(f"https://{render_hostname}")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
