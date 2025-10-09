from django.contrib import admin
from django.urls import path
from django.http import HttpResponse

from nsnapp.views import (
    save_data, 
    get_project_per_period, 
    get_project_per_author, 
    get_project_per_period_and_author,
    list_user_by_Id, 
    list_users, 
    count_issues_grouped_by_project,
    count_issues_by_user_and_total_hours,
    handle_chat_ia
)

def home(request):
    return HttpResponse("API Swag está no ar 🚀")

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('base_update', save_data),
    path('project/project_per_period_and_author', get_project_per_period_and_author),
    path('users/list_users', list_users, name='list_users'),
    path('users/<str:accountId>/', list_user_by_Id, name='list_user_by_accountId'),
    path('project/count_issues_grouped_by_project', count_issues_grouped_by_project, name='count_issues_grouped_by_project'),
    path('project/count_issues_by_user_and_total_hours', count_issues_by_user_and_total_hours, name='count_issues_by_user_and_total_hours'),
    
    path('ia/chat/', handle_chat_ia, name='handle_chat_ia'),
]