from django.http import JsonResponse
from django.urls import path


def health_check(request):
    return JsonResponse({"status": "healthy"})


