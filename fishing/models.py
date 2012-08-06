import sys
import math
import pycurl, urllib

from django.utils import simplejson as json
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.db import models, connection, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver, Signal

from myproject.custom import GoogleLatLng, resize_image
from myproject.location.models import Country, State, BaseLocation, LocationManager
from myproject.customer.models import CustomerCore

# Create your models here.

WATER_TYPES = (('FW', 'Freshwater'),
               ('SW', 'Saltwater'))

WATERBODY_TYPES = (
    'Loch',
    'Canal',
    'Brook',
    'Ocean',
    'Creek',
    'Sea',
    'Lake',
    'River',
    'Stream',
    'Basin',
    'Bay',
    'Bayou',
    'Channel',
    'Strait',
)    

make_thumbnail = Signal(providing_args={'instance', 'max_size'})

class WaterBody(models.Model):
    name = models.CharField("Name of Water Body", max_length=150, unique=True)
    state = models.ForeignKey(State, blank=True, null=True)
    country = models.ForeignKey(Country, null=True, blank=True)
    locations = models.ManyToManyField(BaseLocation, through='GeoRelations', verbose_name="Nearby Locations", blank=True, editable=False, null=True, related_name="WaterBodies")
    lat = models.FloatField(blank=True, default=1000.0, editable=False)
    lng = models.FloatField(blank=True, default=1000.0, editable=False)
    json_response = models.CharField(max_length=2000, editable=False, blank=True, null=True)
    
    objects = models.Manager()
    neighbours = LocationManager()

    def __unicode__(self):
        return self.name
    
    def associate_locations(self, loc_model=BaseLocation, radius=100, use_miles=True):
        near = loc_model.neighbours.nearby_locations(self.lat, self.lng, radius, use_miles)
        for l in near:
            try:
                r = GeoRelations.objects.get(location__exact=l, water__exact=self)
            except:
                r = GeoRelations(location=l, water=self, verified=True)
                r.save()

    def clean(self, **kwargs):
        mquery = kwargs.get('mquery')
        if self.name or mquery:
            if not mquery:
                mquery = GoogleLatLng()
                state = self.state.name if self.state else ''
                country = self.country.abbr if self.country else ''
                if not mquery.requestLatLngJSON(self.name + ', ' + state + ', ' + country, True):
                    raise ValidationError("There is an error in the location string")
            l = mquery.parseLocation() # Again assume that all args to clean with mquery pass this test
            if not l:
                raise ValidationError("This body of water could not be found")
            self.json_response = mquery.results
            self.name = l[0]
            if len(l) > 1:
                newcountry, created = Country.objects.get_or_create(abbr=l[-1][1], name=l[-1][0],
                                                                    defaults={'abbr':l[-1][1], 'name':l[-1][0]})
                self.country = newcountry
            else:
                self.country = None
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
                test = WaterBody.objects.get(lat=self.lat, lng=self.lng)
            except ObjectDoesNotExist:
                pass
            else:
                return
        super(WaterBody, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Body of Water"
        verbose_name_plural = "Bodies of Water"
        unique_together = ('lat', 'lng')

class GeoRelationsManager(models.Manager):
    def user_edit(self, loc, wat, cust):
        """
        loc is a BaseLocation object,
        wat is a WaterBody object,
        cust is a CustomerCore object
        """
        newrel = self.model(location=loc, water=wat, added_by=cust)
        newrel.save()
        return newrel

class GeoRelations(models.Model):
    location = models.ForeignKey(BaseLocation)
    water = models.ForeignKey(WaterBody)
    verified = models.BooleanField(blank=True, default=False)
    added_by = models.ForeignKey(CustomerCore, null=True, related_name="GeoRelations")
    added_on = models.DateTimeField(auto_now_add=True)

    custom = GeoRelationsManager()
    objects = models.Manager()

    def __unicode__(self):
        return '%s - %s' % (self.location, self.water)

    def verify(self):
        self.verified = True

    class Meta:
        verbose_name = "Geographic Relationship"
        unique_together = ('location', 'water')

class Fish(models.Model):
    name = models.CharField("Name of Fish", max_length=30)
    type = models.CharField("Type of Fish", max_length=30)
    water_type = models.CharField("Water Habitat of Fish", max_length=2, choices=WATER_TYPES)
    alternate_name_1 = models.CharField(max_length=30, blank=True, null=True)
    alternate_name_2 = models.CharField(max_length=30, blank=True, null=True)
    alternate_name_3 = models.CharField(max_length=30, blank=True, null=True)
    image = models.ImageField(upload_to='fishimages/', blank=True, null=True)
    verified = models.BooleanField(default=False, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Fish"
        unique_together = ("name", "type", "water_type")

    def save(self, *args, **kwargs):
        try:
            this = Fish.objects.get(id=self.id)
            if this.image != self.image:
                this.image.delete()
        except:
            pass
        super(Fish, self).save(*args, **kwargs)

class FishingType(models.Model):
    method = models.CharField("Type of Fishing Trip", max_length=100, unique=True)
    image = models.ImageField(upload_to='typeimages/', blank=True, null=True)
    verified = models.BooleanField(default=False, blank=True)

    def __unicode__(self):
        return self.method

    class Meta:
        verbose_name = "Fishing Type"

    def save(self, *args, **kwargs):
        try:
            this = FishingType.objects.get(id=self.id)
            if this.image != self.image:
                this.image.delete()
        except:
            pass
        super(FishingType, self).save(*args, **kwargs)

class InheritanceCastModel(models.Model):
    """
    An abstract base class that provides a ``real_type`` FK to ContentType.
    
    For use in trees of inherited models, to be able to downcast
    parent instances to their child types.
    """
    real_type = models.ForeignKey(ContentType, editable=False, null=True)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.real_type = self._get_real_type()
        super(InheritanceCastModel, self).save(*args, **kwargs)

    def _get_real_type(self):
        return ContentType.objects.get_for_model(type(self))

    def cast(self):
        return self.real_type.get_object_for_this_type(pk=self.pk)

    class Meta:
        abstract = True

class BaseBrand(InheritanceCastModel):
    guide = models.ManyToManyField('gprofile.GuideCore', related_name='%(app_label)s_%(class)s_related')
    brand = models.CharField(max_length=200, unique=True)
    image = models.ImageField(upload_to='logos/', blank=True, null=True)
    verified = models.BooleanField(default=False)

    def __unicode__(self):
        return self.brand

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        try:
            this = self.cast()
            if this.image != self.image:
                this.image.delete()
        except:
            pass
        super(BaseBrand, self).save(*args, **kwargs)
        make_thumbnail.send(sender=BaseBrand.__name__, instance=self, max_size=(100,100))

class LureBrand(BaseBrand):
    class Meta:
        verbose_name = "Lure Brand"

class RodBrand(BaseBrand):
    class Meta:
        verbose_name = "Rod Brand"

class ReelBrand(BaseBrand):
    class Meta:
        verbose_name = "Reel Brand"

class LineBrand(BaseBrand):
    class Meta:
        verbose_name = "Line Brand"

class BaitBrand(BaseBrand):
    class Meta:
        verbose_name = "Bait Brand"

class GuideEngine(models.Model):
    guide = models.ForeignKey('gprofile.GuideCore')
    engine_brand = models.ForeignKey('EngineBrand')
    horsepower = models.IntegerField(help_text="Enter the hp of this engine")
    model = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Engine Brands for Guide"
        verbose_name_plural = "Engine Brands for Guide"

    def __unicode__(self):
        return engine_brand.__unicode__() + ' for ' + guide.__unicode__()

class EngineBrand(models.Model):
    brand = models.CharField(max_length=200)
    image = models.ImageField(upload_to='logos/', blank=True, null=True)
    verified = models.BooleanField(default=False)
    guide = models.ManyToManyField('gprofile.GuideCore', blank=True, null=True, through=GuideEngine, related_name='EngineBrands')
    
    class Meta:
        verbose_name = "Engine Brand"

    def __unicode__(self):
        return self.brand

    def save(self, *args, **kwargs):
        try:
            this = EngineBrand.objects.get(id=self.id)
            if this.image != self.image:
                this.image.delete()
        except:
            pass
        super(EngineBrand, self).save(*args, **kwargs)

class BoatBrand(models.Model):
    brand = models.CharField(max_length=200)
    image = models.ImageField(upload_to='logos/', blank=True, null=True)
    verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Boat Brand"

    def __unicode__(self):
        return self.brand

    def save(self, *args, **kwargs):
        try:
            this = BoatBrand.objects.get(id=self.id)
            if this.image != self.image:
                this.image.delete()
        except:
            pass
        super(BoatBrand, self).save(*args, **kwargs)

class GuideBoat(models.Model):
    boat_brand = models.ForeignKey(BoatBrand)
    guide = models.ForeignKey('gprofile.GuideCore', related_name='boats')
    boat_length = models.PositiveIntegerField(help_text="Please enter the length in feet")
    model = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Boat Brands for Guide"
        verbose_name_plural = "Boat Brands for Guide"

    def __unicode__(self):
        return boat_brand.__unicode__() + ' for ' + guide.__unicode__()

class GuideFAQ(models.Model):
    """
    Extras in this model that are not present on the profile page:
    - Capture Release
    - Lost Tackle
    - Allow International
    Things I should include?
    - Boats have a bathroom
    """
    guide = models.OneToOneField('gprofile.GuideCore', related_name='FAQ')
    child_friendly = models.BooleanField(default=True, blank=True)
    alcohol_allowed = models.BooleanField(default=True, blank=True)
    food_provided = models.BooleanField(default=True, blank=True)
    capture_release = models.BooleanField(default=True, blank=True)
    state_certified = models.BooleanField(default=False, blank=True)
    CG_certified = models.BooleanField("US Coast Guard Certified", default=False, blank=True)
    cert_verify = models.BooleanField(default=False, blank=True)
    handicap_friendly = models.BooleanField(default=True, blank=True)
    personal_equipment = models.BooleanField("Require Personal Equipment", default=False, blank=True)
    lost_tackle = models.BooleanField("Extra Charge for Lost Tackle", default=False, blank=True)
    fillet_services = models.BooleanField(default=False, blank=True)
    taxidermy_services = models.BooleanField("Taxidermy Services", default=False, blank=True)
    allow_international = models.BooleanField("Allow International Customers", default=True, blank=True)
    explain = models.CharField("Explanations and Clarifications", max_length=1000, blank=True, null=True)
#    cf_explain = models.CharField("Explanation - Child Friendliness", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your children on board policies?")
#    al_explain = models.CharField("Explanation - Alcohol On Board", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your alcohol on board policies?")
#    fp_explain = models.CharField("Explanation - Food Provisions", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your policies on meals?")
#    cr_explain = models.CharField("Explanation - Capture and Release", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your Capture and Release policies?")
#    sc_explain = models.CharField("Explanation - State Certification", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your State Certification?")
#    cg_explain = models.CharField("Explanation - Coast Guard Certification", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your Coast Guard Certification?")
#    hf_explain = models.CharField("Explanation - Handicap Accessibility", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your Handicap Person's policies?")
#    pe_explain = models.CharField("Explanation - Personal Equipment", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your Policies on Personal Equipment?")
#    lt_explain = models.CharField("Explanation - Lost Tackle", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your Policies on Lost Tackle?")
#    fs_explain = models.CharField("Explanation - Fillet Services", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your Provision of Filleting Services?")
#    ts_explain = models.CharField("Explanation - Taxidermy Services", max_length=300, blank=True, null=True, help_text="Would you like to say a few words regarding your Provision of Taxidermy Services?")
#    ai_explain = models.CharField("Explanation - Allow International Customers", max_length=300, blank=True, null=True, help_text="Would you like to say a few words on your willingness to take International fishermen out on trips?")
    
    def __unicode__(self):
        return 'FAQ set for %s' % self.guide.person.full_name

    class Meta:
        verbose_name = "Guide FAQ"

class ExtraDetails(models.Model):
    """
    This can be divided into 2 portions based on my wishes. Also, remove equipment required from FAQ's
    (follow the table on the test profile page).
    To Bring:
    - Sunscreen
    - Hat
    - Sunglasses
    - Rain Gear
    - Motion Sickness Medicine
    - Food
    - Beverages
    - Ice Chest
    - Camera
    - Life Jacket
    - Fishing License
    - Fishing Rod
    - Fishing Reel
    - Bait
    - Insect Repellent
    - Layered Clothing
    - Fly Fishing Waders

    Not to Bring:
    - Glass Bottles
    - Illegal Drugs
    - Alcohol
    - Black or Dark soled shoes
    - Firearms
    - Bananas
    """
    guide = models.OneToOneField('gprofile.GuideCore', related_name='ExtraDetails')
    good_attitude = models.NullBooleanField(null=True)
    life_jacket = models.NullBooleanField(null=True)
    other = models.CharField(max_length=700, help_text="Anything else that you want your customers to bring?", blank=True, null=True)

    def __unicode__(self):
        return "Extra Details for %s" % self.guide.person.full_name

    class Meta:
        verbose_name = "Extra Details"
        verbose_name_plural = "Extra Details"

class ShadowGuide(models.Model):
    """
    Do not need to be as stringent with these because this is either being filled in through the admin or
    automatically.
    """
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    company_name = models.CharField(max_length=200, null=True, blank=True, help_text="Enter the name of the company if the guide has one")
    phone_number = models.CharField(max_length=15, help_text="Use standard characters in Phone number only", blank=True, null=True)
    locations = models.ManyToManyField(BaseLocation, related_name="ShadowGuides")
    email = models.EmailField(blank=True, null=True)
    added_from = models.URLField()

    class Meta:
        verbose_name = "Shadow Guide"
        unique_together = ('first_name', 'last_name', 'phone_number', 'email')

    def get_full_name(self):
        return self.first_name + self.last_name

    def set_full_name(self, name):
        self.first_name, self.last_name = name.split()

    full_name = property(get_full_name, set_full_name)

    def __unicode__(self):
        return self.full_name

# For the signal handlers below, I don't need to worry about infinite recursion because the model is not being
# updated
@receiver(post_save, sender=BoatBrand)
def boat_thumbnail(sender, created=False, instance=None, **kwargs):
    if instance:
        max_size = (100, 100)
        resize_image(instance.image, max_size)

@receiver(post_save, sender=Fish)
def fish_thumbnail(sender, created=False, instance=None, **kwargs):
    if instance:
        max_size = (200, 150)
        resize_image(instance.image, max_size)

@receiver(post_save, sender=FishingType)
def type_thumbnail(sender, created=False, instance=None, **kwargs):
    if instance:
        max_size = (200, 200)
        resize_image(instance.image, max_size)

@receiver(make_thumbnail, sender='BaseBrand')
def brand_thumbnail(sender, instance=None, max_size=None, **kwargs):
    if instance and max_size:
        resize_image(instance.image, max_size)

@receiver(post_save, sender=EngineBrand)
def type_thumbnail(sender, created=False, instance=None, **kwargs):
    if instance:
        max_size = (100, 100)
        resize_image(instance.image, max_size)

# This is a snippet of code that can prevent infinite save loops in the future
#    if instance:
#        if hasattr(instance, '_already_saving'):
#            del instance._already_saving
#            return
#        instance._already_saving = True
#        #... Do something ...#
#        instance.save()
