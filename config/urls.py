"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

# Handlers de error personalizados
handler403 = 'web.views.permission_denied_view'
handler404 = 'web.views.page_not_found_view'
handler500 = 'web.views.server_error_view'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('web/select2/', include('django_select2.urls')),
    path("web/api/auth/", include("usuarios_api.urls")),
    path("web/api/catalogos/", include("catalogos_api.urls")),
    path("web/api/denuncias/", include("denuncias_api.urls")),
    path("web/api/faq/", include("faq_api.urls")),
    path("web/api/chatbot/", include("chatbot_api.urls")),
    path("web/api/notificaciones/", include("notificaciones.urls")),
    
    #rutas que se topo, se les aumento web/ para probar si el apuntador vale

    path("web/", include("web.urls")),
    path('', RedirectView.as_view(url='/web/', permanent=True)),

]

# Servir archivos estáticos y media (desarrollo y testing con DEBUG=False)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
