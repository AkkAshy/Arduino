from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.full_name})"



class ArduinoDevice(models.Model):
    name = models.CharField(max_length=100)
    token = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='arduino_devices')
    address = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"
