from django.urls import path
from . import views

urlpatterns = [
    # Main assessment endpoint
    path('api/trips/', views.create_trip, name='create_trip'),
    path('api/trips/list/', views.trip_list, name='trip_list'),
    path('api/trips/<int:trip_id>/', views.get_trip, name='get_trip'),
    path('api/geocode/autocomplete/', views.geocode_autocomplete, name='geocode_autocomplete'),

]
