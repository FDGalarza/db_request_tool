#!/usr/bin/env python
"""
Script para configurar las estructuras por defecto de archivos Excel
"""
import os
import sys
import django
import json


#Agrega el path raíz del proyecto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tickets_project.settings')
django.setup()

from tickets.models import ConfiguracionEstructuraExcel

def crear_configuraciones_por_defecto():
    """Crear configuraciones por defecto para cada tipo de solicitud"""
    
    configuraciones = {
        'crear_tabla': {
            'descripcion': 'Estructura para creación de tablas con información completa según formato estándar',
            'estructura': {
                'columnas_requeridas': [
                    'Nombre de la columna', 'Tipo de dato', 'Es nullable', 'Es llave primaria'
                ],
                'columnas_opcionales': [
                    'por por defecto', 'es foranea', 'tabla referencia', 'Comentario de campo'
                ],
                'columnas_info_tabla': [
                    'nombre tabla', 'comentario tabla'
                ],
                'tipos_datos': {
                    'Nombre de la columna': 'string',
                    'Tipo de dato': 'string',
                    'Es nullable': 'string',
                    'por por defecto': 'string',
                    'Es llave primaria': 'string',
                    'es foranea': 'string',
                    'tabla referencia': 'string',
                    'Comentario de campo': 'string'
                },
                'validaciones_adicionales': {
                    'Es nullable': ['Si', 'No', 'YES', 'NO', 'Y', 'N', 'True', 'False', '1', '0'],
                    'Es llave primaria': ['Si', 'No', 'YES', 'NO', 'Y', 'N', 'True', 'False', '1', '0'],
                    'es foranea': ['Si', 'No', 'YES', 'NO', 'Y', 'N', 'True', 'False', '1', '0'],
                    'tipos_dato_permitidos': [
                        'VARCHAR(50)', 'VARCHAR(100)', 'VARCHAR(255)', 'VARCHAR(500)',
                        'CHAR(1)', 'CHAR(10)', 'TEXT', 'LONGTEXT', 'MEDIUMTEXT', 'TINYTEXT',
                        'INT', 'BIGINT', 'SMALLINT', 'TINYINT', 'MEDIUMINT',
                        'INT AUTO_INCREMENT', 'BIGINT AUTO_INCREMENT',
                        'DECIMAL(10,2)', 'DECIMAL(15,2)', 'NUMERIC(10,2)', 'FLOAT', 'DOUBLE',
                        'DATE', 'DATETIME', 'TIMESTAMP', 'TIME', 'YEAR',
                        'BOOLEAN', 'BOOL', 'BIT',
                        'JSON', 'BLOB', 'LONGBLOB', 'MEDIUMBLOB', 'TINYBLOB',
                        'ENUM', 'SET'
                    ]
                },
                'estructura_especial': {
                    'tiene_info_tabla': True,
                    'descripcion_formato': 'Primera fila: nombre tabla, comentario tabla. Siguientes filas: definiciones de columnas',
                    'ejemplo_uso': 'Fila 1: usuarios | Tabla de usuarios del sistema. Fila 2: id | INT | No | | Si | No | | Identificador único'
                },
                'ejemplo_datos': [
                    {
                        'fila': 1,
                        'nombre tabla': 'usuarios',
                        'comentario tabla': 'Tabla de usuarios del sistema'
                    },
                    {
                        'fila': 2,
                        'Nombre de la columna': 'id',
                        'Tipo de dato': 'INT AUTO_INCREMENT',
                        'Es nullable': 'No',
                        'por por defecto': '',
                        'Es llave primaria': 'Si',
                        'es foranea': 'No',
                        'tabla referencia': '',
                        'Comentario de campo': 'Identificador único del usuario'
                    },
                    {
                        'fila': 3,
                        'Nombre de la columna': 'nombre',
                        'Tipo de dato': 'VARCHAR(100)',
                        'Es nullable': 'No',
                        'por por defecto': '',
                        'Es llave primaria': 'No',
                        'es foranea': 'No',
                        'tabla referencia': '',
                        'Comentario de campo': 'Nombre completo del usuario'
                    },
                    {
                        'fila': 4,
                        'Nombre de la columna': 'email',
                        'Tipo de dato': 'VARCHAR(255)',
                        'Es nullable': 'No',
                        'por por defecto': '',
                        'Es llave primaria': 'No',
                        'es foranea': 'No',
                        'tabla referencia': '',
                        'Comentario de campo': 'Correo electrónico único'
                    },
                    {
                        'fila': 5,
                        'Nombre de la columna': 'fecha_creacion',
                        'Tipo de dato': 'DATETIME',
                        'Es nullable': 'No',
                        'por por defecto': 'CURRENT_TIMESTAMP',
                        'Es llave primaria': 'No',
                        'es foranea': 'No',
                        'tabla referencia': '',
                        'Comentario de campo': 'Fecha de creación del registro'
                    },
                    {
                        'fila': 6,
                        'Nombre de la columna': 'departamento_id',
                        'Tipo de dato': 'INT',
                        'Es nullable': 'Si',
                        'por por defecto': '',
                        'Es llave primaria': 'No',
                        'es foranea': 'Si',
                        'tabla referencia': 'departamentos',
                        'Comentario de campo': 'Referencia al departamento'
                    }
                ]
            }
        },
        
        'modificar_tabla': {
            'descripcion': 'Estructura para modificación de tablas existentes',
            'estructura': {
                'columnas_requeridas': ['nombre_tabla', 'nombre_columna', 'accion', 'tipo_dato'],
                'columnas_opcionales': ['nullable', 'default_value', 'comentario'],
                'tipos_datos': {
                    'nombre_tabla': 'string',
                    'nombre_columna': 'string',
                    'accion': 'string',
                    'tipo_dato': 'string',
                    'nullable': 'string',
                    'default_value': 'string',
                    'comentario': 'string'
                },
                'validaciones_adicionales': {
                    'accion': ['ADD', 'DROP', 'MODIFY', 'RENAME'],
                    'nullable': ['Si', 'No', 'YES', 'NO', 'Y', 'N']
                },
                'ejemplo_datos': [
                    {
                        'nombre_tabla': 'usuarios',
                        'nombre_columna': 'telefono',
                        'accion': 'ADD',
                        'tipo_dato': 'VARCHAR(20)',
                        'nullable': 'Si',
                        'comentario': 'Número de teléfono del usuario'
                    }
                ]
            }
        },
        
        'crear_usuarios': {
            'descripcion': 'Estructura para creación de usuarios de base de datos',
            'estructura': {
                'columnas_requeridas': ['nombre_usuario', 'rol', 'permisos'],
                'columnas_opcionales': ['password', 'host', 'comentario'],
                'tipos_datos': {
                    'nombre_usuario': 'string',
                    'rol': 'string',
                    'permisos': 'string',
                    'password': 'string',
                    'host': 'string',
                    'comentario': 'string'
                },
                'validaciones_adicionales': {
                    'host': ['%', 'localhost', '192.168.%'],
                    'permisos': ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'ALL PRIVILEGES']
                },
                'ejemplo_datos': [
                    {
                        'nombre_usuario': 'app_user',
                        'rol': 'aplicacion',
                        'permisos': 'SELECT,INSERT,UPDATE',
                        'host': '%',
                        'comentario': 'Usuario para aplicación web'
                    }
                ]
            }
        },
        
        'asignar_permisos': {
            'descripcion': 'Estructura para asignación de permisos a usuarios',
            'estructura': {
                'columnas_requeridas': ['usuario', 'tabla', 'permisos'],
                'columnas_opcionales': ['host', 'comentario'],
                'tipos_datos': {
                    'usuario': 'string',
                    'tabla': 'string',
                    'permisos': 'string',
                    'host': 'string',
                    'comentario': 'string'
                },
                'validaciones_adicionales': {
                    'permisos': ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'ALL PRIVILEGES'],
                    'host': ['%', 'localhost', '192.168.%']
                },
                'ejemplo_datos': [
                    {
                        'usuario': 'app_user',
                        'tabla': 'usuarios',
                        'permisos': 'SELECT,INSERT,UPDATE',
                        'host': '%',
                        'comentario': 'Permisos para tabla usuarios'
                    }
                ]
            }
        },
        
        'crear_bd': {
            'descripcion': 'Estructura para creación de bases de datos',
            'estructura': {
                'columnas_requeridas': ['nombre_bd', 'charset', 'collation'],
                'columnas_opcionales': ['comentario'],
                'tipos_datos': {
                    'nombre_bd': 'string',
                    'charset': 'string',
                    'collation': 'string',
                    'comentario': 'string'
                },
                'validaciones_adicionales': {
                    'charset': ['utf8mb4', 'utf8', 'latin1'],
                    'collation': ['utf8mb4_unicode_ci', 'utf8mb4_general_ci', 'utf8_general_ci']
                },
                'ejemplo_datos': [
                    {
                        'nombre_bd': 'mi_aplicacion',
                        'charset': 'utf8mb4',
                        'collation': 'utf8mb4_unicode_ci',
                        'comentario': 'Base de datos principal'
                    }
                ]
            }
        },
        
        'crear_esquemas': {
            'descripcion': 'Estructura para creación de esquemas',
            'estructura': {
                'columnas_requeridas': ['nombre_esquema', 'propietario'],
                'columnas_opcionales': ['comentario'],
                'tipos_datos': {
                    'nombre_esquema': 'string',
                    'propietario': 'string',
                    'comentario': 'string'
                },
                'ejemplo_datos': [
                    {
                        'nombre_esquema': 'ventas',
                        'propietario': 'admin',
                        'comentario': 'Esquema para módulo de ventas'
                    }
                ]
            }
        }
    }
    
    for tipo_solicitud, config in configuraciones.items():
        estructura_json = json.dumps(config['estructura'], indent=2, ensure_ascii=False)
        
        configuracion, created = ConfiguracionEstructuraExcel.objects.get_or_create(
            tipo_solicitud=tipo_solicitud,
            defaults={
                'descripcion': config['descripcion'],
                'estructura_json': estructura_json
            }
        )
        
        if created:
            print(f"✅ Configuración creada para: {tipo_solicitud}")
        else:
            # Actualizar la configuración existente
            configuracion.descripcion = config['descripcion']
            configuracion.estructura_json = estructura_json
            configuracion.save()
            print(f"🔄 Configuración actualizada para: {tipo_solicitud}")

if __name__ == '__main__':
    print("Configurando estructuras de archivos Excel...")
    crear_configuraciones_por_defecto()
    print("¡Configuración completada!")
