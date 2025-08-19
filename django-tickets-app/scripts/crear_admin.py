import os
import sys
import django
import getpass

# Agrega el directorio raíz del proyecto al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import PerfilUsuario

def crear_usuario_admin():
    """
    Crea un usuario administrador con rol admin
    """
    try:
        print("🔧 CREACIÓN DE USUARIO ADMINISTRADOR")
        print("=" * 40)
        
        username = input("👤 Nombre de usuario: ").strip()
        if not username:
            print("❌ El nombre de usuario es obligatorio")
            return
        
        # Verificar si el usuario ya existe
        if User.objects.filter(username=username).exists():
            print(f"⚠️  El usuario '{username}' ya existe")
            respuesta = input("¿Desea actualizar su rol a admin? (s/n): ").strip().lower()
            if respuesta == 's':
                usuario = User.objects.get(username=username)
                perfil, created = PerfilUsuario.objects.get_or_create(
                    usuario=usuario,
                    defaults={'rol': 'admin', 'departamento': 'Administración', 'activo': True}
                )
                if not created:
                    perfil.rol = 'admin'
                    perfil.activo = True
                    perfil.save()
                print(f"✅ Rol actualizado para {username}")
            return
        
        email = input("📧 Email: ").strip()
        password = getpass.getpass("🔒 Contraseña: ")
        
        if not password:
            print("❌ La contraseña es obligatoria")
            return
        
        # Crear usuario
        usuario = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        
        # Crear perfil
        perfil = PerfilUsuario.objects.create(
            usuario=usuario,
            rol='admin',
            departamento='Administración',
            activo=True
        )
        
        print(f"✅ Usuario administrador '{username}' creado exitosamente")
        print(f"   📧 Email: {email}")
        print(f"   🎭 Rol: {perfil.get_rol_display()}")
        print(f"   🏢 Departamento: {perfil.departamento}")
        
    except Exception as e:
        print(f"❌ Error al crear usuario administrador: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    crear_usuario_admin()
