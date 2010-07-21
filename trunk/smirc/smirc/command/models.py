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
	ARGUMENTS_REGEX = '(?P<user>\S{1,16})\s+(?P<conversation_identifier>\S{1,16})\s*$' # TODO: pull the regex for a user name and a conversation name from the UserProfile/Conversation objects

	def execute(self, executor):
		"""Invite a user to a conversation that you are an operator of.

		*INVITE [user to be invited] [conversation name]
		"""
		try:
			membership = Membership.load_membership(executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			raise SmircCommandException('you are not in a conversation named %s' % (self.arguments['conversation_identifier']))
		if not membership.mode_operator:
			raise SmircCommandException('you are not an operator of the conversation named %s' % (membership.conversation.name))
				
		try:
			Membership.load_membership(self.arguments['user'], membership.conversation.name)
		except Membership.DoesNotExist:
			pass
		else:
			raise SmircCommandException('user %s is already in a conversation named %s' % (self.arguments['user'].username, membership.conversation.name))

		try:
			Invitation.objects.get(conversation=membership.conversation, invitee=self.arguments['user'])
		except Invitation.DoesNotExist:
			pass
		else:
			raise SmircCommandException('user %s has already been invited to conversation %s' % (self.arguments['user'].username, membership.conversation.name))

		i = Invitation()
		i.invitee = self.arguments['user']
		i.inviter = executor
		i.conversation = membership.conversation
		i.save()
		# TODO: send message to user about their invitation to conversation

class SmircCommandJoin(SmircCommand):
	def execute(self, executor):
		"""Join a chat conversation that you've been invited to.

		*JOIN [conversation you are invited to]
		"""
		pass

class SmircCommandKick(SmircCommand):
	def execute(self, executor):
		"""Kick a user out of a conversation that you control.

		*KICK [user to kick] [conversation you own]
		"""
		# TODO: intertwine this with cmd_invite, as they do basically the same thing.
		# Maybe outsource it to a private function?
		pass

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
