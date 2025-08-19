import os

def verificar_template_actual():
    """
    Verifica el contenido actual del template
    """
    try:
        print("📄 VERIFICANDO TEMPLATE ACTUAL")
        print("=" * 40)
        
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'templates',
            'tickets',
            'detalle_solicitud.html'
        )
        
        if not os.path.exists(template_path):
            print(f"❌ Template no encontrado en: {template_path}")
            return
        
        print(f"✅ Template encontrado: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar las secciones relevantes
        print(f"\n🔍 BUSCANDO SECCIONES RELEVANTES:")
        
        # Buscar condiciones del botón
        if 'puede_generar_script and solicitud.archivo_adjunto and not solicitud.script_sql_generado' in contenido:
            print("✅ Condición correcta del botón encontrada")
        else:
            print("❌ Condición correcta del botón NO encontrada")
        
        # Buscar el botón
        if 'Generar Script SQL' in contenido:
            print("✅ Texto del botón encontrado")
        else:
            print("❌ Texto del botón NO encontrado")
        
        # Buscar name="generar_sql"
        if 'name="generar_sql"' in contenido:
            print("✅ Atributo name='generar_sql' encontrado")
        else:
            print("❌ Atributo name='generar_sql' NO encontrado")
        
        # Mostrar líneas relevantes
        print(f"\n📝 LÍNEAS RELEVANTES DEL TEMPLATE:")
        lineas = contenido.split('\n')
        for i, linea in enumerate(lineas, 1):
            if any(keyword in linea.lower() for keyword in ['generar script', 'generar_sql', 'puede_generar_script']):
                print(f"   Línea {i}: {linea.strip()}")
        
        print(f"\n📊 ESTADÍSTICAS DEL TEMPLATE:")
        print(f"   Total líneas: {len(lineas)}")
        print(f"   Tamaño: {len(contenido)} caracteres")
        
    except Exception as e:
        print(f"❌ Error verificando template: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_template_actual()
