from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import datetime

class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.full_name})"

class ArduinoDevice(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    token = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='arduino_devices', null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # 🕒 Новые поля для настройки времени работы
    work_schedule_enabled = models.BooleanField(default=False, help_text="Включить расписание работы")
    work_start_time = models.TimeField(default=datetime.time(21, 0), help_text="Время начала работы (например, 21:00)")
    work_end_time = models.TimeField(default=datetime.time(9, 0), help_text="Время окончания работы (например, 09:00)")
    timezone_name = models.CharField(max_length=50, default='UTC', help_text="Временная зона устройства")

    # 🔧 Настройки чувствительности
    multi_sensor_required = models.BooleanField(default=True, help_text="Требовать сигнал от нескольких датчиков")
    sensor_count_threshold = models.IntegerField(default=2, help_text="Минимум датчиков для тревоги")
    time_window_seconds = models.IntegerField(default=60, help_text="Временное окно для проверки (секунды)")

    def __str__(self):
        return f"{self.name} ({self.user.username if self.user else 'Unclaimed'})"

    def is_work_time_now(self):
        """Проверяет, работает ли устройство сейчас по расписанию"""
        if not self.work_schedule_enabled:
            return True

        now = timezone.now()
        current_time = now.time()

        start_time = self.work_start_time
        end_time = self.work_end_time

        # Специальный случай: одинаковое время начала и окончания означает работу 24/7
        if start_time == end_time:
            return True

        # Если время начала больше времени окончания, значит работа через полночь
        if start_time > end_time:
            # Работа через полночь (например, с 21:00 до 09:00)
            return current_time >= start_time or current_time <= end_time
        else:
            # Обычное время работы (например, с 09:00 до 18:00)
            return start_time <= current_time <= end_time
    class Meta:
        verbose_name = "Device"
        verbose_name_plural = "Devices"