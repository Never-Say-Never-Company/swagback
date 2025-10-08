from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from nsnapp.views import save_data, get_project_per_period, get_project_per_author, get_project_per_period_and_author
from nsnapp.views import list_user_by_Id, list_users, save_data, get_project_per_period, get_project_per_author,count_issues_grouped_by_project,count_issues_by_user_and_total_hours
from swag.nsnapp.login_view import LoginView, UserListCreateView, UserRetrieveUpdateDestroyView

def home(request):
    return HttpResponse("API Swag está no ar 🚀")

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(), name='login'),
    path('users/', UserListCreateView.as_view(), name='user-list-create'),
    path('users/<pk>/', UserRetrieveUpdateDestroyView.as_view(), name='user-detail'),
    path('base_update', save_data),
    path('project/project_per_period_and_author', get_project_per_period_and_author),
    path('users/list_users', list_users, name='list_users'),
    path('users/<str:accountId>/', list_user_by_Id, name='list_user_by_accountId'),
    path('project/count_issues_grouped_by_project', count_issues_grouped_by_project, name='count_issues_grouped_by_project'),
    path('project/count_issues_by_user_and_total_hours', count_issues_by_user_and_total_hours, name='count_issues_by_user_and_total_hours')
]
