from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Autenticación
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    
    # Dashboard y solicitudes
    path('', views.dashboard, name='dashboard'),
    path('crear/', views.crear_solicitud, name='crear_solicitud'),
    path('solicitud/<int:pk>/', views.detalle_solicitud, name='detalle_solicitud'),
    path('solicitud/<int:pk>/editar/', views.editar_solicitud, name='editar_solicitud'),
    path('solicitud/<int:pk>/descargar-sql/', views.descargar_script_sql, name='descargar_script_sql'),
    
    # Solicitudes pendientes de script SQL
    path('pendientes-script/', views.solicitudes_pendientes_script, name='solicitudes_pendientes_script'),
    
    # Validación de estructura
    path('validar-estructura/', views.validar_estructura, name='validar_estructura'),
    
    # Estadísticas (solo admin)
    path('estadisticas/', views.estadisticas, name='estadisticas'),
]
