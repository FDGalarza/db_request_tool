import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import UserProfile, Solicitud

def test_final_boton():
    """
    Test final para verificar que el botón aparece
    """
    try:
        print("🎯 TEST FINAL - VERIFICACIÓN DEL BOTÓN")
        print("=" * 45)
        
        # Usuario DB
        user_db = User.objects.get(username='db_user')
        print(f"👤 Usuario: {user_db.username}")
        
        # Solicitud específica
        solicitud = Solicitud.objects.get(id=3)
        print(f"📋 Solicitud: #{solicitud.id}")
        print(f"   Tipo: {solicitud.get_tipo_solicitud_display()}")
        print(f"   Archivo: {solicitud.archivo_adjunto.name}")
        
        # Variables exactas del contexto
        puede_generar_script = solicitud.puede_generar_script(user_db)
        mostrar_script = solicitud.puede_ver_script(user_db)
        tiene_archivo = bool(solicitud.archivo_adjunto)
        ya_tiene_script = bool(solicitud.script_sql_generado)
        
        print(f"\n🔍 VARIABLES DEL CONTEXTO:")
        print(f"   puede_generar_script: {puede_generar_script}")
        print(f"   mostrar_script: {mostrar_script}")
        print(f"   tiene_archivo: {tiene_archivo}")
        print(f"   ya_tiene_script: {ya_tiene_script}")
        
        # Condición exacta del template
        condicion_boton = puede_generar_script and tiene_archivo and not ya_tiene_script
        print(f"\n🎯 CONDICIÓN DEL BOTÓN:")
        print(f"   {puede_generar_script} AND {tiene_archivo} AND {not ya_tiene_script} = {condicion_boton}")
        
        if condicion_boton:
            print(f"\n✅ EL BOTÓN DEBERÍA APARECER")
            print(f"🔗 URL: http://127.0.0.1:8000/solicitud/{solicitud.id}/")
            print(f"👤 Inicia sesión como: db_user")
            print(f"🎯 Busca el botón verde: 'Generar Script SQL'")
        else:
            print(f"\n❌ El botón NO debería aparecer")
        
        print(f"\n📋 INSTRUCCIONES:")
        print("1. Guarda el template actualizado")
        print("2. Reinicia el servidor Django")
        print("3. Inicia sesión como 'db_user'")
        print("4. Ve a la solicitud #3")
        print("5. Deberías ver el panel de Debug con todas las variables")
        print("6. Deberías ver el botón verde 'Generar Script SQL'")
        
    except Exception as e:
        print(f"❌ Error en test final: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_final_boton()
