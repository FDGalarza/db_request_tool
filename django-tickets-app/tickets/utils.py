import pandas as pd
import openpyxl
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from .models import ConfiguracionEstructuraExcel
import os
import json
import secrets
import string

def procesar_archivo_excel(solicitud):
    """
    Procesa archivos Excel según el tipo de solicitud y genera scripts SQL
    """
    if not solicitud.archivo_adjunto:
        print("DEBUG: No hay archivo adjunto")
        return None
    
    try:
        # Leer el archivo Excel
        file_path = solicitud.archivo_adjunto.path
        print(f"DEBUG: Procesando archivo: {file_path}")
        
        # Leer con diferentes métodos para debug
        df = pd.read_excel(file_path)
        print(f"DEBUG: DataFrame shape: {df.shape}")
        print(f"DEBUG: Columnas encontradas: {list(df.columns)}")
        print(f"DEBUG: Primeras 5 filas:")
        print(df.head())
        
        if solicitud.tipo_solicitud in ['crear_tabla', 'modificar_tabla']:
            return generar_script_tabla(df, solicitud.tipo_solicitud, solicitud.base_datos_aplicacion)
        elif solicitud.tipo_solicitud in ['asignar_permisos', 'crear_usuarios']:
            return generar_script_permisos_usuarios(solicitud.archivo_adjunto.path)
        elif solicitud.tipo_solicitud in ['crear_bd', 'crear_esquemas']:
            return generar_script_bd_esquemas(df, solicitud.tipo_solicitud, solicitud.base_datos_aplicacion)
        
    except Exception as e:
        print(f"ERROR procesando archivo Excel: {e}")
        import traceback
        traceback.print_exc()
        return f"-- Error procesando archivo: {str(e)}"
    
    return None

def validar_estructura_excel(archivo, tipo_solicitud):
    """
    Valida la estructura del archivo Excel según el tipo de solicitud.
    Soporta validación especial para crear_tabla y crear_usuarios.
    """
    try:
        if tipo_solicitud == 'crear_tabla':
            df = pd.read_excel(archivo)
            return validar_estructura_crear_tabla(df)

        elif tipo_solicitud == 'crear_usuarios':
            # Leer los metadatos (primeras 3 filas)
            metadata = pd.read_excel(archivo, nrows=3, header=None)

            # Verificar contenido de los metadatos
            campos_esperados = ['Nombre Usuario', 'base de datos', 'Es usuario Nuevo']
            for i, campo in enumerate(campos_esperados):
                valor = str(metadata.iloc[i, 0]).strip().lower()
                if valor != campo.strip().lower():
                    return False, f"Se esperaba '{campo}' en la fila {i+1}, columna A"

            # Verificar que las celdas de valor no estén vacías
            for i in range(3):
                if pd.isna(metadata.iloc[i, 1]) or str(metadata.iloc[i, 1]).strip() == "":
                    return False, f"El valor de '{campos_esperados[i]}' no puede estar vacío"

            # Leer tabla de permisos (a partir de la fila 5, es decir, índice 4)
            df_permisos = pd.read_excel(archivo, skiprows=4)

            columnas_requeridas = ['Esquema', 'Nombre Tabla', 'Select', 'Insert', 'Update', 'Delete']
            columnas_df = [str(col).strip().lower() for col in df_permisos.columns]
            faltantes = [col for col in columnas_requeridas if col.lower() not in columnas_df]

            if faltantes:
                return False, f"Faltan las siguientes columnas en la tabla de permisos: {', '.join(faltantes)}"

            if df_permisos.empty:
                return False, "La tabla de permisos está vacía"

            return True, "Estructura válida para creación de usuarios"

        else:
            # Para otros tipos, usar la configuración del modelo
            df = pd.read_excel(archivo)

            try:
                config = ConfiguracionEstructuraExcel.objects.get(tipo_solicitud=tipo_solicitud)
                estructura_esperada = config.get_estructura()
            except ConfiguracionEstructuraExcel.DoesNotExist:
                estructura_esperada = obtener_estructura_por_defecto(tipo_solicitud)

            columnas_requeridas = estructura_esperada.get('columnas_requeridas', [])
            columnas_encontradas = buscar_columnas_flexibles(df, columnas_requeridas)
            faltantes = [col for col in columnas_requeridas if col not in columnas_encontradas]

            if faltantes:
                return False, f"Faltan las siguientes columnas: {', '.join(faltantes)}"

            if df.empty:
                return False, "El archivo no contiene datos"

            return True, f"Estructura válida. Se encontraron {len(df)} filas de datos."

    except Exception as e:
        return False, f"Error al validar el archivo: {str(e)}"

    
def validar_estructura_crear_usuarios(df):
    """
    Valida que el archivo Excel para crear usuarios tenga la estructura correcta.
    Se espera que las primeras celdas contengan:
    - Nombre Usuario
    - base de datos
    - Es usuario Nuevo
    Y luego una tabla con permisos.
    """
    # Normalizamos los nombres de columna a lowercase sin espacios
    columnas = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
    
    columnas_requeridas = ['esquema', 'nombre_tabla', 'select', 'insert', 'update', 'delete']
    columnas_faltantes = [col for col in columnas_requeridas if col not in columnas]
    
    if columnas_faltantes:
        return False, f"Faltan las columnas de permisos: {', '.join(columnas_faltantes)}"
    
    # También puedes validar que las celdas superiores estén llenas, si estás usando múltiples hojas
    if df.empty or df.shape[0] == 0:
        return False, "El archivo está vacío o no contiene datos en la tabla de permisos."
    
    return True, "Estructura válida para creación de usuarios."


def buscar_columnas_flexibles(df, columnas_requeridas):
    """
    Busca columnas de manera flexible, considerando diferentes variaciones de nombres
    """
    columnas_encontradas = []
    
    # Mapeo de variaciones de nombres de columnas
    mapeo_columnas = {
        'nombre_usuario': ['nombre_usuario', 'nombre usuario', 'usuario', 'user', 'username'],
        'rol': ['rol', 'role', 'perfil', 'profile'],
        'permisos': ['permisos', 'permissions', 'privilegios', 'privileges'],
        'usuario': ['usuario', 'user', 'username', 'nombre_usuario'],
        'tabla': ['tabla', 'table', 'esquema', 'schema'],
        'nombre_bd': ['nombre_bd', 'nombre bd', 'database', 'base_datos', 'bd'],
        'charset': ['charset', 'character_set', 'codificacion', 'encoding'],
        'collation': ['collation', 'collate', 'cotejamiento'],
        'nombre_esquema': ['nombre_esquema', 'nombre esquema', 'schema', 'esquema'],
        'propietario': ['propietario', 'owner', 'dueño', 'usuario_propietario']
    }
    
    for col_requerida in columnas_requeridas:
        variaciones = mapeo_columnas.get(col_requerida, [col_requerida])
        
        for col_df in df.columns:
            col_df_lower = str(col_df).lower().strip()
            
            for variacion in variaciones:
                if variacion.lower() in col_df_lower or col_df_lower in variacion.lower():
                    columnas_encontradas.append(col_requerida)
                    break
            
            if col_requerida in columnas_encontradas:
                break
    
    return columnas_encontradas

def validar_estructura_crear_tabla(df):
    """
    Valida la estructura específica para creación de tablas - MEJORADA para buscar en contenido
    """
    try:
        # Verificar que tenga datos
        if df.empty:
            return False, "El archivo está vacío"
        
        # Buscar headers en el contenido del DataFrame
        fila_headers, columnas_headers = encontrar_headers_en_contenido(df)
        
        # Verificar columnas mínimas
        if 'nombre_columna' not in columnas_headers:
            return False, "No se encontró la columna de 'Nombre de la columna'. Verifique que el archivo tenga los headers correctos."
        
        if 'tipo_dato' not in columnas_headers:
            return False, "No se encontró la columna de 'Tipo de dato'. Verifique que el archivo tenga los headers correctos."
        
        # Contar filas con datos válidos después de los headers
        filas_validas = contar_filas_validas(df, fila_headers, columnas_headers)
        
        if filas_validas == 0:
            return False, "No se encontraron definiciones de columnas válidas después de los headers"
        
        return True, f"Estructura válida. Se encontraron {filas_validas} definiciones de columnas."
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Error validando estructura: {str(e)}"

def encontrar_headers_en_contenido(df):
    """
    Busca los headers dentro del contenido del DataFrame, no en los nombres de columnas
    """
    columnas_headers = {}
    fila_headers = None
    
    # Buscar en todas las filas y columnas
    for i in range(len(df)):
        headers_encontrados_en_fila = 0
        headers_temp = {}
        
        for j in range(len(df.columns)):
            valor = df.iloc[i, j]
            
            if pd.notna(valor):
                valor_str = str(valor).lower().strip()
                print(f"DEBUG: Fila {i}, Col {j}: '{valor_str}'")
                
                # Buscar headers específicos
                if valor_str in ['nombre de la columna', 'nombre_columna', 'columna']:
                    headers_temp['nombre_columna'] = j
                    headers_encontrados_en_fila += 1
                    print(f"DEBUG: Header 'nombre_columna' encontrado en fila {i}, col {j}")

                elif valor_str in ['accion', 'acción', 'operacion', 'operación']:
                    headers_temp['accion'] = j
                    headers_encontrados_en_fila += 1
                    print(f"DEBUG: Header 'accion' encontrado en fila {i}, col {j}")
                
                elif valor_str in ['tipo de dato', 'tipo_dato', 'tipo dato']:
                    headers_temp['tipo_dato'] = j
                    headers_encontrados_en_fila += 1
                    print(f"DEBUG: Header 'tipo_dato' encontrado en fila {i}, col {j}")
                
                elif valor_str in ['es nullable', 'nullable', 'acepta null', 'null']:
                    headers_temp['nullable'] = j
                    headers_encontrados_en_fila += 1
                    print(f"DEBUG: Header 'nullable' encontrado en fila {i}, col {j}")
                
                elif valor_str in ['es llave primaria', 'llave primaria', 'clave primaria', 'primary key', 'pk']:
                    headers_temp['primaria'] = j
                    headers_encontrados_en_fila += 1
                    print(f"DEBUG: Header 'primaria' encontrado en fila {i}, col {j}")
                
                elif valor_str in ['por defecto', 'default', 'valor defecto', 'por por defecto']:
                    headers_temp['default'] = j
                    print(f"DEBUG: Header 'default' encontrado en fila {i}, col {j}")
                
                elif valor_str in ['es foranea', 'foranea', 'foreign key', 'fk']:
                    headers_temp['foranea'] = j
                    print(f"DEBUG: Header 'foranea' encontrado en fila {i}, col {j}")
                
                elif valor_str in ['tabla referencia', 'referencia', 'tabla_referencia']:
                    headers_temp['referencia'] = j
                    print(f"DEBUG: Header 'referencia' encontrado en fila {i}, col {j}")
                
                elif valor_str in ['comentario de campo', 'comentario campo', 'comentario']:
                    headers_temp['comentario'] = j
                    print(f"DEBUG: Header 'comentario' encontrado en fila {i}, col {j}")
        
        # Si encontramos al menos los headers mínimos en esta fila
        if (
                ('nombre_columna' in headers_temp and 'tipo_dato' in headers_temp) or
                ('nombre_columna' in headers_temp and 'accion' in headers_temp)
           ):  # Al menos nombre_columna y tipo_dato
            fila_headers = i
            columnas_headers = headers_temp
            print(f"DEBUG: Fila de headers confirmada: {i} con {headers_encontrados_en_fila} headers")
            break
    
    return fila_headers, columnas_headers

def contar_filas_validas(df, fila_headers, columnas_headers):
    """
    Cuenta filas válidas después de encontrar los headers
    """
    if fila_headers is None or 'nombre_columna' not in columnas_headers:
        return 0
    
    filas_validas = 0
    col_nombre = columnas_headers['nombre_columna']
    
    # Empezar a contar desde la fila siguiente a los headers
    inicio_datos = fila_headers + 1
    
    for idx in range(inicio_datos, len(df)):
        valor_nombre = df.iloc[idx, col_nombre]
        print(f"DEBUG: Fila {idx}, valor nombre: '{valor_nombre}', tipo: {type(valor_nombre)}")
        
        if pd.notna(valor_nombre):
            valor_str = str(valor_nombre).strip()
            # Excluir valores vacíos y headers repetidos
            if (valor_str and 
                valor_str.lower() not in ['nombre de la columna', 'nombre_columna', 'nan', 'nombre tabla', 'comentario tabla'] and
                not valor_str.startswith('Unnamed') and
                len(valor_str) > 1):  # Al menos 2 caracteres
                filas_validas += 1
                print(f"DEBUG: Fila válida encontrada: {valor_str}")
    
    return filas_validas

def buscar_columnas_crear_tabla(df):
    """
    Busca columnas para crear_tabla - MEJORADA para buscar en contenido
    """
    # Usar la nueva función que busca en el contenido
    fila_headers, columnas_headers = encontrar_headers_en_contenido(df)
    return columnas_headers

def obtener_estructura_por_defecto(tipo_solicitud):
    """
    Retorna la estructura por defecto para cada tipo de solicitud - UNIFICADA
    """
    estructuras = {
        'crear_tabla': {
            'descripcion': 'Estructura para creación de tablas con información completa',
            'columnas_requeridas': [
                'Nombre de la columna', 'Tipo de dato', 'Es nullable', 'Es llave primaria'
            ],
            'columnas_opcionales': [
                'por por defecto', 'es foranea', 'tabla referencia', 'Comentario de campo'
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
            }
        },
        'modificar_tabla': {
            'columnas_requeridas': ['nombre_tabla', 'nombre_columna', 'accion', 'tipo_dato'],
            'tipos_datos': {
                'nombre_tabla': 'string',
                'nombre_columna': 'string',
                'accion': 'string',
                'tipo_dato': 'string'
            }
        },
        'crear_usuarios': {
            'columnas_requeridas': ['nombre_usuario', 'rol', 'permisos'],
            'tipos_datos': {
                'nombre_usuario': 'string',
                'rol': 'string',
                'permisos': 'string'
            }
        },
        'asignar_permisos': {
            'columnas_requeridas': ['usuario', 'tabla', 'permisos'],
            'tipos_datos': {
                'usuario': 'string',
                'tabla': 'string',
                'permisos': 'string'
            }
        },
        'crear_bd': {
            'columnas_requeridas': ['nombre_bd', 'charset', 'collation'],
            'tipos_datos': {
                'nombre_bd': 'string',
                'charset': 'string',
                'collation': 'string'
            }
        },
        'crear_esquemas': {
            'columnas_requeridas': ['nombre_esquema', 'propietario'],
            'tipos_datos': {
                'nombre_esquema': 'string',
                'propietario': 'string'
            }
        }
    }
    
    return estructuras.get(tipo_solicitud, {'columnas_requeridas': [], 'tipos_datos': {}})

def validar_tipo_columna(serie, tipo_esperado):
    """
    Valida que una serie de pandas tenga el tipo de dato esperado
    """
    if tipo_esperado == 'string':
        return serie.dtype == 'object' or serie.dtype.name.startswith('str')
    elif tipo_esperado == 'number':
        return pd.api.types.is_numeric_dtype(serie)
    elif tipo_esperado == 'date':
        return pd.api.types.is_datetime64_any_dtype(serie)
    
    return True

def generar_script_tabla(df, tipo_solicitud, base_datos):
    """
    Genera script SQL para creación o modificación de tablas - MEJORADA
    """
    try:

        script = f"-- Script generado automáticamente para {tipo_solicitud}\n"
        script += f"-- Base de datos/Aplicación: {base_datos}\n"
        script += f"-- Fecha de generación: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if tipo_solicitud == 'crear_tabla':
            # Buscar información de la tabla en las primeras filas
            nombre_tabla = None
            comentario_tabla = None
            
            print("DEBUG: Buscando información de tabla...")
            
            # Buscar en las primeras filas
            for i in range(min(5, len(df))):
                for j, col in enumerate(df.columns):
                    valor = df.iloc[i, j]
                    
                    if pd.notna(valor):
                        valor_str = str(valor).strip()
                        print(f"DEBUG: Fila {i}, Col {j} ('{col}'): '{valor_str}'")
                        
                        # Si encontramos "nombre tabla" en cualquier celda
                        if valor_str.lower() in ['nombre tabla', 'nombre_tabla']:
                            # El nombre de la tabla debería estar en la siguiente columna o fila
                            if j + 1 < len(df.columns):
                                nombre_tabla_valor = df.iloc[i, j + 1]
                                if pd.notna(nombre_tabla_valor):
                                    nombre_tabla = str(nombre_tabla_valor).strip()
                                    print(f"DEBUG: Nombre tabla encontrado: {nombre_tabla}")
                            # O en la siguiente fila, misma columna
                            elif i + 1 < len(df):
                                nombre_tabla_valor = df.iloc[i + 1, j]
                                if pd.notna(nombre_tabla_valor):
                                    nombre_tabla = str(nombre_tabla_valor).strip()
                                    print(f"DEBUG: Nombre tabla encontrado en fila siguiente: {nombre_tabla}")
                        
                        # Si encontramos "comentario tabla" o solo "comentario" en cualquier celda
                        elif (valor_str.lower() in ['comentario tabla', 'coemtario tabla', 'comentario_tabla', 'comentario'] or
                              'comentario' in valor_str.lower()):
                            # El comentario debería estar en la siguiente columna o fila
                            if j + 1 < len(df.columns):
                                comentario_valor = df.iloc[i, j + 1]
                                if pd.notna(comentario_valor):
                                    comentario_tabla = str(comentario_valor).strip()
                                    print(f"DEBUG: Comentario tabla encontrado: {comentario_tabla}")
                            elif i + 1 < len(df):
                                comentario_valor = df.iloc[i + 1, j]
                                if pd.notna(comentario_valor):
                                    comentario_tabla = str(comentario_valor).strip()
                                    print(f"DEBUG: Comentario tabla encontrado en fila siguiente: {comentario_tabla}")
            
            if not nombre_tabla:
                nombre_tabla = f"tabla_{base_datos.lower().replace(' ', '_')}"
                print(f"DEBUG: Usando nombre tabla por defecto: {nombre_tabla}")
            
            script += f"USE {base_datos};\n\n"
            script += f"-- Creación de tabla: {nombre_tabla}\n"
            if comentario_tabla:
                script += f"-- Comentario: {comentario_tabla}\n"
            script += f"CREATE TABLE {nombre_tabla} (\n"
            
            # Usar la función mejorada de búsqueda de headers
            fila_headers, columnas_headers = encontrar_headers_en_contenido(df)
            
            print(f"DEBUG: Headers mapeados: {columnas_headers}")
            print(f"DEBUG: Fila headers: {fila_headers}")
            
            columnas_sql = []
            claves_primarias = []
            claves_foraneas = []
            
            # Procesar filas después de los headers
            if fila_headers is not None and 'nombre_columna' in columnas_headers:
                inicio_datos = fila_headers + 1
                
                for i in range(inicio_datos, len(df)):
                    nombre_col_valor = df.iloc[i, columnas_headers['nombre_columna']]
                    
                    if pd.notna(nombre_col_valor):
                        nombre_col = str(nombre_col_valor).strip()
                        print(f"DEBUG: Procesando fila {i}, columna: '{nombre_col}'")
                        
                        # Saltar valores inválidos
                        if (not nombre_col or 
                            nombre_col.lower() in ['nombre de la columna', 'nombre_columna', 'nan'] or
                            nombre_col.startswith('Unnamed') or
                            len(nombre_col) <= 1):
                            print(f"DEBUG: Saltando fila {i} - valor inválido")
                            continue
                        
                        # Tipo de dato
                        tipo_dato = 'VARCHAR(255)'  # Default
                        if 'tipo_dato' in columnas_headers:
                            tipo_valor = df.iloc[i, columnas_headers['tipo_dato']]
                            if pd.notna(tipo_valor):
                                tipo_dato = str(tipo_valor).strip()
                                if not tipo_dato or tipo_dato.lower() in ['tipo de dato', 'nan']:
                                    tipo_dato = 'VARCHAR(255)'
                        
                        # Nullable
                        nullable = ""
                        if 'nullable' in columnas_headers:
                            nullable_valor = df.iloc[i, columnas_headers['nullable']]
                            if pd.notna(nullable_valor):
                                val_nullable = str(nullable_valor).strip().lower()
                                if val_nullable in ['no', 'false', '0', 'n']:
                                    nullable = "NOT NULL"
                        
                        # Valor por defecto
                        default_val = ""
                        if 'default' in columnas_headers:
                            default_valor = df.iloc[i, columnas_headers['default']]
                            if pd.notna(default_valor):
                                val_default = str(default_valor).strip()
                                if val_default and val_default.lower() not in ['', 'null', 'none', 'nan']:
                                    if val_default.upper() in ['CURRENT_TIMESTAMP', 'NOW()', 'UUID()']:
                                        default_val = f"DEFAULT {val_default}"
                                    else:
                                        default_val = f"DEFAULT '{val_default}'"
                        
                        # Comentario
                        comentario = ""
                        if 'comentario' in columnas_headers:
                            comentario_valor = df.iloc[i, columnas_headers['comentario']]
                            if pd.notna(comentario_valor):
                                val_comentario = str(comentario_valor).strip()
                                if val_comentario and val_comentario.lower() not in ['comentario de campo', 'nan']:
                                    comentario = f"COMMENT '{val_comentario}'"
                        
                        # Construir definición de columna
                        columna_def = f"    {nombre_col} {tipo_dato} {nullable} {default_val} {comentario}".strip()
                        columnas_sql.append(columna_def)
                        print(f"DEBUG: Columna agregada: {columna_def}")
                        
                        # Verificar si es clave primaria
                        if 'primaria' in columnas_headers:
                            primaria_valor = df.iloc[i, columnas_headers['primaria']]
                            if pd.notna(primaria_valor):
                                val_pk = str(primaria_valor).strip().lower()
                                if val_pk in ['si', 'yes', '1', 'true', 'y']:
                                    claves_primarias.append(nombre_col)
                                    print(f"DEBUG: Clave primaria: {nombre_col}")
                        
                        # Verificar si es clave foránea
                        if 'foranea' in columnas_headers:
                            foranea_valor = df.iloc[i, columnas_headers['foranea']]
                            if pd.notna(foranea_valor):
                                val_fk = str(foranea_valor).strip().lower()
                                if val_fk in ['si', 'yes', '1', 'true', 'y']:
                                    tabla_ref = ""
                                    if 'referencia' in columnas_headers:
                                        ref_valor = df.iloc[i, columnas_headers['referencia']]
                                        if pd.notna(ref_valor):
                                            tabla_ref = str(ref_valor).strip()
                                            if tabla_ref and tabla_ref.lower() not in ['tabla referencia', 'nan']:
                                                claves_foraneas.append((nombre_col, tabla_ref))
                                                print(f"DEBUG: Clave foránea: {nombre_col} -> {tabla_ref}")
            
            print(f"DEBUG: Total columnas procesadas: {len(columnas_sql)}")
            print(f"DEBUG: Claves primarias: {claves_primarias}")
            print(f"DEBUG: Claves foráneas: {claves_foraneas}")
            
            # Agregar definiciones de columnas
            if columnas_sql:
                script += ",\n".join(columnas_sql)
                
                # Agregar clave primaria
                if claves_primarias:
                    script += f",\n    PRIMARY KEY ({', '.join(claves_primarias)})"
                
                # Agregar claves foráneas
                for col_fk, tabla_ref in claves_foraneas:
                    script += f",\n    FOREIGN KEY ({col_fk}) REFERENCES {tabla_ref}(id)"
                
                script += "\n);\n\n"
                
                # Agregar comentario de tabla si existe
                if comentario_tabla:
                    script += f"ALTER TABLE {nombre_tabla} COMMENT = '{comentario_tabla}';\n"
                    
                print(f"DEBUG: Script generado exitosamente")
            else:
                script += "    -- No se encontraron definiciones de columnas válidas\n);\n"
                print("DEBUG: No se encontraron columnas válidas")
                
        else:  # modificar_tabla
            # Buscar nombre de la tabla (igual que en crear_tabla)
            nombre_tabla = None
            for i in range(min(5, len(df))):
                for j, col in enumerate(df.columns):
                    valor = df.iloc[i, j]
                    if pd.notna(valor) and str(valor).strip().lower() in ["nombre tabla", "nombre_tabla"]:
                        if j + 1 < len(df.columns):
                            nombre_tabla_valor = df.iloc[i, j+1]
                            if pd.notna(nombre_tabla_valor):
                                nombre_tabla = str(nombre_tabla_valor).strip()
                        elif i + 1 < len(df):
                            nombre_tabla_valor = df.iloc[i+1, j]
                            if pd.notna(nombre_tabla_valor):
                                nombre_tabla = str(nombre_tabla_valor).strip()
            
            if not nombre_tabla:
                nombre_tabla = f"tabla_{base_datos.lower().replace(' ', '_')}"
            
            script += f"-- Modificación de tabla: {nombre_tabla}\n"
            
            # Usar la misma lógica de headers
            fila_headers, columnas_headers = encontrar_headers_en_contenido(df)
            print(f"DEBUG: Headers detectados en modificar_tabla: {columnas_headers}")
            
            if fila_headers is not None and "nombre_columna" in columnas_headers and "accion" in columnas_headers:
                print("DEBUG: Mostrando filas a procesar:")
                print(df.iloc[fila_headers+1 : fila_headers+6].to_string())
                inicio_datos = fila_headers + 1
                for i in range(inicio_datos, len(df)):
                    nombre_col_valor = df.iloc[i, columnas_headers["nombre_columna"]]
                    accion_valor = df.iloc[i, columnas_headers["accion"]] if "accion" in columnas_headers else None
                    tipo_valor = df.iloc[i, columnas_headers["tipo_dato"]] if "tipo_dato" in columnas_headers else None
                    
                    if pd.isna(nombre_col_valor) or pd.isna(accion_valor):
                        continue
                    
                    nombre_col = str(nombre_col_valor).strip()
                    accion = str(accion_valor).strip().upper()
                    tipo_dato = str(tipo_valor).strip() if pd.notna(tipo_valor) else ""
                    
                    if not nombre_col:
                        continue
                    
                    # Generar ALTER según acción
                    if accion in ["AGREGAR", "ADD"]:
                        script += f"ALTER TABLE {nombre_tabla} ADD COLUMN {nombre_col} {tipo_dato};\n"
                    elif accion in ["ELIMINAR", "DROP"]:
                        script += f"ALTER TABLE {nombre_tabla} DROP COLUMN {nombre_col};\n"
                    elif accion in ["MODIFICAR", "MODIFY"]:
                        script += f"ALTER TABLE {nombre_tabla} MODIFY COLUMN {nombre_col} {tipo_dato};\n"
            
            else:
                script += "-- No se encontraron encabezados válidos para modificar la tabla\n"
        
        print(f"DEBUG: Script final generado, longitud: {len(script)}")
        return script
        
    except Exception as e:
        print(f"ERROR generando script de tabla: {e}")
        import traceback
        traceback.print_exc()
        return f"-- Error generando script de tabla: {str(e)}\n-- Verifique que el archivo tenga la estructura correcta"


def generar_script_permisos_usuarios(ruta_archivo):
    # Leer archivo sin header para analizar filas
    df_original = pd.read_excel(ruta_archivo, header=None)
    
    # Buscar fila con cabecera "Esquema"
    header_row_index = None
    for idx, row in df_original.iterrows():
        if isinstance(row.iloc[0], str) and row.iloc[0].strip().lower() == 'esquema':
            header_row_index = idx
            break
    if header_row_index is None:
        raise ValueError("No se encontró la fila con la cabecera 'Esquema'")
    
    # Leer nuevamente con la fila cabecera detectada
    df = pd.read_excel(ruta_archivo, skiprows=header_row_index, header=0)
    
    # Validar columnas
    columnas_esperadas = ['Esquema', 'Nombre Tabla', 'Select', 'Insert', 'Update', 'Delete']
    for col in columnas_esperadas:
        if col not in df.columns:
            raise ValueError(f"Falta columna esperada: {col}")
    
    # Leer "Nombre Usuario" y "Es usuario Nuevo" de filas antes de la cabecera
    # Se asume que están en filas 0 y 1, columna 1 (índice 1)
    nombre_usuario = None
    es_usuario_nuevo = str(df_original.iloc[2,1]).strip().lower()
    
    # Intentar obtener datos
    try:
        if 'Nombre Usuario' in df_original.iloc[0, 0]:
            nombre_usuario = str(df_original.iloc[0,1]).strip()
        if 'Es usuario Nuevo' in df_original.iloc[1, 0]:
            es_usuario_nuevo = str(df_original.iloc[2,1]).strip().lower()
            print(f"DEBUG: es_usuario_nuevo: {es_usuario_nuevo}")
            if es_usuario_nuevo not in ['si', 'no']:
                raise ValueError("El valor de 'Es usuario Nuevo' debe ser 'Si' o 'No'")
    except Exception:
        pass
    print(f"DEBUG: es_usuario_nuevo: {es_usuario_nuevo}")
    if not nombre_usuario:
        raise ValueError("No se encontró el nombre de usuario en el archivo")
    if es_usuario_nuevo not in ['si', 'no']:
        raise ValueError("El valor de 'Es usuario Nuevo' debe ser 'Si' o 'NO'")
    
    # Generar scripts
    scripts = []
    
    if es_usuario_nuevo == 'si':
        # Script para crear usuario (ejemplo)
        scripts.append(f"CREATE USER {nombre_usuario} IDENTIFIED BY 'password';")
    
    # Asignar permisos según filas
    for idx, row in df.iterrows():
        esquema = row['Esquema']
        tabla = row['Nombre Tabla']
        permisos = []
        if str(row['Select']).strip().lower() == 'si':
            permisos.append('SELECT')
        if str(row['Insert']).strip().lower() == 'si':
            permisos.append('INSERT')
        if str(row['Update']).strip().lower() == 'si':
            permisos.append('UPDATE')
        if str(row['Delete']).strip().lower() == 'si':
            permisos.append('DELETE')
        
        if permisos:
            permisos_str = ", ".join(permisos)
            scripts.append(f"GRANT {permisos_str} ON {esquema}.{tabla} TO {nombre_usuario};")
    
    # Retornar script completo
    return "\n".join(scripts)


def generar_script_bd_esquemas(df, tipo_solicitud, base_datos):
    """
    Genera script SQL para creación de bases de datos y esquemas
    """
    try:
        script = f"-- Script generado automáticamente para {tipo_solicitud}\n"
        script += f"-- Aplicación: {base_datos}\n"
        script += f"-- Fecha de generación: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if tipo_solicitud == 'crear_bd':
            for _, row in df.iterrows():
                if pd.isna(row.get('nombre_bd')):
                    continue
                    
                nombre_bd = row['nombre_bd']
                charset = row.get('charset', 'utf8mb4')
                collation = row.get('collation', 'utf8mb4_unicode_ci')
                
                script += f"CREATE DATABASE {nombre_bd} "
                script += f"CHARACTER SET {charset} COLLATE {collation};\n"
                
        else:  # crear_esquemas
            for _, row in df.iterrows():
                if pd.isna(row.get('nombre_esquema')):
                    continue
                    
                nombre_esquema = row['nombre_esquema']
                propietario = row.get('propietario', 'admin')
                
                script += f"CREATE SCHEMA {nombre_esquema} AUTHORIZATION {propietario};\n"
        
        return script
        
    except Exception as e:
        return f"-- Error generando script de BD/esquemas: {str(e)}"

def generar_credenciales_usuario(solicitud):
    """
    Genera credenciales para un nuevo usuario
    """
    base_username = f"user_{solicitud.id}"
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(12))
    return base_username, password

def enviar_correo_notificacion(solicitud, estado, comentario=""):
    """
    Envía correo de notificación cuando se resuelve una solicitud
    """
    try:
        subject = f"Solicitud #{solicitud.id} - {solicitud.get_estado_display()}"
        
        context = {
            'solicitud': solicitud,
            'estado': estado,
            'comentario': comentario,
        }
        
        html_content = render_to_string('emails/notificacion_resolucion.html', context)
        
        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[solicitud.correo_notificacion],
        )
        email.content_subtype = 'html'
        
        if solicitud.script_sql_generado:
            email.attach(
                f'script_solicitud_{solicitud.id}.sql',
                solicitud.script_sql_generado,
                'text/plain'
            )
        
        email.send()
        return True
        
    except Exception as e:
        print(f"Error enviando correo de notificación: {e}")
        return False

def enviar_correo_credenciales(solicitud, usuario, password):
    """
    Envía correo con las credenciales del usuario creado
    """
    try:
        subject = f"Credenciales de acceso - Usuario creado"
        
        context = {
            'solicitud': solicitud,
            'usuario': usuario,
            'password': password,
        }
        
        html_content = render_to_string('emails/credenciales_usuario.html', context)
        
        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[solicitud.correo_notificacion],
        )
        email.content_subtype = 'html'
        
        email.send()
        return True
        
    except Exception as e:
        print(f"Error enviando correo de credenciales: {e}")
        return False

def enviar_correo_aprobacion_lider(solicitud):
    """
    Envía correo al líder de proyecto para aprobación de creación de usuario
    """
    try:
        subject = f"Aprobación requerida - Solicitud #{solicitud.id}"
        
        context = {
            'solicitud': solicitud,
            'url_detalle': f"{settings.SITE_URL}/solicitud/{solicitud.id}/",
        }
        
        html_content = render_to_string('emails/aprobacion_lider.html', context)
        
        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[solicitud.lider_proyecto.email],
        )
        email.content_subtype = 'html'
        
        email.send()
        return True
        
    except Exception as e:
        print(f"Error enviando correo de aprobación: {e}")
        return False

def enviar_correo_cambio_estado(solicitud, estado_anterior, estado_nuevo, usuario_cambio, comentario=""):
    """
    Envía correo de notificación cuando cambia el estado de una solicitud
    """
    try:
        destinatarios = [solicitud.correo_notificacion]
        
        if usuario_cambio != solicitud.usuario and solicitud.usuario.email:
            destinatarios.append(solicitud.usuario.email)
        
        if (solicitud.lider_proyecto and solicitud.lider_proyecto.email and 
            solicitud.lider_proyecto != usuario_cambio):
            destinatarios.append(solicitud.lider_proyecto.email)
        
        destinatarios = list(set(destinatarios))
        
        subject = f"Cambio de Estado - Solicitud #{solicitud.id}"
        
        context = {
            'solicitud': solicitud,
            'estado_anterior': dict(solicitud.ESTADOS)[estado_anterior],
            'estado_nuevo': dict(solicitud.ESTADOS)[estado_nuevo],
            'usuario_cambio': usuario_cambio,
            'comentario': comentario,
        }
        
        html_content = render_to_string('emails/aprobacion_lider.html', context)
        
        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
        )
        email.content_subtype = 'html'
        
        email.send()
        return True
        
    except Exception as e:
        print(f"Error enviando correo de cambio de estado: {e}")
        return False

def generar_script_sql(solicitud):
    """
    Función principal para generar scripts SQL basados en el tipo de solicitud
    """
    if solicitud.tipo_solicitud in ['pull_request', 'despliegue']:
        script = f"-- Solicitud de {solicitud.get_tipo_solicitud_display()}\n"
        script += f"-- Base de datos/Aplicación: {solicitud.base_datos_aplicacion}\n"
        script += f"-- URL: {solicitud.url_commit}\n"
        script += f"-- Branch: {solicitud.nombre_branch}\n"
        script += f"-- Entorno: {solicitud.entorno}\n"
        if solicitud.ambientes_ejecucion:
            script += f"-- Ambientes de ejecución: {', '.join(solicitud.ambientes_ejecucion)}\n"
        return script
    
    if solicitud.archivo_adjunto and solicitud.tipo_archivo == 'excel':
        return procesar_archivo_excel(solicitud)
    
    return None
