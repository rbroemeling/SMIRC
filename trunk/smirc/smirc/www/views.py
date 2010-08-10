from django.shortcuts import render_to_response
from smirc.command.models import SmircCommand

def faq(_unused_request):
	return render_to_response('pages/faq.html', {})

def help(_unused_request):
	command_usage_list = []
	for klassname, obj in SmircCommand.available_commands():
		command_usage_list.append({
			'command': klassname.replace('SmircCommand', '').upper(),
			'description': SmircCommand.command_description(obj),
			'examples': SmircCommand.command_examples(obj),
			'usage': SmircCommand.command_usage(obj)
		})
	command_usage_list.sort(key=lambda x: x['command'])

	return render_to_response('pages/help.html', {
		'command_character': SmircCommand.COMMAND_CHARACTER,
		'command_usage_list': command_usage_list
	})

def index(_unused_request):
	return render_to_response('pages/index.html', {})
