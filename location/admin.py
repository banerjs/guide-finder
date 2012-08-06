from django.contrib import admin
from myproject.location.models import BaseLocation, Country, State

def update_water(modeladmin, request, queryset):
    for obj in queryset:
        for w in obj.WaterBodies.all():
            w.associate_locations()
update_water.short_description = "Update Water Bodies"

class BaseLocationAdmin(admin.ModelAdmin):
    actions = [update_water]
    list_display = ('city', 'state', 'country')
    list_editable = ('state',)
    ordering = ('country', 'state', 'city')

admin.site.register(BaseLocation, BaseLocationAdmin)
admin.site.register([Country, State])
