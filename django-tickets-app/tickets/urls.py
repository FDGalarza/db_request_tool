from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Autenticación - SIN REGISTRO PÚBLICO
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard y solicitudes
    path('', views.dashboard, name='dashboard'),
    path('crear/', views.crear_solicitud, name='crear_solicitud'),
    path('solicitud/<int:pk>/', views.detalle_solicitud, name='detalle_solicitud'),
    path('solicitud/<int:pk>/editar/', views.editar_solicitud, name='editar_solicitud'),
    path('solicitud/<int:pk>/descargar-sql/', views.descargar_script_sql, name='descargar_script_sql'),
    
    # Proyectos
    path('proyectos/', views.lista_proyectos, name='lista_proyectos'),
    path('proyectos/crear/', views.crear_proyecto, name='crear_proyecto'),
    path('proyectos/<int:pk>/', views.detalle_proyecto, name='detalle_proyecto'),
    path('proyectos/<int:pk>/editar/', views.editar_proyecto, name='editar_proyecto'),
    path('proyectos/<int:pk>/eliminar/', views.eliminar_proyecto, name='eliminar_proyecto'),
    path('proyectos/<int:pk>/miembros/', views.asignar_miembros_proyecto, name='asignar_miembros_proyecto'),
    
    # Módulo de Administración (Solo para admins)
    path('admin-panel/', views.panel_administracion, name='panel_administracion'),
    path('admin-panel/usuarios/', views.gestionar_usuarios, name='gestionar_usuarios'),
    path('admin-panel/usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('admin-panel/usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    path('admin-panel/usuarios/<int:pk>/inactivar/', views.inactivar_usuario, name='inactivar_usuario'),  # CAMBIADO
    
    # Solicitudes pendientes de script SQL
    path('pendientes-script/', views.solicitudes_pendientes_script, name='solicitudes_pendientes_script'),
    
    # Validación de estructura
    path('validar-estructura/', views.validar_estructura, name='validar_estructura'),
    
    # Estadísticas (solo admin)
    path('estadisticas/', views.estadisticas_avanzadas, name='estadisticas_avanzadas'),

    # Creación y descarga de plantilals
    path("plantillas/", views.lista_plantillas, name="lista_plantillas"),
    path("plantillas/descargar/<str:nombre_archivo>/", views.descargar_plantilla, name="descargar_plantilla"),
]
