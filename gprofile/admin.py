from django.contrib import admin
from myproject.gprofile.models import GuidePayment, GuideParty, GuideProfile, GuideCore
from myproject.customer.models import CustomerCore

class GuideCoreAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'company')
    filter_horizontal = ('locations', 'fish', 'methods', 'boat_brands', 'waterbodies')

#    def formfield_for_foreignkey(self, db_field, request, **kwargs):
#        if db_field.name == "person":
#            kwargs["queryset"] = CustomerCore.objects.filter(is_guide=False)
#        return super(GuideCoreAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

class GuidePaymentAdmin(admin.ModelAdmin):
    list_display = ('guide', 'start_time', 'end_time')
    ordering = ('guide', '-start_time')

class GuidePartyAdmin(admin.ModelAdmin):
    list_display = ('guide', 'avg_party', 'max_party', 'min_party')

admin.site.register(GuideCore, GuideCoreAdmin)
admin.site.register(GuidePayment, GuidePaymentAdmin)
admin.site.register(GuideParty, GuidePartyAdmin)
admin.site.register(GuideProfile)
