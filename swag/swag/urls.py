from django.contrib import admin
from django.urls import path
from django.http import HttpResponse

# ==================================
# 1. IMPORTS DAS VIEWS DE DADOS (PROTEGIDAS)
# ==================================
from nsnapp.views import (
    save_data, 
    get_project_per_period, 
    get_project_per_author, 
    get_project_per_period_and_author,
    list_user_by_Id, 
    list_users, 
    count_issues_grouped_by_project,
    count_issues_by_user_and_total_hours
)

# ==================================
# 2. IMPORTS DAS VIEWS DE AUTENTICAÇÃO (NOVAS ROTAS)
# ==================================
from nsnapp.auth_views import register_user, jwt_login_local 


def home(request):
    return HttpResponse("API Swag está no ar 🚀")

urlpatterns = [
    # ROTA RAIZ E ADMIN
    path('', home),
    path('admin/', admin.site.urls),

    # ==================================
    # ROTAS DE AUTENTICAÇÃO E CADASTRO
    # ==================================
    # 1. Rota para CADASTRO de novo usuário no MongoDB
    path('api/auth/register/', register_user, name='register'),
    
    # 2. Rota para LOGIN local que retorna o JWT
    path('api/auth/login/', jwt_login_local, name='jwt_login_local'),
    
    # ==================================
    # ROTAS DE DADOS / API
    # ==================================
    
    # Rota de atualização de dados (Geralmente acionada via credenciais Jira/token)
    path('api/data/update/', save_data, name='save_data'),
    
    # BUSCAS POR PERÍODO / AUTOR (Estas devem estar protegidas pelo @jwt_required)
    path('api/projects/period/', get_project_per_period, name='project_per_period'),
    path('api/projects/author/', get_project_per_author, name='project_per_author'),
    path('api/projects/period_and_author/', get_project_per_period_and_author, name='project_per_period_and_author'),
    
    # ROTAS DE USUÁRIOS
    path('api/users/', list_users, name='list_users'),
    path('api/users/<str:accountId>/', list_user_by_Id, name='list_user_by_accountId'),
    
    # ROTAS DE AGREGAÇÃO E MÉTRICAS
    path('api/metrics/issues_by_project/', count_issues_grouped_by_project, name='count_issues_grouped_by_project'),
    path('api/metrics/hours_by_user/', count_issues_by_user_and_total_hours, name='count_issues_by_user_and_total_hours')
]