from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
	(r'^$', 'smirc.www.views.index'),     # No arguments, display the main homepage.
	(r'^faq/$', 'smirc.www.views.faq'),   # Display our list of frequently-asked questions.
	(r'^help/$', 'smirc.www.views.help')  # Display help documentation.
)
