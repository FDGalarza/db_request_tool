from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse, HttpResponseNotFound
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.models import User
from django.conf import settings
from .models import Solicitud, UserProfile, HistorialEstado, Comentario, ConfiguracionEstructuraExcel, Proyecto
from .forms import (SolicitudForm, ComentarioForm, 
                   CambiarEstadoForm, EditarSolicitudForm, ValidarEstructuraForm,
                   ProyectoForm, AsignarMiembrosProyectoForm, UserProfileForm, FiltroSolicitudesForm,
                   CrearUsuarioForm)
from .utils import (procesar_archivo_excel, generar_script_sql, validar_estructura_excel,
                   enviar_correo_notificacion, enviar_correo_credenciales, 
                   enviar_correo_aprobacion_lider, enviar_correo_cambio_estado, generar_credenciales_usuario, crear_plantilla_excel)
import json
import os

# Decorador para verificar si el usuario es admin
def es_admin(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'admin'

@login_required
def dashboard(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    # Obtener proyectos del usuario
    if user_profile.role == 'admin':
        proyectos = Proyecto.objects.filter(activo=True)
        solicitudes = Solicitud.objects.all()
    else:
        proyectos = user_profile.get_proyectos_disponibles()
        
        # Base queryset según el rol - ACTUALIZADO según requerimientos
        if user_profile.role == 'db':
            # Ver sus propias solicitudes + solicitudes de BD de TODOS los usuarios
            solicitudes = Solicitud.objects.filter(
                Q(usuario=request.user) | 
                Q(tipo_solicitud__in=Solicitud.TIPOS_BD)
            ).distinct()
        elif user_profile.role == 'devops':
            # Ver sus propias solicitudes + solicitudes DevOps de TODOS los usuarios
            solicitudes = Solicitud.objects.filter(
                Q(usuario=request.user) | 
                Q(tipo_solicitud__in=Solicitud.TIPOS_DEVOPS)
            ).distinct()
        elif user_profile.role == 'lider':
            # Ver sus propias solicitudes + solicitudes que debe aprobar
            solicitudes = Solicitud.objects.filter(
                Q(usuario=request.user) | 
                Q(lider_proyecto=request.user)
            ).distinct()
        else:  # dev - Solo sus propias solicitudes
            solicitudes = Solicitud.objects.filter(usuario=request.user)
    
    # Filtros
    form_filtros = FiltroSolicitudesForm(request.GET)
    if form_filtros.is_valid():
        if form_filtros.cleaned_data['proyecto']:
            solicitudes = solicitudes.filter(proyecto=form_filtros.cleaned_data['proyecto'])
        if form_filtros.cleaned_data['estado']:
            solicitudes = solicitudes.filter(estado=form_filtros.cleaned_data['estado'])
        if form_filtros.cleaned_data['tipo_solicitud']:
            solicitudes = solicitudes.filter(tipo_solicitud=form_filtros.cleaned_data['tipo_solicitud'])
    
    # Filtros adicionales de la URL
    tipo_solicitud = request.GET.get('tipo_solicitud', '')
    estado = request.GET.get('estado', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    if tipo_solicitud:
        solicitudes = solicitudes.filter(tipo_solicitud=tipo_solicitud)
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    if fecha_desde:
        solicitudes = solicitudes.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        solicitudes = solicitudes.filter(fecha_creacion__date__lte=fecha_hasta)
    
    # Paginación
    paginator = Paginator(solicitudes.order_by('-fecha_creacion'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas
    stats = {
        'total_solicitudes': solicitudes.count(),
        'pendientes': solicitudes.filter(estado='registrada').count(),
        'en_proceso': solicitudes.filter(estado__in=['revision', 'aprobada']).count(),
        'finalizadas': solicitudes.filter(estado='finalizada').count(),
        'total_proyectos': proyectos.count(),
    }
    
    context = {
        'page_obj': page_obj,
        'user_profile': user_profile,
        'tipos_solicitud': Solicitud.TIPOS_SOLICITUD,
        'estados': Solicitud.ESTADOS,
        'proyectos': proyectos,
        'stats': stats,
        'form_filtros': form_filtros,
        'filtros': {
            'tipo_solicitud': tipo_solicitud,
            'estado': estado,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        }
    }
    return render(request, 'tickets/dashboard.html', context)

@login_required
def crear_solicitud(request):
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    # Verificar que el usuario tenga proyectos asignados
    proyectos_disponibles = user_profile.get_proyectos_disponibles()
    if not proyectos_disponibles.exists() and user_profile.role != 'admin':
        messages.error(request, 'No tienes proyectos asignados. Contacta al administrador para que te asigne a un proyecto.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SolicitudForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = request.user
            
            # Convertir ambientes_ejecucion a lista
            ambientes = form.cleaned_data.get('ambientes_ejecucion', [])
            solicitud.ambientes_ejecucion = list(ambientes) if ambientes else []
            
            # Si requiere aprobación de líder, cambiar estado
            if solicitud.requiere_aprobacion_lider():
                solicitud.estado = 'pendiente_aprobacion_lider'
            
            solicitud.save()
            
            # IMPORTANTE: Los ingenieros de desarrollo NO generan scripts automáticamente
            if user_profile.role == 'dev':
                messages.success(request, 'Solicitud creada exitosamente. El script SQL será generado por el equipo de Base de Datos.')
            else:
                # Solo admin y DB pueden generar scripts automáticamente
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
                    messages.success(request, 'Solicitud creada exitosamente.')
            
            # Enviar correo si requiere aprobación de líder
            if solicitud.requiere_aprobacion_lider() and solicitud.lider_proyecto:
                try:
                    enviar_correo_aprobacion_lider(solicitud)
                    messages.info(request, 'Se ha enviado correo al líder de proyecto para aprobación.')
                except Exception as e:
                    messages.warning(request, f'Solicitud creada pero no se pudo enviar el correo: {str(e)}')
            
            return redirect('detalle_solicitud', pk=solicitud.pk)
        
        else:
            print(form.errors)
    else:
        form = SolicitudForm(initial={'user': request.user}, user=request.user)
    
    return render(request, 'tickets/crear_solicitud.html', {'form': form})

@login_required
def editar_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    
    # Verificar permisos de edición según requerimientos
    if not solicitud.puede_editar(request.user):
        messages.error(request, 'No tienes permisos para editar esta solicitud o ya no está en estado registrada.')
        return redirect('detalle_solicitud', pk=pk)
    
    if request.method == 'POST':
        form = EditarSolicitudForm(request.POST, request.FILES, instance=solicitud, user=request.user)
        if form.is_valid():
            solicitud_actualizada = form.save(commit=False)
            
            # Convertir ambientes_ejecucion a lista
            ambientes = form.cleaned_data.get('ambientes_ejecucion', [])
            solicitud_actualizada.ambientes_ejecucion = list(ambientes) if ambientes else []
            
            solicitud_actualizada.save()
            
            # Si se cambió el archivo, resetear script generado para que DB lo regenere
            if 'archivo_adjunto' in form.changed_data:
                solicitud_actualizada.script_sql_generado = None
                solicitud_actualizada.estructura_validada = False
                solicitud_actualizada.save()
                messages.info(request, 'Archivo actualizado. El script SQL deberá ser regenerado por el equipo de Base de Datos.')
            
            messages.success(request, 'Solicitud actualizada exitosamente.')
            return redirect('detalle_solicitud', pk=pk)
    else:
        form = EditarSolicitudForm(instance=solicitud, user=request.user)
        if solicitud.ambientes_ejecucion:
            form.initial['ambientes_ejecucion'] = solicitud.ambientes_ejecucion
    
    return render(request, 'tickets/editar_solicitud.html', {'form': form, 'solicitud': solicitud})

@login_required
def detalle_solicitud(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk)
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    # Verificar permisos de visualización según requerimientos
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
    
    # Procesar generación de script SQL (solo para DB/admin)
    if request.method == 'POST' and 'generar_sql' in request.POST:
        if solicitud.puede_generar_script(request.user) and solicitud.archivo_adjunto:
            
            comentario_texto = request.POST.get("comentario")
            
            if not comentario_texto:
                messages.error(request, "Debes ingresar un comentario antes de generar el script.")
                return redirect("detalle_solicitud", pk=pk)
            
            try:
                script_sql = procesar_archivo_excel(solicitud)
                if script_sql:
                    solicitud.script_sql_generado = script_sql
                    solicitud.estructura_validada = True

                    # Marcar como finalizada
                    estado_anterior  = solicitud.estado
                    solicitud.estado = "revision"
                    solicitud.save()

                    # Guardar comentario
                    Comentario.objects.create(
                        solicitud = solicitud,
                        usuario   = request.user,
                        texto     = comentario_texto 
                    )

                    # Guardas historial de estado
                    HistorialEstado.objects.create(
                        solicitud       = solicitud,
                        estado_anterior =  estado_anterior,
                        estado_nuevo    = "revision",
                        usuario_cambio  = request.user,
                        comentario      = comentario_texto
                    )

                    messages.success(request, 'Script SQL generado exitosamente')
                        
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
                
                # Validaciones especiales según requerimientos
                print("Views.py 313")
                if (solicitud.tipo_solicitud == 'crear_tabla' and nuevo_estado == 'finalizada' 
                    and not solicitud.script_sql_generado):
                    print("Views.py 316")
                    messages.error(request, 'No se puede finalizar sin generar el script SQL primero.')
                    return redirect('detalle_solicitud', pk=pk)
                
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
                
                # Enviar correo de cambio de estado
                try:
                    if nuevo_estado != 'finalizada':
                        enviar_correo_cambio_estado(solicitud, estado_anterior, nuevo_estado, request.user, comentario_texto)
                        correo_enviado = True
                except Exception as e:
                    correo_enviado = False
                    print(f"Error enviando correo de cambio de estado: {e}")
                
                # Lógica especial según el nuevo estado
                if nuevo_estado == 'aprobada' and solicitud.tipo_solicitud == 'crear_usuarios':
                    # Generar credenciales y enviar correo
                    try:
                        usuario_creado, password = generar_credenciales_usuario(solicitud)
                        solicitud.usuario_creado = usuario_creado
                        solicitud.password_generado = password
                        solicitud.save()
                        
                        enviar_correo_credenciales(solicitud, usuario_creado, password)
                        messages.success(request, f'Estado cambiado a {solicitud.get_estado_display()}. Usuario creado y credenciales enviadas.')
                    except Exception as e:
                        messages.error(request, f'Estado cambiado pero error al crear usuario: {str(e)}')
                
                elif nuevo_estado == 'finalizada':
                    # Enviar correo con script SQL adjunto si existe
                    try:
                        enviar_correo_notificacion(solicitud, nuevo_estado, comentario_texto)
                        messages.success(request, f'Estado cambiado a {solicitud.get_estado_display()}. Correo con script enviado.')
                    except Exception as e:
                        messages.warning(request, f'Estado cambiado pero error enviando correo con script: {str(e)}')
                else:
                    # Mensaje estándar
                    if correo_enviado:
                        messages.success(request, f'Estado cambiado a {solicitud.get_estado_display()}. Correo de notificación enviado.')
                    else:
                        messages.warning(request, f'Estado cambiado a {solicitud.get_estado_display()}. Error enviando correo.')
                
                return redirect('detalle_solicitud', pk=pk)
            else:
                messages.error(request, 'No tienes permisos para cambiar a ese estado.')
    
    # Determinar qué mostrar según el rol del usuario
    mostrar_script = solicitud.puede_ver_script(request.user)
    puede_generar_script = solicitud.puede_generar_script(request.user)
    puede_descargar_script = solicitud.puede_descargar_script(request.user)
    
    context = {
        'solicitud': solicitud,
        'user_profile': user_profile,
        'comentario_form': comentario_form,
        'cambiar_estado_form': cambiar_estado_form,
        'puede_cambiar_estado': bool(estados_permitidos),
        'puede_editar': solicitud.puede_editar(request.user),
        'puede_gestionar': solicitud.puede_gestionar(request.user),
        'mostrar_script': mostrar_script,
        'puede_generar_script': puede_generar_script,
        'puede_descargar_script': puede_descargar_script,
    }
    return render(request, 'tickets/detalle_solicitud.html', context)

@login_required
def validar_estructura(request):
    """Vista para validar estructura de archivos Excel antes de generar script"""
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
    
    # Verificar permisos según requerimientos (ingenieros dev NO pueden descargar)
    if not solicitud.puede_descargar_script(request.user):
        messages.error(request, 'No tienes permisos para descargar este archivo.')
        return redirect('dashboard')
    
    if not solicitud.script_sql_generado:
        messages.error(request, 'No hay script SQL generado para esta solicitud.')
        return redirect('detalle_solicitud', pk=pk)
    
    response = HttpResponse(solicitud.script_sql_generado, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="script_solicitud_{pk}.sql"'
    return response

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

# ==================== GESTIÓN DE PROYECTOS ====================

@login_required
def lista_proyectos(request):
    """Lista proyectos según el rol del usuario"""
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    if user_profile.role == 'admin':
        # Admin ve todos los proyectos
        proyectos = Proyecto.objects.all().order_by('-fecha_creacion')
    else:
        # Otros usuarios ven solo sus proyectos asignados
        proyectos = user_profile.get_proyectos_disponibles().order_by('-fecha_creacion')
    
    # Filtros
    estado_filtro = request.GET.get('estado')
    if estado_filtro:
        proyectos = proyectos.filter(estado=estado_filtro)
    
    # Paginación
    paginator = Paginator(proyectos, 15)
    page_number = request.GET.get('page')
    proyectos_page = paginator.get_page(page_number)
    
    context = {
        'proyectos': proyectos_page,
        'estado_filtro': estado_filtro,
        'estados_proyecto': Proyecto.ESTADOS_PROYECTO,
        'user_profile': user_profile,
    }
    
    return render(request, 'tickets/admin/lista_proyectos.html', context)

@login_required
@user_passes_test(es_admin)
def crear_proyecto(request):
    """Crear nuevo proyecto - Solo para admins"""
    if request.method == 'POST':
        form = ProyectoForm(request.POST)
        if form.is_valid():
            proyecto = form.save()
            messages.success(request, f'Proyecto "{proyecto.nombre}" creado exitosamente.')
            return redirect('detalle_proyecto', pk=proyecto.pk)
    else:
        form = ProyectoForm()
    
    return render(request, 'tickets/admin/crear_proyecto.html', {'form': form})

@login_required
def detalle_proyecto(request, pk):
    """Detalle de proyecto"""
    proyecto = get_object_or_404(Proyecto, pk=pk)
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    # Verificar permisos
    if not (user_profile.role == 'admin' or user_profile.puede_gestionar_proyecto(proyecto)):
        messages.error(request, 'No tienes permisos para ver este proyecto.')
        return redirect('dashboard')
    
    # Estadísticas del proyecto
    solicitudes = proyecto.solicitudes.all()
    stats = {
        'total_solicitudes': solicitudes.count(),
        'solicitudes_activas': proyecto.get_solicitudes_activas(),
        'solicitudes_por_estado': dict(solicitudes.values('estado').annotate(count=Count('estado')).values_list('estado', 'count')),
        'solicitudes_por_tipo': dict(solicitudes.values('tipo_solicitud').annotate(count=Count('tipo_solicitud')).values_list('tipo_solicitud', 'count')),
    }
    
    # Solicitudes recientes
    solicitudes_recientes = solicitudes.order_by('-fecha_creacion')[:10]
    
    # Miembros del equipo
    miembros = User.objects.filter(profile__proyectos_asignados=proyecto)
    
    context = {
        'proyecto': proyecto,
        'stats': stats,
        'solicitudes_recientes': solicitudes_recientes,
        'miembros': miembros,
        'puede_editar': user_profile.role == 'admin',
        'user_profile': user_profile,
    }
    
    return render(request, 'tickets/detalle_proyecto.html', context)

@login_required
@user_passes_test(es_admin)
def editar_proyecto(request, pk):
    """Editar proyecto - Solo para admins"""
    proyecto = get_object_or_404(Proyecto, pk=pk)
    
    if request.method == 'POST':
        form = ProyectoForm(request.POST, instance=proyecto)
        if form.is_valid():
            proyecto = form.save()
            messages.success(request, f'Proyecto "{proyecto.nombre}" actualizado exitosamente.')
            return redirect('detalle_proyecto', pk=proyecto.pk)
    else:
        form = ProyectoForm(instance=proyecto)
    
    return render(request, 'tickets/admin/editar_proyecto.html', {
        'form': form, 
        'proyecto': proyecto
    })

@login_required
@user_passes_test(es_admin)
def eliminar_proyecto(request, pk):
    """Eliminar proyecto - Solo para admins"""
    proyecto = get_object_or_404(Proyecto, pk=pk)
    
    if request.method == 'POST':
        if proyecto.solicitudes.exists():
            messages.error(request, 'No se puede eliminar el proyecto porque tiene solicitudes asociadas.')
        else:
            nombre_proyecto = proyecto.nombre
            proyecto.delete()
            messages.success(request, f'Proyecto "{nombre_proyecto}" eliminado exitosamente.')
            return redirect('lista_proyectos')
    
    return render(request, 'tickets/admin/eliminar_proyecto.html', {'proyecto': proyecto})

@login_required
@user_passes_test(es_admin)
def asignar_miembros_proyecto(request, pk):
    """Asignar miembros a un proyecto - Solo para admins"""
    proyecto = get_object_or_404(Proyecto, pk=pk)
    
    if request.method == 'POST':
        form = AsignarMiembrosProyectoForm(request.POST, proyecto=proyecto)
        if form.is_valid():
            # Limpiar asignaciones actuales
            for user_profile in UserProfile.objects.all():
                user_profile.proyectos_asignados.remove(proyecto)
            
            # Asignar nuevos miembros
            miembros_seleccionados = form.cleaned_data['miembros']
            for user in miembros_seleccionados:
                user.profile.proyectos_asignados.add(proyecto)
            
            messages.success(request, f'Miembros asignados al proyecto "{proyecto.nombre}" exitosamente.')
            return redirect('detalle_proyecto', pk=proyecto.pk)
    else:
        form = AsignarMiembrosProyectoForm(proyecto=proyecto)
    
    return render(request, 'tickets/admin/asignar_miembros.html', {
        'form': form, 
        'proyecto': proyecto
    })

# ==================== MÓDULO DE ADMINISTRACIÓN ====================

@login_required
@user_passes_test(es_admin)
def panel_administracion(request):
    """Panel principal de administración - Solo para admins"""
    
    # Estadísticas generales
    stats = {
        'total_usuarios': User.objects.count(),
        'usuarios_activos': User.objects.filter(is_active=True).count(),
        'total_proyectos': Proyecto.objects.count(),
        'proyectos_activos': Proyecto.objects.filter(activo=True).count(),
        'total_solicitudes': Solicitud.objects.count(),
        'solicitudes_pendientes': Solicitud.objects.filter(estado='registrada').count(),
    }
    
    # Estadísticas por rol
    roles_stats = dict(UserProfile.objects.values('role').annotate(count=Count('role')).values_list('role', 'count'))
    
    # Proyectos recientes
    proyectos_recientes = Proyecto.objects.order_by('-fecha_creacion')[:5]
    
    # Solicitudes recientes
    solicitudes_recientes = Solicitud.objects.order_by('-fecha_creacion')[:10]
    
    # Usuarios sin perfil
    usuarios_sin_perfil = User.objects.filter(profile__isnull=True)
    
    context = {
        'stats': stats,
        'roles_stats': roles_stats,
        'roles': UserProfile.ROLES,  # AGREGADO para el template
        'proyectos_recientes': proyectos_recientes,
        'solicitudes_recientes': solicitudes_recientes,
        'usuarios_sin_perfil': usuarios_sin_perfil,
    }
    
    return render(request, 'tickets/admin/panel_administracion.html', context)

@login_required
@user_passes_test(es_admin)
def gestionar_usuarios(request):
    """Gestión de usuarios - Solo para admins"""
    usuarios = User.objects.all().order_by('username')
    
    # Filtros
    rol_filtro = request.GET.get('rol')
    activo_filtro = request.GET.get('activo')
    
    if rol_filtro:
        usuarios = usuarios.filter(profile__role=rol_filtro)
    if activo_filtro:
        usuarios = usuarios.filter(is_active=activo_filtro == 'true')
    
    # Paginación
    paginator = Paginator(usuarios, 20)
    page_number = request.GET.get('page')
    usuarios_page = paginator.get_page(page_number)
    
    context = {
        'usuarios': usuarios_page,
        'rol_filtro': rol_filtro,
        'activo_filtro': activo_filtro,
        'roles': UserProfile.ROLES,
    }
    
    return render(request, 'tickets/admin/gestionar_usuarios.html', context)

@login_required
@user_passes_test(es_admin)
def crear_usuario(request):
    """Crear nuevo usuario - Solo para admins"""
    if request.method == 'POST':
        form = CrearUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Usuario "{user.username}" creado exitosamente.')
            return redirect('gestionar_usuarios')
    else:
        form = CrearUsuarioForm()
    
    return render(request, 'tickets/admin/crear_usuario.html', {'form': form})

@login_required
@user_passes_test(es_admin)
def editar_usuario(request, pk):
    """Editar usuario - Solo para admins"""
    usuario = get_object_or_404(User, pk=pk)
    profile, created = UserProfile.objects.get_or_create(user=usuario)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario "{usuario.username}" actualizado exitosamente.')
            return redirect('gestionar_usuarios')
    else:
        form = UserProfileForm(instance=profile)
    
    # Calcular estadísticas del usuario
    solicitudes_activas = usuario.solicitud_set.exclude(estado__in=['finalizada', 'cancelada']).count()
    
    context = {
        'form': form, 
        'usuario': usuario,
        'profile': profile,
        'solicitudes_activas': solicitudes_activas,  # AGREGADO para el template
    }
    
    return render(request, 'tickets/admin/editar_usuario.html', context)

@login_required
@user_passes_test(es_admin)
def inactivar_usuario(request, pk):
    """Inactivar/Activar usuario - Solo para admins"""
    usuario = get_object_or_404(User, pk=pk)
    
    # No permitir inactivar al propio usuario admin
    if usuario == request.user:
        messages.error(request, 'No puedes inactivar tu propia cuenta.')
        return redirect('gestionar_usuarios')
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        if accion == 'inactivar':
            usuario.is_active = False
            usuario.save()
            
            # También inactivar el perfil si existe
            if hasattr(usuario, 'profile'):
                usuario.profile.activo = False
                usuario.profile.save()
            
            messages.success(request, f'Usuario "{usuario.username}" inactivado exitosamente.')
            
        elif accion == 'activar':
            usuario.is_active = True
            usuario.save()
            
            # También activar el perfil si existe
            if hasattr(usuario, 'profile'):
                usuario.profile.activo = True
                usuario.profile.save()
            
            messages.success(request, f'Usuario "{usuario.username}" activado exitosamente.')
        
        return redirect('gestionar_usuarios')
    
    return render(request, 'tickets/admin/inactivar_usuario.html', {'usuario': usuario})

@login_required
@user_passes_test(es_admin)
def estadisticas_avanzadas(request):
    """Estadísticas avanzadas - Solo para admins"""
    
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
    
    # Estadísticas por proyecto
    proyectos_stats = []
    for proyecto in Proyecto.objects.filter(activo=True):
        solicitudes = proyecto.solicitudes.all()
        proyectos_stats.append({
            'proyecto': proyecto,
            'total_solicitudes': solicitudes.count(),
            'solicitudes_activas': proyecto.get_solicitudes_activas(),
            'solicitudes_finalizadas': solicitudes.filter(estado='finalizada').count(),
            'miembros_count': proyecto.miembros_equipo.count(),
        })
    
    context = {
        'total_solicitudes': total_solicitudes,
        'solicitudes_por_estado': solicitudes_por_estado,
        'solicitudes_por_tipo': solicitudes_por_tipo,
        'proyectos_stats': proyectos_stats,
    }
    return render(request, 'tickets/admin/estadisticas_avanzadas.html', context)

def logout_view(request):
    """Vista personalizada de logout que acepta GET y POST"""
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')

def lista_plantillas(request):
    """Muestra todas las plantillas disponibles para descarga."""
    carpeta = os.path.join(settings.MEDIA_ROOT, "plantillas")
    os.makedirs(carpeta, exist_ok=True)

    plantillas = [
        {
            "nombre": "📄 Creación / Modificación de Tablas",
            "archivo": "plantilla_creacion_modificacion_tablas_v2.xlsx",
            "descripcion": "Define columnas, tipos de datos y comentarios.",
        },
        {
            "nombre": "👤 Usuarios y Permisos",
            "archivo": "plantilla_usuarios_permisos.xlsx",
            "descripcion": "Para creación de usuarios y asignación de permisos.",
        },
        {
            "nombre": "🗄️ Creación de Base de Datos",
            "archivo": "plantilla_creacion_bd.xlsx",
            "descripcion": "Estructura para registrar nuevas bases de datos.",
            "generar": lambda: crear_plantilla_excel("crear_bd"),
        },
        {
            "nombre": "📂 Creación de Esquemas",
            "archivo": "plantilla_creacion_esquemas.xlsx",
            "descripcion": "Define los esquemas dentro de las bases de datos.",
            "generar": lambda: crear_plantilla_excel("crear_esquemas"),
        },
    ]

    # Verificar existencia y generar si falta
    for p in plantillas:
        ruta = os.path.join(carpeta, p["archivo"])
        if not os.path.exists(ruta) and "generar" in p:
            p["generar"]()
        p["ruta_relativa"] = f"{settings.MEDIA_URL}plantillas/{p['archivo']}"

    return render(request, "plantillas/lista_plantillas.html", {"plantillas": plantillas})


def descargar_plantilla(request, nombre_archivo):
    """Permite descargar una plantilla específica."""
    ruta = os.path.join(settings.MEDIA_ROOT, "plantillas", nombre_archivo)
    if os.path.exists(ruta):
        return FileResponse(open(ruta, "rb"), as_attachment=True, filename=nombre_archivo)
    return HttpResponseNotFound("Archivo no encontrado.")
