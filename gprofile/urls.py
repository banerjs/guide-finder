from django.conf.urls.defaults import *

urlpatterns = patterns('myproject.gprofile.views',
                       url(r'^profiles/(?P<id>\d+)/(?P<name>[A-Za-z_-]+)/$', 'show_profile'),
)
