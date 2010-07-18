# As a requirement of being used by Django, models defined inside a
# models/ sub-directory need to be tagged with:
# 	class Meta:
#		app_label = 'foo'
# For more information, see:
# http://blog.amber.org/2009/01/19/moving-django-models-into-their-own-module/

from smirc.api.models.message import SMSToolsMessage
from smirc.api.models.userprofile import UserProfile

__all__ = ['SMSToolsMessage', 'UserProfile']



from django.db import models
from django.contrib.auth.models import User

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