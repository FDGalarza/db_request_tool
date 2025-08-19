import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from django.core.management import execute_from_command_line

def crear_migracion():
    """
    Crea la migración para agregar el modelo Proyecto
    """
    try:
        print("🔄 Creando migración para agregar Proyectos...")
        
        # Crear migración
        execute_from_command_line(['manage.py', 'makemigrations', 'tickets', '--name', 'add_proyecto_model'])
        
        print("✅ Migración creada exitosamente")
        print("\n📋 Próximos pasos:")
        print("1. Revisar la migración generada")
        print("2. Ejecutar: python manage.py migrate")
        print("3. Crear proyecto por defecto para solicitudes existentes")
        
    except Exception as e:
        print(f"❌ Error creando migración: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    crear_migracion()
