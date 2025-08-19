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

def diagnosticar_permisos():
    """
    Diagnostica los permisos de generación de scripts
    """
    try:
        print("🔍 DIAGNÓSTICO DE PERMISOS PARA GENERAR SCRIPTS")
        print("=" * 60)
        
        # 1. Verificar todos los usuarios y sus roles
        print("\n👥 USUARIOS Y ROLES:")
        for user in User.objects.all():
            try:
                profile = UserProfile.objects.get(user=user)
                print(f"   🔹 {user.username} - Rol: {profile.role} ({profile.get_role_display()})")
                print(f"      Email: {user.email}")
                print(f"      Activo: {user.is_active}")
                print(f"      Superuser: {user.is_superuser}")
                print(f"      Staff: {user.is_staff}")
                print()
            except UserProfile.DoesNotExist:
                print(f"   ⚠️  {user.username} - SIN PERFIL")
                print()
        
        # 2. Probar permisos de generación de scripts
        print("\n🧪 PRUEBA DE PERMISOS DE GENERACIÓN DE SCRIPTS:")
        
        # Buscar una solicitud de ejemplo
        solicitud_ejemplo = Solicitud.objects.filter(
            tipo_solicitud__in=Solicitud.TIPOS_BD
        ).first()
        
        if solicitud_ejemplo:
            print(f"   📋 Probando con solicitud #{solicitud_ejemplo.id} - {solicitud_ejemplo.get_tipo_solicitud_display()}")
            print()
            
            for user in User.objects.all():
                try:
                    profile = UserProfile.objects.get(user=user)
                    puede_generar = solicitud_ejemplo.puede_generar_script(user)
                    puede_ver = solicitud_ejemplo.puede_ver_script(user)
                    puede_descargar = solicitud_ejemplo.puede_descargar_script(user)
                    
                    print(f"   👤 {user.username} ({profile.role}):")
                    print(f"      ✅ Puede generar script: {puede_generar}")
                    print(f"      👁️  Puede ver script: {puede_ver}")
                    print(f"      📥 Puede descargar script: {puede_descargar}")
                    print()
                    
                except UserProfile.DoesNotExist:
                    print(f"   👤 {user.username}: SIN PERFIL")
                    print()
        else:
            print("   ⚠️  No hay solicitudes de BD para probar")
        
        # 3. Verificar solicitudes con archivos Excel
        print("\n📊 SOLICITUDES CON ARCHIVOS EXCEL:")
        solicitudes_excel = Solicitud.objects.filter(
            tipo_archivo='excel',
            archivo_adjunto__isnull=False
        )
        
        print(f"   Total solicitudes con Excel: {solicitudes_excel.count()}")
        
        for solicitud in solicitudes_excel[:5]:  # Mostrar solo las primeras 5
            print(f"   📄 Solicitud #{solicitud.id}:")
            print(f"      Tipo: {solicitud.get_tipo_solicitud_display()}")
            print(f"      Usuario: {solicitud.usuario.username}")
            print(f"      Archivo: {solicitud.archivo_adjunto.name if solicitud.archivo_adjunto else 'Sin archivo'}")
            print(f"      Script generado: {'Sí' if solicitud.script_sql_generado else 'No'}")
            print()
        
        # 4. Verificar configuración de roles
        print("\n⚙️  CONFIGURACIÓN DE ROLES:")
        print("   Roles definidos en UserProfile.ROLES:")
        for role_code, role_name in UserProfile.ROLES:
            count = UserProfile.objects.filter(role=role_code).count()
            print(f"      {role_code}: {role_name} ({count} usuarios)")
        
        print("\n🎯 RECOMENDACIONES:")
        
        # Verificar si hay usuarios DB
        db_users = UserProfile.objects.filter(role='db')
        if not db_users.exists():
            print("   ⚠️  NO HAY USUARIOS CON ROL 'db' (Ingeniero de Bases de Datos)")
            print("   💡 Solución: Asignar rol 'db' a un usuario")
        else:
            print(f"   ✅ Hay {db_users.count()} usuario(s) con rol 'db'")
        
        # Verificar si hay usuarios admin
        admin_users = UserProfile.objects.filter(role='admin')
        if not admin_users.exists():
            print("   ⚠️  NO HAY USUARIOS CON ROL 'admin'")
            print("   💡 Solución: Asignar rol 'admin' a un superuser")
        else:
            print(f"   ✅ Hay {admin_users.count()} usuario(s) con rol 'admin'")
        
    except Exception as e:
        print(f"❌ Error en diagnóstico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnosticar_permisos()
