from django.contrib.auth.models import User
from smirc.chat.models import Convenience
from smirc.chat.models import Room

class SmircCommandException(Exception):
	def __init__(self, value):
		self.value = value

	def __str__(self):
		return repr(self.value)

class SmircCommand:
	executing_user = None

	def cmd_create(self, room):
		"""Create a new chat room.

		*CREATE [room to create]
		"""
		try:
			Convenience.load_room(room, self.executing_user)
		except Room.DoesNotExist:
			# TODO: create the requested room.
		else:
			raise SmircCommandException('room %s already exists' % (room))

	def cmd_invite(self, user, room):
		"""Invite a user to a chat room that you control.

		*INVITE [user to be invited] [room you own]
		"""
		try:
			user = Convenience.load_user(user)
		except User.DoesNotExist:
			raise SmircCommandException('user %s not found' % (user))
		else:
			try:
				room = Convenience.load_room(room, self.executing_user)
			except Room.DoesNotExist:
				raise SmircCommandException('room %s not found' % (room))
			else:
				if room.owner == self.executing_user:
					# TODO: check whether user is already in room
					# TODO: invite user to room
				else:
					raise SmircCommandException('you do not own room %s', % (room))

	def cmd_join(self, room):
		"""Join a chat room that you've been invited to.

		*JOIN [room you are invited to]
		"""
		pass

	def cmd_kick(self, user, room):
		"""Kick a user out of a chat room that you control.

		*KICK [user to kick] [room you own]
		"""
		# TODO: intertwine this with cmd_invite, as they do basically the same thing.
		# Maybe outsource it to a private function?
		pass

	def cmd_nick(self, new_user):
		"""Change your user nickname.

		*NICK [new user nickname]
		"""
		try:
			Convenience.load_user(new_user)
		except User.DoesNotExist:
			# TODO: check new_user to see if it follows naming requirements
			self.executing_user.name = new_user
			self.executing_user.save()
		else:
			raise SmircCommandException('user nickname %s is already in use' % (new_user))

	def cmd_part(self, room):
		"""Leave a chat room that you're currently in.

		*PART [room you are in]
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
