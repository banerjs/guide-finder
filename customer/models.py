import os, sys
import Image
import random
from Image import ANTIALIAS

from django.db import models
from django.db.models import F
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.conf import settings
from django.core.files import File
from django.core.exceptions import ValidationError, SuspiciousOperation, ObjectDoesNotExist
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

from myproject.custom import digits, GoogleLatLng, resize_image
from myproject.location.models import BaseLocation, State, Country

# Create your models here.

class ContactInfo(models.Model):
    address_line_1 = models.CharField(max_length=150, null=True, blank=True)
    address_line_2 = models.CharField(max_length=150, null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.ForeignKey(State, blank=True, null=True)
    country = models.ForeignKey(Country, blank=True, null=True)
    email = models.EmailField('Email Address', help_text="This is your ID for sign in by default", unique=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    main_phone = models.BigIntegerField(help_text="Enter a phone number (Numbers Only). Include a country code if outside the USA", null=True, blank=True)
    alternate_phone = models.BigIntegerField(blank=True, null=True, help_text="Enter an alternate phone number (Numbers only)")
    lat = models.FloatField(editable=False, default=1000.0)
    lng = models.FloatField(editable=False, default=1000.0)

    class Meta:
        verbose_name = "Contact Information"
        verbose_name_plural = "Contact Information"

    def __unicode__(self):
        if self.ParentInfo:
            return 'Contact Information for %s' % self.ParentInfo.full_name
        else:
            return 'Orphan Information No. %s' % self.id

    def clean(self):
        if self.main_phone and (digits(self.main_phone) < 7 or digits(self.main_phone) > 13):
            raise ValidationError("Please enter a valid main phone number.")
        if self.alternate_phone and (digits(self.alternate_phone) < 7 or digits(self.alternate_phone) > 13):
            raise ValidationError("Please enter a valid alternate phone number")
        if self.state and self.state.country != self.country:
            raise ValidationError("The entered state is not in the country indicated")
        if self.city and self.country:
            self.clean_location()
        else:
            raise ValidationError("Please enter a location")

    def clean_location(self):
        address_1 = self.address_line_1 if self.address_line_1 else ''
        state = self.state.name if self.state else ''
        address_2 = self.address_line_2 if self.address_line_2 else ''
        ncity, created = BaseLocation.objects.get_or_create(city=self.city, state__name=state, country=self.country,
                                                            defaults={'city':self.city,
                                                                      'state':self.state,
                                                                      'country':self.country})
        locQuery = GoogleLatLng()
        if not locQuery.requestLatLngJSON(address_1 + ', ' + address_2 + ', ' + self.city + ', ' + state + ', ' + self.country.abbr):
            if not locQuery.requestLatLngJSON(address_2 + ', ' + self.city + ', ' + state + ', ' + self.country.abbr):
                self.lat = ncity.lat
                self.lng = ncity.lng
            else:
                self.lat = locQuery.lat
                self.lng = locQuery.lng
        else:
            self.lat = locQuery.lat
            self.lng = locQuery.lng

    def save(self, *args, **kwargs):
        if self.city and self.country:
            self.clean_location()
        super(ContactInfo, self).save(*args, **kwargs)

class CustomerCore(models.Model):
    first_name = models.CharField(max_length=30)
    middle_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30)
    contact = models.OneToOneField(ContactInfo, related_name='ParentInfo', editable=False)
    profile = models.OneToOneField('CustomerProfile', related_name='CustomerMain', editable=False)
    user = models.OneToOneField(User, related_name='CustomerCore')
    is_guide = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = "Customer Primary Detail"
        ordering = ['first_name', 'middle_name', 'last_name']

    def save(self, *args, **kwargs):
        newcontact, created = ContactInfo.objects.get_or_create(ParentInfo__user=self.user,
                                                                defaults={'email':self.user.email})
        if created: self.contact = newcontact
        newprofile, created = CustomerProfile.objects.get_or_create(CustomerMain__user=self.user)
        if created: self.profile = newprofile
        super(CustomerCore, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return settings.PROFILE_URL + str(self.id) + '/'

    def get_pretty_url(self):
        return settings.DOMAIN + 'profiles/' + str(self.id) + '/' + slugify(self.full_name) + '/'

    def get_full_name(self):
        if self.middle_name:
            return u'%s %s %s' % (self.first_name, self.middle_name, self.last_name)
        else:
            return u'%s %s' % (self.first_name, self.last_name)

    def set_full_name(self, fullname):
        self.first_name, self.last_name = fullname.split()

    full_name = property(get_full_name, set_full_name)

    def __unicode__(self):
        return self.full_name
    
class CustomerProfile(models.Model):
    allow_text = models.BooleanField(default=False)
    fave_fish_guide = models.ManyToManyField('gprofile.GuideCore', verbose_name="Favorite Guides", blank=True, null=True, related_name='Fans')
    ntrips = models.IntegerField("Number of trips", blank=True, default=0, editable=False)
    date = models.DateField(auto_now_add=True)

    def __unicode__(self):
        if self.CustomerMain:
            return u'Profile for %s' % self.CustomerMain.full_name
        else:
            return u'Orphan Profile No. %s' % self.id

    def save(self, *args, **kwargs):
        #        if self.invites_sent < self.invites_accepted:
        #    raise SuspiciousOperation
        super(CustomerProfile, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Customer Profile Information"

class PictureGallery(models.Model):
    owner_profile = models.ForeignKey(CustomerProfile, related_name="Galleries")
    description = models.CharField(max_length=500, blank=True, null=True)
    creation_date = models.DateField(auto_now_add=True)
    num_photos = models.IntegerField(editable=False, default=0)
    max_photos = models.IntegerField(editable=False, blank=True)
    profile_pic = models.ForeignKey('Photograph', blank=True, null=True, related_name='Album')

    class Meta:
        verbose_name = "Picture Gallery"
        verbose_name_plural = "Picture Galleries"

    def __unicode__(self):
        return 'Picture Gallery for %s' % self.owner_profile.CustomerMain.full_name

    def save(self, *args, **kwargs):
        try:
            if self.owner_profile.CustomerMain.is_guide:
                self.max_photos = 20
            else:
                self.max_photos = 10
        except ObjectDoesNotExist:
            self.max_photos = 10
        if self.num_photos > self.max_photos:
            raise Exception("Photo capacity reached")
        super(PictureGallery, self).save(*args, **kwargs)

    def add_profile(self, photo):
        self.profile_pic = photo
        self.save(force_update=True)

    def remove_profile(self):
        self.profile_pic = None
        self.save(force_update=True)

    def get_gallery_root(self):
        return 'users/' + str(self.Owner.CustomerMain.id) + '/gallery/' + str(self.id) + '/'

    def get_absolute_url(self):
        return settings.PROFILE_URL + str(self.Owner.CustomerMain.id) + '/gallery/' + str(self.id) + '/'

class Photograph(models.Model):
    gallery = models.ForeignKey(PictureGallery, related_name='Photos')
    title = models.CharField(help_text="Give your photo a title", max_length=30)
    summary = models.CharField(max_length=700, blank=True, default='', help_text="Give your photo a summary (optional)")
    date = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='temp/photos/', help_text="Maximum resolution: 800x600. Larger images will be resized")
    thumb = models.ImageField(upload_to='temp/photos/', editable=False)

    class Meta:
        ordering = ['gallery', '-date']

    def __unicode__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.gallery.num_photos = self.gallery.Photos.count()
        self.gallery.save()
        try:
            this = Photograph.objects.get(id=self.id)
            if this.image != self.image:
                this.image.delete()
        except:
            pass
        try:
            if this.thumb != self.thumb:
                this.thumb.delete()
        except:
            pass
        try:
            if self.image and self.thumb:
                max_size = (500, 400)
                t_size = (500, 60)
        except:
            pass
        else:
            resize_image(self.image, max_size)
            resize_image(self.thumb, t_size)
        super(Photograph, self).save(*args, **kwargs)

@receiver(post_save, sender=CustomerProfile)
def make_gallery(sender, created=False, instance=None, **kwargs):
    if created and instance and not instance.Galleries.all():
        gallery = PictureGallery()
        gallery.owner_profile = instance
        gallery.save(force_insert=True)

@receiver(post_save, sender=Photograph)
def order_images(sender, created=False, instance=None,**kwargs):
    if created and instance:
        max_size = (500, 400)
        t_size = (500, 60)
        old_path = instance.image
        name = str(instance.image).split('/')[-1]
        im = Image.open(settings.MEDIA_ROOT + str(instance.image))
        im.thumbnail(max_size, ANTIALIAS)
        try:
            os.makedirs(settings.MEDIA_ROOT + instance.gallery.get_gallery_root())
        except OSError, IOError:
            pass
        while os.path.exists(settings.MEDIA_ROOT + instance.gallery.get_gallery_root() + name):
            splice = name.split('.')
            name = splice[0]+ '_' + str(random.randint(0,9)) + '.' + splice[-1]
        instance.image = instance.gallery.get_gallery_root() + name
        im.save(settings.MEDIA_ROOT + str(instance.image))
        im.thumbnail(t_size, ANTIALIAS)
        name = name.split('.')[0] + '.thumbnail'
        instance.thumb = instance.gallery.get_gallery_root() + name
        im.save(settings.MEDIA_ROOT + str(instance.thumb), "JPEG")
        os.remove(settings.MEDIA_ROOT + str(old_path))
        instance.save()

@receiver(pre_delete, sender=Photograph)
def clean_images(sender, instance=None, **kwargs):
    if instance:
        os.remove(settings.MEDIA_ROOT + str(instance.image))
        os.remove(settings.MEDIA_ROOT + str(instance.thumb))

@receiver(post_save, sender=User)
def make_customer(sender, created=False, instance=None, **kwargs):
    if created and instance:
        customer = CustomerCore(user=instance)
        if instance.first_name: customer.first_name = instance.first_name
        else: customer.first_name = ' '
        if instance.last_name: customer.last_name = instance.last_name
        else: customer.last_name = ' '
        customer.save(force_insert=True)
