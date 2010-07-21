from django.contrib.auth.models import User
from smirc.chat.models import Invitation
from smirc.chat.models import Membership
from smirc.chat.models import Room
from smirc.chat.models import UserProfile

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
			Room.load_room(room, self.executing_user)
		except Room.DoesNotExist:
			r = Room()
			r.name = room
			r.owner = self.executing_user
			r.save()
			m = Membership()
			m.user = self.executing_user
			m.room = r
			m.voice = True
			m.save()
			return 'you have created the room %s' % (r.name)
		else:
			raise SmircCommandException('room %s already exists' % (room))

	def cmd_invite(self, user, room):
		"""Invite a user to a chat room that you control.

		*INVITE [user to be invited] [room you own]
		"""
		try:
			user = UserProfile.load_user(user)
		except User.DoesNotExist:
			raise SmircCommandException('user %s not found' % (user))
		else:
			try:
				room = Room.load_room(room, self.executing_user)
			except Room.DoesNotExist:
				raise SmircCommandException('room %s not found' % (room))
			else:
				if room.owner == self.executing_user:
					try:
						Invitation.objects.get(room=room, user=user)
					except Invitation.DoesNotExist:
						pass
					else:
						raise SmircCommandException('user %s has already been invited to room %s' % (user, room))
					try:
						Membership.objects.get(room=room, user=user)
					except Membership.DoesNotExist:
						pass
					else:
						raise SmircCommandException('user %s is already a member of room %s' % (user, room))
					i = Invitation()
					i.user = user
					i.room = room
					i.save()
					# TODO: send message to user about their invitation to room
					
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
