from django.http import HttpResponse, JsonResponse

# Reuse initiate_payment from the listings app to keep logic in one place
try:
    from listings.views import initiate_payment  # noqa: E402
except Exception:
    # Fallback stub if listings.views isn't available when running lightweight checks
    def initiate_payment(request):
        return JsonResponse({"detail": "initiate_payment not available"}, status=500)


def health_check(request):
    """Simple health check for the project root."""
    return HttpResponse("OK", content_type="text/plain")
