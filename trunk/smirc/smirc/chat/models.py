from django.contrib.auth.models import User
from django.db import models

class Convenience:
	@staticmethod
	def load_room(r, u):
		"""A convenience method to load a given chat room.

		Raises Room.DoesNotExist if the requested room cannot be found.
		"""
		if r is None:
			raise Room.DoesNotExist
		if isinstance(r, Room):
			return r
		assert type(r) == 'str'
		try:
			u = Convenience.load_user(u)
		except User.DoesNotExist:
			raise Room.DoesNotExist
		else:
			return Room.objects.get(name__iexact=r, users__user__id__exact=u.id)

	@staticmethod
	def load_user(u):
		"""A convenience method to load a given user.

		Raises User.DoesNotExist if the user cannot be found.
		"""
		if u is None:
			raise User.DoesNotExist
		if isinstance(u, User):
			return u
		if isinstance(u, UserProfile):
			return u.user
		assert type(u) == 'str'
		if re.match('^[0-9]+$', u):
			try:
				profile = UserProfile.objects.get(phone_number=u)
			except UserProfile.DoesNotExist:
				raise User.DoesNotExist
			else:
				return profile.user
		else:
			return  User.objects.get(name=u)

class Room(models.Model):
	class Meta:
		unique_together = (('owner','name'))

	name = models.CharField(max_length=16, db_index=True)
	owner = models.ForeignKey(User)
	users = models.ManyToManyField(User, related_name='rooms', through='Membership')

	def __unicode__(self):
		return self.name

class Membership(models.Model):
	class Meta:
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
	last_active_room = models.ForeignKey(Room)
	phone_number = models.BigIntegerField(primary_key=True)
	user = models.ForeignKey(User, unique=True)

	def __unicode__(self):
		return str(phone_number)
