from django.contrib import admin
from myproject.tdetails.models import Trip, CustomerReview, GuideReview, GuideRecommend, Referral

admin.site.register([Trip, CustomerReview, GuideReview, GuideRecommend, Referral])
