import logging
import re
import tempfile
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import FieldError

tempfile.tempdir = settings.SMSTOOLS['outbound_dir']

class MessageSkeleton(models.Model):
	user = models.ForeignKey(User)
	room = models.ForeignKey(Room)
	body = None
	headers = {}

	def receive(self, data):
		(phone_number, body) = self.raw_receive(data)

		if phone_number is None:
			raise FieldError('null message sender')
		try:
			profile = UserProfile.objects.get(phone_number=phone_number)
		except UserProfile.DoesNotExist:
			raise FieldError('unknown message sender: %s' % (phone_number))
		self.user = profile.user

		if body:
			room_match = re.match('\s*@(\S+)\s*', body)
			# TODO: the roommatching code below IS NOT RIGHT.  Figure it out.
			if room_match:
				room_name = room_match.group(1)
				self.body = body[room_match.end()+1:]
				try:
					membership = Membership.objects.get(user=self.user, room.name=room_name)
					self.room = membership.room
				except Membership.DoesNotExist:
					raise FieldError('unknown message room: %s' % (room_name))
				if profile.room != self.room:
					profile.room = self.room
					profile.save()
			else:
				self.body = body
				if profile.room:
					self.room = profile.room
				else:
					raise FieldError('no target room defined and no default room found')
		else:
			raise FieldError('null message body')
		self.save()

	def send(self, phone_number, message):
		message = '%s@%s: %s' % (self.user.name, self.room.name, message)
		message = message[:140]
		self.raw_send(phone_number, message)


class SMSTools(MessageSkeleton):
	def raw_receive(self, location):
		body = None
		headers = {}
		while open(location, 'r') as f:
			for line in f:
				if not body is None:
					body += line
				else:
					if line:
						try:
							(key, value) = line.split(':', 1)		
							key = key.strip().lower()
							value = value.strip()
							headers[key] = value
						except ValueError, e:
							logging.warn('skipping invalid header: "%s"' % (line))
					else:
						body = ''
		if headers.has_key('from'):
			return (headers['from'], body)
		else:
			return (None, body)

	def raw_send(self, phone_number, message):
		(f, path) = tempfile.mkstemp('suffix', 'prefix', None, True)
		f.write('To: %s\n' % (phone_number))
		f.write('\n')
		f.write('%s\n' % (message))
		f.close()
