from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Solicitud, UserProfile, HistorialEstado, Comentario, ConfiguracionEstructuraExcel
from .forms import (CustomUserCreationForm, SolicitudForm, ComentarioForm, 
                   CambiarEstadoForm, EditarSolicitudForm, ValidarEstructuraForm)
from .utils import (procesar_archivo_excel, generar_script_sql, validar_estructura_excel,
                   enviar_correo_notificacion, enviar_correo_credenciales, 
                   enviar_correo_aprobacion_lider, enviar_correo_cambio_estado, generar_credenciales_usuario)
import json

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Cuenta creada exitosamente.')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def dashboard(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    # Filtros
    tipo_solicitud = request.GET.get('tipo_solicitud', '')
    estado = request.GET.get('estado', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    # Base queryset según el rol
    if user_profile.role == 'admin':
        solicitudes = Solicitud.objects.all()
    elif user_profile.role == 'db':
        # Ver sus propias solicitudes + solicitudes de BD de todos
        solicitudes = Solicitud.objects.filter(
            Q(usuario=request.user) | Q(tipo_solicitud__in=Solicitud.TIPOS_BD)
        ).distinct()
    elif user_profile.role == 'devops':
        # Ver sus propias solicitudes + solicitudes DevOps de todos
        solicitudes = Solicitud.objects.filter(
            Q(usuario=request.user) | Q(tipo_solicitud__in=Solicitud.TIPOS_DEVOPS)
        ).distinct()
    elif user_profile.role == 'lider':
        # Ver sus propias solicitudes + solicitudes que debe aprobar
        solicitudes = Solicitud.objects.filter(
            Q(usuario=request.user) | Q(lider_proyecto=request.user)
        ).distinct()
    else:  # dev
        solicitudes = Solicitud.objects.filter(usuario=request.user)
    
    # Aplicar filtros
    if tipo_solicitud:
        solicitudes = solicitudes.filter(tipo_solicitud=tipo_solicitud)
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    if fecha_desde:
        solicitudes = solicitudes.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        solicitudes = solicitudes.filter(fecha_creacion__date__lte=fecha_hasta)
    
    # Paginación
    paginator = Paginator(solicitudes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'user_profile': user_profile,
        'tipos_solicitud': Solicitud.TIPOS_SOLICITUD,
        'estados': Solicitud.ESTADOS,
        'filtros': {
            'tipo_solicitud': tipo_solicitud,
            'estado': estado,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        }
    }
    return render(request, 'tickets/dashboard.html', context)

@login_required
def solicitudes_pendientes_script(request):
    """Vista para mostrar solicitudes pendientes de generar script SQL"""
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    # Solo ingenieros DB y admin pueden acceder
    if user_profile.role not in ['admin', 'db']:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('dashboard')
    
    # Solicitudes con archivo Excel pero sin script SQL generado
    solicitudes_pendientes = Solicitud.objects.filter(
        tipo_solicitud__in=Solicitud.TIPOS_BD,
        archivo_adjunto__isnull=False,
        tipo_archivo='excel',
        script_sql_generado__isnull=True
    ).order_by('-fecha_creacion')
    
    # Paginación
    paginator = Paginator(solicitudes_pendientes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'user_profile': user_profile,
    }
    return render(request, 'tickets/solicitudes_pendientes_script.html', context)

@login_required
def crear_solicitud(request):
    if request.method == 'POST':
        form = SolicitudForm(request.POST, request.FILES)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = request.user
            
            # Convertir ambientes_ejecucion a lista
            ambientes = form.cleaned_data.get('ambientes_ejecucion', [])
            solicitud.ambientes_ejecucion = list(ambientes) if ambientes else []
            
            # Si es creación de usuarios, cambiar estado a pendiente aprobación
            if solicitud.tipo_solicitud in ['crear_usuarios', 'asignar_permisos']:
                solicitud.estado = 'pendiente_aprobacion_lider'
            
            solicitud.save()
            
            # Obtener perfil del usuario
            user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
            
            # Solo generar script automáticamente si es admin o ingeniero DB
            if (solicitud.archivo_adjunto and solicitud.tipo_archivo == 'excel' and 
                user_profile.role in ['admin', 'db']):
                try:
                    script_sql = procesar_archivo_excel(solicitud)
                    if script_sql:
                        solicitud.script_sql_generado = script_sql
                        solicitud.save()
                        messages.success(request, 'Solicitud creada y script SQL generado exitosamente.')
                    else:
                        messages.warning(request, 'Solicitud creada, pero no se pudo generar el script SQL.')
                except Exception as e:
                    messages.error(request, f'Error al procesar el archivo: {str(e)}')
            else:
                # Para desarrolladores, solo crear la solicitud sin generar script
                if user_profile.role == 'dev':
                    messages.success(request, 'Solicitud creada exitosamente. El script SQL será generado por el equipo de Base de Datos.')
                else:
                    messages.success(request, 'Solicitud creada exitosamente.')
            
            # Enviar correo de notificación si es creación de usuarios
            if solicitud.tipo_solicitud in ['crear_usuarios', 'asignar_permisos'] and solicitud.lider_proyecto:
                try:
                    enviar_correo_aprobacion_lider(solicitud)
                    messages.info(request, 'Se ha enviado correo al líder de proyecto para aprobación.')
                except Exception as e:
                    messages.warning(request, f'Solicitud creada pero no se pudo enviar el correo: {str(e)}')
            
            return redirect('detalle_solicitud', pk=solicitud.pk)
    else:
        # Pasar el usuario actual para configurar el correo por defecto
        form = SolicitudForm(initial={'user': request.user})
    
    return render(request, 'tickets/crear_solicitud.html', {'form': form})

@login_required
def editar_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    
    # Verificar permisos de edición
    if not solicitud.puede_editar(request.user):
        messages.error(request, 'No tienes permisos para editar esta solicitud.')
        return redirect('detalle_solicitud', pk=pk)
    
    if request.method == 'POST':
        form = EditarSolicitudForm(request.POST, request.FILES, instance=solicitud)
        if form.is_valid():
            solicitud_actualizada = form.save(commit=False)
            
            # Convertir ambientes_ejecucion a lista
            ambientes = form.cleaned_data.get('ambientes_ejecucion', [])
            solicitud_actualizada.ambientes_ejecucion = list(ambientes) if ambientes else []
            
            solicitud_actualizada.save()
            
            # Obtener perfil del usuario
            user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
            
            # Regenerar script SQL si se cambió el archivo y el usuario puede hacerlo
            if ('archivo_adjunto' in form.changed_data and solicitud_actualizada.archivo_adjunto and 
                solicitud_actualizada.tipo_archivo == 'excel' and user_profile.role in ['admin', 'db']):
                try:
                    script_sql = procesar_archivo_excel(solicitud_actualizada)
                    if script_sql:
                        solicitud_actualizada.script_sql_generado = script_sql
                        solicitud_actualizada.estructura_validada = False  # Resetear validación
                        solicitud_actualizada.save()
                        messages.success(request, 'Solicitud actualizada y script SQL regenerado.')
                    else:
                        messages.warning(request, 'Solicitud actualizada, pero no se pudo regenerar el script SQL.')
                except Exception as e:
                    messages.error(request, f'Error al procesar el archivo: {str(e)}')
            else:
                messages.success(request, 'Solicitud actualizada exitosamente.')
            
            return redirect('detalle_solicitud', pk=pk)
    else:
        form = EditarSolicitudForm(instance=solicitud)
        # Configurar ambientes_ejecucion para el formulario
        if solicitud.ambientes_ejecucion:
            form.initial['ambientes_ejecucion'] = solicitud.ambientes_ejecucion
    
    return render(request, 'tickets/editar_solicitud.html', {'form': form, 'solicitud': solicitud})

@login_required
def detalle_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    # Verificar permisos de visualización
    puede_ver = False
    if user_profile.role == 'admin':
        puede_ver = True
    elif solicitud.usuario == request.user:
        puede_ver = True
    elif user_profile.role == 'db' and solicitud.tipo_solicitud in Solicitud.TIPOS_BD:
        puede_ver = True
    elif user_profile.role == 'devops' and solicitud.tipo_solicitud in Solicitud.TIPOS_DEVOPS:
        puede_ver = True
    elif user_profile.role == 'lider' and solicitud.lider_proyecto == request.user:
        puede_ver = True
    
    if not puede_ver:
        messages.error(request, 'No tienes permisos para ver esta solicitud.')
        return redirect('dashboard')
    
    # Formularios
    comentario_form = ComentarioForm()
    cambiar_estado_form = CambiarEstadoForm()
    
    # Obtener estados permitidos para este usuario
    estados_permitidos = solicitud.estados_permitidos_para_usuario(request.user)
    if estados_permitidos:
        cambiar_estado_form.fields['nuevo_estado'].choices = [
            (estado, dict(Solicitud.ESTADOS)[estado]) 
            for estado in estados_permitidos
        ]
    
    # Procesar comentario
    if request.method == 'POST' and 'agregar_comentario' in request.POST:
        comentario_form = ComentarioForm(request.POST)
        if comentario_form.is_valid():
            comentario = comentario_form.save(commit=False)
            comentario.solicitud = solicitud
            comentario.usuario = request.user
            comentario.save()
            messages.success(request, 'Comentario agregado.')
            return redirect('detalle_solicitud', pk=pk)
    
    # Procesar generación manual de script SQL (solo para DB/admin)
    if request.method == 'POST' and 'generar_sql' in request.POST:
        if (user_profile.role in ['admin', 'db'] and 
            solicitud.archivo_adjunto and solicitud.tipo_archivo == 'excel'):
            try:
                script_sql = procesar_archivo_excel(solicitud)
                if script_sql:
                    solicitud.script_sql_generado = script_sql
                    solicitud.estructura_validada = True
                    solicitud.save()
                    messages.success(request, 'Script SQL generado exitosamente.')
                else:
                    messages.error(request, 'No se pudo generar el script SQL.')
            except Exception as e:
                messages.error(request, f'Error al generar el script: {str(e)}')
            return redirect('detalle_solicitud', pk=pk)
    
    # Procesar cambio de estado
    if request.method == 'POST' and 'cambiar_estado' in request.POST and estados_permitidos:
        cambiar_estado_form = CambiarEstadoForm(request.POST)
        if cambiar_estado_form.is_valid():
            nuevo_estado = cambiar_estado_form.cleaned_data['nuevo_estado']
            comentario_texto = cambiar_estado_form.cleaned_data['comentario']
            
            if nuevo_estado in estados_permitidos:
                estado_anterior = solicitud.estado
                
                # Crear historial
                HistorialEstado.objects.create(
                    solicitud=solicitud,
                    estado_anterior=estado_anterior,
                    estado_nuevo=nuevo_estado,
                    usuario_cambio=request.user,
                    comentario=comentario_texto
                )
                
                solicitud.estado = nuevo_estado
                solicitud.save()
                
                # Enviar correo de cambio de estado (SIEMPRE)
                try:
                    enviar_correo_cambio_estado(solicitud, estado_anterior, nuevo_estado, request.user, comentario_texto)
                    correo_enviado = True
                except Exception as e:
                    correo_enviado = False
                    print(f"Error enviando correo de cambio de estado: {e}")
                
                # Procesar lógica especial según el nuevo estado
                if nuevo_estado == 'aprobada' and solicitud.tipo_solicitud == 'crear_usuarios':
                    # Generar credenciales y enviar correo adicional
                    try:
                        usuario_creado, password = generar_credenciales_usuario(solicitud)
                        solicitud.usuario_creado = usuario_creado
                        solicitud.password_generado = password
                        solicitud.save()
                        
                        enviar_correo_credenciales(solicitud, usuario_creado, password)
                        messages.success(request, f'Estado cambiado a {solicitud.get_estado_display()}. Usuario creado y credenciales enviadas por correo.')
                    except Exception as e:
                        messages.error(request, f'Estado cambiado pero error al crear usuario: {str(e)}')
                
                elif nuevo_estado in ['finalizada'] and solicitud.script_sql_generado:
                    # Enviar correo adicional con script SQL para estados finalizados
                    try:
                        enviar_correo_notificacion(solicitud, nuevo_estado, comentario_texto)
                        if correo_enviado:
                            messages.success(request, f'Estado cambiado a {solicitud.get_estado_display()}. Correos de notificación enviados.')
                        else:
                            messages.warning(request, f'Estado cambiado a {solicitud.get_estado_display()}. Error enviando algunos correos.')
                    except Exception as e:
                        messages.warning(request, f'Estado cambiado pero no se pudo enviar el correo con el script: {str(e)}')
                else:
                    # Mensaje estándar para otros cambios de estado
                    if correo_enviado:
                        messages.success(request, f'Estado cambiado a {solicitud.get_estado_display()}. Correo de notificación enviado.')
                    else:
                        messages.warning(request, f'Estado cambiado a {solicitud.get_estado_display()}. Error enviando correo de notificación.')
                
                return redirect('detalle_solicitud', pk=pk)
            else:
                messages.error(request, 'No tienes permisos para cambiar a ese estado.')
    
    # Procesar regeneración de script SQL
    if request.method == 'POST' and 'regenerar_sql' in request.POST:
        if solicitud.puede_gestionar(request.user) and solicitud.archivo_adjunto:
            try:
                script_sql = procesar_archivo_excel(solicitud)
                if script_sql:
                    solicitud.script_sql_generado = script_sql
                    solicitud.estructura_validada = False  # Resetear validación
                    solicitud.save()
                    messages.success(request, 'Script SQL regenerado exitosamente.')
                else:
                    messages.error(request, 'No se pudo regenerar el script SQL.')
            except Exception as e:
                messages.error(request, f'Error al regenerar el script: {str(e)}')
            return redirect('detalle_solicitud', pk=pk)
    
    # Mostrar script solo si no es ingeniero de desarrollo
    mostrar_script = user_profile.role != 'dev'
    
    context = {
        'solicitud': solicitud,
        'user_profile': user_profile,
        'comentario_form': comentario_form,
        'cambiar_estado_form': cambiar_estado_form,
        'puede_cambiar_estado': bool(estados_permitidos),
        'puede_editar': solicitud.puede_editar(request.user),
        'puede_gestionar': solicitud.puede_gestionar(request.user),
        'mostrar_script': mostrar_script,
    }
    return render(request, 'tickets/detalle_solicitud.html', context)

@login_required
def validar_estructura(request):
    """Vista para validar estructura de archivos Excel"""
    if request.method == 'POST':
        form = ValidarEstructuraForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = form.cleaned_data['archivo']
            tipo_solicitud = form.cleaned_data['tipo_solicitud']
            
            try:
                es_valido, mensaje = validar_estructura_excel(archivo, tipo_solicitud)
                if es_valido:
                    messages.success(request, f'✅ Estructura válida: {mensaje}')
                else:
                    messages.error(request, f'❌ Estructura inválida: {mensaje}')
            except Exception as e:
                messages.error(request, f'Error al validar el archivo: {str(e)}')
            
            return redirect('validar_estructura')
    else:
        form = ValidarEstructuraForm()
    
    return render(request, 'tickets/validar_estructura.html', {'form': form})

@login_required
def descargar_script_sql(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    # Verificar permisos
    puede_descargar = False
    if user_profile.role == 'admin':
        puede_descargar = True
    elif solicitud.usuario == request.user:
        puede_descargar = True
    elif user_profile.role == 'db' and solicitud.tipo_solicitud in Solicitud.TIPOS_BD:
        puede_descargar = True
    elif user_profile.role == 'devops' and solicitud.tipo_solicitud in Solicitud.TIPOS_DEVOPS:
        puede_descargar = True
    
    if not puede_descargar:
        messages.error(request, 'No tienes permisos para descargar este archivo.')
        return redirect('dashboard')
    
    if not solicitud.script_sql_generado:
        messages.error(request, 'No hay script SQL generado para esta solicitud.')
        return redirect('detalle_solicitud', pk=pk)
    
    response = HttpResponse(solicitud.script_sql_generado, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="script_solicitud_{pk}.sql"'
    return response

@login_required
def estadisticas(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    if user_profile.role != 'admin':
        messages.error(request, 'No tienes permisos para ver las estadísticas.')
        return redirect('dashboard')
    
    # Estadísticas básicas
    total_solicitudes = Solicitud.objects.count()
    solicitudes_por_estado = {}
    for estado_code, estado_name in Solicitud.ESTADOS:
        count = Solicitud.objects.filter(estado=estado_code).count()
        solicitudes_por_estado[estado_name] = count
    
    solicitudes_por_tipo = {}
    for tipo_code, tipo_name in Solicitud.TIPOS_SOLICITUD:
        count = Solicitud.objects.filter(tipo_solicitud=tipo_code).count()
        solicitudes_por_tipo[tipo_name] = count
    
    context = {
        'total_solicitudes': total_solicitudes,
        'solicitudes_por_estado': solicitudes_por_estado,
        'solicitudes_por_tipo': solicitudes_por_tipo,
    }
    return render(request, 'tickets/estadisticas.html', context)

def logout_view(request):
    """Vista personalizada de logout que acepta GET y POST"""
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')
