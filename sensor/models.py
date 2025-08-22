from django.db import models
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
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.device.name} - {self.timestamp}"

class Alert(models.Model):
    ALERT_TYPES = [
        ('motion', 'Обнаружено движение'),
        ('glass', 'Разбитие стекла'),
        ('door', 'Открытие двери'),
        ('panic', 'Паническая кнопка'),
    ]
    
    device = models.ForeignKey(ArduinoDevice, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_acknowledged = models.BooleanField(default=False)
    sensor_data = models.ForeignKey(SensorData, on_delete=models.CASCADE, null=True, blank=True)
    
    # Сохраняем информацию о владельце и адресе на момент срабатывания
    device_name = models.CharField(max_length=100)
    device_address = models.CharField(max_length=255, blank=True, null=True)
    owner_id = models.IntegerField()  # ID владельца
    owner_username = models.CharField(max_length=150)
    owner_full_name = models.CharField(max_length=150)
    owner_phone = models.CharField(max_length=20, blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.device_name} - {self.get_alert_type_display()} - {self.timestamp}"
    
    def save(self, *args, **kwargs):
        # Автоматически заполняем информацию об устройстве и владельце при создании
        if not self.pk and self.device:
            self.device_name = self.device.name
            self.device_address = self.device.address
            self.owner_id = self.device.user.id
            self.owner_username = self.device.user.username
            self.owner_full_name = self.device.user.full_name
            self.owner_phone = self.device.user.phone_number
        super().save(*args, **kwargs)
