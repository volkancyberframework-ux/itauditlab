from django.shortcuts import render


def privacy(request):
    return render(request, 'mobile_api/store_information.html', {'privacy': True})


def support(request):
    return render(request, 'mobile_api/store_information.html', {'privacy': False})
