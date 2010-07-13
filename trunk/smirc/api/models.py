import re
from django.db import models
from django.contrib.auth.models import User

class Room(models.Model):
	name = models.CharField(max_length=16)
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

	def parse(data):
		self.body = None
		self.headers = {}
		for line in data.splitlines():
			if not self.body is None:
				self.body += line
			else:
				if line:
					(key, value) = line.split(':', 1)
					key = key.strip().lower()
					value = value.strip()
					self.headers[key] = value
				else:
					self.body = ''
		if self.headers['from']:
			self.user = UserProfile.objects.get(phone_number=self.headers['from']).user
		if self.body:
			room_match = re.match('\s*@(\S+)\s*', self.body)
			if room_match:
				self.room = Room.objects.get(name=room_match.group(1))
				self.user.get_profile().room = self.room
				self.body = self.body[room_match.end()+1:]
			else:
				self.room = self.user.get_profile().room

	def render():
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
	phone_number = models.BigIntegerField(unique=True)
	room = models.ForeignKey(Room)
	user = models.ForeignKey(User, unique=True)

	def __unicode__(self):
		return str(phone_number)