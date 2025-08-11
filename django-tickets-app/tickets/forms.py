from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Solicitud, UserProfile, Comentario

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLES, required=True)
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data["role"]
            )
        return user

class SolicitudForm(forms.ModelForm):
    # Campo para seleccionar ambientes (para scripts)
    ambientes_ejecucion = forms.MultipleChoiceField(
        choices=Solicitud.AMBIENTES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Selecciona los ambientes donde se debe ejecutar (solo para compilación de scripts)"
    )
    
    # Campo para seleccionar líder de proyecto
    lider_proyecto = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__role='lider'),
        required=False,
        empty_label="Seleccionar líder...",
        help_text="Requerido para creación de usuarios"
    )
    
    class Meta:
        model = Solicitud
        fields = [
            'tipo_solicitud', 'base_datos_aplicacion', 'correo_notificacion',
            'tipo_archivo', 'archivo_adjunto', 'descripcion', 
            'url_commit', 'nombre_branch', 'entorno', 'ambientes_ejecucion', 'lider_proyecto'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'tipo_solicitud': forms.Select(attrs={'class': 'form-control'}),
            'base_datos_aplicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'correo_notificacion': forms.EmailInput(attrs={'class': 'form-control'}),
            'tipo_archivo': forms.Select(attrs={'class': 'form-control'}),
            'archivo_adjunto': forms.FileInput(attrs={'class': 'form-control'}),
            'url_commit': forms.URLInput(attrs={'class': 'form-control'}),
            'nombre_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'entorno': forms.TextInput(attrs={'class': 'form-control'}),
            'lider_proyecto': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos condicionales según el tipo de solicitud
        self.fields['url_commit'].required = False
        self.fields['nombre_branch'].required = False
        self.fields['entorno'].required = False
        self.fields['lider_proyecto'].required = False
        
        # Configurar el correo por defecto del usuario actual
        if 'initial' in kwargs and 'user' in kwargs['initial']:
            user = kwargs['initial']['user']
            if user.email:
                self.fields['correo_notificacion'].initial = user.email
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_solicitud = cleaned_data.get('tipo_solicitud')
        archivo_adjunto = cleaned_data.get('archivo_adjunto')
        tipo_archivo = cleaned_data.get('tipo_archivo')
        lider_proyecto = cleaned_data.get('lider_proyecto')
        ambientes_ejecucion = cleaned_data.get('ambientes_ejecucion')
        
        # Validar que para creación de usuarios y asignación pmisos se seleccione un líder
        if tipo_solicitud in ['crear_usuarios', 'asignar_permisos'] and not lider_proyecto:
            raise forms.ValidationError("Debe seleccionar un líder de proyecto para la solicitud.")
        
        # Validar que para compilación de objetos se suba archivo SQL
        if tipo_solicitud == 'compilar_objetos' and archivo_adjunto and tipo_archivo != 'sql':
            raise forms.ValidationError("Para compilación de objetos debe subir un archivo SQL.")
        
        # Validar ambientes para scripts
        if tipo_solicitud in ['compilar_scripts_qa', 'compilar_scripts_pu'] and not ambientes_ejecucion:
            raise forms.ValidationError("Debe seleccionar al menos un ambiente para la compilación de scripts.")
        
        return cleaned_data

class EditarSolicitudForm(forms.ModelForm):
    ambientes_ejecucion = forms.MultipleChoiceField(
        choices=Solicitud.AMBIENTES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Selecciona los ambientes donde se debe ejecutar (solo para compilación de scripts)"
    )
    
    lider_proyecto = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__role='lider'),
        required=False,
        empty_label="Seleccionar líder...",
        help_text="Requerido para creación de usuarios"
    )
    
    class Meta:
        model = Solicitud
        fields = [
            'tipo_solicitud', 'base_datos_aplicacion', 'correo_notificacion',
            'tipo_archivo', 'archivo_adjunto', 'descripcion', 
            'url_commit', 'nombre_branch', 'entorno', 'ambientes_ejecucion', 'lider_proyecto'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'tipo_solicitud': forms.Select(attrs={'class': 'form-control'}),
            'base_datos_aplicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'correo_notificacion': forms.EmailInput(attrs={'class': 'form-control'}),
            'tipo_archivo': forms.Select(attrs={'class': 'form-control'}),
            'archivo_adjunto': forms.FileInput(attrs={'class': 'form-control'}),
            'url_commit': forms.URLInput(attrs={'class': 'form-control'}),
            'nombre_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'entorno': forms.TextInput(attrs={'class': 'form-control'}),
            'lider_proyecto': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer campos condicionales según el tipo de solicitud
        self.fields['url_commit'].required = False
        self.fields['nombre_branch'].required = False
        self.fields['entorno'].required = False
        self.fields['lider_proyecto'].required = False
        
        # Agregar texto de ayuda
        self.fields['archivo_adjunto'].help_text = "Dejar vacío para mantener el archivo actual"

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class CambiarEstadoForm(forms.Form):
    ESTADOS = Solicitud.ESTADOS
    
    nuevo_estado = forms.ChoiceField(choices=ESTADOS, widget=forms.Select(attrs={'class': 'form-control'}))
    comentario = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False
    )

class ValidarEstructuraForm(forms.Form):
    """Formulario para validar estructura de archivos Excel"""
    archivo = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls'}),
        help_text="Selecciona el archivo Excel para validar su estructura"
    )
    tipo_solicitud = forms.ChoiceField(
        choices=Solicitud.TIPOS_SOLICITUD,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Tipo de solicitud para validar la estructura correspondiente"
    )
