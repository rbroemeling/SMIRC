from django.contrib.auth.models import User
from smirc.chat.models import Conversation
from smirc.chat.models import Invitation
from smirc.chat.models import Membership
from smirc.chat.models import SmircException
from smirc.chat.models import SmircRestrictedNameException
from smirc.chat.models import UserProfile
import inspect
import sys

class SmircCommandException(SmircException):
	pass

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
			raise SmircCommandException('invalid arguments given, try %s' % (SmircCommand.usage(self)))
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
	def fetch_command_class(klass_name):
		try:
			if not re.match('^[A-Za-z]+$'):
				raise AttributeError
			klass_name = klass_name[0:1].upper() + klass_name[1:].lower()
			klass = getattr(smirc.command.models, "SmircCommand%s" % (klass_name))
		except AttributeError as e:
			raise SmircCommandException('unknown command "%s", try %shelp' % (klass_name.lower(), SmircCommand.COMMAND_CHARACTER))
		else:
			return klass

	@staticmethod
	def handle(s):
		if len(s) == 0 or s[0:1] != COMMAND_CHARACTER:
			return False
		match = re.match('^([A-Za-z]+)\s*(.*)', s[1:])
		if match:	
			klass = SmircCommand.fetch_command_class(match.group(1))
			return klass(match.group(1).lower(), match.group(2))
		else:
			raise SmircCommandException('bad command "%s", try %shelp' % (s, SmircCommand.COMMAND_CHARACTER))

	@staticmethod
	def usage(klass):
		if klass.execute.__doc__:
			for line in klass.execute.__doc__.splitlines():
				line = line.trim()
				if line[0:1] == SmircCommand.COMMAND_CHARACTER:
					return line
		# TODO: log an error that there is no usage for this command here.
		return ''

class SmircCommandCreate(SmircCommand):
	ARGUMENTS_REGEX = '(?P<conversation_identifier>\S+)\s*$'

	def execute(self, executor):
		"""Create a new conversation.
		
		*CREATE [conversation name]
		"""
		try:
			Conversation.validate_name(self.arguments['conversation_identifier'])
		except SmircRestrictedNameException as e:
			raise SmircCommandException(str(e))

		try:
			Membership.load_membership(executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			c = Conversation()
			c.name = self.arguments['conversation_identifier']
			c.save()
			m = Membership()
			m.conversation = c
			m.mode_operator = True
			m.user = executor
			m.save()
			return 'you have created a conversation named %s' % (c.name)
		else:
			raise SmircCommandException('you are already taking part in a conversation named %s' % (self.arguments['conversation_identifier']))

class SmircCommandHelp(SmircCommand):
	ARGUMENTS_REGEX = '(?P<command>\S+)?\s*$'
	
	def execute(self, executor):
		"""Get help about what commands are available or what the syntax
		for executing a command is.
		
		*HELP or *HELP [command]
		"""
		if self.arguments['command']:
			klass = SmircCommand.fetch_command_class(self.arguments['command'])
			return SmircCommand.usage(klass)
		else:
			commands = []
			for name, obj in inspect.getmembers(sys.modules[__name__]):
				if inspect.isclass(obj) and issubclass(obj, SmircCommand):
					name = name.replace('SmircCommand', '')
					commands.append(name.upper())
			return string.join(commands, ', ')
	
class SmircCommandInvite(SmircCommand):
	ARGUMENTS_REGEX = '(?P<user>\S+)\s+to\s+(?P<conversation_identifier>\S+)\s*$'

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
		# TODO: send message to self.arguments['user'], alerting them that they have been invited to i.conversation
		return 'user %s has been invited to the conversation named %s' % (self.arguments['user'].username, membership.conversation.name)

class SmircCommandJoin(SmircCommand):
	ARGUMENTS_REGEX = '(?P<user>\S+)\s+in\s+(?P<conversation_identifier>\S+)\s*$'

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
		return 'you have joined the conversation named %s' % (m.conversation.name)

class SmircCommandKick(SmircCommand):
	ARGUMENTS_REGEX = '(?P<user>\S+)\s+out\s+of\s+(?P<conversation_identifier>\S+)\s*$'

	def execute(self, executor):
		"""Kick a user out of a conversation that you control.

		*KICK [user to kick] out of [conversation you are an operator of]
		"""
		try:
			executor_membership = Membership.load_membership(executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			raise SmircCommandException('you are not in a conversation named %s' % (self.arguments['conversation_identifier']))
		if not executor_membership.mode_operator:
			raise SmircCommandException('you are not an operator of the conversation named %s' % (executor_membership.conversation.name))

		result = None
		try:
			invitations = Invitation.objects.get(invitee=self.arguments['user'], conversation=executor_membership.conversation)
		except Invitation.DoesNotExist:
			pass
		else:
			result = 'user %s has had all invitations to join the conversation %s revoked' % (self.arguments['user'].username, executor_membership.conversation.name)
			invitations.delete()

		try:
			membership = Membership.load_membership(self.arguments['user'], executor_membership.conversation)
		except Membership.DoesNotExist:
			pass
		else:
			result = 'user %s has been removed from the conversation %s' % (self.arguments['user'].username, executor_membership.conversation.name)
			membership.delete()
		
		if result is not None:
			return result
		else:
			return 'user %s was not a member of the conversation %s' % (self.arguments['user'].username, executor_membership.conversation.name)

class SmircCommandNick(SmircCommand):
	ARGUMENTS_REGEX = '(?P<new_username>\S+)\s*$'

	def execute(self, executor):
		"""Change your user nickname.

		*NICK [new user nickname]
		"""
		raise SmircCommandException('the NICK command is currently disabled while possible issues with it are examined')

		try:
			UserProfile.validate_name(self.arguments['new_username'])
		except SmircRestrictedNameException as e:
			raise SmircCommandException(str(e))

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
		try:
			membership = Membership.load_membership(executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			raise SmircCommandException('you are not in a conversation named %s' % (self.arguments['conversation_identifier']))
		membership.delete()
