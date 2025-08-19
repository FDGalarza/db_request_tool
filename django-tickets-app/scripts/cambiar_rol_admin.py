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

def cambiar_rol_admin():
    """
    Cambia el rol del usuario administrador a 'admin'
    """
    try:
        # Buscar el usuario administrador (superuser)
        admin_users = User.objects.filter(is_superuser=True)
        
        if not admin_users.exists():
            print("❌ No se encontraron usuarios administradores (superuser)")
            return
        
        for admin_user in admin_users:
            print(f"🔍 Procesando usuario: {admin_user.username}")
            
            # Obtener o crear el perfil del usuario
            perfil, created = UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={
                    'role': 'admin'
                }
            )
            
            if created:
                print(f"✅ Perfil creado para {admin_user.username} con rol 'admin'")
            else:
                # Actualizar el rol si ya existe
                rol_anterior = perfil.role
                perfil.role = 'admin'
                perfil.activo = True
                perfil.save()
                print(f"✅ Rol actualizado para {admin_user.username}: {rol_anterior} → admin")
            
            # Mostrar información del perfil
            print(f"   📋 Información del perfil:")
            print(f"   - Usuario: {perfil.user.username}")
            print(f"   - Email: {perfil.user.email}")
            print(f"   - Rol: {perfil.role}")
           
            print(f"   - Activo: {perfil.activo}")
            print(f"   - Es superuser: {perfil.user.is_superuser}")
            print(f"   - Es staff: {perfil.user.is_staff}")
            print()
        
        print("🎉 Proceso completado exitosamente")
        
    except Exception as e:
        print(f"❌ Error al cambiar rol del administrador: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Iniciando cambio de rol para usuario administrador...")
    cambiar_rol_admin()
