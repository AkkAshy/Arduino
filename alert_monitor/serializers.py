# alert_monitor/serializers.py - Исправленная версия с полной информацией о датчиках

from rest_framework import serializers
from sensor.models import Alert, SensorData
from security.models import ArduinoDevice

class AlertMonitorSerializer(serializers.ModelSerializer):
    """Расширенный serializer для мониторинга тревог с полной информацией о датчиках"""
    device_info = serializers.SerializerMethodField()
    owner_info = serializers.SerializerMethodField()
    sensor_details = serializers.SerializerMethodField()
    sensor_states = serializers.SerializerMethodField()
    triggered_sensors_display = serializers.SerializerMethodField()
    time_elapsed = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            'id', 'alert_type', 'timestamp', 'is_acknowledged',
            'device_name', 'device_address',
            'owner_username', 'owner_full_name', 'owner_phone',
            'triggered_sensors', 'sensors_count', 'confidence_level',
            'device_info', 'owner_info', 'sensor_details',
            'sensor_states', 'triggered_sensors_display', 'time_elapsed'
        ]

    def get_device_info(self, obj):
        try:
            device = ArduinoDevice.objects.get(id=obj.device.id)
            return {
                'id': device.id,
                'name': device.name or 'Unnamed Device',
                'address': device.address or 'No address',
                'is_active': device.is_active,
                'created_at': device.created_at
            }
        except:
            return {
                'name': obj.device_name,
                'address': obj.device_address,
                'status': 'offline'
            }

    def get_owner_info(self, obj):
        return {
            'id': obj.owner_id,
            'username': obj.owner_username,
            'full_name': obj.owner_full_name,
            'phone': obj.owner_phone or 'No phone'
        }

    def get_sensor_details(self, obj):
        """Данные с датчиков (температура, влажность если есть)"""
        if obj.sensor_data:
            return {
                'temperature': obj.sensor_data.temperature,
                'humidity': obj.sensor_data.humidity,
            }
        return None

    def get_sensor_states(self, obj):
        """Полная информация о состоянии всех датчиков (true/false)"""
        # Если есть связанные данные датчиков, берем оттуда
        if obj.sensor_data:
            return {
                'pir_motion': obj.sensor_data.pir_motion,
                'glass_break': obj.sensor_data.glass_break,
                'door_open': obj.sensor_data.door_open,
                'panic_button': obj.sensor_data.panic_button
            }

        # Иначе восстанавливаем из triggered_sensors
        all_sensors = {
            'pir_motion': False,
            'glass_break': False,
            'door_open': False,
            'panic_button': False
        }

        # Устанавливаем true для сработавших датчиков
        for sensor in obj.triggered_sensors:
            if sensor in all_sensors:
                all_sensors[sensor] = True

        return all_sensors

    def get_triggered_sensors_display(self, obj):
        """Человекочитаемые названия только сработавших датчиков на узбекском"""
        sensor_names = {
            'pir_motion': '🚶 Harakat',
            'glass_break': '🔨 Shisha sinishi',
            'door_open': '🚪 Eshik ochilishi',
            'panic_button': '🚨 Favqulodda tugma'
        }
        return [sensor_names.get(sensor, sensor) for sensor in obj.triggered_sensors]

    def get_time_elapsed(self, obj):
        """Точное время с момента создания тревоги"""
        from django.utils import timezone

        now = timezone.now()
        elapsed = now - obj.timestamp

        # Общее количество секунд с момента создания
        total_seconds = int(elapsed.total_seconds())

        if total_seconds < 0:
            return "Hozir"
        elif total_seconds < 60:
            return f"{total_seconds} Soniya oldin"
        elif total_seconds < 3600:  # Меньше часа
            minutes = total_seconds // 60
            return f"{minutes} Daqiqa oldin"
        elif total_seconds < 86400:  # Меньше дня
            hours = total_seconds // 3600
            remaining_minutes = (total_seconds % 3600) // 60
            if remaining_minutes > 0:
                return f"{hours} Saot {remaining_minutes} Daqiqa oldin"
            else:
                return f"{hours} Soat oldin"
        else:  # Больше дня
            days = elapsed.days
            hours = (total_seconds % 86400) // 3600
            if hours > 0:
                return f"{days} Kun {hours} Soat oldin"
            else:
                return f"{days} Kun oldin"

class AlertStatsSerializer(serializers.Serializer):
    """Статистика тревог"""
    total_alerts = serializers.IntegerField()
    unacknowledged_alerts = serializers.IntegerField()
    alerts_today = serializers.IntegerField()
    alerts_by_type = serializers.DictField()
    most_active_device = serializers.CharField()
    latest_alert_time = serializers.DateTimeField()