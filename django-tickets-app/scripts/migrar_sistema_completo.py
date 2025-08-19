import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from tickets.models import Proyecto, Solicitud, UserProfile  # ← CORREGIDO: UserProfile en lugar de PerfilUsuario
from django.contrib.auth.models import User

def migrar_sistema_completo():
    """
    Migra el sistema completo según todos los requerimientos
    """
    try:
        print("🚀 MIGRACIÓN COMPLETA DEL SISTEMA DE TICKETS")
        print("=" * 60)
        
        # 1. Crear proyecto por defecto si no existe
        proyecto_defecto, created = Proyecto.objects.get_or_create(
            codigo='DEFAULT',
            defaults={
                'nombre': 'Proyecto Por Defecto',
                'descripcion': 'Proyecto creado automáticamente para solicitudes existentes',
                'cliente': 'Interno',
                'estado': 'activo',
                'motor_bd': 'mysql',
                'base_datos_principal': 'sistema_principal',
                'activo': True
            }
        )
        
        if created:
            print(f"✅ Proyecto por defecto creado: {proyecto_defecto}")
        else:
            print(f"ℹ️  Proyecto por defecto ya existe: {proyecto_defecto}")
        
        # 2. Migrar perfiles de usuario existentes
        print("\n🔄 Migrando perfiles de usuario...")
        usuarios_actualizados = 0
        
        for user in User.objects.all():
            # Verificar si ya tiene perfil
            try:
                perfil = UserProfile.objects.get(user=user)
                print(f"ℹ️  Usuario {user.username} ya tiene perfil")
            except UserProfile.DoesNotExist:
                # Crear perfil nuevo
                rol = 'admin' if user.is_superuser else 'dev'
                UserProfile.objects.create(
                    user=user,
                    role=rol,
                    activo=True
                )
                print(f"✅ Creado perfil para {user.username}: {rol}")
                usuarios_actualizados += 1
        
        print(f"📊 Perfiles actualizados: {usuarios_actualizados}")
        
        # 3. Asignar solicitudes sin proyecto al proyecto por defecto
        print("\n🔄 Asignando solicitudes al proyecto por defecto...")
        solicitudes_sin_proyecto = Solicitud.objects.filter(proyecto__isnull=True)
        count = solicitudes_sin_proyecto.count()
        
        if count > 0:
            solicitudes_sin_proyecto.update(proyecto=proyecto_defecto)
            print(f"✅ {count} solicitudes asignadas al proyecto por defecto")
        else:
            print("ℹ️  No hay solicitudes sin proyecto")
        
        # 4. Verificar campos requeridos en solicitudes
        print("\n🔄 Verificando campos requeridos en solicitudes...")
        solicitudes_sin_correo = Solicitud.objects.filter(correo_notificacion__isnull=True)
        solicitudes_sin_bd = Solicitud.objects.filter(base_datos_aplicacion__isnull=True)
        
        for solicitud in solicitudes_sin_correo:
            if solicitud.usuario.email:
                solicitud.correo_notificacion = solicitud.usuario.email
                solicitud.save()
                print(f"✅ Correo asignado a solicitud #{solicitud.id}")
        
        for solicitud in solicitudes_sin_bd:
            if solicitud.proyecto and solicitud.proyecto.base_datos_principal:
                solicitud.base_datos_aplicacion = solicitud.proyecto.base_datos_principal
            else:
                solicitud.base_datos_aplicacion = 'sistema_principal'
            solicitud.save()
            print(f"✅ BD/Aplicación asignada a solicitud #{solicitud.id}")
        
        # 5. Asignar usuarios al proyecto por defecto
        print("\n🔄 Asignando usuarios al proyecto por defecto...")
        perfiles_sin_proyecto = UserProfile.objects.filter(proyectos_asignados__isnull=True)
        
        for perfil in perfiles_sin_proyecto:
            if perfil.role != 'admin':  # Admin no necesita ser asignado
                perfil.proyectos_asignados.add(proyecto_defecto)
                print(f"✅ Usuario {perfil.user.username} asignado al proyecto por defecto")
        
        # 6. Estadísticas finales
        print(f"\n📊 ESTADÍSTICAS FINALES:")
        print(f"   - Total proyectos: {Proyecto.objects.count()}")
        print(f"   - Total usuarios con perfil: {UserProfile.objects.count()}")
        print(f"   - Total solicitudes: {Solicitud.objects.count()}")
        print(f"   - Solicitudes en proyecto por defecto: {proyecto_defecto.get_solicitudes_total()}")
        print(f"   - Usuarios asignados al proyecto por defecto: {proyecto_defecto.miembros_equipo.count()}")
        
        # 7. Verificar roles
        print(f"\n👥 DISTRIBUCIÓN DE ROLES:")
        for rol_code, rol_name in UserProfile.ROLES:
            count = UserProfile.objects.filter(role=rol_code).count()
            print(f"   - {rol_name}: {count}")
        
        print("\n🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. Verificar que todas las solicitudes tengan proyecto asignado")
        print("2. Verificar que todos los usuarios tengan correo configurado")
        print("3. Crear proyectos específicos según sea necesario")
        print("4. Reasignar usuarios a proyectos específicos")
        print("5. Configurar líderes de proyecto")
        print("6. Probar todas las funcionalidades según los requerimientos")
        
        print("\n⚠️  RECORDATORIOS IMPORTANTES:")
        print("- Los ingenieros de desarrollo solo pueden ver/editar sus propias solicitudes")
        print("- Los ingenieros DB pueden ver todas las solicitudes de BD")
        print("- Los ingenieros DevOps pueden ver todas las solicitudes DevOps")
        print("- Solo ingenieros DB y admin pueden generar scripts SQL")
        print("- Los ingenieros de desarrollo NO pueden ver ni descargar scripts")
        print("- Las solicitudes de crear usuarios requieren aprobación de líder")
        print("- Todos los cambios de estado envían correos de notificación")
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrar_sistema_completo()
