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
from smirc.command.models import SmircCommandException
from smirc.message.models import SmircMessageException
from smirc.message.models import SmircOutOfAreaException
from smirc.message.models import SmircRawMessageException
from smirc.message.models import SMSToolsMessage

__version__ = '$Rev$'

class SMSFileHandler(pyinotify.ProcessEvent):
	def process_IN_MODIFY(self, event):
		logging.debug('event IN_MODIFY occurred for %s' % event.pathname)
		message = SMSToolsMessage()
		response = None
		try:
			message.receive(event.pathname)
		except (SmircCommandException, SmircMessageException) as e:
			response = SMSToolsMessage()
			response.body = str(e)
			response.system = True
		except SmircOutOfAreaException as e:
			logging.warning('message out of area exception: %s' % (str(e)))
		except SmircRawMessageException as e:
			logging.error('raw message exception occurred while receiving messages %s: %s' % (event.pathname, e))
		except Exception as e:
			logging.exception('unhandled exception occurred while receiving message %s: %s' % (event.pathname, e))
		else:
			if (message.command):
				response = SMSToolsMessage()
				try:
					response.body = message.command.execute()
				except SmircCommandException as e:
					response.body = str(e)
				response.system = True
			else:
				message.sender.last_active = datetime.datetime.utcnow()
				message.sender.save()
				try:
					for recipient in Membership.objects.exclude(user__id__exact=sender.user).get(conversation=sender):
						message.send(recipient.user.get_profile().phone_number)
				except Membership.DoesNotExist:
					pass		
		os.rename(event.pathname, '%s/archived/%s' % (settings.SMSTOOLS['inbound_dir'], os.path.basename(event.pathname)))
		if response is not None:
			try:
				response.send(message.raw_phone_number)
			except Exception as e:
				logging.exception('unhandled exception occurred while sending message to %s: %s' % (message.raw_phone_number, e))

def signal_handler(signum, frame):
	global smircd_terminate
	
	sigdesc = 'UNKNOWN'
	for member in inspect.getmembers(signal):
		if member[0][0:3] == 'SIG' and member[1] == signum:
			sigdesc = member[0]
			break
	if signum in [ signal.SIGINT, signal.SIGTERM, signal.SIGQUIT ]:
		logging.info('signal_handler received signal %s(%d), setting termination flag' % (sigdesc, signum))
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

	if not os.path.exists('%s/archived' % (settings.SMSTOOLS['inbound_dir'])):
		os.mkdir('%s/archived' % (settings.SMSTOOLS['inbound_dir']))

	signal.signal(signal.SIGHUP, signal_handler)
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	watch_manager = pyinotify.WatchManager()
	sms_file_handler = SMSFileHandler()
	notifier = pyinotify.Notifier(watch_manager, sms_file_handler)
	watch_manager.add_watch(settings.SMSTOOLS['inbound_dir'], pyinotify.IN_MODIFY)
	
	# TODO: deal with pre-existing files (i.e. files that have already been received and
	# are sitting on our inbound directory right now.
	while True:
		notifier.process_events()
		if smircd_terminate == True:
			notifier.stop()
			break
		if notifier.check_events(timeout=500):
			notifier.read_events()
