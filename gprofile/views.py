from django.shortcuts import render
from django.http import Http404

from myproject.gprofile.models import GuideCore

# Create your views here.

def show_profile(request, id, name, template='profile_django.html'):
    try:
        id = int(id)
        guide = GuideCore.objects.select_related('person',
                                                 'profile',
                                                 'profile__cust_profile',
                                                 'waterbodies',
                                                 'locations',
                                                 'methods',
                                                 'Recommendations',
                                                 'PartyModel',
                                                 'Fans',
                                                 'FAQ', 'ExtraDetails').get(person__id=id)
    except:
        raise Http404
    return render(request, template, { 'guide':guide })
