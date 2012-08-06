from django.conf.urls.defaults import *
from django.views.generic import TemplateView
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'back.views.home', name='home'),
    # url(r'^back/', include('back.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^messages/', include('messages.urls')),
    url(r'^', include('social_auth.urls')),
    url(r'^', include('registration.urls')),
    url(r'^', include('myproject.fishing.urls')),
    url(r'^', include('myproject.gprofile.urls')),
    url(r'^$', TemplateView.as_view(template_name="index.html")),
    url(r'^about/$', TemplateView.as_view(template_name="about.html")),
    url(r'^contact/$', TemplateView.as_view(template_name="contact.html")),
    url(r'^dashboard/$', TemplateView.as_view(template_name='dashboard/controlpanel.html')),
)

urlpatterns += patterns('myproject.views',
                        url('^thanks/$', 'contact_response'),
)
