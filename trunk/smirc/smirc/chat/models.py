from django.contrib.auth.models import User
from django.db import models

class Conversation(models.Model):
	class Meta:
		unique_together = (('owner','name'))

	name = models.CharField(max_length=16, db_index=True)
	owner = models.ForeignKey(User)
	topic = models.CharField(max_length=64)
	users = models.ManyToManyField(User, related_name='conversations', through='Membership')

	def __unicode__(self):
		return self.name

	@staticmethod
	def load_conversation(c, u):
		"""A convenience method to load a given conversation.

		Raises Conversation.DoesNotExist if the requested conversation cannot be found.
		"""
		if c is None:
			raise Conversation.DoesNotExist
		if isinstance(c, Conversation):
			return c
		assert type(c) == 'str'
		try:
			u = UserProfile.load_user(u)
		except User.DoesNotExist:
			raise Conversation.DoesNotExist
		else:
			return Conversation.objects.get(name__iexact=r, users__user__id__exact=u.id)

class Invitation(models.Model):
	class Meta:
		unique_together = (('user','conversation'))

	invited_by = models.ForeignKey(User)
	user = models.ForeignKey(User)
	conversation = models.ForeignKey(Conversation)

class Membership(models.Model):
	class Meta:
		unique_together = (('user','conversation'))

	user = models.ForeignKey(User)
	conversation = models.ForeignKey(Conversation)
	voice = models.BooleanField()

	def __unicode__(self):
		return '%s:%s' % (conversation.name, user.username)

# Add a user profile to the Django User model so that we can
# add on our own fields/user data as necessary.
# Technique taken from:
#    http://www.b-list.org/weblog/2006/jun/06/django-tips-extending-user-model/
class UserProfile(models.Model):
	last_active_conversation = models.ForeignKey(Conversation)
	phone_number = models.BigIntegerField(primary_key=True)
	user = models.ForeignKey(User, unique=True)

	def __unicode__(self):
		return str(phone_number)

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
