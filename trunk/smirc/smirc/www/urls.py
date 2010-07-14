from django.conf.urls.defaults import *

urlpatterns = patterns('',
	(r'^$', 'smirc.www.views.welcome') 
)
