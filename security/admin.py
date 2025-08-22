from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ArduinoDevice

# 🔧 Настройка отображения CustomUser в админке
class CustomUserAdmin(UserAdmin):
    # Поля, которые отображаются в списке пользователей
    list_display = ('username', 'full_name', 'phone_number', 'is_staff')
    
    # Поля, по которым можно фильтровать
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    
    # Поля, по которым можно искать
    search_fields = ('username', 'full_name', 'phone_number')
    
    # Группировка полей при редактировании пользователя
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Поля при создании пользователя
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'full_name', 'phone_number', 'password1', 'password2'),
        }),
    )

# 🔧 Настройка отображения ArduinoDevice в админке
class ArduinoDeviceAdmin(admin.ModelAdmin):
    # Поля, которые отображаются в списке устройств
    list_display = ('name', 'token', 'user', 'address', 'is_active', 'created_at')
    
    # Поля, по которым можно фильтровать
    list_filter = ('is_active', 'created_at')
    
    # Поля, по которым можно искать
    search_fields = ('name', 'token', 'user__username', 'address')
    
    # Поля, которые можно редактировать прямо из списка
    list_editable = ('is_active',)
    
    # Автозаполнение slug (если бы было такое поле)
    # prepopulated_fields = {"slug": ("name",)}
    
    # Разбивка формы на секции
    fieldsets = (
        (None, {
            'fields': ('name', 'token', 'user', 'is_active')
        }),
        ('Additional Info', {
            'fields': ('address',),
            'classes': ('collapse',)  # Сворачиваем секцию по умолчанию
        }),
    )

# 📝 Регистрация моделей в админке
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(ArduinoDevice, ArduinoDeviceAdmin)
