from django.contrib.auth.models import User
from smirc.chat.models import Conversation
from smirc.chat.models import Invitation
from smirc.chat.models import Membership
from smirc.chat.models import UserProfile

class SmircCommandException(Exception):
	def __init__(self, value):
		self.value = value

	def __str__(self):
		return repr(self.value)

class SmircCommand:
	executing_user = None

	def cmd_create(self, conversation_identifier):
		"""Create a new conversation.

		*CREATE [conversation name]
		"""
		try:
			Membership.load_membership(self.executing_user, conversation_identifier)
		except Membership.DoesNotExist:
			c = Conversation()
			c.name = conversation_identifier
			c.save()
			m = Membership()
			m.conversation = c
			m.last_active = datetime.datetime()
			m.mode_operator = True
			m.user = self.executing_user
			m.save()
			return 'you have created a conversation named %s' % (c.name)
		else:
			raise SmircCommandException('you are already taking part in a conversation named %s' % (conversation_identifier))

	def cmd_invite(self, user_identifier, conversation_identifier):
		"""Invite a user to a conversation that you are an operator of.

		*INVITE [user to be invited] [conversation name]
		"""
		try:
			user = UserProfile.load_user(user_identifier)
		except User.DoesNotExist:
			raise SmircCommandException('user %s not found' % (user_identifier))
		else:
			try:
				membership = Membership.load_membership(self.executing_user, conversation_identifier)
			except Membership.DoesNotExist:
				raise SmircCommandException('you are not involved in a conversation named %s' % (conversation_identifier))
			else:
				if not membership.mode_operator:
					raise SmircCommandException('you are not an operator of the conversation named %s' % (conversation_identifier))
				else:
					try:
						Invitation.objects.get(conversation=membership.conversation, invitee=user)
					except Invitation.DoesNotExist:
						pass
					else:
						raise SmircCommandException('user %s has already been invited to conversation %s' % (user, conversation))
					try:
						Membership.load_membership(user, conversation_identifier)
					except Membership.DoesNotExist:
						pass
					else:
						raise SmircCommandException('user %s is already in a conversation named %s' % (conversation_identifier))			
					i = Invitation()
					i.invitee = user
					i.inviter = self.executing_user
					i.conversation = membership.conversation
					i.save()
					# TODO: send message to user about their invitation to conversation

	def cmd_join(self, conversation):
		"""Join a chat conversation that you've been invited to.

		*JOIN [conversation you are invited to]
		"""
		pass

	def cmd_kick(self, user, conversation):
		"""Kick a user out of a conversation that you control.

		*KICK [user to kick] [conversation you own]
		"""
		# TODO: intertwine this with cmd_invite, as they do basically the same thing.
		# Maybe outsource it to a private function?
		pass

	def cmd_nick(self, new_username):
		"""Change your user nickname.

		*NICK [new user nickname]
		"""
		try:
			UserProfile.load_user(new_username)
		except User.DoesNotExist:
			# TODO: check new_username to see if it follows naming requirements
			self.executing_user.username = new_username
			self.executing_user.save()
		else:
			raise SmircCommandException('user nickname %s is already in use' % (new_username))

	def cmd_part(self, conversation):
		"""Leave a chat conversation that you're currently in.

		*PART [conversation you are in]
		"""
		pass

	def execute(message):
		self.executing_user = message.user
		try:
			command = getattr(self, 'cmd_%s' % (message.command.lower()))
		except AttributeError, e:
			raise SmircCommandException('unknown command "%s"' % (message.command))
		else:
			args = message.body.split()
			try:
				return command(*args)
			except TypeError, e:
				usage = ''
				for line in command.__doc__.splitlines():
					line = line.trim()
					if line[0:1] == '*':
						usage = line
				assert usage != ''
				raise SmircCommandException('invalid arguments given, use "%s"' % (usage))
