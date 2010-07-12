from django.db import models
from django.contrib.auth.models import User

class Room(models.Model):
	name = models.CharField(max_length=16)

	def __unicode__(self):
		return self.name

# Add a user profile to the Django User model so that we can
# add on our own fields/user data as necessary.
# Technique taken from:
#    http://www.b-list.org/weblog/2006/jun/06/django-tips-extending-user-model/
class UserProfile(models.Model):
	phone_number = models.BigIntegerField(unique=True)
	rooms = models.ManyToManyField(Room, related_name="users")
	user = models.ForeignKey(User, unique=True)

	def __unicode__(self):
		return str(phone_number)
