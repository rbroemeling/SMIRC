import logging
import re
import tempfile
from django.db import models
from django.contrib.auth.models import User
# TODO: Create our own class of exception, rather than over-loading FieldError
from django.core.exceptions import FieldError
from smirc.chat.models import Conversation
from smirc.chat.models import UserProfile

class MessageSkeleton(models.Model):
	body = None
	command = None
	conversation = models.ForeignKey(Conversation)
	system = False
	user = models.ForeignKey(User)

	def receive(self, data):
		(phone_number, body) = self.raw_receive(data)

		try:
			self.user = UserProfile.load_user(phone_number)
		except User.DoesNotExist:
			raise FieldError('unknown message sender: %s' % (phone_number))

		if body is None:
			raise FieldError('null message body')
		body = body.strip()
		if body == '':
			raise FieldError('empty message body')

		command_match = re.match('^\*([A-Za-z]*)\s*(.*)', body)
		if command_match:
			self.command = command_match.group(1)
			body = command_match.group(2)
		else:
			conversation_match = re.match('^@(\S*)\s*(.*)', body)
			if conversation_match:
				conversation = conversation_match.group(1)
				body = conversation_match.group(2)
				try:
					self.conversation = Conversation.load_conversation(conversation, self.user)
				except Conversation.DoesNotExist:
					raise FieldError('unknown conversation: %s' % (conversation))
				else:
					if self.user.profile.last_active_conversation != self.conversation:
						self.user.profile.last_active_conversation = self.conversation
						self.user.profile.save()
			else:
				if self.user.profile.last_active_conversation:
					self.conversation = self.user.profile.last_active_conversation
			if self.conversation is None:
				raise FieldError('no target conversation defined and no default conversation found')

		self.body = body

	def send(self, phone_number):
		if self.body is None:
			raise FieldError('null message body')
		if self.system:
			message = 'SMIRC: %s' % (self.body)		
		else:
			if self.conversation is None:
				raise FieldError('null message conversation')
			if self.user is None:
				raise FieldError('null message sender')
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
			self.assertRaises(FieldError, self.msg.receive('/tmp/empty.message'))
		except FieldError:
			pass

	def test_receive_nonexistent(self):
		self.assertEqual(self.msg.raw_receive('/tmp/nonexistent.message'), (None, None))
		try:
			self.assertRaises(FieldError, self.msg.receive('/tmp/nonexistent.message'))
		except FieldError:
			pass

	def test_receive_permissionerror(self):
		self.assertEqual(self.msg.raw_receive('/tmp/permissionerror.message'), (None, None))
		try:
			self.assertRaises(FieldError, self.msg.receive('/tmp/permissionerror.message'))
		except FieldError:
			pass

	def test_receive_unknownuser(self):
		self.assertEqual(self.msg.raw_receive('/tmp/unknownuser.message'), ('491721234567', 'This is the Text that I have sent with my mobile phone to the computer.'))
		try:
			self.assertRaises(FieldError, self.msg.receive('/tmp/unknownuser.message'))
		except FieldError:
			pass
