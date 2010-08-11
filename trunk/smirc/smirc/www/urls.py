from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
	(r'^$', 'smirc.www.views.index'),          # No arguments, display the main homepage.
	(r'^500$', 'smirc.www.views.nonexistent'), # Test our "Internal Server Error" page by purposefully causing an internal server error.
	(r'^faq/$', 'smirc.www.views.faq'),        # Display our list of frequently-asked questions.
	(r'^help/$', 'smirc.www.views.help')       # Display help documentation.
)
