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
			# self.user = FIND THIS USER IN DJANGO

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
	user = models.ForeignKey(User, unique=True)

	def __unicode__(self):
		return str(phone_number)