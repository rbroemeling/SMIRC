#!/usr/local/bin/python
#
# Monitor a directory for incoming SMS messages and deal with them as they arrive.
#
import optparse
import logging
import pyinotify
import re

__version__ = "$Rev$"

class SMSFileHandler(pyinotify.ProcessEvent):
	def process_IN_CREATE(self, event):
		print "IN_CREATE:", event.pathname

	def process_IN_CLOSE_WRITE(self, event):
		print "IN_CLOSE_WRITE:", event.pathname

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
	
	(options, args) = parser.parse_args()
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
	watch_manager.add_watch('/tmp', pyinotify.IN_CLOSE_WRITE, rec=True)
	
	notifier.loop()