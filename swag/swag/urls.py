from django.contrib import admin
from django.urls import path  # <- path precisa estar aqui
from django.http import HttpResponse
from nsnapp.views import save_data, get_project_per_period, get_project_per_author

# view simples para a raiz
def home(request):
    return HttpResponse("API Swag está no ar 🚀")

urlpatterns = [
    path('', home),  # rota para a raiz
    path('admin/', admin.site.urls),
    path('project/save_project', save_data),
    path('project/project_per_period', get_project_per_period),
    path('project/project_per_author', get_project_per_author),
]
