from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from nsnapp.views import get_users, list_user_by_Id, list_users, save_data, get_project_per_period, get_project_per_author

def home(request):
    return HttpResponse("API Swag está no ar 🚀")

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('project/save_project', save_data),
    path('project/project_per_period', get_project_per_period),
    path('project/project_per_author', get_project_per_author),
    path('users/save_users', get_users, name='get_users'),
    path('users/list_users', list_users, name='list_users'),
    path('users/<str:accountId>/', list_user_by_Id, name='list_user_by_accountId')
]
