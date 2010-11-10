from django.shortcuts import render_to_response
from django.template import RequestContext
from smirc.command.models import SmircCommand

def smirc_render_to_response(request, *args, **kwargs):
	kwargs['context_instance'] = RequestContext(request)
	return render_to_response(*args, **kwargs)

def changelog(request):
	return smirc_render_to_response(request, 'pages/changelog.html', {})

def faq(request):
	return smirc_render_to_response(request, 'pages/faq.html', {})

def help(request):
	command_usage_list = []
	for klassname, obj in SmircCommand.available_commands():
		command_usage_list.append({
			'command': klassname.replace('SmircCommand', '').upper(),
			'description': SmircCommand.command_description(obj),
			'examples': SmircCommand.command_examples(obj),
			'usage': SmircCommand.command_usage(obj)
		})
	command_usage_list.sort(key=lambda x: x['command'])

	return smirc_render_to_response(request, 'pages/help.html', {
		'command_character': SmircCommand.COMMAND_CHARACTER,
		'command_usage_list': command_usage_list
	})

def index(request):
	return smirc_render_to_response(request, 'pages/index.html', {})
