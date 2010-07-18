import logging
import re
import tempfile
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import FieldError

class MessageSkeleton(models.Model):
	class Meta:
		app_label = 'api'

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
			command_match = re.match('\s*/(\S+)\s*', body)
			if command_match:
				command = command_match.group(1)
				command_body = body[command_match.end()+1:]
				return

			room_match = re.match('\s*@(\S+)\s*', body)
			if room_match:
				room = room_match.group(1)
				body = body[room_match.end()+1:]
				try:
					self.room = Room.objects.get(name__iexact=room, users__user__id__exact=self.user.id)
				except Room.DoesNotExist:
					raise FieldError('unknown message room: %s' % (room))
				if profile.room != self.room:
					profile.room = self.room
					profile.save()
			else:
				if profile.room:
					self.room = profile.room
			self.body = body

		if self.body is None:
			raise FieldError('null message body')
		if self.room is None:
			raise FieldError('no target room defined and no default room found')
		self.save()

	def send(self, phone_number, message):
		message = '%s@%s: %s' % (self.user.name, self.room.name, message)
		message = message[:140]
		self.raw_send(phone_number, message)

class SMSTools(MessageSkeleton):
	class Meta:
		app_label = 'api'

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
		tempfile.tempdir = settings.SMSTOOLS['outbound_dir']
		(f, path) = tempfile.mkstemp('suffix', 'prefix', None, True)
		f.write('To: %s\n' % (phone_number))
		f.write('\n')
		f.write('%s\n' % (message))
		f.close()