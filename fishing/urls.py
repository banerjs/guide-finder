from django.conf.urls.defaults import *

urlpatterns = patterns('myproject.fishing.views',
                       url(r'^display/$', 'searchDisplay', name='Primarysearch'),
                       url(r'^xmlhttp/search/$', 'searchDisplay',
                           { 'template_name':'results.html' }, name='AJAXsearch'),
                       url(r'^xmlhttp/fish/$', 'XMLfish', name='AJAXfish'),
)
