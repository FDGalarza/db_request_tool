from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class UserProfile(models.Model):
    ROLES = [
        ('dev', 'Ingeniero de Desarrollo'),
        ('db', 'Ingeniero de Bases de Datos'),
        ('devops', 'Ingeniero DevOps'),
        ('admin', 'Administrador'),
        ('lider', 'Líder de Proyecto'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLES, default='dev')
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

class ConfiguracionEstructuraExcel(models.Model):
    """Configuración de estructuras esperadas para archivos Excel"""
    tipo_solicitud = models.CharField(max_length=50, unique=True)
    estructura_json = models.TextField(help_text="JSON con la estructura esperada")
    descripcion = models.TextField(blank=True)
    
    def get_estructura(self):
        try:
            return json.loads(self.estructura_json)
        except:
            return {}
    
    def __str__(self):
        return f"Estructura para {self.tipo_solicitud}"

class Solicitud(models.Model):
    TIPOS_SOLICITUD = [
        ('crear_tabla', 'Creación de tablas base de datos'),
        ('modificar_tabla', 'Modificación de tabla base de datos'),
        ('compilar_objetos', 'Compilación de objetos'),
        ('asignar_permisos', 'Asignación de permisos'),
        ('crear_usuarios', 'Creación de usuarios y roles'),
        ('pull_request', 'Solicitud pull request'),
        ('despliegue', 'Solicitud de despliegue'),
        ('crear_bd', 'Creación de bases de datos'),
        ('crear_esquemas', 'Creación de esquemas'),
        ('compilar_scripts_qa', 'Compilación de scripts de tickets en QA'),
        ('compilar_scripts_pu', 'Compilación de scripts de tickets en PU'),
    ]
    
    TIPOS_ARCHIVO = [
        ('excel', 'Excel'),
        ('zip', 'ZIP'),
        ('sql', 'SQL'),
    ]
    
    ESTADOS = [
        ('registrada', 'Registrada'),
        ('revision', 'En revisión'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
        ('pendiente_aprobacion_lider', 'Pendiente aprobación líder'),
    ]
    
    AMBIENTES = [
        ('desarrollo', 'Desarrollo'),
        ('qa', 'QA'),
        ('pu', 'Producción'),
        ('todos', 'Todos los ambientes'),
    ]
    
    # Tipos de solicitud por categoría
    TIPOS_BD = ['crear_tabla', 'modificar_tabla', 'asignar_permisos', 'crear_usuarios', 'crear_bd', 'crear_esquemas']
    TIPOS_DEVOPS = ['pull_request', 'despliegue']
    TIPOS_COMPILACION = ['compilar_objetos', 'compilar_scripts_qa', 'compilar_scripts_pu']
    
    tipo_solicitud = models.CharField(max_length=30, choices=TIPOS_SOLICITUD)
    tipo_archivo = models.CharField(max_length=10, choices=TIPOS_ARCHIVO, blank=True, null=True)
    archivo_adjunto = models.FileField(upload_to='solicitudes/', blank=True, null=True)
    estado = models.CharField(max_length=30, choices=ESTADOS, default='registrada')
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Nuevos campos
    base_datos_aplicacion = models.CharField(max_length=100, help_text="Base de datos o aplicación donde se aplicará")
    correo_notificacion = models.EmailField(help_text="Correo para notificaciones")
    ambientes_ejecucion = models.JSONField(default=list, blank=True, help_text="Ambientes donde ejecutar (para scripts)")
    lider_proyecto = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='solicitudes_lideradas',
                                     help_text="Líder que debe aprobar (para creación de usuarios)")
    
    # Campos adicionales para Pull Request / Despliegue
    url_commit = models.URLField(blank=True, null=True)
    nombre_branch = models.CharField(max_length=100, blank=True, null=True)
    entorno = models.CharField(max_length=50, blank=True, null=True)
    
    # Script SQL generado
    script_sql_generado = models.TextField(blank=True, null=True)
    estructura_validada = models.BooleanField(default=False, help_text="Si la estructura del archivo fue validada")
    
    # Campos para creación de usuarios
    usuario_creado = models.CharField(max_length=100, blank=True, null=True)
    password_generado = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_tipo_solicitud_display()} - {self.usuario.username} - {self.estado}"
    
    def puede_editar(self, user):
        """Verifica si un usuario puede editar esta solicitud"""
        user_profile = UserProfile.objects.get_or_create(user=user)[0]
        
        # Admin puede editar todo
        if user_profile.role == 'admin':
            return True
            
        # Solo el propietario puede editar si está en estado registrada o revision
        if self.usuario == user and self.estado in ['registrada', 'revision']:
            return True
            
        return False
    
    def puede_gestionar(self, user):
        """Verifica si un usuario puede gestionar (cambiar estado) esta solicitud"""
        user_profile = UserProfile.objects.get_or_create(user=user)[0]

        # Admin puede gestionar todo
        if user_profile.role == 'admin':
            return True

        # Ingeniero DB puede gestionar solicitudes de tipo BD (de cualquier usuario)
        if user_profile.role == 'db' and self.tipo_solicitud in self.TIPOS_BD:
            return True

        # Ingeniero DB también puede gestionar SUS PROPIAS solicitudes
        if user_profile.role == 'db' and self.usuario == user:
            return True

        # Ingeniero DevOps puede gestionar solicitudes DevOps
        if user_profile.role == 'devops' and self.tipo_solicitud in self.TIPOS_DEVOPS:
            return True

        # Líder puede aprobar creación de usuarios
        if (user_profile.role == 'lider' and self.tipo_solicitud == 'crear_usuarios' 
            and self.lider_proyecto == user):
            return True

        return False

    
    def estados_permitidos_para_usuario(self, user):
        user_profile = UserProfile.objects.get_or_create(user=user)[0]

        # Admin puede cambiar a cualquier estado
        if user_profile.role == 'admin':
            return [estado[0] for estado in self.ESTADOS]

        # Líder puede aprobar/rechazar creación de usuarios
        if (user_profile.role == 'lider' and self.tipo_solicitud == 'crear_usuarios' 
            and self.lider_proyecto == user and self.estado == 'pendiente_aprobacion_lider'):
            return ['aprobada', 'rechazada']

        # Ingenieros especializados pueden gestionar (aunque sean autores)
        if self.puede_gestionar(user):
            return ['revision', 'aprobada', 'rechazada', 'finalizada']

        # Solo propietarios pueden cancelar si no tienen otros permisos
        if self.usuario == user and self.estado == 'registrada':
            return ['cancelada']

        return []

    
    def requiere_aprobacion_lider(self):
        """Verifica si la solicitud requiere aprobación de líder"""
        return self.tipo_solicitud == 'crear_usuarios'
    
    def get_ambientes_display(self):
        """Retorna los ambientes de ejecución como texto"""
        if not self.ambientes_ejecucion:
            return "No especificado"
        return ", ".join(self.ambientes_ejecucion)
    
    class Meta:
        ordering = ['-fecha_creacion']

class HistorialEstado(models.Model):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name='historial')
    estado_anterior = models.CharField(max_length=30, choices=Solicitud.ESTADOS)
    estado_nuevo = models.CharField(max_length=30, choices=Solicitud.ESTADOS)
    usuario_cambio = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.solicitud.id} - {self.estado_anterior} -> {self.estado_nuevo}"

class Comentario(models.Model):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name='comentarios')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Comentario de {self.usuario.username} en solicitud {self.solicitud.id}"
    
    class Meta:
        ordering = ['-fecha_creacion']
