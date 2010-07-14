#!/usr/bin/env python
#
# Monitor a directory for incoming SMS messages and deal with them as they arrive.
#
# Note that because this daemon includes django models and thus has a dependency
# on the django framework, it requires the DJANGO_SETTINGS_MODULE environment
# variable to be set.
#   See http://docs.djangoproject.com/en/dev/topics/settings/ for more information.
#
import logging
import os
import pyinotify
import sys
from django.conf import settings
from smirc.api.models import Message
from smirc.api.models import UserProfile
from smirc.api.models import Room

__version__ = '$Rev$'

class SMSFileHandler(pyinotify.ProcessEvent):
	def process_IN_CLOSE_WRITE(self, event):
		logging.debug('event IN_CLOSE_WRITE occurred for %s' % event.pathname)
		try:
			with open(event.pathname, 'r') as f:
				data = f.read()
			message = Message()
			message.parse(data)
		except IOError, e:
			logging.error('error reading file: %s', str(e))

def smircd_sanity_check():
	errors = 0

	if not os.path.exists(settings.SMSTOOLS['inbound_dir']):
		logging.error('inbound directory %s does not exist' % (settings.SMSTOOLS['inbound_dir']))
		errors += 1
	else:
		if not os.path.isdir(settings.SMSTOOLS['inbound_dir']):
			logging.error('inbound directory %s is not a directory' % (settings.SMSTOOLS['inbound_dir']))
			errors += 1
		else:
			if not os.access(settings.SMSTOOLS['inbound_dir'], os.R_OK):
				logging.error('inbound directory %s is not readable' % (settings.SMSTOOLS['inbound_dir']))
				errors += 1

	if not os.path.exists(settings.SMSTOOLS['outbound_dir']):
		logging.error('outbound directory %s does not exist' % (settings.SMSTOOLS['outbound_dir']))
		errors += 1
	else:
		if not os.path.isdir(settings.SMSTOOLS['outbound_dir']):
			logging.error('outbound directory %s is not a directory' % (settings.SMSTOOLS['outbound_dir']))
			errors += 1
		else:
			if not os.access(settings.SMSTOOLS['outbound_dir'], os.W_OK):
				logging.error('outbound directory %s is not writable' % (settings.SMSTOOLS['outbound_dir']))
				errors += 1

	if errors > 0:
		sys.exit(-2)

if __name__ == '__main__':
	logging.debug('settings.SMSTOOLS: %s', str(settings.SMSTOOLS))
	smircd_sanity_check()

	watch_manager = pyinotify.WatchManager()
	sms_file_handler = SMSFileHandler()
	notifier = pyinotify.Notifier(watch_manager, sms_file_handler)
	watch_manager.add_watch(settings.SMSTOOLS['inbound_dir'], pyinotify.IN_CLOSE_WRITE)
	
	notifier.loop()
