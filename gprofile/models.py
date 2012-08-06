from datetime import datetime, time, timedelta, date

from django.db import models
from django.db.models import Sum, Avg, Count, Q
from django.db.models.signals import post_save, post_delete
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.dispatch import receiver, Signal
from django.template.defaultfilters import slugify

from myproject.location.models import BaseLocation, Country
from myproject.customer.models import CustomerCore, ContactInfo, CustomerProfile
from myproject.fishing.models import FishingType, Fish, GuideFAQ, BoatBrand, WaterBody, ExtraDetails, GuideBoat

# Create your models here.

def name_cal(obj=None):
    """
    This is under the assumptino that obj is an object of GuideCore
    """
    if not obj:
        return None
    return slugify(obj.person.full_name+obj.person.profile.date.strftime("%d%Y%m")+str(obj.person.id))

class GuidePayment(models.Model):
    guide = models.ForeignKey('GuideCore', related_name='PaymentModels')
    start_time = models.TimeField(default=time(9))
    end_time = models.TimeField(default=time(17))
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="How much do you charge for this time period? (In your local currency)")

    class Meta:
        verbose_name = "Payments Model"
        ordering = ['start_time', 'end_time']

    def __unicode__(self):
        return '%s: %s to %s' % (self.guide.person.full_name, self.start_time.strftime('%H-%M'), self.end_time.strftime('%H-%M'))

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("You cannot end before you started!")
        if self.amount < 0:
            raise ValidationError("Is giving away money really necessary?")
        payments = self.guide.PaymentModels.exclude((Q(start_time__lt=self.start_time) &
                                                     Q(end_time__lte=self.start_time)) |
                                                    (Q(end_time__gt=self.end_time) &
                                                     Q(start_time__gte=self.end_time)))
        if payments.exists():
            raise ValidationError("You have already defined an amount for this time period")

class GuideParty(models.Model):
    guide = models.OneToOneField('GuideCore', related_name='PartyModel')
    max_party = models.IntegerField("Max party size", help_text="Maximum Party Size that you are willing to take", blank=True, default=10)
    min_party = models.IntegerField("Min party size", help_text="Minimum Party Size that you are willing to take", blank=True, default=1)
    avg_party = models.IntegerField("Preferred party size", help_text="Leave blank to use average of max and min (if provided), otherwise default = 4", blank=True, default=4)

    def __unicode__(self):
        return 'Party Model for %s' % self.guide.person.full_name

    def clean(self):
        if self.max_party < self.min_party:
            raise ValidationError("Lookup minimum and maximum in the dictionary, and then fill these in")
        if self.avg_party > self.max_party or self.avg_party < self.min_party:
            raise ValidationError("Your math is truly awful. The avg lies between the min and max...")

    class Meta:
        verbose_name = "Party Model"

class GuideProfile(models.Model):
    cust_profile = models.OneToOneField(CustomerProfile, editable=False, related_name='GuideProfile')
    blurb = models.CharField(help_text="Hook your customers with a few sentences", max_length=300, blank=True, default='')
    text = models.TextField(help_text="Say something about yourself on the Profile Page", blank=True, default='')
    num_recommends = models.IntegerField(editable=False, default=0)
    num_referrals = models.IntegerField(editable=False, default=0)

    class Meta:
        verbose_name = "Guide Profile"

    def __unicode__(self):
        return "Profile for Guide %s" % self.cust_profile.CustomerMain.full_name

class GuideCore(models.Model):
    is_paying = models.BooleanField(blank=True, default=False, editable=False)
    is_signed_up = models.BooleanField(blank=True, default=False, editable=False)
    is_new = models.BooleanField(blank=True, default=True, editable=False)
    person = models.OneToOneField(CustomerCore, related_name='GuideCore')
    profile = models.OneToOneField(GuideProfile, related_name='GuideMain', editable=False, null=True)
    company = models.CharField(max_length=200, help_text="If you operate as part of a company, Enter the company name", blank=True, null=True)
    locations = models.ManyToManyField(BaseLocation, related_name='FishingGuides', blank=True, null=True)
    waterbodies = models.ManyToManyField(WaterBody, verbose_name="Bodies of Water", related_name='Operators', blank=True, null=True)
    fish = models.ManyToManyField(Fish, related_name='FishCatchers', null=True, blank=True)
    methods = models.ManyToManyField(FishingType, related_name='FishingMasters', verbose_name="Methods of Fishing", help_text="What methods do you specialize in?", null=True, blank=True)
    experience = models.IntegerField("Years of Experience", default=0, blank=True)
    full_day_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, null=True)
    search_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, null=True)
    boat_brands = models.ManyToManyField(BoatBrand, related_name='Owners', blank=True, null=True, through=GuideBoat)

    class Meta:
        verbose_name = "Core Guide Detail"
        verbose_name_plural = "Core Guide Details"

    def __unicode__(self):
        return 'Guide - %s' % self.person.full_name

    def associate_land(self):
        """
        Function to add locations of fishing for a guide, given the water bodies that he fishes in
        """
        if self.waterbodies.all():
            for w in self.waterbodies.all():
                self.locations.add(*w.locations.all())

    def associate_water(self):
        """
        Function to add water bodies for a guide, given the locations that he fishes in
        """
        if self.locations.all():
            for l in self.locations.all():
                self.waterbodies.add(*l.WaterBodies.all())

    def clean(self):
        if self.experience > settings.MAX_EXPERIENCE:
            raise ValidationError('Having over' + str(settings.MAX_EXPERIENCE) + 'years of experience is impossible without being in the record books')
        if self.experience < 0:
            raise ValidationError('Are you sure you are a Fishing Guide?')

    def save(self, *args, **kwargs):
        newprofile, created = GuideProfile.objects.get_or_create(cust_profile=self.person.profile,
                                                                 defaults={'cust_profile':self.person.profile})
        if created: self.profile = newprofile
        if not self.person.is_guide:
            self.person.is_guide = True
            self.person.save(force_update=True)
        try:
            this = GuideCore.objects.get(id=self.id)
        except:
            pass
        else:
            if self.is_new and date.today() > self.profile.cust_profile.date + timedelta(settings.NEW_TIME_LENGTH):
                self.is_new = False
        super(GuideCore, self).save(*args, **kwargs)

def update_price(obj, **kwargs):
    dict = obj.guide.PaymentModels.aggregate(sum=Sum('amount'), avg=Avg('amount'), count=Count('id'))
    if not dict['count']:
        dict['avg'] = 0
        dict['sum'] = 0
    obj.guide.full_day_price = dict['sum']
    obj.guide.search_price = dict['avg']*(dict['count']/float(2))
    obj.guide.save(force_update=True)

@receiver(post_save, sender=GuidePayment)
def new_price_handler(sender, created=False, instance=None, **kwargs):
    if created and instance:
        update_price(instance, **kwargs)

@receiver(post_delete, sender=GuidePayment)
def change_price_handler(sender, instance=None, **kwargs):
    if instance:
        update_price(instance, **kwargs)

@receiver(post_save, sender=GuideCore)
def update_profile(sender, created=False, instance=False, **kwargs):
    if created and instance:
        party = GuideParty.objects.get_or_create(guide=instance, defaults={'guide':instance})
        FAQ = GuideFAQ.objects.get_or_create(guide=instance, defaults={'guide':instance})
        details = ExtraDetails.objects.get_or_create(guide=instance, defaults={'guide':instance})
        home = BaseLocation.objects.get(city=instance.person.contact.city, state=instance.person.contact.state)
        if home.city != '!':
            instance.locations.add(home)
            instance.associate_water()
        instance.associate_land()
        instance.save(force_update=True)
        return True

# The following is the code to automatically add a calendar. Changes in the business model have made this
# unnecessary. Could be used as reference though
#            test = name_cal(self)
#            try:
#                Calendar.objects.get(name=test)
#            except ObjectDoesNotExist:
#                cal = Calendar(name=test, slug=test)
#                cal.save()
#                event = Event(title="Default Available", calendar=cal, creator=self.person, description="These are the default times that the guide is free. This can be altered by the guide at their discretion.")
#                event.start, event.end = datetime.combine(date.today(),time(8)), datetime.combine(date.today(),time(19))
#                event.rule = Rule.objects.get(name="Weekdays")
#                event.save()
