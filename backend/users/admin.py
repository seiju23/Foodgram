from django.contrib import admin

from . import models


class UserAdmin(admin.ModelAdmin):
    list_display = (
        'username', 'pk', 'email', 'password', 'first_name', 'last_name',
    )
    list_editable = ('password', )
    list_filter = ('username', 'email')
    search_fields = ('username', 'email')
    empty_value_display = '???'


class FollowAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'author')
    list_editable = ('user', 'author')
    empty_value_display = '???'


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Follow, FollowAdmin)
