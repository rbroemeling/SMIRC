from django.db import models
from django.contrib.auth.models import User

# As a requirement of being used by Django, models defined inside a
# models/ sub-directory need to be tagged with:
# 	class Meta:
#		app_label = 'foo'
# For more information, see:
# http://blog.amber.org/2009/01/19/moving-django-models-into-their-own-module/

class Room(models.Model):
	class Meta:
		app_label = 'api'
		unique_together = (('owner','name'))

	name = models.CharField(max_length=16, db_index=True)
	owner = models.ForeignKey(User)
	users = models.ManyToManyField(User, related_name='rooms', through='Membership')

	def __unicode__(self):
		return self.name

class Membership(models.Model):
	class Meta:
		app_label = 'api'
		unique_together = (('user','room'))

	user = models.ForeignKey(User)
	room = models.ForeignKey(Room)
	voice = models.BooleanField()

	def __unicode__(self):
		return '%s:%s' % (room.name, user.name)

# Add a user profile to the Django User model so that we can
# add on our own fields/user data as necessary.
# Technique taken from:
#    http://www.b-list.org/weblog/2006/jun/06/django-tips-extending-user-model/
class UserProfile(models.Model):
	class Meta:
		app_label = 'api'
	
	last_active_room = models.ForeignKey(Room)
	phone_number = models.BigIntegerField(primary_key=True)
	user = models.ForeignKey(User, unique=True)

	def __unicode__(self):
		return str(phone_number)
