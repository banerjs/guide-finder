from django.db import models
from django.db.models import F, Max, Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.template.defaultfilters import slugify

from myproject.customer.models import CustomerCore
from myproject.gprofile.models import GuideCore
from myproject.location.models import BaseLocation

# Create your models here.

class Referral(models.Model):
    guide = models.ForeignKey(GuideCore, related_name='Referrals')
    date_created = models.DateField(auto_now_add=True)
    rand_id = models.SlugField(editable=False, default=None, unique=True)
    date_accepted = models.DateField(blank=True, null=True)
    is_accepted = models.BooleanField(editable=False, default=False)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()

    class Meta:
        ordering = ['guide', 'first_name', 'last_name']

    def __unicode__(self):
        return "%s %s for %s" % (self.first_name, self.last_name, self.guide)

    def save(self, *args, **kwargs):
        self.guide.profile.num_referrals = F('num_referrals') + 1
        self.guide.profile.save(fore_update=True)
        if not self.rand_id:
            self.rand_id = slugify(str(self.guide.id*3) +
                                   str(self.id*5)+
                                   self.date_created.strftime("\%m\%Y\%d"))
        super(Referral, self).save(*args, **kwargs)

    def confirm_accept(self):
        self.is_accepted = True
        self.save(force_update=True)

class Trip(models.Model):
    customer = models.ForeignKey(CustomerCore, related_name='Adventure')
    guide = models.ForeignKey(GuideCore, related_name='Tours')
    trip_start_date = models.DateTimeField()
    trip_end_date = models.DateTimeField()
    location = models.ForeignKey(BaseLocation, related_name='Trips')
    num_people = models.IntegerField("Number of Guests")
    price = models.DecimalField(max_digits=17, decimal_places=2, default=0.00, blank=True, editable=False)
    paid = models.BooleanField(default=False, blank=True, editable=False)
    is_reviewed = models.BooleanField(default=False, blank=True, editable=False)
    rand_id = models.SlugField(editable=False, default=None, unique=True)

    class Meta:
        ordering = ['-trip_start_date']
        unique_together = ('customer', 'guide', 'trip_start_date', 'trip_end_date')

    def __unicode__(self):
        return '%s guiding %s from %s onwards' % (self.guide.person.full_name, self.customer.full_name, self.trip_start_date.strftime('%d-%m-%Y'))

    def clean(self):
        if self.trip_end_date < self.trip_start_date:
            raise ValidationError("Start Date cannot be after the End Date")
        if self.num_people < 1:
            raise ValidationError("The number of people cannot be less than 1")

    def save(self, *args, **kwargs):
        if not self.rand_id:
            self.rand_id = slugify(str(self.customer.id) +
                                   str(self.guide.id) +
                                   self.trip_start_date.strftime('\%m\%Y\%d') +
                                   self.trip_end_date.strftime('\%Y\%d\%m') +
                                   str(self.location.id))
        super(Trip, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return settings.DOMAIN+'review/'+self.rand_id+'/'

    def set_price(self, amt):
        self.price = amt
        self.save(force_update=True)

    def confirm_pay(self):
        self.paid = True
        self.save(force_update=True)

class BaseReview(models.Model):
    comment = models.CharField(max_length=3000)
    submit_date = models.DateField(auto_now_add=True)
    is_removed = models.BooleanField(blank=True, default=False)

    def remove_post(self):
        self.is_removed = True
        super(BaseReview, self).save(force_update=True)

    class Meta:
        abstract = True

class CustomerReview(BaseReview):
    trip = models.ForeignKey(Trip, unique=True, related_name='CustomerReview')
    recommend = models.BooleanField()
    is_responded = models.BooleanField(blank=True, default=False)

    class Meta:
        verbose_name = "Customer Submitted Review"
        ordering = ('submit_date',)

    def __unicode__(self):
        return '%s: %s' % (self.trip.customer.full_name, self.comment[:50])

    def clean(self):
        if self.trip.is_reviewed:
            raise ValidationError("You have already reviewed this trip")

    def save(self, *args, **kwargs):
        if not self.trip.is_reviewed:
            self.trip.is_reviewed = True
            self.trip.save(force_update=True)
            self.trip.guide.profile.num_recommends = F('num_recommends') + 1
            self.trip.guide.profile.save(force_update=True)
            super(CustomerReview, self).save(*args, **kwargs)
        else:
            raise Exception("A review has already been submitted")

class GuideReview(BaseReview):
    response = models.ForeignKey(CustomerReview, unique=True, related_name='GuideResponse')

    class Meta:
        verbose_name = "Guide Response"
        ordering = ('submit_date',)

    def __unicode__(self):
        return '%s: @%s' % (self.response.trip.guide.full_name, self.response.trip.customer.full_name)

    def clean(self):
        if self.response.is_responded:
            raise ValidationError("You have answered this response")

    def save(self, *args, **kwargs):
        if not self.response.is_responded:
            self.response.is_responded = True
            self.response.save(force_update=True)
            super(GuideReview, self).save(*args, **kwargs)
        else:
            raise Exception("A response has already been submitted")

class GuideRecommend(BaseReview):
    customer = models.ForeignKey(CustomerCore, related_name="Recommendation")
    guide = models.ForeignKey(GuideCore, related_name="Recommendations")
    recommend = models.BooleanField()

    def __unicode__(self):
        return '%s for %s' % (self.customer.full_name, self.guide.person.full_name)

    def clean(self):
        if self.customer == self.guide.person:
            raise ValidationError("You cannot review yourself")

    def save(self, *args, **kwargs):
        self.guide.profile.num_recommends = F('num_recommends') + 1
        self.guide.profile.save(force_update=True)
        super(GuideRecommend, self).save(*args, **kwargs)

@receiver(post_save, sender=Trip)
def update_profile(sender, created=False, instance=None, **kwargs):
    if created and instance:
        dict = obj.customer.Adventure.aggregate(num=Count('id'), date=Max('trip_end_date'))
        obj.customer.profile.ntrips = dict['num']
        try:
            obj.customer.profile.last_trip = Trip.objects.get(customer=obj, trip_end_date=dict['date'])
        except:
            obj.customer.profile.last_trip = None
        obj.customer.profile.save(force_update=True)
