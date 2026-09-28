from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("School role", {"fields": ("role", "phone_number")}),
    )
    list_display = ("username", "email", "role", "is_staff")
    list_filter = DjangoUserAdmin.list_filter + ("role",)
