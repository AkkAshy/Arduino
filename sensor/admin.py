from django.contrib import admin
from .models import SensorData, Alert

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('device', 'timestamp', 'pir_motion', 'glass_break', 'door_open', 'panic_button')
    list_filter = ('timestamp', 'device')
    readonly_fields = ('timestamp',)

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('device_name', 'alert_type', 'timestamp', 'owner_username', 'is_acknowledged')
    list_filter = ('alert_type', 'is_acknowledged', 'timestamp', 'owner_username')
    readonly_fields = ('timestamp', 'device_name', 'device_address', 'owner_username', 'owner_full_name', 'owner_phone')
    search_fields = ('device_name', 'owner_username', 'owner_full_name')
    actions = ['mark_acknowledged']

    def mark_acknowledged(self, request, queryset):
        queryset.update(is_acknowledged=True)
    mark_acknowledged.short_description = "Пометить как обработанные"
