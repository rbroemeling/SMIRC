from django.contrib.auth.models import User
from django.db import models

class Conversation(models.Model):
	name = models.CharField(max_length=16, db_index=True)
	topic = models.CharField(max_length=64)
	users = models.ManyToManyField(User, related_name='conversations', through='Membership')

	def __unicode__(self):
		return self.name

class Invitation(models.Model):
	class Meta:
		unique_together = (('invitee','conversation'))

	conversation = models.ForeignKey(Conversation)
	inviter = models.ForeignKey(User)
	invitee = models.ForeignKey(User)

class Membership(models.Model):
	class Meta:
		unique_together = (('user','conversation'))

	conversation = models.ForeignKey(Conversation)
	last_active = models.DateTimeField()
	mode_operator = models.BooleanField()
	mode_voice = models.BooleanField()
	user = models.ForeignKey(User)

	def __unicode__(self):
		return '%s:%s' % (conversation.name, user.username)

	@staticmethod
	def load_membership(u, c):
		"""A convenience method to load a given membership, given some
		identifying information about the conversation and a participant user.

		Raises Membership.DoesNotExist if the requested membership cannot be found.
		"""
		if u is None or c is None:
			raise Membership.DoesNotExist
		if isinstance(c, Membership):
			return c
		try:
			u = UserProfile.load_user(u)
		except User.DoesNotExist:
			raise Membership.DoesNotExist
		if type(c) == 'str':
			return Membership.objects.get(conversation__name__iexact=c, user__id__exact=u.id)
		elif type(c) == 'instance' and isinstance(c, Conversation):
			return Membership.objects.get(conversation__id__exact=c.id, user__id__exact=u.id)

# Add a user profile to the Django User model so that we can
# add on our own fields/user data as necessary.
# Technique taken from:
#    http://www.b-list.org/weblog/2006/jun/06/django-tips-extending-user-model/
class UserProfile(models.Model):
	phone_number = models.BigIntegerField(primary_key=True)
	user = models.ForeignKey(User, unique=True)

	def __unicode__(self):
		return str(phone_number)

	@staticmethod
	def load_user(u):
		"""A convenience method to load a given user, given some
		identifying information about them.

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
			return User.objects.get(name=u)
