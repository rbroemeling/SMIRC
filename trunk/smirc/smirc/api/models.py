import logging
import re
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import FieldError

class Room(models.Model):
	name = models.CharField(max_length=16, db_index=True)
	owner = models.ForeignKey(User)
	users = models.ManyToManyField(User, related_name='rooms', through='Membership')

	def __unicode__(self):
		return self.name

class Membership(models.Model):
	user = models.ForeignKey(User)
	room = models.ForeignKey(Room)
	voice = models.BooleanField()

	def __unicode__(self):
		return '%s:%s' % (room.name, user.name)

class Message(models.Model):
	user = models.ForeignKey(User)
	room = models.ForeignKey(Room)
	body = None
	headers = {}

	def parse(self, data):
		self.body = None
		self.headers = {}
		for line in data.splitlines():
			if not self.body is None:
				self.body += line
			else:
				if line:
					try:
						(key, value) = line.split(':', 1)		
						key = key.strip().lower()
						value = value.strip()
						self.headers[key] = value
					except ValueError, e:
						logging.warn('skipping invalid header: "%s"' % (line))
				else:
					self.body = ''

		profile = None
		if self.headers.has_key('from'):
			try:
				profile = UserProfile.objects.get(phone_number=self.headers['from'])
			except UserProfile.DoesNotExist:
				raise FieldError('unknown message sender: %s' % (self.headers['from']))
		else:
			raise FieldError('null message sender')
		self.user = profile.user

		if self.body:
			room_match = re.match('\s*@(\S+)\s*', self.body)
			if room_match:
				room_name = room_match.group(1)
				self.body = self.body[room_match.end()+1:]
				try:
					self.room = Room.objects.get(name=room_name)
				except Room.DoesNotExist:
					raise FieldError('unknown message room: %s' % (room_name))
				if profile.room != self.room:
					profile.room = self.room
					profile.save()
			else:
				if profile.room:
					self.room = profile.room
				else:
					raise FieldError('no target room defined and no default room found')
		else:
			raise FieldError('null message body')
		self.save()

	def render(self):
		data = ''
		for key, value in self.headers:
			data += '%s: %s\n' % (key, value)
		data += '\n'
		data += ('%s@%s: %s' % (self.user.name, self.room.name, self.body))[:140]
		return data

# Add a user profile to the Django User model so that we can
# add on our own fields/user data as necessary.
# Technique taken from:
#    http://www.b-list.org/weblog/2006/jun/06/django-tips-extending-user-model/
class UserProfile(models.Model):
	last_active_room = models.ForeignKey(Room)
	phone_number = models.BigIntegerField(primary_key=True)
	user = models.ForeignKey(User, unique=True)

	def __unicode__(self):
		return str(phone_number)
