from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Solicitud, HistorialEstado, Comentario

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ['id', 'tipo_solicitud', 'usuario', 'estado', 'fecha_creacion']
    list_filter = ['tipo_solicitud', 'estado', 'fecha_creacion']
    search_fields = ['usuario__username', 'descripcion']
    readonly_fields = ['fecha_creacion']

@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'estado_anterior', 'estado_nuevo', 'usuario_cambio', 'fecha_cambio']
    list_filter = ['estado_anterior', 'estado_nuevo', 'fecha_cambio']

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'usuario', 'fecha_creacion']
    list_filter = ['fecha_creacion']
