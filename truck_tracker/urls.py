from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_health(request):
    """Health check endpoint"""
    return JsonResponse({'status': 'ok', 'message': 'HOS ELD API is running'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('health/', api_health, name='api_health'),
]