from django.contrib.auth.models import User
from smirc.api.models import Room

class Membership(models.Model):
	class Meta:
		app_label = 'api'
		unique_together = (('user','room'))

	user = models.ForeignKey(User)
	room = models.ForeignKey(Room)
	voice = models.BooleanField()

	def __unicode__(self):
		return '%s:%s' % (room.name, user.name)