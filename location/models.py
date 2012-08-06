import sys
import math

from django.db import models, connection, transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.conf import settings

from myproject.custom import GoogleLatLng

# Create your models here.

class Country(models.Model):
    abbr = models.CharField("Abbreviation", max_length=2, primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    verified = models.BooleanField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)

class State(models.Model):
    country = models.ForeignKey(Country, related_name='States')
    key = models.CharField(max_length=100, editable=False)
    name = models.CharField(max_length=150)
    verified = models.BooleanField()

    def __unicode__(self):
        return self.name

    def save(self, **kwargs):
        if not self.key or len(self.key) > 100:
            self.key = self.name[:100]
        super(State, self).save(**kwargs)
    
    class Meta:
        unique_together = ('country', 'name')

class LocationManager(models.Manager):
    def nearby_locations(self, latitude, longitude, radius, use_miles=False):
        if use_miles:
            distance_unit = 3959
        else:
            distance_unit = 6371
        cursor = connection.cursor()
        sql = """SELECT id, lat, lng FROM %s WHERE (%f * acos( cos( radians(%f) ) * cos( radians( lat ) ) *
        cos( radians( lng ) - radians(%f) ) + sin( radians(%f) ) * sin( radians( lat ) ) ) ) < %d
        """ % (self.model._meta.db_table, distance_unit, latitude, longitude, latitude, int(radius))
        cursor.execute(sql)
        ids = [row[0] for row in cursor.fetchall()]
        return self.filter(id__in=ids)

class BaseLocation(models.Model):
    city = models.CharField(max_length=150)
    state = models.ForeignKey(State, blank=True, null=True)
    country = models.ForeignKey(Country, blank=True, null=True)
    lat = models.FloatField(blank=True, default=1000.0, editable=False)
    lng = models.FloatField(blank=True, default=1000.0, editable=False)
    json_response = models.CharField(max_length=2000, editable=False, blank=True, null=True)
    
    objects = models.Manager()
    neighbours = LocationManager()

    def __unicode__(self):
        return u'%s, %s, %s' % (self.city, self.state.name, self.country.name)

    def clean(self, **kwargs):
        mquery = kwargs.get('mquery')
        if self.city or mquery:
            if not mquery:
                mquery = GoogleLatLng()
                state = self.state.name if self.state else ''
                country = self.country.abbr if self.country else ''
                if not mquery.requestLatLngJSON(self.city + ', ' + state + ', ' + country):
                    raise ValidationError("There is an error in the location string")
            l = mquery.parseLocation()
            if not l: # It is assumed that all args to clean with mquery will be cities
                raise ValidationError("This city could not be found")
            self.json_response = mquery.results
            self.city = l[0]
            newcountry, created = Country.objects.get_or_create(abbr=l[-1][1], name=l[-1][0],
                                                                defaults={'abbr':l[-1][1], 'name':l[-1][0]})
            self.country = newcountry
            if len(l) > 2:
                newstate, created = State.objects.get_or_create(key=l[-2][1], name=l[-2][0], country=self.country,
                                                                defaults={'key':l[-2][1],
                                                                          'name':l[-2][0],
                                                                          'country':self.country})
                self.state = newstate
            else:
                self.state = None
            self.lat = mquery.lat
            self.lng = mquery.lng

    def save(self, mquery=None, *args, **kwargs):
        self.clean(mquery=mquery)
        if mquery:
            try:
                test = BaseLocation.objects.get(lat=self.lat, lng=self.lng)
            except ObjectDoesNotExist:
                pass
            else:
                return
        super(BaseLocation, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Location of Operation"
        unique_together = ('lat', 'lng')
