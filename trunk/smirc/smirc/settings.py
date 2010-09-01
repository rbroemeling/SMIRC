# Determine whether we are running in development or production mode.
import os
import sys

# Default to the production environment.
DEBUG = False
if 'SMIRC_ENVIRONMENT' in os.environ and os.environ['SMIRC_ENVIRONMENT'].lower()[:3] == 'dev':
	# We have been explicitly told to go to development mode via the environment variable SMIRC_ENVIRONMENT.
	DEBUG = True
if 'runserver' in sys.argv:
	# We are implicitly in development mode because we are running under 'manage.py runserver'.
	DEBUG = True

if DEBUG:
	os.environ['SMIRC_ENVIRONMENT'] = 'Development'
else:
	os.environ['SMIRC_ENVIRONMENT'] = 'Production'

# Determine whether we are running as part of smircd.py (SMIRC SMS daemon) or part of the
# SMIRC website (SMIRC WWW).
if (os.path.basename(sys.argv[0]) == 'smircd.py'):
	os.environ['SMIRC_AREA'] = 'Daemon'
else:
	os.environ['SMIRC_AREA'] = 'WWW'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

ADMINS = (
	('Remi Broemeling', 'remi@broemeling.org'),
	# ('Your Name', 'your_email@domain.com'),
)

# Tie our custom user profile class to the User.get_profile() method.
# Technique taken from:
#	http://www.b-list.org/weblog/2006/jun/06/django-tips-extending-user-model/
AUTH_PROFILE_MODULE = 'chat.UserProfile'

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
		'NAME': 'smirc',                      # Or path to database file if using sqlite3.
		'USER': 'smirc',                      # Not used with sqlite3.
		'PASSWORD': 'fBzeaG3oWUl1X1OdChb7',   # Not used with sqlite3.
		'TEST_NAME': 'smirc_test',            # The database that will be used for running tests.
		'HOST': '',                           # Set to empty string for localhost. Not used with sqlite3.
		'PORT': '',                           # Set to empty string for default. Not used with sqlite3.
		'OPTIONS': {
			'init_command': 'SET storage_engine=INNODB'
		}
	}
}

EMAIL_HOST = 'localhost'
EMAIL_SUBJECT_PREFIX = '[SMIRC] '

INSTALLED_APPS = (
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.sites',
	'django.contrib.messages',
	# Uncomment the next line to enable the admin:
	# 'django.contrib.admin',
	'smirc.chat',
	'smirc.command',
	'smirc.message',
	'smirc.www'
)

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# Configure Python's logging module for use throughout smirc.  Use an attribute on the
# logging module to work-around the fact that settings.py can be (and sometimes is) executed
# multiple times, but we really only want to carry out our logging initialization once.
import logging
import logging.handlers
if not getattr(logging.getLogger(''), 'smirc_logging_initialized', False):
	# Initialize a basic (stderr) logger, with a log-level based on our DEBUG constant.
	log_level = logging.INFO
	if DEBUG:
		log_level = logging.DEBUG
	logging.basicConfig(
		level = log_level,
		format = '%(asctime)s %(levelname)-8s %(process)-5d [%(pathname)s:%(lineno)d] %(message)s',
		datefmt = '%d/%b/%Y %H:%M:%S')
	del log_level

	# Also duplicate logging information to syslog via /dev/log, on facility LOG_LOCAL0.  Note
	# that our logging format is different, as syslog implicitly includes a timestamp.
	sh = logging.handlers.SysLogHandler('/dev/log', 'local0')
	sh.setFormatter(logging.Formatter('%(levelname)s <' + os.environ['SMIRC_AREA'] + ':' + os.environ['SMIRC_ENVIRONMENT'] + ', PID %(process)d> [%(pathname)s:%(lineno)d] %(message)s'))
	logging.getLogger('').addHandler(sh)

	logging.info('configuring SMIRC for %s environment' % (os.environ['SMIRC_ENVIRONMENT'].lower()))
	setattr(logging.getLogger(''), 'smirc_logging_initialized', True)

MANAGERS = ADMINS

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

MIDDLEWARE_CLASSES = (
	'django.middleware.common.CommonMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'smirc.urls'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '_b!mf0hketu4xt(l-j+ilw75*bh&xqt#25!v1(8rmv@l3q81wo'

SITE_ID = 1

# SMIRC's phone number.
SMIRC_PHONE_NUMBER = '17807291450'

# Configuration for smstools sms inbound/outbound directories.
SMSTOOLS = {
	'inbound_dir': '/var/spool/sms/incoming',
	'outbound_dir': '/var/spool/sms/outgoing'
}

TEMPLATE_CONTEXT_PROCESSORS =  (
	'django.contrib.auth.context_processors.auth',
	'django.core.context_processors.debug',
	'django.core.context_processors.i18n',
	'django.core.context_processors.media',
	'django.core.context_processors.request',
	'django.contrib.messages.context_processors.messages'
)

TEMPLATE_DEBUG = DEBUG

TEMPLATE_DIRS = (
	# Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
	# Always use forward slashes, even on Windows.
	# Don't forget to use absolute paths, not relative paths.
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
	'django.template.loaders.filesystem.Loader',
	'django.template.loaders.app_directories.Loader',
#	'django.template.loaders.eggs.Loader',
)

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Edmonton'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True
