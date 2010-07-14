from django.shortcuts import render_to_response

def faq(request):
	return render_to_response('pages/faq.html', {})

def help(request):
	return render_to_response('pages/help.html', {})

def index(request):
	return render_to_response('pages/index.html', {})
