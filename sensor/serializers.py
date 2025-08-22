from rest_framework import serializers
from .models import SensorData, Alert

class SensorDataSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)
    
    class Meta:
        model = SensorData
        fields = ['token', 'pir_motion', 'glass_break', 'door_open', 'panic_button', 'temperature', 'humidity']
    
    def validate(self, data):
        token = data.pop('token')
        try:
            device = ArduinoDevice.objects.get(token=token, is_active=True)
        except ArduinoDevice.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive device token")
        
        data['device'] = device
        return data

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            'id', 'alert_type', 'timestamp', 'is_acknowledged',
            'device_name', 'device_address',
            'owner_username', 'owner_full_name', 'owner_phone'
        ]
        read_only_fields = ['id', 'timestamp']
