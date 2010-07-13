#!/usr/local/bin/python
#
# Monitor a directory for incoming SMS messages and deal with them as they arrive.
#
# Note that because this daemon includes django models and thus has a dependency
# on the django framework, it requires the DJANGO_SETTINGS_MODULE environment
# variable to be set.
#   See http://docs.djangoproject.com/en/dev/topics/settings/ for more information.
#
import logging
import optparse
import os
import pyinotify
import re
from api.models import Message
from api.models import UserProfile
from api.models import Room

__version__ = "$Rev$"

class SMSFileHandler(pyinotify.ProcessEvent):
	def process_IN_CLOSE_WRITE(self, event):
		logging.debug("event IN_CLOSE_WRITE occurred for %s" % event.pathname)

def parse_arguments():
	"""
	Parse command-line arguments and setup an optparse object specifying
	the settings for this daemon to use.
	"""
	parser = optparse.OptionParser(
		usage="%prog [options]",
		version="%prog r" + re.sub("[^0-9]", "", __version__)
	)
	parser.add_option(
		"--debug",
		action="store_true",
		default=False,
		help="enable display of verbose debugging information"
	)
	parser.add_option(
		"--path",
		action="append",
		help="path to watch for new files in"
	)
	
	(options, args) = parser.parse_args()
	if not options.path:
		parser.error("option --path: at least one path to watch is required")
	else:
		for path in options.path:
			if not os.path.exists(path):
				parser.error("option --path: %s does not exist" % path)
			if not os.path.isdir(path):
				parser.error("option --path: %s is not a directory" % path)
			if not os.access(path, os.R_OK):
				parser.error("option --path: %s is not accessible" % path)
	return options

if __name__ == "__main__":
	options = parse_arguments()

	# Initialize our logging layer.
	loglevel = logging.INFO
	if options.debug:
		loglevel = logging.DEBUG
	logging.basicConfig(datefmt = "%d %b %Y %H:%M:%S", format = "%(asctime)s %(levelname)-8s %(message)s", level = loglevel)
	del loglevel
	
	logging.debug("options: %s", str(options))

	watch_manager = pyinotify.WatchManager()
	sms_file_handler = SMSFileHandler()
	notifier = pyinotify.Notifier(watch_manager, sms_file_handler)
	watch_manager.add_watch(options.path, pyinotify.IN_CLOSE_WRITE)
	
	notifier.loop()