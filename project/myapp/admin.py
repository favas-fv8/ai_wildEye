from django.contrib import admin

# Register your models here.

from .models import user_login, user_details

from.models import user_login ,category_settings ,image_pool 
from.models import user_details, test_history   


admin.site.register(user_login)
admin.site.register(user_details)
admin.site.register(category_settings) 
admin.site.register(image_pool)

admin.site.register(test_history) 
