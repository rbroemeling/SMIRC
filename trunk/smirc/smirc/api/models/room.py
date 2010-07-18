from django.contrib.auth.models import User
from smirc.api.models import Membership

class Room(models.Model):
	class Meta:
		app_label = 'api'
		unique_together = (('owner','name'))

	name = models.CharField(max_length=16, db_index=True)
	owner = models.ForeignKey(User)
	users = models.ManyToManyField(User, related_name='rooms', through='Membership')

	def __unicode__(self):
		return self.name