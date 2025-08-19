import os
import sys
import django

#Agrega el path raíz del proyecto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import UserProfile, Solicitud

def debug_template_variables():
    """
    Simula las variables que se pasan al template
    """
    try:
        print("🐛 DEBUG DE VARIABLES DEL TEMPLATE")
        print("=" * 45)
        
        # Usuario DB
        user_db = User.objects.get(username='db_user')
        user_profile = UserProfile.objects.get(user=user_db)
        
        print(f"👤 Usuario: {user_db.username}")
        print(f"🎭 Rol: {user_profile.role} ({user_profile.get_role_display()})")
        
        # Solicitud con Excel
        solicitud = Solicitud.objects.filter(
            tipo_archivo='excel',
            archivo_adjunto__isnull=False
        ).first()
        
        if not solicitud:
            print("❌ No hay solicitudes con Excel")
            return
        
        print(f"\n📋 Solicitud: #{solicitud.id}")
        print(f"📁 Archivo: {solicitud.archivo_adjunto.name}")
        print(f"📊 Tipo archivo: {solicitud.tipo_archivo}")
        print(f"💾 Script generado: {'Sí' if solicitud.script_sql_generado else 'No'}")
        
        # Simular variables del contexto (como en la vista)
        puede_generar_script = solicitud.puede_generar_script(user_db)
        mostrar_script = solicitud.puede_ver_script(user_db)
        puede_descargar_script = solicitud.puede_descargar_script(user_db)
        
        print(f"\n🔍 VARIABLES DEL CONTEXTO:")
        print(f"   puede_generar_script: {puede_generar_script}")
        print(f"   mostrar_script: {mostrar_script}")
        print(f"   puede_descargar_script: {puede_descargar_script}")
        
        # Condiciones del template
        print(f"\n🎯 CONDICIONES DEL TEMPLATE:")
        
        # Condición 1: Script ya generado
        condicion1 = mostrar_script and solicitud.script_sql_generado
        print(f"   1. Mostrar script generado: {condicion1}")
        print(f"      (mostrar_script={mostrar_script} AND script_generado={bool(solicitud.script_sql_generado)})")
        
        # Condición 2: Botón generar script
        condicion2 = puede_generar_script and solicitud.archivo_adjunto and not solicitud.script_sql_generado
        print(f"   2. Mostrar botón generar: {condicion2}")
        print(f"      (puede_generar={puede_generar_script} AND tiene_archivo={bool(solicitud.archivo_adjunto)} AND no_script={not bool(solicitud.script_sql_generado)})")
        
        # Condición 3: Mensaje para usuarios sin permisos
        condicion3 = solicitud.archivo_adjunto and solicitud.tipo_archivo == 'excel' and not puede_generar_script
        print(f"   3. Mostrar mensaje espera: {condicion3}")
        print(f"      (tiene_archivo={bool(solicitud.archivo_adjunto)} AND tipo_excel={solicitud.tipo_archivo == 'excel'} AND no_puede_generar={not puede_generar_script})")
        
        print(f"\n🎯 RESULTADO ESPERADO:")
        if condicion1:
            print("   ✅ Debería mostrar el script generado")
        elif condicion2:
            print("   ✅ Debería mostrar el BOTÓN GENERAR SCRIPT")
            print(f"   🔗 URL: http://127.0.0.1:8000/solicitud/{solicitud.id}/")
        elif condicion3:
            print("   ⏳ Debería mostrar mensaje de espera")
        else:
            print("   ❌ No debería mostrar nada especial")
        
    except Exception as e:
        print(f"❌ Error en debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_template_variables()
