from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "healthy"})


def root_view(request):
    return JsonResponse(
        {"status": "success", "status_code": 200, "message": "Welcome to the API root."}
    )
