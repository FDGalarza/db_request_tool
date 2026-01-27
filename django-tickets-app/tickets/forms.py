from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Solicitud, UserProfile, Comentario, Proyecto
import json
import os

class ProyectoForm(forms.ModelForm):
    """Formulario para crear y editar proyectos"""
    configuraciones = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 10, 
            'class': 'form-control', 
            'placeholder': 'Ingrese la configuración de nombramiento en formato JSON'
        }),
        required=False,
        help_text="Configuración de reglas de nombramiento (JSON)."
    )

    class Meta:
        model = Proyecto
        fields = [
            'nombre', 'codigo', 'descripcion', 'cliente', 'lider_proyecto',
            'base_datos_principal', 'motor_bd', 'estado',
            'fecha_inicio', 'fecha_fin_estimada', 'activo', 'configuraciones'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin_estimada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: PROJ001'}),
            'cliente': forms.TextInput(attrs={'class': 'form-control'}),
            'base_datos_principal': forms.TextInput(attrs={'class': 'form-control'}),
            'motor_bd': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'lider_proyecto': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrar solo usuarios que pueden ser líderes de proyecto
        self.fields['lider_proyecto'].queryset = User.objects.filter(
            profile__role__in=['admin', 'lider']
        )
        self.fields['lider_proyecto'].empty_label = "Seleccionar líder..."

        # Prellenar configuraciones como JSON legible si el proyecto ya existe
        if self.instance and self.instance.pk and self.instance.configuraciones:
            self.initial['configuraciones'] = json.dumps(
                self.instance.configuraciones, indent=2
            )

    def clean_configuraciones(self):
        """Validar que el JSON ingresado sea válido"""
        data = self.cleaned_data.get("configuraciones")
        if not data:
            return {}
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"El JSON no es válido: {str(e)}")


class SolicitudForm(forms.ModelForm):
    # Campo para seleccionar ambientes (para scripts)
    ambientes_ejecucion = forms.MultipleChoiceField(
        choices=Solicitud.AMBIENTES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Ambientes de Ejecución",
        help_text="Selecciona los ambientes donde se debe ejecutar (solo para compilación de scripts)"
    )
    
    # Campo para seleccionar líder de proyecto
    lider_proyecto = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role__in=['lider', 'admin']),
        required=False,
        empty_label="Seleccionar líder...",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Líder de Proyecto",
        help_text="Requerido para creación de usuarios y asignación de permisos"
    )
    
    # AGREGAR ESTE CAMPO:
    ticket_referencia = forms.ModelChoiceField(
        queryset=Solicitud.objects.none(),
        required=False,
        empty_label="Seleccionar ticket de referencia...",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Ticket de Referencia (Desarrollo)",
        help_text="Solicitud original en desarrollo que contiene los scripts a compilar"
    )
    
    class Meta:
        model = Solicitud
        fields = [
            'proyecto', 'tipo_solicitud', 'base_datos_aplicacion', 'correo_notificacion',
            'tipo_archivo', 'archivo_adjunto', 'descripcion', 
            'url_commit', 'nombre_branch', 'entorno', 'ambientes_ejecucion', 'lider_proyecto'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'proyecto': forms.Select(attrs={'class': 'form-control'}),
            'tipo_solicitud': forms.Select(attrs={'class': 'form-control'}),
            'base_datos_aplicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: sistema_ventas, app_inventario'}),
            'correo_notificacion': forms.EmailInput(attrs={'class': 'form-control'}),
            'tipo_archivo': forms.Select(attrs={'class': 'form-control'}),
            'archivo_adjunto': forms.FileInput(attrs={'class': 'form-control'}),
            'url_commit': forms.URLInput(attrs={'class': 'form-control'}),
            'nombre_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'entorno': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'proyecto': 'Proyecto *',  # REQUERIDO AHORA
            'tipo_solicitud': 'Tipo de Solicitud',
            'base_datos_aplicacion': 'Base de Datos/Aplicación',
            'correo_notificacion': 'Correo de Notificación',
            'tipo_archivo': 'Tipo de Archivo',
            'archivo_adjunto': 'Archivo Adjunto',
            'descripcion': 'Descripción',
            'url_commit': 'URL del Commit',
            'nombre_branch': 'Nombre del Branch',
            'entorno': 'Entorno',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # PROYECTO ES OBLIGATORIO AHORA
        self.fields['proyecto'].required = True
        
        # Filtrar proyectos según el rol del usuario
        if user and hasattr(user, 'profile'):
            proyectos_disponibles = user.profile.get_proyectos_disponibles()
            self.fields['proyecto'].queryset = proyectos_disponibles
            
            # Si no hay proyectos disponibles, mostrar mensaje
            if not proyectos_disponibles.exists():
                self.fields['proyecto'].empty_label = "No tienes proyectos asignados"
                self.fields['proyecto'].widget.attrs['disabled'] = True
        
        # Pre-llenar correo de notificación con el email del usuario
        if user and user.email and not self.instance.pk:
            self.fields['correo_notificacion'].initial = user.email
        
        # Hacer campos condicionales según el tipo de solicitud
        self.fields['url_commit'].required = False
        self.fields['nombre_branch'].required = False
        self.fields['entorno'].required = False
        self.fields['lider_proyecto'].required = False

        # Filtrar tickets de referencia - solo solicitudes finalizadas de tipo BD
        self.fields['ticket_referencia'].queryset = Solicitud.objects.filter(
            estado='finalizada',
            tipo_solicitud__in=['crear_tabla', 'modificar_tabla', 'asignar_permisos', 
                               'crear_usuarios', 'crear_bd', 'crear_esquemas']
        ).order_by('-fecha_creacion')


    def clean_archivo_adjunto(self):
        """Validar extensión de archivo según tipo de solicitud"""
        archivo = self.cleaned_data.get('archivo_adjunto')
        tipo_solicitud = self.cleaned_data.get('tipo_solicitud')
        
        if not archivo or not tipo_solicitud:
            return archivo
        
        # Obtener extensión del archivo
        nombre_archivo = archivo.name.lower()
        extension = os.path.splitext(nombre_archivo)[1]
        
        # Definir extensiones permitidas por tipo de solicitud
        EXTENSIONES_PERMITIDAS = {
            'crear_tabla'     : ['.xls', '.xlsx'],
            'modificar_tabla' : ['.xls', '.xlsx'], 
            'asignar_permisos': ['.xls', '.xlsx'],
            'crear_usuarios'  : ['.xls', '.xlsx'],
            'compilar_objetos': ['.sql'],
            'crear_bd'        : ['.xls', '.xlsx'],
            'crear_esquemas'  : ['.xls', '.xlsx'],
        }
        
        # Validar si el tipo requiere archivo específico
        if tipo_solicitud in EXTENSIONES_PERMITIDAS:
            extensiones_validas = EXTENSIONES_PERMITIDAS[tipo_solicitud]
            if extension not in extensiones_validas:
                extensiones_str = ', '.join(extensiones_validas)
                raise forms.ValidationError(
                    f"Para {self.get_tipo_solicitud_display(tipo_solicitud)} debe subir un archivo con extensión: {extensiones_str}"
                )
        
        return archivo

    def get_tipo_solicitud_display(self, tipo_solicitud):
        """Helper para obtener el display name del tipo de solicitud"""
        for codigo, nombre in Solicitud.TIPOS_SOLICITUD:
            if codigo == tipo_solicitud:
                return nombre
        return tipo_solicitud
    
    def clean(self):
        cleaned_data        = super().clean()
        tipo_solicitud      = cleaned_data.get('tipo_solicitud')
        archivo_adjunto     = cleaned_data.get('archivo_adjunto')
        tipo_archivo        = cleaned_data.get('tipo_archivo')
        lider_proyecto      = cleaned_data.get('lider_proyecto')
        ambientes_ejecucion = cleaned_data.get('ambientes_ejecucion')
        proyecto            = cleaned_data.get('proyecto')
        
        # VALIDAR QUE SE SELECCIONE UN PROYECTO
        if not proyecto:
            raise forms.ValidationError("Debe seleccionar un proyecto para crear la solicitud.")
        
        # Definir tipos que requieren archivo obligatorio
        TIPOS_REQUIEREN_ARCHIVO = [
            'crear_tabla', 'modificar_tabla', 'asignar_permisos', 
            'crear_usuarios', 'compilar_objetos', 'crear_bd',
            'crear_esquemas'
        ]

        # Validar archivo obligatorio para ciertos tipos
        if tipo_solicitud in TIPOS_REQUIEREN_ARCHIVO:
            if not archivo_adjunto:
                tipo_display = self.get_tipo_solicitud_display(tipo_solicitud)
                if tipo_solicitud == 'compilar_objetos':
                    raise forms.ValidationError(f"Para {tipo_display} debe subir un archivo SQL.")
                else:
                    raise forms.ValidationError(f"Para {tipo_display} debe subir un archivo Excel (.xls o .xlsx).")

        # Validar tipo_archivo según tipo_solicitud
        if tipo_solicitud in TIPOS_REQUIEREN_ARCHIVO and archivo_adjunto:
            if tipo_solicitud == 'compilar_objetos':
                if tipo_archivo != 'sql':
                    raise forms.ValidationError("Para compilación de objetos debe seleccionar 'SQL' como tipo de archivo.")
            elif tipo_solicitud in ['crear_tabla', 'modificar_tabla', 'asignar_permisos', 'crear_usuarios', 'crear_bd', 'crear_esquemas']:
                if tipo_archivo != 'excel':
                    raise forms.ValidationError("Para este tipo de solicitud debe seleccionar 'Excel' como tipo de archivo.")
        
        # Validar que para creación de usuarios y asignación de permisos se seleccione un líder
        if tipo_solicitud in ['crear_usuarios', 'asignar_permisos'] and not lider_proyecto:
            raise forms.ValidationError("Debe seleccionar un líder de proyecto para solicitudes de creación de usuarios y asignación de permisos.")
        
        # Validar que para compilación de objetos se suba archivo SQL
        if tipo_solicitud == 'compilar_objetos':
            if not archivo_adjunto:
                raise forms.ValidationError("Para compilación de objetos debe subir un archivo.")
            if tipo_archivo != 'sql':
                raise forms.ValidationError("Para compilación de objetos debe subir un archivo SQL.")
        
                # Validar ticket de referencia y líder para compilar_scripts_qa y compilar_scripts_pu
        if tipo_solicitud in ['compilar_scripts_qa', 'compilar_scripts_pu']:
            ticket_referencia = cleaned_data.get('ticket_referencia')
            if not ticket_referencia:
                raise forms.ValidationError(
                    f"Para {self.get_tipo_solicitud_display(tipo_solicitud)} debe seleccionar un ticket de referencia."
                )
            if not lider_proyecto:
                raise forms.ValidationError(
                    f"Para {self.get_tipo_solicitud_display(tipo_solicitud)} debe seleccionar un líder de proyecto para aprobación."
                )
        
        # Validar campos requeridos para Pull Request/Despliegue
        
        # Validar campos requeridos para Pull Request/Despliegue
        if tipo_solicitud in ['pull_request', 'despliegue']:
            if not cleaned_data.get('url_commit'):
                raise forms.ValidationError("URL del commit es requerida para solicitudes de Pull Request y Despliegue.")
            if not cleaned_data.get('nombre_branch'):
                raise forms.ValidationError("Nombre del branch es requerido para solicitudes de Pull Request y Despliegue.")
        
        return cleaned_data

class EditarSolicitudForm(forms.ModelForm):
    """Formulario para editar solicitudes (solo estado registrada)"""
    
    ambientes_ejecucion = forms.MultipleChoiceField(
        choices=Solicitud.AMBIENTES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Ambientes de Ejecución",
        help_text="Selecciona los ambientes donde se debe ejecutar (solo para compilación de scripts)"
    )

    lider_proyecto = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role__in=['lider', 'admin']),
        required=False,
        empty_label="Seleccionar líder...",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Líder de Proyecto",
        help_text="Requerido para creación de usuarios y asignación de permisos"
    )
    
    # Campo para compilación de scripts QA/PU
    ticket_referencia = forms.ModelChoiceField(
        queryset=Solicitud.objects.none(),
        required=False,
        empty_label="Seleccionar ticket de referencia...",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Ticket de Referencia (Desarrollo)",
        help_text="Solicitud original en desarrollo que contiene los scripts a compilar"
    )
    
    class Meta:
        model = Solicitud
        fields = [
            'proyecto', 'tipo_solicitud', 'base_datos_aplicacion', 'correo_notificacion',
            'tipo_archivo', 'archivo_adjunto', 'descripcion', 
            'url_commit', 'nombre_branch', 'entorno', 'ambientes_ejecucion', 'lider_proyecto',
            'ticket_referencia'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'proyecto': forms.Select(attrs={'class': 'form-control'}),
            'tipo_solicitud': forms.Select(attrs={'class': 'form-control'}),
            'base_datos_aplicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'correo_notificacion': forms.EmailInput(attrs={'class': 'form-control'}),
            'tipo_archivo': forms.Select(attrs={'class': 'form-control'}),
            'archivo_adjunto': forms.FileInput(attrs={'class': 'form-control'}),
            'url_commit': forms.URLInput(attrs={'class': 'form-control'}),
            'nombre_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'entorno': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # PROYECTO ES OBLIGATORIO
        self.fields['proyecto'].required = True
        
        # Filtrar proyectos según el rol del usuario
        if user and hasattr(user, 'profile'):
            proyectos_disponibles = user.profile.get_proyectos_disponibles()
            self.fields['proyecto'].queryset = proyectos_disponibles
        
        # Hacer campos condicionales según el tipo de solicitud
        self.fields['url_commit'].required = False
        self.fields['nombre_branch'].required = False
        self.fields['entorno'].required = False
        self.fields['lider_proyecto'].required = False
        
        # Agregar texto de ayuda
        self.fields['archivo_adjunto'].help_text = "Dejar vacío para mantener el archivo actual"

    def clean_archivo_adjunto(self):
        """Validar extensión de archivo según tipo de solicitud"""
        archivo = self.cleaned_data.get('archivo_adjunto')
        tipo_solicitud = self.cleaned_data.get('tipo_solicitud')
        
        # Si no se sube nuevo archivo, no validar
        if not archivo or not tipo_solicitud:
            return archivo
        
        # Obtener extensión del archivo
        nombre_archivo = archivo.name.lower()
        extension = os.path.splitext(nombre_archivo)[1]
        
        # Definir extensiones permitidas por tipo de solicitud
        EXTENSIONES_PERMITIDAS = {
            'crear_tabla'     : ['.xls', '.xlsx'],
            'modificar_tabla' : ['.xls', '.xlsx'], 
            'asignar_permisos': ['.xls', '.xlsx'],
            'crear_usuarios'  : ['.xls', '.xlsx'],
            'compilar_objetos': ['.sql']         ,
            'crear_bd'        : ['.xls', '.xlsx'],
            'crear_esquemas'  : ['.xls', '.xlsx'],

        }
        
        # Validar si el tipo requiere archivo específico
        if tipo_solicitud in EXTENSIONES_PERMITIDAS:
            extensiones_validas = EXTENSIONES_PERMITIDAS[tipo_solicitud]
            if extension not in extensiones_validas:
                extensiones_str = ', '.join(extensiones_validas)
                raise forms.ValidationError(
                    f"Para {self.get_tipo_solicitud_display(tipo_solicitud)} debe subir un archivo con extensión: {extensiones_str}"
                )
        
        return archivo

    def get_tipo_solicitud_display(self, tipo_solicitud):
        """Helper para obtener el display name del tipo de solicitud"""
        for codigo, nombre in Solicitud.TIPOS_SOLICITUD:
            if codigo == tipo_solicitud:
                return nombre
        return tipo_solicitud
        

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'form-control',
                'placeholder': 'Escriba su comentario aquí...'
            }),
        }
        labels = {
            'texto': 'Comentario'
        }

class CambiarEstadoForm(forms.Form):
    ESTADOS = Solicitud.ESTADOS
    
    nuevo_estado = forms.ChoiceField(
        choices=ESTADOS, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Nuevo Estado"
    )
    comentario = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'class': 'form-control',
            'placeholder': 'Comentario sobre el cambio de estado (opcional)...'
        }),
        required=False,
        label="Comentario"
    )

class ValidarEstructuraForm(forms.Form):
    """Formulario para validar estructura de archivos Excel antes de generar script"""
    archivo = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control', 
            'accept': '.xlsx,.xls'
        }),
        label="Archivo Excel",
        help_text="Selecciona el archivo Excel para validar su estructura"
    )
    tipo_solicitud = forms.ChoiceField(
        choices=Solicitud.TIPOS_SOLICITUD,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Tipo de Solicitud",
        help_text="Tipo de solicitud para validar la estructura correspondiente"
    )

class AsignarMiembrosProyectoForm(forms.Form):
    """Formulario para asignar miembros a un proyecto"""
    miembros = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Miembros del equipo"
    )
    
    def __init__(self, *args, **kwargs):
        proyecto = kwargs.pop('proyecto', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar usuarios activos con perfil
        self.fields['miembros'].queryset = User.objects.filter(
            profile__activo=True,
            is_active=True
        ).exclude(profile__role='admin')  # Admin no necesita ser asignado
        
        # Pre-seleccionar miembros actuales si estamos editando
        if proyecto:
            miembros_actuales = User.objects.filter(profile__proyectos_asignados=proyecto)
            self.fields['miembros'].initial = miembros_actuales

class UserProfileForm(forms.ModelForm):
    """Formulario para editar perfiles de usuario"""
    class Meta:
        model = UserProfile
        fields = ['role', 'departamento', 'telefono', 'activo']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'departamento': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'role': 'Rol',
            'departamento': 'Departamento',
            'telefono': 'Teléfono',
            'activo': 'Activo'
        }

# NUEVO: Formulario para crear usuarios (solo admin)
class CrearUsuarioForm(forms.ModelForm):
    """Formulario para crear usuarios - Solo para administradores"""
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='La contraseña debe tener al menos 8 caracteres.'
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Ingresa la misma contraseña para verificación.'
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Rol del usuario'
    )
    departamento = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Departamento'
    )
    telefono = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Teléfono'
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'username': 'Nombre de usuario',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo electrónico',
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya existe.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            # Crear perfil de usuario
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                departamento=self.cleaned_data.get('departamento', ''),
                telefono=self.cleaned_data.get('telefono', ''),
                activo=True
            )
        return user

class FiltroSolicitudesForm(forms.Form):
    """Formulario para filtrar solicitudes en el dashboard"""
    proyecto = forms.ModelChoiceField(
        queryset=Proyecto.objects.filter(activo=True),
        required=False,
        empty_label="Todos los proyectos",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Proyecto"
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + Solicitud.ESTADOS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Estado"
    )
    tipo_solicitud = forms.ChoiceField(
        choices=[('', 'Todos los tipos')] + Solicitud.TIPOS_SOLICITUD,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Tipo de Solicitud"
    )

