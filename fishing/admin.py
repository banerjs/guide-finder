from django.contrib import admin
from myproject.fishing.models import WaterBody, GeoRelations, Fish, FishingType, BoatBrand, GuideFAQ, ShadowGuide
from myproject.fishing.models import LureBrand, RodBrand, ReelBrand, LineBrand, BaitBrand, ExtraDetails
from myproject.fishing.models import GuideBoat, EngineBrand, GuideEngine

def update_locations(modeladmin, request, queryset):
    for obj in queryset:
        obj.associate_locations()
update_locations.short_description = "Reassociate locations"

class WaterBodyAdmin(admin.ModelAdmin):
    actions = [update_locations]
    list_display = ('__unicode__', 'state', 'country')

class FishAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'water_type', 'verified')
    list_editable = ('verified',)

class FishingTypeAdmin(admin.ModelAdmin):
    list_display = ('method', 'verified')
    list_editable = ('verified',)

class GeoRelationsAdmin(admin.ModelAdmin):
    list_display = ('location', 'water', 'verified')
    list_editable = ('verified',)
    list_display_links = ('location', 'water')

class ShadowGuideAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'phone_number', 'email')
    list_editable = ('phone_number', 'email')

class GuideFAQAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'child_friendly', 'alcohol_allowed', 'food_provided', 'capture_release',
                    'state_certified', 'CG_certified', 'handicap_friendly', 'personal_equipment',
                    'lost_tackle', 'fillet_services', 'taxidermy_services', 'allow_international')

class ExtraDetailsAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'good_attitude')

class BrandAdmin(admin.ModelAdmin):
    filter_horizontal = ('guide',)

admin.site.register(WaterBody, WaterBodyAdmin)
admin.site.register(Fish, FishAdmin)
admin.site.register(FishingType, FishingTypeAdmin)
admin.site.register(GeoRelations, GeoRelationsAdmin)
admin.site.register(ShadowGuide, ShadowGuideAdmin)
admin.site.register(GuideFAQ, GuideFAQAdmin)
admin.site.register(ExtraDetails, ExtraDetailsAdmin)
admin.site.register([LureBrand, RodBrand, ReelBrand, LineBrand, BaitBrand], BrandAdmin)
admin.site.register([BoatBrand, GuideBoat, EngineBrand, GuideEngine])
