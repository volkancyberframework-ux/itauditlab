from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods


@require_http_methods(['GET', 'POST'])
def page(request):
    """Retire old shared links without accepting new waitlist registrations."""
    return redirect('landing:home')
