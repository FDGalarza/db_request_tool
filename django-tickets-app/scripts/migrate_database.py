#!/usr/bin/env python
"""
Script para ejecutar migraciones de Django
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

 #Agrega el path raíz del proyecto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')

def run_migrations():
    """Ejecutar migraciones de Django"""
    print("Ejecutando migraciones...")
    
    # Crear migraciones
    execute_from_command_line(['manage.py', 'makemigrations'])
    
    # Aplicar migraciones
    execute_from_command_line(['manage.py', 'migrate'])
    
    print("Migraciones completadas!")

if __name__ == '__main__':
    run_migrations()
