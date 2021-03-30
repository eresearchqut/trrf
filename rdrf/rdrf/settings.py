# Django settings for rdrf project.
import os
# A wrapper around environment which has been populated from
# /etc/rdrf/rdrf.conf in production. Also does type conversion of values
from ccg_django_utils.conf import EnvConfig
# import message constants so we can use bootstrap style classes
from django.contrib.messages import constants as message_constants
import rdrf
from rdrf.helpers.settings_helpers import get_static_url_domain, get_csp
from rdrf.system_role import SystemRoles
from rdrf.security import url_whitelist
env = EnvConfig()

TRRF_SITE_NAME = env.get("trrf_site_name", "trrf")

SCRIPT_NAME = env.get("script_name", os.environ.get("HTTP_SCRIPT_NAME", ""))
FORCE_SCRIPT_NAME = env.get("force_script_name", "") or SCRIPT_NAME or None

WEBAPP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# General site config
PRODUCTION = env.get("production", False)

# https://docs.djangoproject.com/en/1.8/ref/middleware/#django.middleware.security.SecurityMiddleware
SECURE_SSL_REDIRECT = env.get("secure_ssl_redirect", PRODUCTION)
SECURE_SSL_HOST = env.get("secure_ssl_host", False)
SECURE_CONTENT_TYPE_NOSNIFF = env.get("secure_content_type_nosniff", PRODUCTION)
SECURE_BROWSER_XSS_FILTER = env.get("secure_browser_xss_filter", PRODUCTION)
SECURE_REDIRECT_EXEMPT = env.getlist("secure_redirect_exempt", [])
SECURE_HSTS_SECONDS = env.get("SECURE_HSTS_SECONDS", 3600)  # TODO: Bump to 1 week, 1 month, 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

X_FRAME_OPTIONS = env.get("x_frame_options", 'DENY')

DEBUG = env.get("debug", not PRODUCTION)

SITE_ID = env.get("site_id", 1)
APPEND_SLASH = env.get("append_slash", True)

FORM_SECTION_DELIMITER = "____"

IMPORT_MODE = False

ROOT_URLCONF = 'rdrf.urls'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SECRET_KEY = env.get("secret_key", "changeme")
# Locale
TIME_ZONE = env.get("time_zone", 'Australia/Brisbane')
LANGUAGE_CODE = env.get("language_code", 'en')
USE_I18N = env.get("use_i18n", True)

DATE_FORMAT = "d-m-Y"

# This must be a superset of LANGUAGES
ALL_LANGUAGES = (("en", "English"),
                 ("ar", "Arabic"),
                 ("pl", "Polish"),
                 ("es", "Spanish"),
                 ("de", "German"),
                 ("fr", "French"),
                 ("it", "Italian"))


# EnvConfig can't handle structure of tuple of tuples so we pass in a flat association list
# E.g. ["en","English","ar","Arabic"]
# This must be a subset of ALL_LANGUAGES
LANGUAGES_ASSOC_LIST = env.getlist("languages", ["en", "English"])
LANGUAGES = tuple(zip(LANGUAGES_ASSOC_LIST[0::2], LANGUAGES_ASSOC_LIST[1::2]))


DATABASES = {
    'default': {
        # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': env.get_db_engine("dbtype", "pgsql"),
        # Or path to database file if using sqlite3.
        'NAME': env.get("dbname", "rdrf"),
        'USER': env.get("dbuser", "rdrf"),                      # Not used with sqlite3.
        'PASSWORD': env.get("dbpass", "rdrf"),                  # Not used with sqlite3.
        # Set to empty string for localhost. Not used with sqlite3.
        'HOST': env.get("dbserver", ""),
        # Set to empty string for default. Not used with sqlite3.
        'PORT': env.get("dbport", ""),
    }
}

# Clinical database (defaults to main db if not specified).
DATABASES["clinical"] = {
    "ENGINE": env.get_db_engine("clinical_dbtype", "pgsql"),
    "NAME": env.get("clinical_dbname", DATABASES["default"]["NAME"]),
    "USER": env.get("clinical_dbuser", DATABASES["default"]["USER"]),
    "PASSWORD": env.get("clinical_dbpass", DATABASES["default"]["PASSWORD"]),
    "HOST": env.get("clinical_dbserver", DATABASES["default"]["HOST"]),
    "PORT": env.get("clinical_dbport", DATABASES["default"]["PORT"]),
}

DATABASES["reporting"] = {
    "ENGINE": env.get_db_engine("reporting_dbtype", "pgsql"),
    "NAME": env.get("reporting_dbname", DATABASES["default"]["NAME"]),
    "USER": env.get("reporting_dbuser", DATABASES["default"]["USER"]),
    "PASSWORD": env.get("reporting_dbpass", DATABASES["default"]["PASSWORD"]),
    "HOST": env.get("reporting_dbserver", DATABASES["default"]["HOST"]),
    "PORT": env.get("reporting_dbport", DATABASES["default"]["PORT"]),
}

DATABASE_ROUTERS = ["rdrf.db.db.RegistryRouter"]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(WEBAPP_ROOT, 'rdrf', 'templates')],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "rdrf.context_processors.context_processors.production",
                "rdrf.context_processors.context_processors.common_settings",
                "rdrf.context_processors.context_processors.cic_system_role",

            ],
            "debug": DEBUG,
            "loaders": [
                'django.template.loaders.app_directories.Loader',
                'django.template.loaders.filesystem.Loader',
                'rdrf.template_loaders.translation.Loader'
            ]
        },
    },
]

MESSAGE_TAGS = {
    message_constants.ERROR: 'alert alert-danger',
    message_constants.SUCCESS: 'alert alert-success',
    message_constants.INFO: 'alert alert-info'
}

# Always store messages in the session, as the default storage sometimes
# shows up messages addressed to other users.
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

MIDDLEWARE = (
    'aws_xray_sdk.ext.django.middleware.XRayMiddleware',
    'useraudit.middleware.RequestToThreadLocalMiddleware',
    'django.middleware.common.CommonMiddleware',
    'registry.common.middleware.NoCacheMiddleware',
    'csp.middleware.CSPMiddleware',
    'registry.common.middleware.LaxSameSiteCookieMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'registry.common.middleware.UserSentryMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'stronghold.middleware.LoginRequiredMiddleware',
)


INSTALLED_APPS = [
    'rdrf',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django_extensions',
    'django.contrib.admin',
    'messages_ui',
    'ajax_select',
    'explorer',
    'useraudit',
    'templatetag_handlebars',
    'rest_framework',
    'rest_framework.authtoken',
    'anymail',
    'registry.groups',
    'registry.patients',
    'registry.common',
    'registration',
    'reversion',
    'storages',
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
    'django_user_agents',
    'simple_history',
    'django_js_reverse',
    'stronghold',
    'aws_xray_sdk.ext.django',
]


# these determine which authentication method to use
# apps use modelbackend by default, but can be overridden here
# see: https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    'useraudit.password_expiry.AccountExpiryBackend',
    'django.contrib.auth.backends.ModelBackend',
    'useraudit.backend.AuthFailedLoggerBackend',
]

# AWS X-Ray
# To enable X-Ray locally, in .env_local set `AWS_XRAY_SDK_ENABLED` to 1 and add AWS keys
XRAY_RECORDER = {
    'AWS_XRAY_DAEMON_ADDRESS': env.get("aws_xray_daemon_address", "") or None,
    'AUTO_INSTRUMENT': True,
    'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR',
    'PLUGINS': ('ECSPlugin',),
    'SAMPLING': True,
    'AWS_XRAY_TRACING_NAME': TRRF_SITE_NAME,
}

# email
EMAIL_USE_TLS = env.get("email_use_tls", False)
EMAIL_HOST = env.get("email_host", 'smtp')
EMAIL_PORT = env.get("email_port", 25)
EMAIL_HOST_USER = env.get("email_host_user", "webmaster@localhost")
EMAIL_HOST_PASSWORD = env.get("email_host_password", "")
EMAIL_APP_NAME = env.get("email_app_name", "RDRF {0}".format(SCRIPT_NAME))
EMAIL_SUBJECT_PREFIX = env.get("email_subject_prefix", "DEV {0}".format(SCRIPT_NAME))

# Email Notifications
# NB. This initialises the email notification form
DEFAULT_FROM_EMAIL = env.get('default_from_email', 'no-reply@registryframework.net')
SERVER_EMAIL = env.get('server_email', DEFAULT_FROM_EMAIL)

if env.get('ALL_EMAIL_JUST_PRINTED_TO_CONSOLE', False):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'anymail.backends.amazon_ses.EmailBackend'

ANYMAIL = {
    "AMAZON_SES_CLIENT_PARAMS": {
        "aws_access_key_id": env.get("aws_ses_access_key_id", env.get("aws_access_key_id", "")),
        "aws_secret_access_key": env.get("aws_ses_secret_access_key", env.get("aws_secret_access_key", "")),
        "region_name": env.get("aws_ses_region_name", "ap-southeast-2"),
    },
}

# default emailsn
ADMINS = [
    ('alerts', env.get("alert_email", "root@localhost"))
]
MANAGERS = ADMINS


STATIC_ROOT = env.get('STATIC_ROOT', os.path.join(WEBAPP_ROOT, 'static'))
GIT_COMMIT_HASH = env.get('GIT_COMMIT_HASH', '')
STATIC_URL = env.get('STATIC_URL', '{0}/static/'.format(SCRIPT_NAME))

# a directory that will be writable by the webserver, for storing various files...
WRITABLE_DIRECTORY = env.get("writable_directory", "/tmp")

#
#       File Uploads

# Use S3 by default to avoid writing sensitive data to FS in production
if env.get("FILE_STORAGE", "S3") == "FS":
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
else:
    DEFAULT_FILE_STORAGE = "rdrf.db.filestorage.CustomS3Storage"

# Configure different aspects of file uploads to S3

# Never create buckets, create them from CloudFormation and pass them in
AWS_AUTO_CREATE_BUCKET = False
AWS_DEFAULT_ACL = None

# To test locally set these values in your .env_local file
# .env_local is in .gitignore so it can have your local settings without being checked in

AWS_STORAGE_BUCKET_NAME = env.get("AWS_STORAGE_BUCKET_NAME", "")  # set to trrf-storage-dev in local dev

# Set these to an IAM user's keys when testing locally.
# On the servers EC2 roles will take care of this.
AWS_ACCESS_KEY_ID = env.get("aws_storage_access_key_id", env.get("aws_access_key_id", ""))
AWS_SECRET_ACCESS_KEY = env.get("aws_storage_secret_access_key", env.get("aws_secret_access_key", ""))

AWS_S3_REGION_NAME = env.get("aws_storage_region_name", env.get("aws_region_name", "ap-southeast-2"))
AWS_LOCATION = env.get("aws_storage_location", "")  # set to "local/{YOUR_USERNAME}/" in local dev

VIRUS_CHECKING_ENABLED = env.get("VIRUS_CHECKING_ENABLED", False)

#
#       END OF - File Uploads

# settings used when FileSystemStorage is enabled
MEDIA_ROOT = env.get('media_root', os.path.join(WEBAPP_ROOT, 'uploads'))
MEDIA_URL = '{0}/uploads/'.format(SCRIPT_NAME)

# setting used when DatabaseStorage is enabled
DB_FILES = {
    "db_table": "rdrf_filestorage",
    "fname_column": "name",
    "blob_column": "data",
    "size_column": "size",
    "base_url": None,
}
DATABASE_ODBC_DRIVER = "{PostgreSQL}"  # depends on odbcinst.ini
DATABASE_NAME = DATABASES["default"]["NAME"]
DATABASE_USER = DATABASES["default"]["USER"]
DATABASE_PASSWORD = DATABASES["default"]["PASSWORD"]
DATABASE_HOST = DATABASES["default"]["HOST"]

# session and cookies
SESSION_COOKIE_AGE = env.get("session_cookie_age", 15 * 60)
SESSION_COOKIE_PATH = '{0}/'.format(SCRIPT_NAME)
SESSION_SAVE_EVERY_REQUEST = env.get("session_save_every_request", True)
SESSION_COOKIE_HTTPONLY = env.get("session_cookie_httponly", True)
SESSION_COOKIE_SECURE = env.get("session_cookie_secure", PRODUCTION)
SESSION_COOKIE_NAME = env.get(
    "session_cookie_name", "trrf_{0}".format(SCRIPT_NAME.replace("/", "")))
SESSION_COOKIE_DOMAIN = env.get("session_cookie_domain", "") or None
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

CSRF_COOKIE_NAME = env.get("csrf_cookie_name", "csrf_{0}".format(SESSION_COOKIE_NAME))
CSRF_COOKIE_DOMAIN = env.get("csrf_cookie_domain", "") or SESSION_COOKIE_DOMAIN
CSRF_COOKIE_PATH = env.get("csrf_cookie_path", SESSION_COOKIE_PATH)
CSRF_COOKIE_SECURE = env.get("csrf_cookie_secure", PRODUCTION)
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_HTTPONLY = env.get("csrf_cookie_httponly", True)
CSRF_COOKIE_AGE = env.get('csrf_cookie_age', 31449600)
CSRF_FAILURE_VIEW = env.get("csrf_failure_view", "rdrf.views.handler_views.handler_csrf")
CSRF_HEADER_NAME = env.get("csrf_header_name", 'HTTP_X_CSRFTOKEN')
CSRF_TRUSTED_ORIGINS = env.getlist("csrf_trusted_origins", ['localhost'])

# Content Security Policy
_CSP_STATIC_URL = get_static_url_domain(env.get("STATIC_URL", ""))

CSP_DEFAULT_SRC = ["'self'"]
CSP_OBJECT_SRC = ["'none'"]
CSP_SCRIPT_SRC = get_csp(
    ["'self'", "'unsafe-inline'", "https://js-agent.newrelic.com", "https://bam.nr-data.net"],
    [_CSP_STATIC_URL]
)
CSP_STYLE_SRC = get_csp(["'self'", "'unsafe-inline'"], [_CSP_STATIC_URL])
CSP_FONT_SRC = get_csp(["'self'"], [_CSP_STATIC_URL])
CSP_IMG_SRC = get_csp(["'self'"], [_CSP_STATIC_URL])
CSP_CONNECT_SRC = ["'self'", "https://bam.nr-data.net"]

# The maximum size in bytes that a request body may be before a
# SuspiciousOperation (RequestDataTooBig) is raised.
DATA_UPLOAD_MAX_MEMORY_SIZE = env.get("data_upload_max_memory_size", 2621440) or None
# The maximum number of parameters that may be received via GET or
# POST before a SuspiciousOperation (TooManyFields) is raised.
DATA_UPLOAD_MAX_NUMBER_FIELDS = env.get("data_upload_max_number_fields", 30000) or None

# django-useraudit
# The setting `LOGIN_FAILURE_LIMIT` allows to enable a number of allowed login attempts.
# If the settings is not set or set to 0, the feature is disabled.
LOGIN_FAILURE_LIMIT = env.get("login_failure_limit", 3)

# APPLICATION SPECIFIC SETTINGS
AUTH_PROFILE_MODULE = 'groups.User'
ALLOWED_HOSTS = env.getlist("allowed_hosts", ["localhost"])

# This honours the X-Forwarded-Host header set by our nginx frontend when
# constructing redirect URLS.
# see: https://docs.djangoproject.com/en/1.4/ref/settings/#use-x-forwarded-host
USE_X_FORWARDED_HOST = env.get("use_x_forwarded_host", True)

if env.get("memcache", ""):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': env.getlist("memcache"),
            'KEY_PREFIX': env.get("key_prefix", "rdrf")
        }
    }

    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'trrf_django_cache',
            'TIMEOUT': 3600,
            'MAX_ENTRIES': 600
        }
    }

    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# #
# # LOGGING
# #
LOG_DIRECTORY = env.get('log_directory', os.path.join(WEBAPP_ROOT, "log"))

# UserAgent lookup cache location - used by django_user_agents
USER_AGENTS_CACHE = 'default'

CONSOLE_LOG_LEVEL = env.get('console_log_level', 'DEBUG')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(levelname)s:%(asctime)s:%(filename)s:%(lineno)s:%(funcName)s] %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'simplest': {
            'format': '%(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': CONSOLE_LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'shell': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False
        },
        'django': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True
        },
        'parso': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'rdrf.management.commands': {
            'handlers': ['shell'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'rdrf.export_import': {
            'handlers': ['shell'],
            'formatter': 'simplest',
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'aws_xray_sdk': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propograte': True,
        },
        'botocore': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propograte': True,
        },
        'urllib3': {
            'handlers': ['console'],
            'level': 'INFO',
            'propograte': True,
        },
    }
}

# Design Mode:
# True means forms. sections, cdes can be edited in Django admin
# False ( the default) means registry definition cannot be edited on site
DESIGN_MODE = env.get('design_mode', False)


################################################################################
# Customize settings for each registry below
################################################################################

AUTH_USER_MODEL = 'groups.CustomUser'
AUTH_USER_MODEL_PASSWORD_CHANGE_DATE_ATTR = "password_change_date"

# How long a user's password is good for. None or 0 means no expiration.
PASSWORD_EXPIRY_DAYS = env.get("password_expiry_days", 180)
# How long before expiry will the frontend start bothering the user
PASSWORD_EXPIRY_WARNING_DAYS = env.get("password_expiry_warning_days", 30)
# Disable the user's account if they haven't logged in for this time
ACCOUNT_EXPIRY_DAYS = env.get("account_expiry_days", 100)

# Allow users to unlock their accounts by requesting a reset link in email and then visiting it
ACCOUNT_SELF_UNLOCK_ENABLED = env.get("account_self_unlock_enabled", True)

INTERNAL_IPS = ('127.0.0.1', '172.16.2.1')

INSTALL_NAME = env.get("install_name", 'rdrf')

ACCOUNT_ACTIVATION_DAYS = 2

LOGIN_URL = '{0}/account/login'.format(SCRIPT_NAME)
LOGIN_REDIRECT_URL = '{0}/'.format(SCRIPT_NAME)


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissions',
    ),
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
}

# setup for SYSTEM_ROLE
SYSTEM_ROLE = SystemRoles[env.get("SYSTEM_ROLE", "NORMAL_NO_PROMS")]

PROJECT_TITLE = env.get("project_title", "Trial Ready Registry Framework")
PROJECT_TITLE_LINK = "admin:index" if SYSTEM_ROLE is SystemRoles.CIC_PROMS else "patientslisting"

PROJECT_LOGO = env.get("project_logo", "")
PROJECT_LOGO_LINK = env.get("project_logo_link", "")

LOCALE_PATHS = env.getlist("locale_paths", [os.path.join(WEBAPP_ROOT, "translations/locale")])

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'rdrf.auth.password_validation.HasUppercaseLetterValidator',
    },
    {
        'NAME': 'rdrf.auth.password_validation.HasLowercaseLetterValidator',
    },
    {
        'NAME': 'rdrf.auth.password_validation.HasNumberValidator',
    },
    {
        'NAME': 'rdrf.auth.password_validation.HasSpecialCharacterValidator',
    },
    {
        'NAME': 'rdrf.auth.password_validation.ConsecutivelyRepeatingCharacterValidator',
        'OPTIONS': {
            'length': 3
        }
    },
    {
        'NAME': 'rdrf.auth.password_validation.ConsecutivelyIncreasingNumberValidator',
        'OPTIONS': {
            'length': 3
        }
    },
    {
        'NAME': 'rdrf.auth.password_validation.ConsecutivelyDecreasingNumberValidator',
        'OPTIONS': {
            'length': 3
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'
    },
    {
        'NAME': 'rdrf.auth.password_validation.DifferentToPrevious'
    }
]

# setup for PROMS
PROMS_SECRET_TOKEN = env.get("proms_secret_token", "foobar")  # todo set this us in env etc
PROMS_USERNAME = env.get("proms_username", "promsuser")
PROMS_LOGO = env.get("proms_logo", "")

VERSION = env.get('app_version', rdrf.VERSION)

HIGHLIGHT_FORM_CHANGES_ENABLED = env.get('highlight_form_changes_enabled', True)

# Feature to auto-logout users if their are inactive

# Enable/disable feature overall
AUTO_LOGOUT_ENABLED = env.get('auto_logout_enabled', False)
# Warn the user they will be logged out after this much milliseconds
AUTO_LOGOUT_WARN_AFTER_MS = env.get('auto_logout_warn_after_ms', 120 * 1000)
# Log out the user if they have been warned but didn't react for this many milliseconds
AUTO_LOGOUT_WARNED_USER_AFTER_MS = env.get('auto_logout_warned_user_after_ms', 30 * 1000)

ACCOUNT_AUTHENTICATED_REGISTRATION_REDIRECTS = env.get('account_authenticated_registration_redirects', False)

# Patient Registration
REGISTRATION_FORM = "rdrf.forms.registration_forms.PatientRegistrationForm"
REGISTRATION_CLASS = "registry.groups.registration.patient.PatientRegistration"

# Parent Registration (also adding a patient at registration time)
# REGISTRATION_FORM = "rdrf.forms.registration_forms.ParentWithPatientRegistrationForm"
# REGISTRATION_CLASS = "registry.groups.registration.parent_with_patient.ParentWithPatientRegistration"

# In case you set up customised email templates for the "new-patient" notification, you should
# set this to False, otherwise the default registration email will also be sent to the user.
# Setting it to False turns off django-registration-redux's email notifications as we would like to
# send email registration through TRRF's email notification system.
SEND_ACTIVATION_EMAIL = False

RECAPTCHA_SITE_KEY = env.get("recaptcha_site_key", "")
RECAPTCHA_SECRET_KEY = env.get("recaptcha_secret_key", "")

# Including only the API urls for now, add more later if needed
JS_REVERSE_INCLUDE_ONLY_NAMESPACES = ('v1', )

EXTRA_HIDABLE_DEMOGRAPHICS_FIELDS = ('living_status', )
LOGIN_LOG_FILTERED_USERS = env.getlist('login_log_filtered_users', ['newrelic'])

STRONGHOLD_DEFAULTS = False
STRONGHOLD_PUBLIC_URLS = (
    r'/account/login',
    r'/(?P<registry_code>\w+)/register',
    r'/activate/(?P<activation_key>\w+)/?$',
    r'/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/?$',
    r'^i18n/',
    r'/api/v1/countries/(?P<country_code>[A-Z]{2})/states/$',
    r'/api/v1/registries/(?P<registry_code>\w+)/patients/$',  # Authentication implemented in class
)
if DEBUG:
    STRONGHOLD_PUBLIC_URLS = STRONGHOLD_PUBLIC_URLS + (r"^%s.+$" % STATIC_URL, )

# Public named urls can contain only urls without parameters
# as django-stronghold cannot handle it otherwise
STRONGHOLD_PUBLIC_NAMED_URLS = (
    'health_check',
    'landing',
    'login_assistance',
    'registration_complete',
    'registration_failed',
    'registration_disallowed',
    'registration_activation_complete',
    'registration_activate_complete',
    'password_reset_done',
    'password_reset_complete',
    'favicon',
    'robots_txt',
    'js_reverse',
    'javascript-catalog',
)

# URLs whitelisted for meeting the security conventions
# Refer to docs/security/README.rst
SECURITY_WHITELISTED_URLS = url_whitelist.SECURITY_WHITELISTED_URLS

# Frontend session renewal
SESSION_REFRESH_MAX_RETRIES = env.get('session_refresh_max_retries', 5)
SESSION_REFRESH_LEAD_TIME = env.get('session_refresh_lead_time', 120)

# Quicklinks settings
QUICKLINKS_CLASS = 'rdrf.forms.navigation.quick_links.QuickLinks'

# Use the setting below in registries derived from trrf to setup extra UI widgets
# it shoud be a string indicating the module where registry specific widgets are defined
# EXTRA_WIDGETS = '<fill module name here>'

# Override the setting below in registries derived from trrf to tag forms to
# allow customising the behaviour of trrf when interacting with them
REGISTRY_FORM_TAGS = ()
