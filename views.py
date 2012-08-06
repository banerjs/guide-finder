# Used for generic templates
from django.views.generic import TemplateView
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.conf import settings

from myproject.forms import ContactUsForm

def settings_processor(request):
    return { 'DOMAIN':settings.DOMAIN,
             'LOGIN_URL':settings.LOGIN_URL,
             'LOGOUT_URL':settings.LOGOUT_URL,
             'CSS_URL':settings.CSS_URL,
             'JS_URL':settings.JS_URL,
           }

def contact_response(request):
    if request.method == 'POST' and request.POST.__getitem__('name') and request.POST.__getitem__('email') and request.POST.__getitem__('msg'):
        subject = 'Review for the site'
        from_email = settings.DEFAULT_FROM_EMAIL
        message = 'Name: ' + request.POST.__getitem__('name') + '\nEmail: ' + request.POST.__getitem__('email')
        message += '\nMessage:\n' + request.POST.__getitem__('msg')
        send_mail(subject, message, from_email, ['contact@theguidefinder.com'], fail_silently=False)
        return render(request, 'thanks.html')
    else:
        return redirect(settings.DOMAIN+'contact/')
