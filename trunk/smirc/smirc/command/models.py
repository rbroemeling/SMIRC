import inspect
import logging
import re
import string
import sys
from django.contrib.auth.models import User
from smirc.chat.models import SmircException

class SmircCommandException(SmircException):
	pass

class SmircCommand:
	ANONYMOUSLY_EXECUTABLE = False
	ARGUMENTS_REGEX = None
	COMMAND_CHARACTER = '/'
	arguments = None
	command = None
	executor = None

	def __init__(self, command, arguments):
		self.command = command
		if self.ARGUMENTS_REGEX is None:
			raise SmircCommandException('command "%s%s" has not yet been implemented' % (SmircCommand.COMMAND_CHARACTER, self.command))
		match = re.match(self.ARGUMENTS_REGEX, arguments)
		if match:
			self.arguments = match.groupdict()
		else:
			raise SmircCommandException('invalid arguments given, try "%s"' % (SmircCommand.command_usage(self)))
		if 'user' in self.arguments:
			try:
				u = UserProfile.load_user(self.arguments['user'])
			except User.DoesNotExist:
				raise SmircCommandException('user %s not found' % (self.arguments['user']))
			else:
				self.arguments['user'] = u

	@staticmethod
	def available_commands():
		for name, obj in inspect.getmembers(sys.modules[__name__]):
			if inspect.isclass(obj) and obj != SmircCommand and issubclass(obj, SmircCommand):
				yield (name, obj)

	@staticmethod
	def command_description(klass):
		description = ''
		if klass.execute.__doc__:
			for line in klass.execute.__doc__.splitlines():
				line = line.strip()
				if line == '':
					break
				if len(description) > 0:
					description = description + ' '
				description = description + line
		if len(description) == 0:
			logging.error('no description defined for command class %s' % (repr(klass)))
		return description

	@staticmethod
	def command_examples(klass):
		examples = []
		current_example = None
		current_description = None
		if klass.execute.__doc__:
			for line in klass.execute.__doc__.splitlines():
				line = line.strip()
				if line == '':
					if current_example is not None:
						examples.append((current_example, current_description))
					current_example = None
					current_description = None
				elif current_example is not None:
					if len(current_description) > 0:
						current_description = current_description + ' '
					current_description = current_description + line
				elif line[0:8] == 'Example:':
					current_example = line.replace('Example:', '').strip()
					current_description = ''
		if current_example is not None:
			examples.append((current_example, current_description))
		return examples

	@staticmethod
	def command_usage(klass):
		if klass.execute.__doc__:
			for line in klass.execute.__doc__.splitlines():
				line = line.strip()
				if line[0:1] == SmircCommand.COMMAND_CHARACTER:
					return line
		logging.error('no usage information defined for command class %s' % (repr(klass)))
		return ''

	def execute(self):
		raise SmircCommandException('command "%s%s" has not yet been implemented' % (SmircCommand.COMMAND_CHARACTER, self.command))

	@staticmethod
	def fetch_command_class(klass_name):
		try:
			if not re.match('^[A-Za-z]+$', klass_name):
				raise AttributeError
			klass_name = klass_name[0:1].upper() + klass_name[1:].lower()
			klass = getattr(sys.modules[__name__], 'SmircCommand%s' % (klass_name))
		except AttributeError as e:
			raise SmircCommandException('unknown command "%s%s", try "%shelp".' % (SmircCommand.COMMAND_CHARACTER, klass_name.lower(), SmircCommand.COMMAND_CHARACTER))
		else:
			return klass

	@staticmethod
	def handle(u, s):
		if len(s) == 0 or s[0:1] != SmircCommand.COMMAND_CHARACTER:
			return False
		match = re.match('^([A-Za-z]+)\s*(.*)', s[1:])
		if match:
			klass = SmircCommand.fetch_command_class(match.group(1))
			logging.debug('mapped raw command "%s" to %s("%s", "%s")' % (s, klass, match.group(1).lower(), match.group(2)))
			cmd = klass(match.group(1).lower(), match.group(2))
			if isinstance(u, User) or cmd.ANONYMOUSLY_EXECUTABLE:
				cmd.executor = u
				return cmd
			else:
				return False
		else:
			raise SmircCommandException('bad command "%s", try "%shelp".' % (s, SmircCommand.COMMAND_CHARACTER))

class SmircCommandCreate(SmircCommand):
	ARGUMENTS_REGEX = '(?P<conversation_identifier>\S+)\s*$'

	def execute(self):
		"""Create a new SMIRC conversation.  Executor automatically joins
		the created conversation and is given operator permissions in it.
		
		/CREATE [conversation name]
		
		Example: /CREATE HelloWorld
		Creates a new SMIRC conversation called "HelloWorld" and automatically
		joins the executing user to it with full operator permissions.
		"""
		try:
			Conversation.validate_name(self.arguments['conversation_identifier'])
		except SmircRestrictedNameException as e:
			raise SmircCommandException(str(e))

		try:
			m = Membership.load_membership(self.executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			c = Conversation()
			c.name = self.arguments['conversation_identifier']
			c.save()
			m = Membership()
			m.conversation = c
			m.mode_operator = True
			m.user = self.executor
			m.save()
			return 'you have created a conversation named "%s"' % (c.name)
		else:
			raise SmircCommandException('you are already taking part in a conversation named "%s"' % (m.conversation.name))

class SmircCommandHelp(SmircCommand):
	ANONYMOUSLY_EXECUTABLE = True
	ARGUMENTS_REGEX = '(?P<command>\S+)?\s*$'
	
	def execute(self):
		"""Retrieve a list of available commands (if no argument is
		given) or retrieve the usage information of a specific command
		(if a command is given as the argument).
		
		/HELP or /HELP [command]
		"""
		if self.arguments['command']:
			klass = SmircCommand.fetch_command_class(self.arguments['command'])
			return SmircCommand.command_usage(klass)
		else:
			commands = []
			for klassname, obj in SmircCommand.available_commands():
				commands.append(klassname.replace('SmircCommand', '').upper())
			commands.sort()
			return 'Commands: %s. Usage: "%sHELP [command]"' % (string.join(commands, ', '), SmircCommand.COMMAND_CHARACTER)
	
class SmircCommandInvite(SmircCommand):
	ARGUMENTS_REGEX = '(?P<user>\S+)\s+to\s+(?P<conversation_identifier>\S+)\s*$'

	def execute(self):
		"""Invite a user to a conversation that you are a member of and
		that you have operator permissions in.

		/INVITE [user to be invited] to [conversation name]

		Example: /INVITE Foo to Bar
		Invites the user "Foo" to the conversation "Bar", assuming that
		you are in a conversation named "Bar" and that you have operator
		permissions in it.
		"""
		try:
			membership = Membership.load_membership(self.executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			raise SmircCommandException('you are not in a conversation named "%s"' % (self.arguments['conversation_identifier']))
		if not membership.mode_operator:
			raise SmircCommandException('you are not an operator of the conversation named "%s"' % (membership.conversation.name))
				
		try:
			Membership.load_membership(self.arguments['user'], membership.conversation)
		except Membership.DoesNotExist:
			pass
		else:
			raise SmircCommandException('%s is already a member of the conversation named "%s"' % (self.arguments['user'].username, membership.conversation.name))

		try:
			Invitation.objects.get(invitee=self.arguments['user'], conversation=membership.conversation)
		except Invitation.DoesNotExist:
			pass
		else:
			raise SmircCommandException('%s has already been invited to the conversation named "%s"' % (self.arguments['user'].username, membership.conversation.name))

		i = Invitation()
		i.invitee = self.arguments['user']
		i.inviter = self.executor
		i.conversation = membership.conversation
		i.save()
		
		notification = SMSToolsMessage()
		notification.body = 'you have been invited to the conversation "%s" by %s.  Respond with "%sjoin %s in %s" to accept the invitation.' % (membership.conversation.name, self.executor.username, SmircCommand.COMMAND_CHARACTER, self.executor.username, membership.conversation.name)
		notification.system = True
		notification.send(self.arguments['user'].get_profile().phone_number)

		return '%s has been invited to the conversation named "%s"' % (self.arguments['user'].username, membership.conversation.name)

class SmircCommandJoin(SmircCommand):
	ARGUMENTS_REGEX = '(?P<user>\S+)\s+in\s+(?P<conversation_identifier>\S+)\s*$'

	def execute(self):
		"""Join a chat conversation that you have been invited to.

		/JOIN [user who invited you] in [conversation you are invited to]
		
		Example: /JOIN Foo in Bar
		Take the user "Foo" up on their invitation and join them in the
		conversation "Bar".
		"""
		try:
			invitation = Invitation.objects.get(invitee=self.executor, inviter=self.arguments['user'], conversation__name__iexact=self.arguments['conversation_identifier'])
		except Invitation.DoesNotExist:
			raise SmircCommandException('you do not have an outstanding invitation from %s to the conversation "%s"' % (self.arguments['user'].username, self.arguments['conversation_identifier']))
		
		try:
			Membership.load_membership(self.executor, invitation.conversation)
		except Membership.DoesNotExist:
			pass
		else:
			raise SmircCommandException('you are already in the conversation "%s"', invitation.conversation.name)

		try:
			Membership.load_membership(self.executor, invitation.conversation.name)
		except Membership.DoesNotExist:
			pass
		else:
			raise SmircCommandException('you are already in a different conversation named "%s"')
		
		m = Membership()
		m.conversation = invitation.conversation
		m.user = self.executor
		m.save()
		invitation.delete()
		return 'you have joined the conversation named "%s"' % (m.conversation.name)

class SmircCommandKick(SmircCommand):
	ARGUMENTS_REGEX = '(?P<user>\S+)\s+out\s+of\s+(?P<conversation_identifier>\S+)\s*$'

	def execute(self):
		"""Kick a user out of a conversation that you have operator
		permissions in.  Revokes membership in the conversation and/or
		any outstanding invitations for the user to join the
		conversation.  Does not prevent further invitations from being
		issued or the user from joining the conversation in the future.

		/KICK [user to kick] out of [conversation you are an operator of]
		
		Example: /KICK Foo out of Bar
		Removes the user "Foo" from the conversation "Bar", as well as
		revoking any outstanding invitations for the user "Foo" to join
		the conversation "Bar".		
		"""
		try:
			executor_membership = Membership.load_membership(self.executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			raise SmircCommandException('you are not in a conversation named "%s"' % (self.arguments['conversation_identifier']))
		if not executor_membership.mode_operator:
			raise SmircCommandException('you are not an operator of the conversation named "%s"' % (executor_membership.conversation.name))

		result = None
		try:
			invitations = Invitation.objects.get(invitee=self.arguments['user'], conversation=executor_membership.conversation)
		except Invitation.DoesNotExist:
			pass
		else:
			result = '%s has had all invitations to join the conversation "%s" revoked' % (self.arguments['user'].username, executor_membership.conversation.name)
			invitations.delete()

		try:
			membership = Membership.load_membership(self.arguments['user'], executor_membership.conversation)
		except Membership.DoesNotExist:
			pass
		else:
			result = '%s has been removed from the conversation "%s"' % (self.arguments['user'].username, executor_membership.conversation.name)
			membership.delete()
		
		if result is not None:
			return result
		else:
			return '%s was not a member of the conversation "%s"' % (self.arguments['user'].username, executor_membership.conversation.name)

class SmircCommandNick(SmircCommand):
	ANONYMOUSLY_EXECUTABLE = True
	ARGUMENTS_REGEX = '(?P<new_username>\S+)\s*$'

	def execute(self):
		"""Change your user nickname.

		/NICK [new user nickname]
		
		Example: /NICK Foo
		Changes your user nickname to "Foo".
		"""
		try:
			UserProfile.validate_name(self.arguments['new_username'])
		except SmircRestrictedNameException as e:
			raise SmircCommandException(str(e))

		try:
			existing_user = UserProfile.load_user(self.arguments['new_username'])
		except User.DoesNotExist:
			pass
		else:
			if isinstance(self.executor, User) and existing_user.id == self.executor.id:
				# There is an existing user with this name, but it is US, 
				# so let the request continue.  This allows case adjustments to usernames.
				pass
			else:
				# There is an existing user with this name and it isn't us,
				# so report the error to the user.
				raise SmircCommandException('sorry, the nickname %s is already in use' % (self.arguments['new_username']))
		if isinstance(self.executor, User):
			self.executor.username = self.arguments['new_username']
			self.executor.save()
			return 'nickname has been changed to %s' % (self.executor.username)
		else:
			u = User.objects.create_user(self.arguments['new_username'], '')
			p = UserProfile()
			p.phone_number = self.executor	
			p.user = u
			p.save()
			self.executor = u
			return 'welcome to SMIRC, %s' % (self.executor.username)

class SmircCommandPart(SmircCommand):
	ARGUMENTS_REGEX = '(?P<conversation_identifier>\S+)\s*$'

	def execute(self):
		"""Leave a conversation that you are currently a member of.

		/PART [conversation you are in]
		
		Example: /PART Foo
		Assuming that you are currently a member of a conversation
		named "Foo", revokes your membership in that conversation.
		"""
		try:
			membership = Membership.load_membership(self.executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			raise SmircCommandException('you are not in a conversation named "%s"' % (self.arguments['conversation_identifier']))
		membership.delete()
		return 'you have left the conversation "%s"' % (membership.conversation.name)

class SmircCommandWho(SmircCommand):
	ARGUMENTS_REGEX = '(?P<conversation_identifier>\S+)\s*$'
	
	def execute(self):
		"""List all of the people in a conversation that you are
		currently a member of.
		
		/WHO [conversation you are in]
		
		Example: /WHO Foo
		Fetches a list of people who are currently in the conversation
		named "Foo" (that you are also a member of).
		"""
		try:
			membership = Membership.load_membership(self.executor, self.arguments['conversation_identifier'])
		except Membership.DoesNotExist:
			raise SmircCommandException('you are not in a conversation named "%s"' % (self.arguments['conversation_identifier']))

		members = []
		for membership in Membership.objects.filter(conversation=membership.conversation):
			member = str(membership)
			if member.rfind('@') > 0:
				member = member[:member.rfind('@')]
			members.append(member)
		members = string.join(members, ', ')
		if len(members) > 130:
			members = members[:125]
			members = members[:members.rfind(',')]
			members = members + ', ...'
		return members

# We import smirc.* modules at the bottom (instead of at the top) as a fix for
# circular import problems.
from smirc.chat.models import Conversation
from smirc.chat.models import Invitation
from smirc.chat.models import Membership
from smirc.chat.models import SmircRestrictedNameException
from smirc.chat.models import UserProfile
from smirc.message.models import SMSToolsMessage