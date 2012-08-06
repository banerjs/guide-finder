from django.contrib import admin
from myproject.customer.models import CustomerCore, ContactInfo, CustomerProfile, PictureGallery, Photograph

class CustomerCoreAdmin(admin.ModelAdmin):
    list_display = ('id', '__unicode__')
    list_display_links = ('__unicode__', 'id')
    ordering = ('id',)

class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'city', 'state', 'country')

admin.site.register(CustomerCore, CustomerCoreAdmin)
admin.site.register(ContactInfo, ContactInfoAdmin)
admin.site.register(CustomerProfile)
admin.site.register([PictureGallery, Photograph])
