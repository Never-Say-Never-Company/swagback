from django.contrib import admin
from django.urls import path
from django.http import HttpResponse

from nsnapp.views import (
    save_data,
    get_project_per_period,
    get_project_per_author,
    get_project_per_period_and_author,
    paginate_date,
    list_user_by_Id,
    list_users,
    count_issues_grouped_by_project,
    count_issues_by_user_and_total_hours,
    save_developer_rates,
    list_developer_rates,
    list_projects,
)


def home(request):
    return HttpResponse("API Swag está no ar 🚀")


urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("base_update", save_data),
    path("developer-rates/save/", save_developer_rates, name="save_developer_rates"),
    path("developer-rates/list/", list_developer_rates, name="list_developer_rates"),
    path(
        "project/project_per_period", get_project_per_period, name="project_per_period"
    ),
    path(
        "project/project_per_author", get_project_per_author, name="project_per_author"
    ),
    path(
        "project/project_per_period_and_author",
        get_project_per_period_and_author,
        name="project_per_period_and_author",
    ),
    path(
        "project/count_issues_grouped_by_project",
        count_issues_grouped_by_project,
        name="count_issues_grouped_by_project",
    ),
    path("project/paginate_date", paginate_date, name="paginate_date"),
    path("users/list_users", list_users, name="list_users"),
    path("users/<str:accountId>/", list_user_by_Id, name="list_user_by_accountId"),
    path("project/list_projects", list_projects, name="list_projects"),
    path(
        "project/count_issues_by_user_and_total_hours/<str:project_id>/",
        count_issues_by_user_and_total_hours,
        name="count_issues_by_user_and_total_hours_by_project",
    ),
]
