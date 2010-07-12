from django.db import models
from django.contrib.auth.models import User

class Room(models.Model):
	name = models.CharField(max_length=16)
	owner = models.ForeignKey(User)
	users = models.ManyToManyField(User, related_name="rooms", through="Membership")

	def __unicode__(self):
		return self.name

class Membership(models.Model):
	user = models.ForeignKey(User)
	room = models.ForeignKey(Room)
	voice = models.BooleanField()

	def __unicode__(self):
		return "%s:%s" % (room.name, user.name)

# Add a user profile to the Django User model so that we can
# add on our own fields/user data as necessary.
# Technique taken from:
#    http://www.b-list.org/weblog/2006/jun/06/django-tips-extending-user-model/
class UserProfile(models.Model):
	phone_number = models.BigIntegerField(unique=True)
	user = models.ForeignKey(User, unique=True)

	def __unicode__(self):
		return str(phone_number)
