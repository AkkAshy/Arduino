from django.urls import path
from .views import (
    UserRegistrationView,
    ArduinoCreateView,
    ArduinoUpdateView,
    ArduinoListView,
    authorize_arduino,
    ArduinoClaimView,
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user_register'),
    path('arduino/create/', ArduinoCreateView.as_view(), name='arduino_create'),
    path('arduino/<int:pk>/update/', ArduinoUpdateView.as_view(), name='arduino_update'),
    path('arduino/list/', ArduinoListView.as_view(), name='arduino_list'),
    path('arduino/auth/', authorize_arduino, name='arduino_auth'),
    path('arduino/claim/', ArduinoClaimView.as_view(), name='arduino_claim'),
]
