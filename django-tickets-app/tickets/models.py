from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
import json

class Proyecto(models.Model):
    """Modelo para gestionar proyectos y separar las solicitudes por proyecto"""
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Proyecto")
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código del Proyecto", 
                             help_text="Código único para identificar el proyecto (ej: PROJ001)")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    cliente = models.CharField(max_length=100, blank=True, verbose_name="Cliente")
    lider_proyecto = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='proyectos_liderados', verbose_name="Líder del Proyecto")
    
    # Configuraciones del proyecto
    base_datos_principal = models.CharField(max_length=100, blank=True, verbose_name="Base de Datos Principal")
    motor_bd = models.CharField(max_length=50, choices=[
        ('mysql', 'MySQL'),
        ('postgresql', 'PostgreSQL'),
        ('sqlserver', 'SQL Server'),
        ('oracle', 'Oracle'),
        ('sqlite', 'SQLite')
    ], default='mysql', verbose_name="Motor de Base de Datos")
    
    # Estados del proyecto
    ESTADOS_PROYECTO = [
        ('activo', 'Activo'),
        ('en_pausa', 'En Pausa'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS_PROYECTO, default='activo', verbose_name="Estado")
    
    # Metadatos
    fecha_inicio = models.DateField(null=True, blank=True, verbose_name="Fecha de Inicio")
    fecha_fin_estimada = models.DateField(null=True, blank=True, verbose_name="Fecha de Fin Estimada")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    # Configuraciones futuras (JSON para flexibilidad)
    configuraciones = models.JSONField(default=dict, blank=True, verbose_name="Configuraciones Adicionales",
                                     help_text="Configuraciones específicas del proyecto en formato JSON")
    
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def clean(self):
        if self.fecha_fin_estimada and self.fecha_inicio:
            if self.fecha_fin_estimada < self.fecha_inicio:
                raise ValidationError("La fecha de fin no puede ser anterior a la fecha de inicio")
    
    def get_solicitudes_activas(self):
        """Retorna el número de solicitudes activas del proyecto"""
        return self.solicitudes.exclude(estado__in=['finalizada', 'cancelada']).count()
    
    def get_solicitudes_total(self):
        """Retorna el número total de solicitudes del proyecto"""
        return self.solicitudes.count()
    
    def get_miembros_equipo(self):
        """Retorna los miembros del equipo asignados al proyecto"""
        return User.objects.filter(profile__proyectos_asignados=self)

class UserProfile(models.Model):
    ROLES = [
        ('dev', 'Ingeniero de Desarrollo'),
        ('db', 'Ingeniero de Bases de Datos'),
        ('devops', 'Ingeniero DevOps'),
        ('admin', 'Administrador'),
        ('lider', 'Líder de Proyecto'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLES, default='dev')
    
    # Proyectos asignados al usuario
    proyectos_asignados = models.ManyToManyField(Proyecto, blank=True, 
                                               related_name='miembros_equipo',
                                               verbose_name="Proyectos Asignados")
    
    # Campos adicionales
    departamento = models.CharField(max_length=100, blank=True, verbose_name="Departamento")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def puede_gestionar_proyecto(self, proyecto):
        """Verifica si el usuario puede gestionar un proyecto específico"""
        if self.role == 'admin':
            return True
        if self.role == 'lider' and proyecto.lider_proyecto == self.user:
            return True
        return proyecto in self.proyectos_asignados.all()
    
    def get_proyectos_disponibles(self):
        """Retorna los proyectos que el usuario puede ver/gestionar"""
        if self.role == 'admin':
            return Proyecto.objects.filter(activo=True)
        elif self.role == 'lider':
            # Líder puede ver proyectos que lidera + proyectos asignados
            return Proyecto.objects.filter(
                models.Q(lider_proyecto=self.user) | 
                models.Q(miembros_equipo=self.user),
                activo=True
            ).distinct()
        else:
            return self.proyectos_asignados.filter(activo=True)

class ConfiguracionEstructuraExcel(models.Model):
    """Configuración de estructuras esperadas para archivos Excel por proyecto"""
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, 
                                related_name='configuraciones_excel',
                                verbose_name="Proyecto", null=True, blank=True)
    tipo_solicitud = models.CharField(max_length=50)
    estructura_json = models.TextField(help_text="JSON con la estructura esperada")
    descripcion = models.TextField(blank=True)
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Configuración", default="Default")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración de Estructura Excel"
        verbose_name_plural = "Configuraciones de Estructura Excel"
        unique_together = ['proyecto', 'tipo_solicitud', 'nombre']
    
    def get_estructura(self):
        try:
            return json.loads(self.estructura_json)
        except:
            return {}
    
    def __str__(self):
        proyecto_str = f"{self.proyecto.codigo} - " if self.proyecto else "Global - "
        return f"{proyecto_str}{self.tipo_solicitud} - {self.nombre}"

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
    
    # NUEVO CAMPO: Proyecto al que pertenece la solicitud
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, 
                                related_name='solicitudes', verbose_name="Proyecto",  null=True, blank=True)
    
    tipo_solicitud = models.CharField(max_length=30, choices=TIPOS_SOLICITUD)
    tipo_archivo = models.CharField(max_length=10, choices=TIPOS_ARCHIVO, blank=True, null=True)
    archivo_adjunto = models.FileField(upload_to='solicitudes/', blank=True, null=True)
    estado = models.CharField(max_length=30, choices=ESTADOS, default='registrada')
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Campos existentes
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
    
    def save(self, *args, **kwargs):
        # Auto-asignar líder de proyecto si no está asignado
        if not self.lider_proyecto and self.proyecto and self.proyecto.lider_proyecto:
            self.lider_proyecto = self.proyecto.lider_proyecto
        
        # Auto-asignar base de datos principal del proyecto si no está especificada
        if not self.base_datos_aplicacion and self.proyecto and self.proyecto.base_datos_principal:
            self.base_datos_aplicacion = self.proyecto.base_datos_principal
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        proyecto_codigo = self.proyecto.codigo if self.proyecto else "SIN-PROJ"
        return f"#{self.id} - {self.get_tipo_solicitud_display()} - {self.usuario.username} - {proyecto_codigo}"
    
    def puede_editar(self, user):
        """Verifica si un usuario puede editar esta solicitud"""
        user_profile = UserProfile.objects.get_or_create(user=user)[0]
        
        # Admin puede editar todo
        if user_profile.role == 'admin':
            return True
        
        # Verificar si el usuario puede gestionar el proyecto
        if self.proyecto and user_profile.puede_gestionar_proyecto(self.proyecto):
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

        # Verificar si el usuario puede gestionar el proyecto
        if self.proyecto and user_profile.puede_gestionar_proyecto(self.proyecto):
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
    
    def puede_generar_script(self, user):
        """
        Verifica si un usuario puede generar scripts SQL
        """
        user_profile = UserProfile.objects.get_or_create(user=user)[0]
        
        # Solo ingenieros DB y admin pueden generar scripts
        if user_profile.role not in ['admin', 'db']:
            return False
        
        # No permitir generar script si está en revisión
        if self.estado == 'pendiente_aprobacion_lider':
            return False
        
        return True
    
    def puede_ver_script(self, user):
        """Verifica si un usuario puede ver el script SQL generado"""
        user_profile = UserProfile.objects.get_or_create(user=user)[0]
        
        # Ingenieros de desarrollo NO pueden ver scripts
        if user_profile.role == 'dev':
            if self.estado == 'finalizada':
                 return user_profile.role in ['admin', 'db', 'devops', 'dev']
            return False
            
        return user_profile.role in ['admin', 'db', 'devops']
    
    def puede_descargar_script(self, user):
        """Verifica si un usuario puede descargar el script SQL"""
        user_profile = UserProfile.objects.get_or_create(user=user)[0]
        
        # Ingenieros de desarrollo NO pueden descargar scripts
        if user_profile.role == 'dev':
            if self.estado == 'finalizada':
                 return user_profile.role in ['admin', 'db', 'devops', 'dev']
            return False
            
        return user_profile.role in ['admin', 'db', 'devops']

    def estados_permitidos_para_usuario(self, user):
        user_profile = UserProfile.objects.get_or_create(user=user)[0]
        perfil = getattr(user, "userprofile", None)
       
        if not user_profile:
            print("Sin perfil")
            return []

        # 🔹 Caso especial para devs
        if user_profile.role == "dev":
            if self.usuario == user and self.estado == "registrada":
                return ["cancelada"]  # único estado permitido
            else:
                return []  # en cualquier otro caso no puede cambiar estado


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
