import logging
import re
import tempfile
from django.db import models
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
	sender = models.ForeignKey(Membership)
	system = False

	def receive(self, data):
		(phone_number, body) = self.raw_receive(data)
		logging.debug('received message "%s" from %s' % (body, phone_number))

		try:
			user = UserProfile.load_user(phone_number)
		except User.DoesNotExist:
			raise MessageException('unknown message sender: %s' % (phone_number))

		if body is None:
			raise MessageException('null message body')
		body = body.strip()
		if body == '':
			raise MessageException('empty message body')

		self.command = SmircCommand.handle(body)
		if self.command:
			return

		conversation_match = re.match('^@(\S*)\s*(.*)', body)
		if conversation_match:
			conversation_identifier = conversation_match.group(1)
			body = conversation_match.group(2)
			try:
				self.sender = Membership.load_membership(user, conversation_identifier)
			except Membership.DoesNotExist:
				raise MessageException('you are not involved in a conversation named %s' % (conversation_identifier))
		else:
			try:
				self.sender = Membership.objects.filter(user__id__exact=user.id).order_by('last_active').reverse()[0]
			except IndexError:
				raise MessageException('no target conversation defined and no default conversation found')

		self.body = body
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

class SMSToolsMessage(MessageSkeleton):
	def raw_receive(self, location):
		body = None
		headers = {}
		try:
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
							except ValueError, e:
								logging.warn('skipping invalid header: "%s"' % (line))
						else:
							body = ''
		except IOError, e:
			# TODO: Ensure that we throw an exception on this error case, map it to some sort of Message.Exception
			logging.warning('I/O error encountered attempting to read file: %s' % (str(e)))
			pass
		else:
			if headers.has_key('from'):
				return (headers['from'], body)
			else:
				return (None, body)

	def raw_send(self, phone_number, message):
		tempfile.tempdir = settings.SMSTOOLS['outbound_dir']
		(f, path) = tempfile.mkstemp('suffix', 'prefix', None, True)
		f.write('To: %s\n' % (phone_number))
		f.write('\n')
		f.write('%s\n' % (message))
		f.close()
		return path

# TODO: Move these unit tests elsewhere.
import os
import unittest

class SMSToolsMessageTestCase(unittest.TestCase):
	def setUp(self):
		open('/tmp/permissionerror.message', 'w').close()
		os.chmod('/tmp/permissionerror.message', 0)
		open('/tmp/empty.message', 'w').close()
		with open('/tmp/unknownuser.message', 'w') as f:
			f.write("""From: 491721234567
From_SMSC: 491722270333
Sent: 00-02-21 22:26:23
Received: 00-02-21 22:26:29
Subject: modem1
Alphabet: ISO
UDH: false

This is the Text that I have sent with my mobile phone to the computer.""")
		self.msg = SMSToolsMessage()

	def tearDown(self):
		os.remove('/tmp/permissionerror.message')
		os.remove('/tmp/empty.message')
		os.remove('/tmp/unknownuser.message')

	def test_receive_empty(self):
		self.assertEqual(self.msg.raw_receive('/tmp/empty.message'), (None, None))
		try:
			self.assertRaises(MessageException, self.msg.receive('/tmp/empty.message'))
		except MessageException:
			pass

	def test_receive_nonexistent(self):
		self.assertEqual(self.msg.raw_receive('/tmp/nonexistent.message'), (None, None))
		try:
			self.assertRaises(MessageException, self.msg.receive('/tmp/nonexistent.message'))
		except MessageException:
			pass

	def test_receive_permissionerror(self):
		self.assertEqual(self.msg.raw_receive('/tmp/permissionerror.message'), (None, None))
		try:
			self.assertRaises(MessageException, self.msg.receive('/tmp/permissionerror.message'))
		except MessageException:
			pass

	def test_receive_unknownuser(self):
		self.assertEqual(self.msg.raw_receive('/tmp/unknownuser.message'), ('491721234567', 'This is the Text that I have sent with my mobile phone to the computer.'))
		try:
			self.assertRaises(MessageException, self.msg.receive('/tmp/unknownuser.message'))
		except MessageException:
			pass
