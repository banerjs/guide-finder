import re
from datetime import datetime, timedelta

from django.db.models import Q, F, Max, Min
from django.contrib.localflavor.us import us_states
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.conf import settings

from myproject.custom import GoogleLatLng
from myproject.location.models import BaseLocation
from myproject.fishing.models import WaterBody, Fish, FishingType
from myproject.gprofile.models import GuideCore, name_cal

# Create your views here.

def locDetermine(location):
    params = location.split(',')
    for a in range(len(params)):
        params[a] = params[a].strip()
    if len(params) == 1:
        test = BaseLocation.objects.filter(city__icontains=params[0])
        if not test.exists():
            test = BaseLocation.objects.filter(Q(state__key__iexact=params[0]) | Q(state__name__icontains=params[0]))
            if not test.exists():
                test = BaseLocation.objects.filter(Q(country__abbr__iexact=params[0]) | Q(country__name__icontains=params[0]))
                if not test.exists():
                    test = WaterBody.objects.filter(name__icontains=params[0])
                    if not test.exists():
                        return (None, None)
                    else:
                        return test[0], ['natural_feature',]
                else:
                    return test[0], ['country',]
            else:
                return test[0], ['administrative_area_level_1',]
        else:
            return test[0], ['city',]
    elif len(params) == 2:
        test = BaseLocation.objects.filter(Q(city__icontains=params[0]),
                                           Q(state__key__iexact=params[1]) | Q(state__name__icontains=params[1]))
        if not test.exists():
            test = BaseLocation.objects.filter(Q(state__key__iexact=params[0]) | Q(state__name__icontains=params[0]),
                                               Q(country__abbr__iexact=params[1]) | Q(country__name__icontains=params[1]))
            if not test.exists():
                test = WaterBody.objects.filter(Q(name__icontains=params[0]),
                                                Q(state__key__iexact=params[1]) | Q(state__name__icontains=params[1]) |
                                                Q(country__abbr__iexact=params[1]) | Q(country__name__icontains=params[1]))
                if not test.exists():
                    return None, None
                else:
                    return test[0], ['natural_feature',]
            else:
                return test[0], ['administrative_area_level_1',]
        else:
            return test[0], ['city',]
    else:
        test = BaseLocation.objects.filter(Q(city__icontains=params[0]),
                                           Q(state__key__iexact=params[1]) | Q(state__name__icontains=params[1]),
                                           Q(country__abbr__iexact=params[2]) | Q(country__name__icontains=params[2]))
        if not test.exists():
            test = WaterBody.objects.filter(Q(name__icontains=params[0]),
                                            Q(state__key__iexact=params[1]) | Q(state__name__icontains=params[1]),
                                            Q(country__abbr__iexact=params[2]) | Q(country__name__icontains=params[2]))
            if not test.exists():
                return None, None
            else:
                return test[0], ['natural_feature',]
        else:
            return test[0], ['city',]

def locQuery(location, **kwargs):
    """
    Function to return matching locations. Can be optimized in 2 manners:
    1) Get rid of for loops on WaterBody and BaseLocation querysets
    2) Optimize locDetermine()
    """
    q = GoogleLatLng()
    query = GuideCore.objects.none()
    loc, type = locDetermine(location)
    if not type:
        if q.requestLatLngJSON(location):
            loc, type = q, q.results['types']
            newloc = BaseLocation()
            try:
                newloc.save(mquery=q)
            except:
                pass
        elif q.requestLatLngJSON(location, True):
            loc, type = q, q.results['types']
            newloc = WaterBody()
            try:
                newloc.save(mquery=q)
            except:
                pass
            if newloc.id: newloc.associate_locations()
        else:
            return query
    rad = kwargs.get('radius', 100)
    if 'country' in type:
        # If it was a search by Country name
        try:
            l = loc.results['address_components'][0]['short_name']
        except:
            l = loc.country.abbr
        query = GuideCore.objects.filter(Q(locations__country__abbr=l))
    elif 'administrative_area_level_1' in type:
        # If it was a search by a state name
        try:
            l = loc.results['address_components'][0]['short_name']
        except:
            l = loc.state.key
        query = GuideCore.objects.filter(Q(locations__state__key=l))
    else:
        # If is was a search by a city name or a WaterBody
        locs = BaseLocation.neighbours.nearby_locations(loc.lat, loc.lng, rad, True).select_related('FishingGuides')
        for l in locs:
            query = query | GuideCore.objects.filter(locations=l)
        locs = WaterBody.neighbours.nearby_locations(loc.lat, loc.lng, rad, True).select_related('Operators')
        for w in locs:
            query = query | GuideCore.objects.filter(waterbodies=w)
    return query

def datQuery(query, date):
    """
    Search for date might take too long. Can be optimized, and should be with location
    """
    return query

def fisQuery(query, **kwargs):
    fish = kwargs.get('fish')
    watertype = kwargs.get('watertype')
    method = kwargs.get('method')
    if fish:
        query = query.filter(Q(fish__name__icontains=fish) |
                             Q(fish__type__icontains=fish) |
                             Q(fish__alternate_name_1__icontains=fish) |
                             Q(fish__alternate_name_2__icontains=fish) |
                             Q(fish__alternate_name_3__icontains=fish))
    if watertype:
        query = query.filter(fish__water_type__iexact=watertype)
    if method:
        query = query.filter(methods__method__icontains=method)
    return query

def groQuery(query, **kwargs):
    boatsize = int(kwargs.get('boatsize', 0))
    partysize = int(kwargs.get('partysize', 0))
    if boatsize:
        query = query.annotate(max_boat=Max('boats__boat_length')).exclude(max_boat__lt=int(boatsize))
        query = query.annotate(min_boat=Min('boats__boat_length')).exclude(min_boat__gt=int(boatsize))
    if partysize:
        query = query.filter(PartyModel__max_party__gte=partysize, PartyModel__min_party__lte=partysize)
    return query

def priQuery(query, **kwargs):
    if kwargs.get('price'):
        maxprice = float(kwargs.get('maxprice', 99999999.99))
        minprice = float(kwargs.get('minprice', 0))
        query = query.filter(search_price__gte=minprice, search_price__lte=maxprice)
    return query

def faqQuery(query, **kwargs):
    isnew = kwargs.get('isnew')
    cf = kwargs.get('child_friendly')
    al = kwargs.get('alcohol_allowed')
    fp = kwargs.get('food_provided')
    cr = kwargs.get('capture_release')
    sc = kwargs.get('state_certified')
    cg = kwargs.get('CG_certified')
    hf = kwargs.get('handicap_friendly')
    pe = kwargs.get('personal_equipment')
    lt = kwargs.get('lost_tackle')
    fs = kwargs.get('fillet_services')
    ts = kwargs.get('taxidermy_services')
    ai = kwargs.get('allow_international')
    if isnew:
        isnew = False if isnew == 'False' else True
        query = query.filter(is_new=isnew)
    if cf:
        cf = False if cf == 'False' else True
        query = query.filter(faq__child_friendly=cf)
    if al:
        al = False if al == 'False' else True
        query = query.filter(faq__alcohol_allowed=al)
    if fp:
        fp = False if fp == 'False' else True
        query = query.filter(faq__food_provided=fp)
    if cr:
        cr = False if cr == 'False' else True
        query = query.filter(faq__capture_release=cr)
    if sc:
        sc = False if sc == 'False' else True
        query = query.filter(faq__state_certified=sc)
    if cg:
        cg = False if cg == 'False' else True
        query = query.filter(faq__CG_certified=cg)
    if hf:
        hf = False if hf == 'False' else True
        query = query.filter(faq__handicap_friendly=hf)
    if pe:
        pe = False if pe == 'False' else True
        query = query.filter(faq__personal_equipment=pe)
    if lt:
        lt = False if lt == 'False' else True
        query = query.filter(faq__lost_tackle=lt)
    if fs:
        fs = False if fs == 'False' else True
        query = query.filter(faq__fillet_services=fs)
    if ts:
        ts = False if ts == 'False' else True
        query = query.filter(faq__taxidermy_services=ts)
    if ai:
        ai = False if ai == 'False' else True
        query = query.filter(faq__allow_international=ai)
    return query

def retQuery(location, day, **kwargs):
    query = locQuery(location, **kwargs)  # Filter based on Location
    if query.exists():
        query = datQuery(query, day)      # Filter based on Date
        query = fisQuery(query, **kwargs) # Filter based on Fish, WaterType and FishingMethod
        query = groQuery(query, **kwargs) # Filter based on BoatSize and Number of People
        query = priQuery(query, **kwargs) # Filter based on Price
        query = faqQuery(query, **kwargs) # Filter based on FAQ's (including new)
    return query.distinct()

def ordQuery(query, ordering):
    sort = ['full_day_price', '-profile__num_recommends', '-experience', 'person__first_name', 'person__last_name', '-PartyModel__avg_party']
    if not ordering or ordering == 'price':
        new_sort = sort
    if ordering == 'recommend':
        new_sort = list(sort.pop(1))
        new_sort.extend(sort)
    if ordering == 'experience':
        new_sort = list(sort.pop(2))
        new_sort.extend(sort)
    if ordering == 'alpha':
        new_sort = [sort.pop(3), sort.pop(4)]
        new_sort.extend(sort)
    if ordering == 'party' or ordering == 'boat':
        new_sort = list(sort.pop(5))
        new_sort.extend(sort)
        if ordering == 'boat':
            return query.annotate(max_length=Max('boats__boat_length')).order_by('-max_length', *new_sort)
    return query.order_by(*new_sort)

def parQuery(location, pday, **kwargs):
    if pday == '':
        day = datetime.today()+timedelta(1)
    else:
        day = datetime.strptime(pday, '%m/%d/%Y')
    query = ordQuery(retQuery(location, day, **kwargs), kwargs.get('ordering'))
    return query

def searchDisplay(request, template_name='display.html'):
    location = ''
    if request.method == 'GET':
        location = request.GET.get('loc', '')
        day = request.GET.get('date', '')
        if re.match(" .*", location):
            location = ''
        if not re.match("[\d/]+", day):
            day = ''
    if location == '':
        if template_name == 'display.html':
            return HttpResponseRedirect(settings.DOMAIN)
        else:
            return render(request, template_name, { 'guides_list':[] })
    diction = dict(request.GET.items())
    guides = parQuery(location, day, **diction)
    return render(request, template_name, { 'guides_list': list(guides)[:50] })

def testSearch(**kwargs):
    location = kwargs.get('loc', '')
    day = kwargs.get('date', '')
    if re.match(" .*", location):
        location = ''
    if not re.match("[\d/]+", day):
        day = ''
    if location == '':
        return ("Send in results with blank location", [])
    guides = parQuery(location, day, **kwargs)
    return ("Send in results", list(guides))

def XMLfish(request):
    if request.method == 'GET':
        name = request.GET.get('fish', ' ')
        q = Fish.objects.filter(Q(type__istartswith=name) |
                                Q(name__istartswith=name) |
                                Q(alternate_name_1__istartswith=name) |
                                Q(alternate_name_2__istartswith=name) |
                                Q(alternate_name_3__istartswith=name)).order_by('type','name','alternate_name_1')
        message = ""
        if q:
            for a in q:
                message += a.name + ', '
    else:
        message = ""
    return HttpResponse(message)

def XMLlocation(request):
    if request.method == 'GET':
        message = ""
        location = request.GET.get('loc', ' ')
        # Filter and get possibilites for cities
        q = BaseLocation.objects.filter(city__istartswith=location)
        for a in q:
            message += a.city + ', ' + a.state.key + ', ' + a.country.abbr + ';'
        # Filter and get possibilies for states
        q = BaseLocation.objects.filter(Q(state__key__istartswith=location) |
                                        Q(state__name__istartswith=location))
        for a in q:
            message += a.state.name + ', ' + a.country.abbr + ';'
        # Filter and get possibilities for countries
        q = BaseLocation.objects.filter(Q(country__name__istartswith=location) |
                                        Q(country__abbr__istartswith=location))
        for a in q:
            message += a.country.name + ';'
        # Filter and sort by potential waterbodies
        q = WaterBody.objects.filter(name__istartswith=location)
        for a in q:
            message += a.name + ';'
    else:
        message = ""
    return HttpResponse(message)

def XMLmethod(request):
    if request.method == "GET":
        type = request.GET.get('method', ' ')
        message = ""
        q = FishingType.objects.filter(method__istartswith=type)
        for a in q:
            message += a.method + ';'
    else:
        message = ""
    return HttpResponse(message)

#def XMLboats(request):
#    message = ""
#    if request.method == 'GET':
#        name = request.GET.get('boatname', ' ')
#        q = Boats.objects.filter(Q(boat_model_name__istartswith=name) |
#                                 Q(boat_brand_name__istartswith=name)).distinct()
#        for a in q:
#            message += a.boat_brand_name + ', ' + a.boat_model_name + ';'
#    return HttpResponse(message)

# This is for future reference of JSON, if required
#def JSONsearch(request):
#    location = fish = ''
#    if request.method == 'GET':
#        try:
#            location = request.GET.__getitem__('loc')
#        except:
#            location = ''
#        else:
#            if location == " Enter a location":
#                location = ''
#        try:
#            fish = request.GET.__getitem__('fish')
#        except:
#            fish = ''
#        else:
#            if fish == " Enter a fish name":
#                fish = ''
#    if location == '' and fish == '':
#        return HttpResponseRedirect(domain)
#    diction = dict(request.GET.items())
#    guides = parQuery(location, fish, **diction)
#    answer = serializers.serialize('json', guides, relations={'guide':
#                                                              {'relations':{'customer':
#                                                                            {'relations':{'contact':
#                                                                                          {'fields':('city','state','country')
#                                                                                          }
#                                                                                         },
#                                                                             'extras':('__unicode__',)
#                                                                             },
#                                                                            'company':
#                                                                            {'fields':('company_name',)
#                                                                             }
#                                                                            }
#                                                               },
#                                                              'fish':
#                                                              {'fields':('name',)
#                                                               },
#                                                              'location':
#                                                              {'fields':('city','state','country')
#                                                               }
#                                                              })
#    return HttpResponse(answer)
