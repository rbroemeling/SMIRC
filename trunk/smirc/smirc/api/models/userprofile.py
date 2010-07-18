from django.db import models
from django.contrib.auth.models import User
from smirc.api.models.room import Room

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
