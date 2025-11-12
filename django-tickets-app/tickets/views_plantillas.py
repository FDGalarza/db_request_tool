import os
from django.shortcuts import render
from django.http import FileResponse, HttpResponseNotFound
from django.conf import settings
from tickets.utils import crear_plantilla_excel

def lista_plantillas(request):
    """Muestra todas las plantillas disponibles para descarga."""
    carpeta = os.path.join(settings.MEDIA_ROOT, "plantillas")
    os.makedirs(carpeta, exist_ok=True)

    plantillas = [
        {
            "nombre": "📄 Creación / Modificación de Tablas",
            "archivo": "plantilla_creacion_modificaion_tablas_v2.xlsx",
            "descripcion": "Define columnas, tipos de datos y comentarios.",
        },
        {
            "nombre": "👤 Usuarios y Permisos",
            "archivo": "plantilla_usuarios_permisos.xlsx",
            "descripcion": "Para creación de usuarios y asignación de permisos.",
        },
        {
            "nombre": "🗄️ Creación de Base de Datos",
            "archivo": "plantilla_creacion_bd.xlsx",
            "descripcion": "Estructura para registrar nuevas bases de datos.",
            "generar": lambda: crear_plantilla_excel("crear_bd"),
        },
        {
            "nombre": "📂 Creación de Esquemas",
            "archivo": "plantilla_creacion_esquemas.xlsx",
            "descripcion": "Define los esquemas dentro de las bases de datos.",
            "generar": lambda: crear_plantilla_excel("crear_esquemas"),
        },
    ]

    # Verificar existencia y generar si falta
    for p in plantillas:
        ruta = os.path.join(carpeta, p["archivo"])
        if not os.path.exists(ruta) and "generar" in p:
            p["generar"]()
        p["ruta_relativa"] = f"{settings.MEDIA_URL}plantillas/{p['archivo']}"

    return render(request, "plantillas/lista_plantillas.html", {"plantillas": plantillas})


def descargar_plantilla(request, nombre_archivo):
    """Permite descargar una plantilla específica."""
    ruta = os.path.join(settings.MEDIA_ROOT, "plantillas", nombre_archivo)
    if os.path.exists(ruta):
        return FileResponse(open(ruta, "rb"), as_attachment=True, filename=nombre_archivo)
    return HttpResponseNotFound("Archivo no encontrado.")
