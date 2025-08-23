# sensor/models.py - Обновленные модели для умного сохранения

from django.db import models
from django.utils import timezone
from datetime import timedelta
from security.models import ArduinoDevice

class SensorData(models.Model):
    device = models.ForeignKey(ArduinoDevice, on_delete=models.CASCADE, related_name='sensor_data')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Данные с датчиков
    pir_motion = models.BooleanField(default=False)
    glass_break = models.BooleanField(default=False)
    door_open = models.BooleanField(default=False)
    panic_button = models.BooleanField(default=False)
    
    # Дополнительные метаданные
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    
    # 🧠 Новые поля для умной логики
    triggered_sensors_count = models.IntegerField(default=0, help_text="Количество сработавших датчиков")
    is_valid_alert = models.BooleanField(default=False, help_text="Прошла ли проверку на валидность")
    work_time_status = models.BooleanField(default=True, help_text="Было ли рабочее время при получении")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['is_valid_alert', '-timestamp']),
        ]
    
    def save(self, *args, **kwargs):
        # Считаем количество сработавших датчиков
        self.triggered_sensors_count = sum([
            self.pir_motion,
            self.glass_break, 
            self.door_open,
            self.panic_button
        ])
        
        # Проверяем рабочее время
        self.work_time_status = self.device.is_work_time_now()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.device.name} - {self.timestamp} ({'Valid' if self.is_valid_alert else 'Pending'})"

class SensorBuffer(models.Model):
    """Временный буфер для накопления сигналов датчиков за определенное время"""
    device = models.ForeignKey(ArduinoDevice, on_delete=models.CASCADE, related_name='sensor_buffer')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Буферизованные данные
    pir_motion = models.BooleanField(default=False)
    glass_break = models.BooleanField(default=False)
    door_open = models.BooleanField(default=False)
    panic_button = models.BooleanField(default=False)
    
    
    # Статус обработки
    is_processed = models.BooleanField(default=False)
    created_alert = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Buffer {self.device.name} - {self.timestamp}"

class Alert(models.Model):
    ALERT_TYPES = [
        ('motion', 'Обнаружено движение'),
        ('glass', 'Разбитие стекла'),
        ('door', 'Открытие двери'),
        ('panic', 'Паническая кнопка'),
        ('multi_sensor', 'Множественное срабатывание'),  # Новый тип
    ]
    
    device = models.ForeignKey(ArduinoDevice, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=15, choices=ALERT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_acknowledged = models.BooleanField(default=False)
    sensor_data = models.ForeignKey(SensorData, on_delete=models.CASCADE, null=True, blank=True)
    
    # Информация о владельце и адресе
    device_name = models.CharField(max_length=100)
    device_address = models.CharField(max_length=255, blank=True, null=True)
    owner_id = models.IntegerField()
    owner_username = models.CharField(max_length=150)
    owner_full_name = models.CharField(max_length=150)
    owner_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # 🔥 Новые поля для расширенной информации
    triggered_sensors = models.JSONField(default=list, help_text="Список сработавших датчиков")
    sensors_count = models.IntegerField(default=1, help_text="Количество сработавших датчиков")
    confidence_level = models.CharField(
        max_length=10, 
        choices=[('low', 'Низкая'), ('medium', 'Средняя'), ('high', 'Высокая')],
        default='medium'
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['is_acknowledged', '-timestamp']),
            models.Index(fields=['alert_type', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.device_name} - {self.get_alert_type_display()} - {self.timestamp}"
    
    def save(self, *args, **kwargs):
        # Автоматически заполняем информацию об устройстве и владельце при создании
        if not self.pk and self.device:
            self.device_name = self.device.name or 'Unnamed Device'
            self.device_address = self.device.address
            if self.device.user:
                self.owner_id = self.device.user.id
                self.owner_username = self.device.user.username
                self.owner_full_name = self.device.user.full_name
                self.owner_phone = self.device.user.phone_number
        super().save(*args, **kwargs)