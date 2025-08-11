#!/usr/bin/env python
"""
Script para configurar la base de datos inicial
"""
import os
import sys
import django

# Agrega el directorio raíz del proyecto al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import UserProfile

def create_admin_user():
    """Crear usuario administrador por defecto"""
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        UserProfile.objects.create(user=admin_user, role='admin')
        print("Usuario administrador creado: admin/admin123")
    else:
        print("Usuario administrador ya existe")

def create_sample_users():
    """Crear usuarios de ejemplo para cada rol"""
    sample_users = [
        {'username': 'dev_user', 'email': 'dev@example.com', 'role': 'dev'},
        {'username': 'db_user', 'email': 'db@example.com', 'role': 'db'},
        {'username': 'devops_user', 'email': 'devops@example.com', 'role': 'devops'},
    ]
    
    for user_data in sample_users:
        if not User.objects.filter(username=user_data['username']).exists():
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password='password123'
            )
            UserProfile.objects.create(user=user, role=user_data['role'])
            print(f"Usuario {user_data['username']} creado con rol {user_data['role']}")
        else:
            print(f"Usuario {user_data['username']} ya existe")

if __name__ == '__main__':
    print("Configurando base de datos...")
    create_admin_user()
    create_sample_users()
    print("Configuración completada!")
