class SmircCommandException(Exception):
	def __init__(self, value):
		self.value = value

	def __str__(self):
		return repr(self.value)

class SmircCommand:
	def cmd_create(self, room):
		"""Create a new chat room.

		*CREATE [room to create]
		"""
		pass

	def cmd_invite(self, user, room):
		"""Invite a user to a chat room that you control.

		*INVITE [user to be invited] [room you own]
		"""
		pass
	
	def cmd_join(self, room):
		"""Join a chat room that you've been invited to.

		*JOIN [room you are invited to]
		"""
		pass

	def cmd_kick(self, user, room):
		"""Kick a user out of a chat room that you control.

		*KICK [user to kick] [room you own]
		"""
		pass

	def cmd_nick(self, room):
		"""Change your user nickname.

		*NICK [new user nickname]
		"""
		pass

	def cmd_part(self, room):
		"""Leave a chat room that you're currently in.

		*PART [room you are in]
		"""
		pass
	
	def execute(message):
		# execute message.command(message.body) by message.user
		try:
			command = getattr(self, 'cmd_%s' % (message.command.lower()))
		except AttributeError, e:
			raise SmircCommandException('unknown command "%s"' % (message.command))
		else:
			args = message.body.split()
			try:
				result = command(*args)
			except TypeError, e:
				usage = ''
				for line in command.__doc__.splitlines():
					line = line.trim()
					if line[0:1] == '*':
						usage = line
				assert usage != ''
				raise SmircCommandException('invalid arguments given, use "%s"' % (usage))
			else:
				return result
