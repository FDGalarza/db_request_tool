import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import UserProfile, Solicitud

def diagnostico_completo_boton():
    """
    Diagnóstico completo del problema del botón
    """
    try:
        print("🔍 DIAGNÓSTICO COMPLETO DEL BOTÓN GENERAR SCRIPT")
        print("=" * 60)
        
        # 1. Verificar usuario DB
        try:
            user_db = User.objects.get(username='db_user')
            profile_db = UserProfile.objects.get(user=user_db)
            print(f"✅ Usuario DB: {user_db.username}")
            print(f"✅ Rol: {profile_db.role} ({profile_db.get_role_display()})")
        except User.DoesNotExist:
            print("❌ Usuario 'db_user' no encontrado")
            return
        except UserProfile.DoesNotExist:
            print("❌ Perfil de 'db_user' no encontrado")
            return
        
        # 2. Buscar solicitud específica para probar
        solicitud_test = Solicitud.objects.filter(
            tipo_archivo='excel',
            archivo_adjunto__isnull=False,
            script_sql_generado__isnull=True
        ).first()
        
        if not solicitud_test:
            print("❌ No hay solicitudes de prueba disponibles")
            return
        
        print(f"\n📋 SOLICITUD DE PRUEBA: #{solicitud_test.id}")
        print(f"   Tipo: {solicitud_test.get_tipo_solicitud_display()}")
        print(f"   Usuario: {solicitud_test.usuario.username}")
        print(f"   Archivo: {solicitud_test.archivo_adjunto.name}")
        print(f"   Tipo archivo: {solicitud_test.tipo_archivo}")
        print(f"   Script generado: {bool(solicitud_test.script_sql_generado)}")
        
        # 3. Probar métodos del modelo
        print(f"\n🧪 PROBANDO MÉTODOS DEL MODELO:")
        
        puede_generar = solicitud_test.puede_generar_script(user_db)
        puede_ver = solicitud_test.puede_ver_script(user_db)
        puede_descargar = solicitud_test.puede_descargar_script(user_db)
        
        print(f"   puede_generar_script(db_user): {puede_generar}")
        print(f"   puede_ver_script(db_user): {puede_ver}")
        print(f"   puede_descargar_script(db_user): {puede_descargar}")
        
        # 4. Simular exactamente lo que hace la vista
        print(f"\n🎭 SIMULANDO LA VISTA detalle_solicitud:")
        
        # Como en la vista
        user_profile = UserProfile.objects.get_or_create(user=user_db)[0]
        print(f"   user_profile.role: {user_profile.role}")
        
        # Variables del contexto (como en la vista)
        mostrar_script = solicitud_test.puede_ver_script(user_db)
        puede_generar_script = solicitud_test.puede_generar_script(user_db)
        puede_descargar_script = solicitud_test.puede_descargar_script(user_db)
        
        print(f"   mostrar_script: {mostrar_script}")
        print(f"   puede_generar_script: {puede_generar_script}")
        print(f"   puede_descargar_script: {puede_descargar_script}")
        
        # 5. Probar condiciones del template
        print(f"\n🎯 CONDICIONES DEL TEMPLATE:")
        
        # Condición 1: Script ya generado
        condicion1 = mostrar_script and solicitud_test.script_sql_generado
        print(f"   1. Mostrar script existente: {condicion1}")
        print(f"      (mostrar_script={mostrar_script} AND script_generado={bool(solicitud_test.script_sql_generado)})")
        
        # Condición 2: Botón generar (LA IMPORTANTE)
        condicion2 = puede_generar_script and solicitud_test.archivo_adjunto and not solicitud_test.script_sql_generado
        print(f"   2. Mostrar botón generar: {condicion2}")
        print(f"      (puede_generar={puede_generar_script} AND tiene_archivo={bool(solicitud_test.archivo_adjunto)} AND no_script={not bool(solicitud_test.script_sql_generado)})")
        
        # Condición 3: Mensaje de espera
        condicion3 = solicitud_test.archivo_adjunto and solicitud_test.tipo_archivo == 'excel' and not puede_generar_script
        print(f"   3. Mostrar mensaje espera: {condicion3}")
        print(f"      (tiene_archivo={bool(solicitud_test.archivo_adjunto)} AND tipo_excel={solicitud_test.tipo_archivo == 'excel'} AND no_puede_generar={not puede_generar_script})")
        
        # 6. Resultado esperado
        print(f"\n🎯 RESULTADO ESPERADO:")
        if condicion1:
            print("   ✅ Debería mostrar script existente")
        elif condicion2:
            print("   ✅ DEBERÍA MOSTRAR EL BOTÓN GENERAR SCRIPT")
            print(f"   🔗 URL para probar: http://127.0.0.1:8000/solicitud/{solicitud_test.id}/")
        elif condicion3:
            print("   ⏳ Debería mostrar mensaje de espera")
        else:
            print("   ❌ No debería mostrar nada especial")
        
        # 7. Verificar archivo físico
        print(f"\n📁 VERIFICANDO ARCHIVO FÍSICO:")
        if solicitud_test.archivo_adjunto:
            archivo_path = solicitud_test.archivo_adjunto.path
            existe = os.path.exists(archivo_path)
            print(f"   Ruta: {archivo_path}")
            print(f"   Existe: {existe}")
            if existe:
                size = os.path.getsize(archivo_path)
                print(f"   Tamaño: {size} bytes")
        
        # 8. Información adicional para debug
        print(f"\n🐛 INFORMACIÓN ADICIONAL:")
        print(f"   ID de la solicitud: {solicitud_test.id}")
        print(f"   Estado: {solicitud_test.estado}")
        print(f"   Proyecto: {solicitud_test.proyecto.codigo if solicitud_test.proyecto else 'Sin proyecto'}")
        
        print(f"\n📋 PASOS PARA PROBAR:")
        print("1. Reinicia el servidor Django")
        print("2. Inicia sesión como 'db_user'")
        print(f"3. Ve a: http://127.0.0.1:8000/solicitud/{solicitud_test.id}/")
        print("4. Busca la sección 'Script SQL' en la página")
        print("5. Deberías ver un botón verde 'Generar Script SQL'")
        
    except Exception as e:
        print(f"❌ Error en diagnóstico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostico_completo_boton()
