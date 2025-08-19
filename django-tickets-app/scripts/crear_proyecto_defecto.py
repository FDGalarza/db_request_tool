
import os
import sys
import django

#Agrega el path raíz del proyecto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from tickets.models import Proyecto, Solicitud
from django.contrib.auth.models import User

def crear_proyecto_defecto():
    """
    Crea un proyecto por defecto y asigna las solicitudes existentes
    """
    try:
        print("🚀 Creando proyecto por defecto...")
        
        # Crear proyecto por defecto
        proyecto_defecto, created = Proyecto.objects.get_or_create(
            codigo='DEFAULT',
            defaults={
                'nombre': 'Proyecto Por Defecto',
                'descripcion': 'Proyecto creado automáticamente para solicitudes existentes',
                'cliente': 'Interno',
                'estado': 'activo',
                'motor_bd': 'mysql',
                'activo': True
            }
        )
        
        if created:
            print(f"✅ Proyecto creado: {proyecto_defecto}")
        else:
            print(f"ℹ️  Proyecto ya existe: {proyecto_defecto}")
        
        # Asignar solicitudes sin proyecto al proyecto por defecto
        solicitudes_sin_proyecto = Solicitud.objects.filter(proyecto__isnull=True)
        count = solicitudes_sin_proyecto.count()
        
        if count > 0:
            print(f"🔄 Asignando {count} solicitudes al proyecto por defecto...")
            solicitudes_sin_proyecto.update(proyecto=proyecto_defecto)
            print(f"✅ {count} solicitudes asignadas al proyecto por defecto")
        else:
            print("ℹ️  No hay solicitudes sin proyecto")
        
        # Mostrar estadísticas
        print(f"\n📊 Estadísticas del proyecto:")
        print(f"   - Total solicitudes: {proyecto_defecto.get_solicitudes_total()}")
        print(f"   - Solicitudes activas: {proyecto_defecto.get_solicitudes_activas()}")
        
        print("\n🎉 Proceso completado exitosamente")
        
    except Exception as e:
        print(f"❌ Error creando proyecto por defecto: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    crear_proyecto_defecto()
