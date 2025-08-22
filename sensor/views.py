from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import SensorData, Alert
from .serializers import SensorDataSerializer, AlertSerializer
from security.models import ArduinoDevice

class SensorDataView(APIView):
    def post(self, request):
        serializer = SensorDataSerializer(data=request.data)
        if serializer.is_valid():
            sensor_data = serializer.save()
            
            # Проверяем триггеры и создаем оповещения при необходимости
            self.check_alerts(sensor_data)
            
            return Response({"status": "data received"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def check_alerts(self, sensor_data):
        # Создаем оповещения для активных датчиков
        if sensor_data.pir_motion:
            self.create_alert(sensor_data, 'motion')
        
        if sensor_data.glass_break:
            self.create_alert(sensor_data, 'glass')
        
        if sensor_data.door_open:
            self.create_alert(sensor_data, 'door')
        
        if sensor_data.panic_button:
            self.create_alert(sensor_data, 'panic')
    
    def create_alert(self, sensor_data, alert_type):
        # Создаем оповещение с полной информацией
        alert = Alert.objects.create(
            device=sensor_data.device,
            alert_type=alert_type,
            sensor_data=sensor_data
        )
        # Информация о владельце и адресе автоматически заполнится в методе save модели Alert

class AlertListView(APIView):
    def get(self, request):
        # Получаем только оповещения для устройств текущего пользователя
        user_alerts = Alert.objects.filter(owner_id=request.user.id)
        serializer = AlertSerializer(user_alerts, many=True)
        return Response(serializer.data)

class AcknowledgeAlertView(APIView):
    def post(self, request, alert_id):
        try:
            alert = Alert.objects.get(id=alert_id, owner_id=request.user.id)
            alert.is_acknowledged = True
            alert.save()
            return Response({"status": "alert acknowledged"})
        except Alert.DoesNotExist:
            return Response({"error": "Alert not found"}, status=status.HTTP_404_NOT_FOUND)
