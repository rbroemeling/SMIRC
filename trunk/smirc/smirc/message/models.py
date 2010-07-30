import logging
import os
import re
import tempfile
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from smirc.chat.models import Conversation
from smirc.chat.models import Membership
from smirc.chat.models import UserProfile

class MessageException(Exception):
	def __init__(self, value):
		self.value = value

	def __str__(self):
		return repr(self.value)

class MessageSkeleton(models.Model):
	body = None
	command = False
	raw_body = None
	raw_phone_number = None
	sender = models.ForeignKey(Membership)
	system = False

	def receive(self, data):
		self.raw_receive(data)
		logging.debug('received message "%s" from %s' % (self.raw_body, self.raw_phone_number))

		if self.raw_body is None:
			raise MessageException('null message body')
		self.raw_body = self.raw_body.strip()
		if self.raw_body == '':
			raise MessageException('empty message body')

		try:
			user = UserProfile.load_user(self.raw_phone_number)
		except User.DoesNotExist:
			raise MessageException('unknown message sender: %s' % (self.raw_phone_number))

		self.command = SmircCommand.handle(self.raw_body)
		if self.command:
			return

		conversation_match = re.match('^@(\S*)\s*(.*)', self.raw_body)
		if conversation_match:
			conversation_identifier = conversation_match.group(1)
			self.body = conversation_match.group(2)
			try:
				self.sender = Membership.load_membership(user, conversation_identifier)
			except Membership.DoesNotExist:
				raise MessageException('you are not involved in a conversation named %s' % (conversation_identifier))
		else:
			try:
				self.sender = Membership.objects.filter(user__id__exact=user.id).order_by('last_active').reverse()[0]
			except IndexError:
				raise MessageException('no target conversation defined and no default conversation found')

		# TODO: remember to update self.sender.last_active timestamp
		return self

	def send(self, phone_number):
		if self.body is None:
			raise MessageException('null message body')
		if self.system:
			message = 'SMIRC: %s' % (self.body)		
		else:
			if self.conversation is None:
				raise MessageException('null message conversation')
			if self.user is None:
				raise MessageException('null message sender')
			message = '%s@%s: %s' % (self.user.username, self.conversation.name, self.body)
		message = message[:140]
		return self.raw_send(phone_number, message)

class RawMessageException(MessageException):
	pass

class SMSToolsMessage(MessageSkeleton):
	def raw_receive(self, location):
		body = None
		headers = {}
		with open(location, 'r') as f:
			for line in f:
				if not body is None:
					body += line
				else:
					if line != '\n':
						try:
							(key, value) = line.split(':', 1)		
							key = key.strip().lower()
							value = value.strip()
							headers[key] = value
						except ValueError:
							logging.warn('skipping invalid header: "%s"' % (line))
					else:
						body = ''
		self.raw_body = body
		if headers.has_key('from'):
			self.raw_phone_number = headers['from']
		else:
			raise RawMessageException('no "from" header was found in the file %s' % (location))

	def raw_send(self, phone_number, message):
		tempfile.tempdir = settings.SMSTOOLS['outbound_dir']
		(fd, path) = tempfile.mkstemp('suffix', 'prefix', None, True)
		f = os.fdopen(fd, 'w')
		f.write('To: %s\n' % (phone_number))
		f.write('\n')
		f.write('%s\n' % (message))
		f.close()
		return path

# TODO: Move these unit tests elsewhere.
# import os
# import unittest
# 
# class SMSToolsMessageTestCase(unittest.TestCase):
	# def setUp(self):
		# open('/tmp/permissionerror.message', 'w').close()
		# os.chmod('/tmp/permissionerror.message', 0)
		# open('/tmp/empty.message', 'w').close()
		# with open('/tmp/unknownuser.message', 'w') as f:
			# f.write("""From: 491721234567
# From_SMSC: 491722270333
# Sent: 00-02-21 22:26:23
# Received: 00-02-21 22:26:29
# Subject: modem1
# Alphabet: ISO
# UDH: false
# 
# This is the Text that I have sent with my mobile phone to the computer.""")
		# self.msg = SMSToolsMessage()
# 
	# def tearDown(self):
		# os.remove('/tmp/permissionerror.message')
		# os.remove('/tmp/empty.message')
		# os.remove('/tmp/unknownuser.message')
# 
	# def test_receive_empty(self):
		# self.assertEqual(self.msg.raw_receive('/tmp/empty.message'), (None, None))
		# try:
			# self.assertRaises(MessageException, self.msg.receive('/tmp/empty.message'))
		# except MessageException:
			# pass
# 
	# def test_receive_nonexistent(self):
		# self.assertEqual(self.msg.raw_receive('/tmp/nonexistent.message'), (None, None))
		# try:
			# self.assertRaises(MessageException, self.msg.receive('/tmp/nonexistent.message'))
		# except MessageException:
			# pass
# 
	# def test_receive_permissionerror(self):
		# self.assertEqual(self.msg.raw_receive('/tmp/permissionerror.message'), (None, None))
		# try:
			# self.assertRaises(MessageException, self.msg.receive('/tmp/permissionerror.message'))
		# except MessageException:
			# pass
# 
	# def test_receive_unknownuser(self):
		# self.assertEqual(self.msg.raw_receive('/tmp/unknownuser.message'), ('491721234567', 'This is the Text that I have sent with my mobile phone to the computer.'))
		# try:
			# self.assertRaises(MessageException, self.msg.receive('/tmp/unknownuser.message'))
		# except MessageException:
			# pass
