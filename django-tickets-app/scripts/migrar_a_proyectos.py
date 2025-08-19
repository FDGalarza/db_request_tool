import os
import sys
import django

#Agrega el path raíz del proyecto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from tickets.models import Proyecto, Solicitud, UserProfile
from django.contrib.auth.models import User

def migrar_a_proyectos():
    """
    Migra el sistema existente para incluir proyectos
    """
    try:
        print("🚀 MIGRACIÓN A SISTEMA DE PROYECTOS")
        print("=" * 50)
        
        # 1. Crear proyecto por defecto
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
        
        # 2. Asignar solicitudes sin proyecto al proyecto por defecto
        solicitudes_sin_proyecto = Solicitud.objects.filter(proyecto__isnull=True)
        count = solicitudes_sin_proyecto.count()
        
        if count > 0:
            print(f"🔄 Asignando {count} solicitudes al proyecto por defecto...")
            solicitudes_sin_proyecto.update(proyecto=proyecto_defecto)
            print(f"✅ {count} solicitudes asignadas al proyecto por defecto")
        else:
            print("ℹ️  No hay solicitudes sin proyecto")
        
        # 3. Verificar y actualizar perfiles de usuario
        usuarios_sin_perfil = User.objects.filter(profile__isnull=True)
        for usuario in usuarios_sin_perfil:
            rol = 'admin' if usuario.is_superuser else 'dev'
            UserProfile.objects.create(
                user=usuario,
                role=rol,
                activo=True
            )
            print(f"✅ Perfil creado para {usuario.username} con rol {rol}")
        
        # 4. Asignar todos los usuarios activos al proyecto por defecto
        perfiles_activos = UserProfile.objects.filter(activo=True)
        for perfil in perfiles_activos:
            if not perfil.proyectos_asignados.exists():
                perfil.proyectos_asignados.add(proyecto_defecto)
                print(f"✅ Usuario {perfil.user.username} asignado al proyecto por defecto")
        
        # 5. Mostrar estadísticas finales
        print(f"\n📊 Estadísticas finales:")
        print(f"   - Total proyectos: {Proyecto.objects.count()}")
        print(f"   - Total usuarios con perfil: {UserProfile.objects.count()}")
        print(f"   - Total solicitudes: {Solicitud.objects.count()}")
        print(f"   - Solicitudes en proyecto por defecto: {proyecto_defecto.get_solicitudes_total()}")
        print(f"   - Usuarios asignados al proyecto por defecto: {proyecto_defecto.miembros_equipo.count()}")
        
        print("\n🎉 Migración completada exitosamente")
        print("\n📋 Próximos pasos:")
        print("1. Verificar que todas las solicitudes tengan proyecto asignado")
        print("2. Crear proyectos específicos según sea necesario")
        print("3. Reasignar usuarios a proyectos específicos")
        print("4. Probar el módulo de administración")
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrar_a_proyectos()
