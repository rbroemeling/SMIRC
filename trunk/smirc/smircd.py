#!/usr/bin/env python
#
# Monitor a directory for incoming SMS messages and deal with them as they arrive.
#
# Note that because this daemon includes django models and thus has a dependency
# on the django framework, it requires the DJANGO_SETTINGS_MODULE environment
# variable to be set.
#
# In general, an example DJANGO_SETTINGS_MODULE environment variable setting
# will look like this:
#
#	export DJANGO_SETTINGS_MODULE="smirc.settings"
#
# See http://docs.djangoproject.com/en/dev/topics/settings/ for more information.
#
import inspect
import logging
import os
import pyinotify
import signal
import sys
from django.conf import settings
from smirc.command.models import SmircCommand
from smirc.message.models import SMSToolsMessage

__version__ = '$Rev$'

class SMSFileHandler(pyinotify.ProcessEvent):
	def process_IN_CLOSE_WRITE(self, event):
		logging.debug('event IN_CLOSE_WRITE occurred for %s' % event.pathname)
		message = SMSToolsMessage()
		receive_exception = None
		response = SMSToolsMessage()
		try:
			message.receive(event.pathname)
		except FieldError, e:
			if message.user:
				response.body = str(e)
				response.system = True
			else:
				receive_exception = e
		except Exception, e:
			receive_exception = e
		else:
			if (message.command):
				command = SmircCommand()
				try:
					response.body = command.execute(message)
				except SmircCommandException, e:
					response.body = str(e)
				response.system = True
			else:
				# TODO: deal with the message in message.body, sent by message.user to message.conversation
		if receive_exception:
			logging.warning('unhandled exception occurred while receiving message %s: %s' % (event.pathname, str(receive_exception))
		if response.body:
			response.send(message.user.profile.phone_number)			

def signal_handler(signum, frame):
	global smircd_terminate
	
	sigdesc = 'UNKNOWN'
	for member in inspect.getmembers(signal):
		if member[0][0:3] == 'SIG' and member[1] == signum:
			sigdesc = member[0]
			break
	if signum in [ signal.SIGINT, signal.SIGTERM, signal.SIGQUIT ]:
		logging.info('signal_handler received signal %s(%d), setting terminate flag' % (sigdesc, signum))
		smircd_terminate = True
	elif signum in [ signal.SIGHUP ]:
		logging.warning('signal_handler ignoring signal %s(%d)' % (sigdesc, signum))
	else:
		logging.error('signal_handler ignoring unhandled signal %s(%d)' % (sigdesc, signum))

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

smircd_terminate = False

if __name__ == '__main__':
	logging.debug('settings.SMSTOOLS: %s', str(settings.SMSTOOLS))
	smircd_sanity_check()

	signal.signal(signal.SIGHUP, signal_handler)
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	watch_manager = pyinotify.WatchManager()
	sms_file_handler = SMSFileHandler()
	notifier = pyinotify.Notifier(watch_manager, sms_file_handler)
	watch_manager.add_watch(settings.SMSTOOLS['inbound_dir'], pyinotify.IN_CLOSE_WRITE)
	
	while True:
		notifier.process_events()
		if smircd_terminate == True:
			notifier.stop()
			break
		if notifier.check_events():
			notifier.read_events()
