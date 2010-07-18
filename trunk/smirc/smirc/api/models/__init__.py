# As a requirement of being used by Django, models defined inside a
# models/ sub-directory need to be tagged with:
# 	class Meta:
#		app_label = 'foo'
# For more information, see:
# http://blog.amber.org/2009/01/19/moving-django-models-into-their-own-module/

from smirc.api.models.membership import Membership
from smirc.api.models.room import Room
from smirc.api.models.message import SMSToolsMessage
from smirc.api.models.userprofile import UserProfile

__all__ = ['Membership', 'Room', 'SMSToolsMessage', 'UserProfile']