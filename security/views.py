from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserRegistrationSerializer

class UserRegistrationView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .serializers import ArduinoDeviceTokenSerializer
from .models import ArduinoDevice

class ArduinoCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ArduinoDeviceTokenSerializer(data={}, context={'request': request})
        if serializer.is_valid():
            device = serializer.save(user=request.user)
            return Response({'token': device.token}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from .models import ArduinoDevice
from .serializers import ArduinoDeviceUpdateSerializer

class ArduinoUpdateView(UpdateAPIView):
    queryset = ArduinoDevice.objects.all()
    serializer_class = ArduinoDeviceUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)



from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from .models import ArduinoDevice
from .serializers import ArduinoDeviceSerializer

class ArduinoListView(ListAPIView):
    serializer_class = ArduinoDeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ArduinoDevice.objects.filter(user=self.request.user)


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import ArduinoDevice

@api_view(['POST'])
def authorize_arduino(request):
    token = request.data.get('token')
    if not token:
        return Response({'error': 'Missing token'}, status=status.HTTP_400_BAD_REQUEST)

    device = ArduinoDevice.objects.filter(token=token, is_active=True).first()
    if not device:
        return Response({'error': 'Invalid or inactive device'}, status=status.HTTP_401_UNAUTHORIZED)

    return Response({'status': 'authorized', 'device': device.name}, status=status.HTTP_200_OK)



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import ArduinoDevice

class ArduinoClaimView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        if not token or len(token) != 16:
            return Response({'error': 'Invalid or missing token'}, status=status.HTTP_400_BAD_REQUEST)

        device = ArduinoDevice.objects.filter(token=token, user__isnull=True, is_active=True).first()
        if not device:
            return Response({'error': 'Device not found or already claimed'}, status=status.HTTP_404_NOT_FOUND)

        device.user = request.user
        device.save()

        return Response({'message': 'Device successfully linked', 'device_id': device.id}, status=status.HTTP_200_OK)
