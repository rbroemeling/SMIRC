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
	ARGUMENTS_REGEX = None
	COMMAND_CHARACTER = '*'
	arguments = None
	command = None

	def __init__(self, command, arguments):
		self.command = command
		if self.ARGUMENTS_REGEX is None:
			raise SmircCommandException('command %s has not yet been implemented' % (self.command))
		match = re.match(self.ARGUMENTS_REGEX, arguments)
		if match:
			self.arguments = match.groupdict()
		else:
			usage = ''
			if self.execute.__doc__:
				for line in self.execute.__doc__.splitlines():
					line = line.trim()
					if line[0:1] == SmircCommand.COMMAND_CHARACTER:
						usage = line
			assert usage != ''
			raise SmircCommandException('invalid arguments given, try %s' % (usage))
		if 'user' in self.arguments:
			try:
				u = UserProfile.load_user(self.arguments['user'])
			except User.DoesNotExist:
				raise SmircCommandException('user %s not found' % (self.arguments['user']))
			else:
				self.arguments['user'] = u

	def execute(self, executor):
		raise SmircCommandException('command %s has not yet been implemented' % (self.command))

	@staticmethod
	def handle(s):
		if len(s) == 0 or s[0:1] != COMMAND_CHARACTER:
			return False
		match = re.match('^([A-Za-z]+)\s*(.*)', s[1:])
		if match:
			klass_name = match.group(1)
			klass_name = klass_name[0:1].upper() + klass_name[1:].lower()
			arguments = match.group(2)
			try:
				klass = getattr(smirc.command.models, "SmircCommand%s" % (klass_name))
			except AttributeError, e:
				raise SmircCommandException('unknown command "%s", try %shelp' % (klass_name.lower(), SmircCommand.COMMAND_CHARACTER))
			else:
				return klass(klass_name.lower(), arguments)
		else:
			raise SmircCommandException('bad command "%s", try %shelp' % (s, SmircCommand.COMMAND_CHARACTER))

class SmircCommandCreate(SmircCommand):
	ARGUMENTS_REGEX = '(?P<conversation_identifier>\S{1,16})\s*$' # TODO: pull the regex for a conversation name from the Conversation object

	def execute(self, executor):
		"""Create a new conversation.
		
		*CREATE [conversation name]
		"""
		try:
			Membership.load_membership(executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			c = Conversation()
			c.name = self.arguments['conversation_identifier']
			c.save()
			m = Membership()
			m.conversation = c
			m.last_active = datetime.datetime()
			m.mode_operator = True
			m.user = executor
			m.save()
			return 'you have created a conversation named %s' % (c.name)
		else:
			raise SmircCommandException('you are already taking part in a conversation named %s' % (self.arguments['conversation_identifier']))

class SmircCommandInvite(SmircCommand):
	ARGUMENTS_REGEX = '(?P<user>\S{1,16})\s+to\s+(?P<conversation_identifier>\S{1,16})\s*$' # TODO: pull the regex for a user name and a conversation name from the UserProfile/Conversation objects

	def execute(self, executor):
		"""Invite a user to a conversation that you are an operator of.

		*INVITE [user to be invited] to [conversation name]
		"""
		try:
			membership = Membership.load_membership(executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			raise SmircCommandException('you are not in a conversation named %s' % (self.arguments['conversation_identifier']))
		if not membership.mode_operator:
			raise SmircCommandException('you are not an operator of the conversation named %s' % (membership.conversation.name))
				
		try:
			Membership.load_membership(self.arguments['user'], membership.conversation)
		except Membership.DoesNotExist:
			pass
		else:
			raise SmircCommandException('user %s is already a member of the conversation named %s' % (self.arguments['user'].username, membership.conversation.name))

		try:
			Invitation.objects.get(invitee=self.arguments['user'], conversation=membership.conversation)
		except Invitation.DoesNotExist:
			pass
		else:
			raise SmircCommandException('user %s has already been invited to the conversation named %s' % (self.arguments['user'].username, membership.conversation.name))

		i = Invitation()
		i.invitee = self.arguments['user']
		i.inviter = executor
		i.conversation = membership.conversation
		i.save()
		# TODO: send message to user about their invitation to conversation

class SmircCommandJoin(SmircCommand):
	ARGUMENTS_REGEX = '(?P<user>\S{1,16})\s+in\s+(?P<conversation_identifier>\S{1,16})\s*$' # TODO: pull the regex for the user name and the conversation name from UserProfile/Conversation objects

	def execute(self, executor):
		"""Join a chat conversation that you've been invited to.

		*JOIN [user who invited you] in [conversation you are invited to]
		"""
		try:
			invitation = Invitation.objects.get(invitee=executor, inviter=self.arguments['user'], conversation__name__iexact=self.arguments['conversation_identifier'])
		except Invitation.DoesNotExist:
			raise SmircCommandException('you do not have an outstanding invitation from %s to the conversation %s' % (self.arguments['user'].username, self.arguments['conversation_identifier']))
		
		try:
			Membership.load_membership(executor, invitation.conversation)
		except Membership.DoesNotExist:
			pass
		else:
			raise SmircCommandException('you are already in the conversation %s with the user %s', invitation.conversation.name, self.arguments['user'].username)

		try:
			Membership.load_membership(executor, invitation.conversation.name)
		except Membership.DoesNotExist:
			pass
		else:
			raise SmircCommandException('you are already in a conversation named %s')
		
		m = Membership()
		m.conversation = invitation.conversation
		m.user = executor
		m.save()
		invitation.delete()
		# TODO: send message to user about joining ther conversation

class SmircCommandKick(SmircCommand):
	ARGUMENTS_REGEX = '(?P<user>\S{1,16})\s+out of\s+(?P<conversation_identifier>\S{1,16})\s*$' # TODO: pull the regex for the user name and the conversation name from UserProfile/Conversation objects

	def execute(self, executor):
		"""Kick a user out of a conversation that you control.

		*KICK [user to kick] out of [conversation you own]
		"""
		try:
			executor_membership = Membership.load_membership(executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			raise SmircCommandException('you are not in a conversation named %s' % (self.arguments['conversation_identifier']))
		if not executor_membership.mode_operator:
			raise SmircCommandException('you are not an operator of the conversation named %s' % (executor_membership.conversation.name))

		try:
			invitations = Invitation.objects.get(invitee=self.arguments['user'], conversation=executor_membership.conversation)
		except Invitation.DoesNotExist:
			pass
		else:
			invitations.delete()

		try:
			membership = Membership.load_membership(self.arguments['user'], executor_membership.conversation)
		except Membership.DoesNotExist:
			pass
		else:
			membership.delete()
		
		# TODO: send a success message to the executor about the user being removed from the conversation.

class SmircCommandNick(SmircCommand):
	ARGUMENTS_REGEX = '(?P<new_username>\S{1,16})\s*$' # TODO: pull the regex for a user name from the UserProfile object

	def execute(self, executor):
		"""Change your user nickname.

		*NICK [new user nickname]
		"""
		try:
			UserProfile.load_user(self.arguments['new_username'])
		except User.DoesNotExist:
			executor.username = self.arguments['new_username']
			executor.save()
		else:
			raise SmircCommandException('the nickname %s is already in use' % (self.arguments['new_username']))

class SmircCommandPart(SmircCommand):
	def execute(self, executor):
		"""Leave a chat conversation that you're currently in.

		*PART [conversation you are in]
		"""
		pass
