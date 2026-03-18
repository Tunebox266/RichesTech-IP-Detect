"""
Local development settings
"""
from .base import *

DEBUG = True

# Use console email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable password validators in development
AUTH_PASSWORD_VALIDATORS = []

# Show debug toolbar
INTERNAL_IPS = ['127.0.0.1']

# Disable Axes in development
AXES_ENABLED = False

# Use SQLite for development (optional - comment out to use PostgreSQL)
import sys
if 'test' in sys.argv or 'migrate' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
