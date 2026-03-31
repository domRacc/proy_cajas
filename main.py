from flask import Flask, request
import os, math, requests

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "mi-token-secreto")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")  
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Guarda el estado de cada usuario
usuarios = {}

# ==== CONSTANTES ====
# Grosor de cartón por tipo (en mm)
GROSORES_CARTON = {
    "12": 3,  # Simple (liviano)
    "14": 4,  # Reforzado
    "17": 5,  # Doble cara
    "20": 7   # Extra resistente
}

# ==== LÓGICA DE CÁLCULO ====
def calcular_caja(largo_interno, ancho_interno, alto_interno, tipocarton, color_carton, 
                  valorkilo, matriz, clisse, color, cantidad, bobinax=1600):
    """
    Calcula la cotización de una caja de cartón.
    
    IMPORTANTE: Recibe medidas INTERNAS en cm y las convierte a medidas EXTERNAS
    sumando el grosor del cartón según el tipo.
    
    Args:
        largo_interno, ancho_interno, alto_interno: Medidas internas en cm
        tipocarton: Tipo de cartón (12, 14, 17, 20)
        color_carton: 'blanco' o 'cafe'
        valorkilo: Precio base por kilo
        matriz, clisse: Costos de herramientas
        color: Número de colores de impresión
        cantidad: Cantidad de cajas
        bobinax: Ancho de bobina alternativa (por defecto 1600mm)
    
    Returns:
        String con la cotización formateada
    """
    try:
        # Convertir a enteros
        valorkilo = int(valorkilo)
        matriz = int(matriz)
        clisse = int(clisse)
        color = int(color)
        cantidad = int(cantidad)
        bobinax = int(bobinax)
        
        # Obtener grosor del cartón
        grosor_mm = GROSORES_CARTON.get(tipocarton, 0)
        
        # ===== PASO 1: CALCULAR MEDIDAS EXTERNAS =====
        # Sumar grosor del cartón a cada dimensión interna para obtener externa
        # Convertir cm a mm y sumar grosor
        largo_externo_mm = int(largo_interno) * 10 + grosor_mm
        ancho_externo_mm = int(ancho_interno) * 10 + grosor_mm
        alto_externo_mm = int(alto_interno) * 10 + grosor_mm
        
        # ===== PASO 2: CALCULAR DESARROLLO DE LA PLACA =====
        # Fórmula: (2*largo + 2*ancho + 50mm) x (ancho + alto)
        largo_placa = int(largo_externo_mm)*2 + int(ancho_externo_mm)*2 + 50
        ancho_placa_desarrollo = int(ancho_externo_mm) + int(alto_externo_mm)
        
        # Área de la placa en m²
        placam2 = (largo_placa * ancho_placa_desarrollo) / 1000000
        
        # Formateo para mostrar
        desarrollo_interno = f"{int(largo_interno)}x{int(ancho_interno)}x{int(alto_interno)}"
        desarrollo_externo = f"{largo_externo_mm/10:.1f}x{ancho_externo_mm/10:.1f}x{alto_externo_mm/10:.1f}"
        placa = f"{largo_placa}x{ancho_placa_desarrollo}"
        
        # ===== PASO 3: SELECCIONAR BOBINA ÓPTIMA =====
        # Evaluar 4 anchos de bobina estándar (descontando 30mm de pérdida)
        r1000 = math.fmod(970, ancho_placa_desarrollo)
        r1200 = math.fmod(1170, ancho_placa_desarrollo)
        r1400 = math.fmod(1370, ancho_placa_desarrollo)
        r1600 = math.fmod(1570, ancho_placa_desarrollo)
        
        # Seleccionar la bobina que minimiza el desperdicio
        bobina_residuo = min(r1000, r1200, r1400, r1600)
        
        if bobina_residuo == r1000: bobina = 1000
        elif bobina_residuo == r1200: bobina = 1200
        elif bobina_residuo == r1400: bobina = 1400
        elif bobina_residuo == r1600: bobina = 1600
        else: bobina = 1600  # Por defecto
        
        # ===== PASO 4: CALCULAR PLANCHAS POR GOLPE =====
        # Cuántas placas caben en un golpe de corte
        un_golpe = int((bobina - 30) / ancho_placa_desarrollo)
        ancho_placa_real = int(bobina / un_golpe) if un_golpe > 0 else bobina
        
        un_golpex = int((bobinax - 30) / ancho_placa_desarrollo)
        ancho_placax_real = int(bobinax / un_golpex) if un_golpex > 0 else bobinax
        
        # ===== PASO 5: OBTENER DATOS DEL TIPO DE CARTÓN =====
        tipos = {
            "12": (400, valorkilo / 2.5),              # Gramaje 400 g/m²
            "14": (450, valorkilo / 2.5 * 1.125),     # Gramaje 450 g/m²
            "17": (500, valorkilo / 2.5 * 1.25),      # Gramaje 500 g/m²
            "20": (600, valorkilo / 2.5 * 1.5),       # Gramaje 600 g/m²
        }
        
        if tipocarton not in tipos:
            return "❌ Tipo de cartón no válido. Elige: 12, 14, 17 o 20."
        
        m2_gramaje, valor_por_m2 = tipos[tipocarton]
        
        # ===== PASO 6: APLICAR RECARGOS =====
        # Recargo del 25% si el cartón es blanco
        recargo_blanco = 1.25 if color_carton == "blanco" else 1.0
        IVA = 0.19
        
        # Peso teórico de la placa
        peso = int(ancho_placa_real * largo_placa * m2_gramaje / 1000000)
        
        # ===== PASO 7: CALCULAR PRECIOS =====
        # Costo de material: área × precio por m²
        # Costo de ranurado: $10 fijo
        # Costo de impresión: $30 por color
        # Amortización de herramientas: (matriz + clisé × colores) / cantidad
        
        if cantidad > 0:
            # Bobina óptima
            precio_material = valor_por_m2 * ancho_placa_real * largo_placa / 1000000
            precio_ranurado = 10
            precio_impresion = color * 30
            precio_herramientas = (matriz + clisse * color) / cantidad
            preciocaja = (precio_material + precio_ranurado + precio_impresion + precio_herramientas) * recargo_blanco
            
            # Bobina alternativa
            precio_material_x = valor_por_m2 * ancho_placax_real * largo_placa / 1000000
            preciocajax = (precio_material_x + precio_ranurado + precio_impresion + precio_herramientas) * recargo_blanco
        else:
            # Sin cantidad específica (no se amortizan herramientas)
            precio_material = valor_por_m2 * ancho_placa_real * largo_placa / 1000000
            preciocaja = (precio_material + 10 + color * 30) * recargo_blanco
            
            precio_material_x = valor_por_m2 * ancho_placax_real * largo_placa / 1000000
            preciocajax = (precio_material_x + 10 + color * 30) * recargo_blanco
        
        # Aplicar IVA
        preciocaja_iva = preciocaja * (1 + IVA)
        preciocajax_iva = preciocajax * (1 + IVA)
        
        # Precio total
        precio_total = preciocaja_iva * cantidad if cantidad > 0 else 0
        
        # ===== PASO 8: FORMATEAR COTIZACIÓN =====
        tipo_carton_label = "Blanco" if color_carton == "blanco" else "Café"
        
        resultado = (
            f"📦 *COTIZACIÓN DE CAJA DE CARTÓN*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📏 *ESPECIFICACIONES*\n"
            f"• Medidas internas: {desarrollo_interno} cm\n"
            f"• Medidas externas: {desarrollo_externo} cm\n"
            f"• Tipo de cartón: *{tipocarton}* ({tipo_carton_label})\n"
            f"• Grosor añadido: {grosor_mm}mm\n"
            f"• Placa: {placa} mm ({placam2:.3f} m²)\n"
            f"• Peso teórico: {peso} grs\n"
        )
        
        if color > 0:
            resultado += f"• Impresión: {color} color(es)\n"
        
        if cantidad > 0:
            resultado += f"• Cantidad: *{cantidad:,}* unidades\n"
        
        resultado += (
            f"\n💰 *COTIZACIÓN*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Bobina óptima ({bobina}mm):*\n"
            f"   • Precio unitario (sin IVA): ${int(preciocaja):,}\n"
            f"   • Precio unitario (con IVA): ${int(preciocaja_iva):,}\n"
        )
        
        if cantidad > 0:
            resultado += f"   • *PRECIO TOTAL: ${int(precio_total):,}* (IVA inc.)\n"
        
        resultado += (
            f"\n📊 *Bobina alternativa ({bobinax}mm):*\n"
            f"   • Precio unitario (sin IVA): ${int(preciocajax):,}\n"
            f"   • Precio unitario (con IVA): ${int(preciocajax_iva):,}\n"
        )
        
        if cantidad > 0:
            precio_total_x = preciocajax_iva * cantidad
            resultado += f"   • PRECIO TOTAL: ${int(precio_total_x):,} (IVA inc.)\n"
        
        resultado += (
            f"\n━━━━━━━━━━━━━━━━━━━━\n"
            f"ℹ️ _IVA incluido: 19%_\n"
            f"ℹ️ _Esta es una cotización de referencia_\n\n"
            f"📞 *Para confirmar tu pedido, contáctanos:*\n"
            f"   📧 Email: ventas@cartonchile.cl\n"
            f"   ☎️ Teléfono: +56 9 1234 5678\n\n"
            f"Escribe *menu* para hacer otra cotización."
        )
        
        return resultado
        
    except Exception as e:
        return f"❌ Error al calcular la cotización: {str(e)}\n\nEscribe *menu* para intentar nuevamente."

# ==== MENSAJES FIJOS ====
MSG_BIENVENIDA = (
    "🏭 *¡Bienvenido a Cartón Chile!*\n\n"
    "👋 Soy tu asistente virtual de cotizaciones.\n\n"
    "🔹 *1* - Cotizar caja de cartón\n"
    "🔹 *2* - Consultar tipos de cartón\n"
    "🔹 *0* - Salir\n\n"
    "_Responde con el número de la opción._"
)

MSG_TIPOS_CARTON = (
    "📋 *Tipos de cartón disponibles:*\n\n"
    "🔹 *12* - Simple (liviano) - 3mm grosor\n"
    "🔹 *14* - Reforzado - 4mm grosor\n"
    "🔹 *17* - Doble cara - 5mm grosor\n"
    "🔹 *20* - Extra resistente - 7mm grosor\n\n"
    "🎨 *Color de cartón:*\n"
    "• *Café* - Precio estándar\n"
    "• *Blanco* - Precio + 25%\n\n"
    "💡 _Nota: El grosor se suma automáticamente_\n"
    "_a las medidas internas que nos indiques._\n\n"
    "Escribe *menu* para volver al inicio."
)

# ==== FUNCIONES DE VALIDACIÓN ====
def validar_medida(texto):
    """Valida que la medida sea un número válido entre 1 y 300 cm"""
    if not texto.isdigit():
        return False, "⚠️ Ingresa solo números."
    
    medida = int(texto)
    if medida <= 0:
        return False, "⚠️ La medida debe ser mayor a 0 cm."
    if medida > 300:
        return False, "⚠️ La medida no puede ser mayor a 300 cm."
    
    return True, medida

def validar_cantidad(texto):
    """Valida que la cantidad sea un número válido entre 0 y 100000"""
    if not texto.isdigit():
        return False, "⚠️ Ingresa solo números."
    
    cantidad = int(texto)
    if cantidad < 0:
        return False, "⚠️ La cantidad no puede ser negativa."
    if cantidad > 100000:
        return False, "⚠️ La cantidad no puede ser mayor a 100,000 unidades.\nContacta a ventas para pedidos mayores."
    
    return True, cantidad

# ==== FLUJO CONVERSACIONAL ====
def procesar_mensaje(numero, texto):
    """
    Procesa el mensaje del usuario y retorna la respuesta apropiada.
    Implementa una máquina de estados para guiar la conversación.
    """
    texto = texto.strip()
    texto_lower = texto.lower()

    # Comando para cancelar en cualquier momento
    if texto_lower in ["cancelar", "cancel", "salir", "exit"]:
        usuarios[numero] = {"paso": 0}
        return "🚫 *Cotización cancelada.*\n\nEscribe *menu* para iniciar una nueva cotización."

    # Palabras que reinician el flujo
    if texto_lower in ["hola", "inicio", "menu", "menú", "start", "0", "hi", "hello"]:
        usuarios[numero] = {"paso": 0}
        return MSG_BIENVENIDA

    # Si el usuario no tiene estado, mostrar bienvenida
    if numero not in usuarios:
        usuarios[numero] = {"paso": 0}
        return MSG_BIENVENIDA

    estado = usuarios[numero]
    paso = estado.get("paso", 0)

    # ── MENÚ PRINCIPAL ──
    if paso == 0:
        if texto == "1":
            usuarios[numero]["paso"] = 1
            return "📏 *Paso 1/6*\n\n¿Cuál es el *largo INTERNO* de la caja? (en cm)\n\n_Ejemplo: 30_\n\n💡 _Tip: Solo necesitas las medidas internas._\n_Nosotros calculamos las externas sumando el grosor del cartón._"
        elif texto == "2":
            return MSG_TIPOS_CARTON
        else:
            return "⚠️ Opción no válida.\n\nResponde *1*, *2* o *0*."

    # ── RECOLECCIÓN DE DATOS ──
    elif paso == 1:  # LARGO
        valido, resultado = validar_medida(texto)
        if not valido:
            return f"{resultado}\n\n¿Cuál es el *largo interno*? (cm)"
        estado["largo"] = resultado
        estado["paso"] = 2
        return "📏 *Paso 2/6*\n\n¿Cuál es el *ancho INTERNO* de la caja? (en cm)\n\n_Ejemplo: 20_"

    elif paso == 2:  # ANCHO
        valido, resultado = validar_medida(texto)
        if not valido:
            return f"{resultado}\n\n¿Cuál es el *ancho interno*? (cm)"
        estado["ancho"] = resultado
        estado["paso"] = 3
        return "📏 *Paso 3/6*\n\n¿Cuál es el *alto INTERNO* de la caja? (en cm)\n\n_Ejemplo: 10_"

    elif paso == 3:  # ALTO
        valido, resultado = validar_medida(texto)
        if not valido:
            return f"{resultado}\n\n¿Cuál es el *alto interno*? (cm)"
        estado["alto"] = resultado
        estado["paso"] = 4
        return (
            "📦 *Paso 4/6*\n\n¿Qué *tipo de cartón* necesitas?\n\n"
            "🔹 *12* - Simple (3mm)\n"
            "🔹 *14* - Reforzado (4mm)\n"
            "🔹 *17* - Doble cara (5mm)\n"
            "🔹 *20* - Extra resistente (7mm)\n\n"
            "_Responde con el número._"
        )

    elif paso == 4:  # TIPO DE CARTÓN
        if texto not in ["12", "14", "17", "20"]:
            return "⚠️ Tipo no válido.\n\nElige: *12*, *14*, *17* o *20*."
        estado["tipocarton"] = texto
        estado["paso"] = 5
        return (
            "🎨 *Paso 5/6*\n\n¿De qué *color* es el cartón?\n\n"
            "🔹 *1* - Café (precio estándar)\n"
            "🔹 *2* - Blanco (precio + 25%)\n\n"
            "_Responde con 1 o 2._"
        )

    elif paso == 5:  # COLOR
        if texto not in ["1", "2"]:
            return "⚠️ Opción no válida.\n\nResponde *1* para Café o *2* para Blanco."
        estado["color_carton"] = "cafe" if texto == "1" else "blanco"
        estado["paso"] = 6
        return "🎨 *Paso 6/6*\n\n¿Cuántos *colores de impresión* lleva la caja?\n\n_Responde 0 si no lleva impresión._"

    elif paso == 6:  # COLORES
        if not texto.isdigit():
            return "⚠️ Ingresa solo números.\n\n¿Cuántos *colores*? (0-4)"
        colores = int(texto)
        if colores < 0 or colores > 4:
            return "⚠️ El número de colores debe estar entre 0 y 4.\n\n¿Cuántos *colores*?"
        estado["color"] = colores
        estado["paso"] = 7
        return "📊 *Paso 7/7*\n\n¿Cuántas *cajas* necesitas?\n\n_Responde 0 si aún no lo sabes._"

    elif paso == 7:  # CANTIDAD
        valido, resultado = validar_cantidad(texto)
        if not valido:
            return f"{resultado}\n\n¿Cuántas *cajas*?"
        estado["cantidad"] = resultado

        # ===== CALCULAR PRECIO POR KILO SEGÚN CANTIDAD =====
        # Escala de precios por volumen
        cantidad = estado["cantidad"]
        if cantidad > 20:
            valorkilo = 1150  # Precio más bajo para pedidos grandes
        elif cantidad > 10:
            valorkilo = 1200
        elif cantidad > 5:
            valorkilo = 1250
        else:
            valorkilo = 1300  # Precio más alto para pedidos pequeños

        # ===== CALCULAR COTIZACIÓN =====
        try:
            cotizacion = calcular_caja(
                largo_interno=estado["largo"],
                ancho_interno=estado["ancho"],
                alto_interno=estado["alto"],
                tipocarton=estado["tipocarton"],
                color_carton=estado["color_carton"],
                valorkilo=valorkilo,
                matriz=0,      # Sin costo de matriz por defecto
                clisse=0,      # Sin costo de clisé por defecto
                color=estado["color"],
                cantidad=estado["cantidad"]
            )
            
            # Resetear estado para nueva cotización
            usuarios[numero] = {"paso": 0}
            
            return cotizacion
            
        except Exception as e:
            print(f"Error al calcular cotización: {e}")
            usuarios[numero] = {"paso": 0}
            return (
                f"❌ *Error al calcular la cotización*\n\n"
                f"Por favor, intenta nuevamente.\n\n"
                f"Escribe *menu* para iniciar."
            )

    # Estado desconocido, resetear
    usuarios[numero] = {"paso": 0}
    return MSG_BIENVENIDA

# ==== WEBHOOK ====
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """
    Endpoint GET para verificación del webhook por parte de Meta.
    Meta envía hub.mode, hub.verify_token y hub.challenge.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    print(f"DEBUG: Verificación de webhook - mode={mode}, token={token}")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook verificado correctamente")
        return challenge, 200
    else:
        print("❌ Verificación de webhook fallida")
        return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Endpoint POST para recibir mensajes de WhatsApp.
    Meta envía los mensajes en formato JSON.
    """
    try:
        data = request.get_json()
        print(f"DEBUG: Datos recibidos de Meta: {data}")
        
        # Extraer mensajes del payload
        if "entry" not in data:
            print("⚠️ Payload sin 'entry'")
            return "OK", 200
        
        entry = data["entry"][0]
        changes = entry.get("changes", [])
        
        if not changes:
            print("⚠️ Payload sin 'changes'")
            return "OK", 200
        
        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        
        if not messages:
            print("ℹ️ Webhook sin mensajes (probablemente notificación de estado)")
            return "OK", 200
        
        # Procesar primer mensaje
        msg = messages[0]
        numero = msg.get("from")
        texto = msg.get("text", {}).get("body", "")
        
        print(f"📩 Mensaje recibido de {numero}: {texto}")
        
        # Procesar mensaje y obtener respuesta
        respuesta = procesar_mensaje(numero, texto)
        
        # Enviar respuesta
        resultado_envio = enviar_mensaje(numero, respuesta)
        print(f"📤 Respuesta enviada: {resultado_envio}")
        
    except KeyError as e:
        print(f"❌ Error de estructura en payload: {e}")
    except Exception as e:
        print(f"❌ Error inesperado en webhook: {e}")
    
    # Siempre retornar 200 para que Meta no reintente
    return "OK", 200

# ==== ENVIAR MENSAJE ====
def enviar_mensaje(to_number, mensaje):
    """
    Envía un mensaje de texto a través de WhatsApp Business API.
    
    Args:
        to_number: Número de teléfono del destinatario (con código de país)
        mensaje: Texto del mensaje a enviar
    
    Returns:
        dict: Respuesta de la API de WhatsApp
    """
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("⚠️ WHATSAPP_TOKEN o PHONE_NUMBER_ID no configurados")
        return {"error": "Credenciales no configuradas"}
    
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "text": {"body": mensaje}
    }
    
    try:
        respuesta = requests.post(url, headers=headers, json=payload, timeout=10)
        respuesta_json = respuesta.json()
        
        if respuesta.status_code == 200:
            print(f"✅ Mensaje enviado exitosamente a {to_number}")
        else:
            print(f"❌ Error al enviar mensaje: {respuesta_json}")
        
        return respuesta_json
        
    except requests.exceptions.Timeout:
        print("❌ Timeout al enviar mensaje")
        return {"error": "Timeout"}
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")
        return {"error": str(e)}

# ==== ENDPOINT DE HEALTH CHECK ====
@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint para verificar que el servicio está activo"""
    return {
        "status": "ok",
        "service": "Cartón Chile WhatsApp Bot",
        "version": "2.0"
    }, 200

if __name__ == "__main__":
    print("="*50)
    print("🏭 Cartón Chile - Bot de WhatsApp")
    print("="*50)
    print(f"✅ Servidor Flask iniciando en puerto 5000")
    print(f"✅ VERIFY_TOKEN configurado: {VERIFY_TOKEN}")
    print(f"✅ WHATSAPP_TOKEN configurado: {'Sí' if WHATSAPP_TOKEN else 'No'}")
    print(f"✅ PHONE_NUMBER_ID configurado: {'Sí' if PHONE_NUMBER_ID else 'No'}")
    print("="*50)
    print("📝 Endpoints disponibles:")
    print("   GET  /webhook - Verificación de webhook")
    print("   POST /webhook - Recibir mensajes")
    print("   GET  /health  - Health check")
    print("="*50)
    
    app.run(host="0.0.0.0", port=5000, debug=True)