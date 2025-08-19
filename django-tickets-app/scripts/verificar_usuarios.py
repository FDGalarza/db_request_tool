import os
import sys
import django


# Agrega el directorio raíz del proyecto al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import UserProfile

def verificar_usuarios():
    """
    Muestra información de todos los usuarios y sus roles
    """
    try:
        print("👥 LISTADO DE USUARIOS Y ROLES")
        print("=" * 50)
        
        usuarios = User.objects.all().order_by('username')
        
        if not usuarios.exists():
            print("❌ No se encontraron usuarios en el sistema")
            return
        
        for usuario in usuarios:
            print(f"🔹 Usuario: {usuario.username}")
            print(f"   📧 Email: {usuario.email}")
            print(f"   🔑 Superuser: {'Sí' if usuario.is_superuser else 'No'}")
            print(f"   👤 Staff: {'Sí' if usuario.is_staff else 'No'}")
            print(f"   ✅ Activo: {'Sí' if usuario.is_active else 'No'}")
            
            try:
                perfil = UserProfile.objects.get(usuario=usuario)
                print(f"   🎭 Rol: {perfil.get_rol_display()}")
                print(f"   🏢 Departamento: {perfil.departamento}")
                print(f"   📞 Teléfono: {perfil.telefono or 'No especificado'}")
                print(f"   🟢 Perfil activo: {'Sí' if perfil.activo else 'No'}")
            except UserProfile.DoesNotExist:
                print(f"   ⚠️  Sin perfil de usuario")
            
            print("-" * 30)
        
        print(f"\n📊 Total de usuarios: {usuarios.count()}")
        
        # Estadísticas por rol
        print("\n📈 ESTADÍSTICAS POR ROL:")
        roles_stats = {}
        for usuario in usuarios:
            try:
                perfil = UserProfile.objects.get(usuario=usuario)
                rol = perfil.get_rol_display()
                roles_stats[rol] = roles_stats.get(rol, 0) + 1
            except UserProfile.DoesNotExist:
                roles_stats['Sin perfil'] = roles_stats.get('Sin perfil', 0) + 1
        
        for rol, cantidad in roles_stats.items():
            print(f"   {rol}: {cantidad}")
        
    except Exception as e:
        print(f"❌ Error al verificar usuarios: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Verificando usuarios del sistema...")
    verificar_usuarios()
