from django.shortcuts import render_to_response
from smirc.command.models import SmircCommand

def faq(request):
	return render_to_response('pages/faq.html', {})

def help(request):
	command_usage_list = []
	for klassname, obj in SmircCommand.available_commands():
		command_usage_list.append({
			'command': klassname.replace('SmircCommand', '').upper(),
			'description': SmircCommand.command_description(obj).join(' '),
			'usage': SmircCommand.command_usage(obj)
		})
	command_usage_list.sort(key=lambda x: x['command'])

	return render_to_response('pages/help.html', {
		'comchar': SmircCommand.COMMAND_CHARACTER,
		'command_usage_list': command_usage_list
	})

def index(request):
	return render_to_response('pages/index.html', {})
