import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import UserProfile, Solicitud, Proyecto
from django.core.files.base import ContentFile
import pandas as pd
import io

def crear_solicitud_test():
    """
    Crea una solicitud de prueba con archivo Excel
    """
    try:
        print("🧪 CREANDO SOLICITUD DE PRUEBA")
        print("=" * 40)
        
        # Buscar usuario DB
        try:
            user_db = User.objects.get(username='db_user')
            print(f"✅ Usuario DB: {user_db.username}")
        except User.DoesNotExist:
            print("❌ Usuario 'db_user' no encontrado")
            return
        
        # Buscar proyecto por defecto
        proyecto = Proyecto.objects.filter(codigo='DEFAULT').first()
        if not proyecto:
            print("❌ Proyecto DEFAULT no encontrado")
            return
        
        print(f"✅ Proyecto: {proyecto.codigo}")
        
        # Crear archivo Excel de prueba
        print("📊 Creando archivo Excel de prueba...")
        
        # Datos para crear tabla
        data = {
            'tabla_nombre': ['usuarios_test', 'productos_test'],
            'columnas': [
                'id:INT:11:NO:AUTO_INCREMENT,nombre:VARCHAR:100:NO:,email:VARCHAR:150:YES:',
                'id:INT:11:NO:AUTO_INCREMENT,nombre:VARCHAR:200:NO:,precio:DECIMAL:10,2:NO:'
            ],
            'descripcion': ['Tabla de usuarios de prueba', 'Tabla de productos de prueba']
        }
        
        df = pd.DataFrame(data)
        
        # Crear archivo en memoria
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, sheet_name='Tablas')
        excel_buffer.seek(0)
        
        # Crear solicitud
        solicitud = Solicitud.objects.create(
            proyecto=proyecto,
            tipo_solicitud='crear_tabla',
            tipo_archivo='excel',
            estado='registrada',
            descripcion='Solicitud de prueba para generar script SQL',
            usuario=user_db,
            base_datos_aplicacion='test_database',
            correo_notificacion=user_db.email or 'test@example.com'
        )
        
        # Adjuntar archivo Excel
        archivo_content = ContentFile(excel_buffer.getvalue())
        solicitud.archivo_adjunto.save(
            f'test_crear_tablas_{solicitud.id}.xlsx',
            archivo_content,
            save=True
        )
        
        print(f"✅ Solicitud creada: #{solicitud.id}")
        print(f"   Tipo: {solicitud.get_tipo_solicitud_display()}")
        print(f"   Archivo: {solicitud.archivo_adjunto.name}")
        print(f"   Usuario: {solicitud.usuario.username}")
        
        # Verificar condiciones
        puede_generar = solicitud.puede_generar_script(user_db)
        print(f"   Puede generar script: {puede_generar}")
        
        print(f"\n🎯 SOLICITUD DE PRUEBA LISTA:")
        print(f"   URL: http://127.0.0.1:8000/solicitud/{solicitud.id}/")
        print("   Inicia sesión como 'db_user' y ve a esa URL")
        print("   Deberías ver el botón 'Generar Script SQL'")
        
        return solicitud.id
        
    except Exception as e:
        print(f"❌ Error creando solicitud de prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    crear_solicitud_test()
