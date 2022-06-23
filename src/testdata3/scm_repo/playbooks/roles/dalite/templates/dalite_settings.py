import getpass

import os

SECRET_KEY = '{{ DALITE_SECRET_KEY }}'

DEBUG = False

ALLOWED_HOSTS = ['{{ DALITE_SERVER_DOMAIN }}']

SECURE_PROXY_SSL_HEADER = ('HTTP_X_SCHEME', 'https')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '{{ MYSQL_DALITE_DATABASE }}',
        'USER': '{{ MYSQL_DALITE_USER }}',
        'PASSWORD': '{{ MYSQL_DALITE_PASSWORD }}',
        'HOST': '{{ MYSQL_DALITE_HOST }}',
    }
}

INSTALLED_APPS = (
    'grappelli',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'peerinst',
    'django_lti_tool_provider',
)

STATIC_ROOT="{{ DALITE_STATICFILES_ROOT }}"
STATIC_URL="/static/"

MEDIA_ROOT="{{ DALITE_MEDIA_ROOT }}"
MEDIA_URL="/media/"

if getpass.getuser() == '{{ DALITE_USER_NAME }}':
    # change log paths only for production requests
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file_debug_log': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': '{{ DALITE_LOG_DIR }}/debug.log',
            },
            'file_student_log': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': '{{ DALITE_LOG_DIR }}/student.log',
            },
        },
        'loggers': {
            'django.request': {
                'handlers': ['file_debug_log'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'peerinst.views': {
                'handlers': ['file_student_log'],
                'level': 'INFO',
                'propagate': True,
            },
            'django_lti_tool_provider': {
                'handlers': ['file_debug_log'],
                'level': 'DEBUG',
                'propagate': True,
            },
        },
    }

#LTI settings
LTI_CLIENT_KEY = '{{ DALITE_LTI_CLIENT_KEY }}'
LTI_CLIENT_SECRET = '{{ DALITE_LTI_CLIENT_SECRET }}'
PASSWORD_GENERATOR_NONCE = '{{ DALITE_PASSWORD_GENERATOR_NONCE }}'

DEFAULT_FILE_STORAGE='swift.storage.SwiftStorage'
SWIFT_CONTAINER_NAME='{{ DALITE_MEDIA_CONTAINER }}'

# These variables are passed to gunicorn --- so they are not here when you call
# management commands (by design) if you need a management command to touch
# Swift containers we'll change that.
SWIFT_AUTH_URL=os.environ.get("OS_AUTH_URL")
SWIFT_USERNAME=os.environ.get("OS_USERNAME")
SWIFT_KEY=os.environ.get("OS_PASSWORD")
SWIFT_AUTH_VERSION=2
SWIFT_TENANT_ID=os.environ.get("OS_TENANT_ID")
