from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ArduinoDevice

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'full_name', 'phone_number', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'full_name', 'phone_number')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'full_name', 'phone_number', 'password1', 'password2'),
        }),
    )

class ArduinoDeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'token', 'user', 'is_active', 'work_schedule_enabled', 'multi_sensor_required', 'created_at')
    list_filter = ('is_active', 'work_schedule_enabled', 'multi_sensor_required', 'created_at')
    search_fields = ('name', 'token', 'user__username', 'address')
    list_editable = ('is_active', 'work_schedule_enabled', 'multi_sensor_required')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'token', 'user', 'address', 'is_active')
        }),
        ('Work Schedule', {
            'fields': ('work_schedule_enabled', 'work_start_time', 'work_end_time', 'timezone_name'),
            'classes': ('collapse',)
        }),
        ('Sensor Settings', {
            'fields': ('multi_sensor_required', 'sensor_count_threshold', 'time_window_seconds'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Редактирование существующего объекта
            return ['token', 'created_at']
        return ['created_at']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(ArduinoDevice, ArduinoDeviceAdmin)