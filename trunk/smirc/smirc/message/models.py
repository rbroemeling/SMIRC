import logging
import os
import re
import stat
import tempfile
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from smirc.chat.models import Membership
from smirc.chat.models import SmircException

class SmircOutOfAreaException(SmircException):
	pass

class SmircMessageException(SmircException):
	pass

class SmircRawMessageException(SmircMessageException):
	pass

class AreaCode(models.Model):
	COUNTRY_CHOICES = (
		('CA', 'Canada'),
		('USA', 'United States of America')
	)
	area_code = models.PositiveSmallIntegerField(primary_key=True)
	country_code = models.PositiveSmallIntegerField()
	region = models.CharField(max_length=32)
	country = models.CharField(max_length=32, choices=COUNTRY_CHOICES)

	@staticmethod
	def validate_phone_number(s):
		try:
			country_code = s[0]
			area_code = s[1:4]
		except IndexError:
			logging.warning('invalid phone number failed validation: %s' % (s))
			pass
		else:
			try:
				AreaCode.objects.get(area_code__exact=area_code, country_code__exact=country_code)
				return True
			except AreaCode.DoesNotExist:
				logging.warning('phone number %s failed validation due to unknown country code (%s) or area code (%s)' % (s, country_code, area_code))
				pass
		return False

class MessageSkeleton(models.Model):
	body = None
	command = False
	raw_body = None
	raw_phone_number = None
	sender = models.ForeignKey(Membership)
	system = False

	def receive(self, data):
		self.raw_receive(data)
		logging.debug('received raw SMS message text "%s" from %s' % (self.raw_body, self.raw_phone_number))
		
		if not AreaCode.validate_phone_number(self.raw_phone_number):
			raise SmircOutOfAreaException('disregarding message from outside of SMIRC service area (%s)' % (self.raw_phone_number))
		
		if self.raw_body is None:
			raise SmircMessageException('disregarding null message')
		self.raw_body = self.raw_body.strip()
		if self.raw_body == '':
			raise SmircMessageException('disregarding empty message')

		try:
			user = UserProfile.load_user(self.raw_phone_number)
			self.command = SmircCommand.handle(user, self.raw_body)
		except User.DoesNotExist:
			user = None
			self.command = SmircCommand.handle(self.raw_phone_number, self.raw_body)

		if self.command:
			return
		if user is None:
			raise SmircMessageException('unknown sender (%s) -- maybe you are not registered? Please use "%sNICK <your nick>" to register or see www.smirc.com for help.' % (self.raw_phone_number, SmircCommand.COMMAND_CHARACTER))

		conversation_match = re.match('^@(\S*)\s*(.*)', self.raw_body)
		if conversation_match:
			conversation_identifier = conversation_match.group(1)
			self.body = conversation_match.group(2)
			try:
				self.sender = Membership.load_membership(user, conversation_identifier)
			except Membership.DoesNotExist:
				raise SmircMessageException('you are not involved in a conversation named %s' % (conversation_identifier))
		else:
			self.body = self.raw_body
			try:
				self.sender = Membership.objects.filter(user__id__exact=user.id).order_by('last_active').reverse()[0]
			except IndexError:
				raise SmircMessageException('you did not target a conversation, and you have no last-active (default) conversation')
		logging.debug('message body = "%s", target conversation = "%s" (id:%d), sender = "%s" (id:%d)' % (self.body, self.sender.conversation.name, self.sender.conversation.id, self.sender.user.username, self.sender.user.id))
		
	def send(self, phone_number):
		if self.body is None:
			raise SmircMessageException('disregarding null message')
		self.body = self.body.strip()
		if self.body == '':
			raise SmircMessageException('disregarding empty message')

		if self.system:
			message = 'SMIRC: %s' % (self.body)		
		else:
			if self.sender is None:
				raise SmircMessageException('disregarding message with invalid (null) sender')
			message = '%s: %s' % (str(self.sender), self.body)

		message = message[:140]
		logging.debug('sending message "%s" to %s' % (message, phone_number))
		return self.raw_send(phone_number, message)

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
			raise SmircRawMessageException('no "from" header was found in the file %s' % (location))

	def raw_send(self, phone_number, message):
		tempfile.tempdir = settings.SMSTOOLS['outbound_dir']
		(fd, path) = tempfile.mkstemp('suffix', 'prefix', None, True)
		os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
		f = os.fdopen(fd, 'w')
		f.write('To: %s\n' % (phone_number))
		f.write('\n')
		f.write('%s\n' % (message))
		f.close()
		return path

# We import smirc.* modules at the bottom (instead of at the top) as a fix for
# circular import problems.
from smirc.chat.models import UserProfile
from smirc.command.models import SmircCommand
