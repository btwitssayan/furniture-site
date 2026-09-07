from .models import Category


def nav_categories(request):
    """Categories for the shared footer links in base.html."""
    return {"nav_categories": Category.objects.filter(is_active=True)}
