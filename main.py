from flask import Flask, request
import os
import math
import requests

app = Flask(__name__)

# Variables de entorno
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "mi-token-secreto")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Diccionario para guardar el estado de cada usuario (conversación)
usuarios = {}

# ===== LÓGICA DE CÁLCULO (extraída de tu script) =====
def calcular_caja(largo, ancho, alto, tipocarton, valorkilo, matriz, clisse, color, cantidad, bobinax):
    valorkilo = int(valorkilo)
    matriz = int(matriz)
    clisse = int(clisse)
    color = int(color)
    cantidad = int(cantidad)
    bobinax = int(bobinax)
    
    largo_placa = int(largo)*2 + int(ancho)*2 + 50
    desarrollo = f"{int(largo)}x{int(ancho)}x{int(alto)}"
    placam2 = ((int(largo)*2 + int(ancho)*2 + 50) * (int(ancho) + int(alto))) / 10000
    
    ancho_placao = int(ancho) + int(alto)
    placa = f"{largo_placa}x{ancho_placao}"
    
    r1000 = math.fmod(970, ancho_placao)
    r1200 = math.fmod(1170, ancho_placao)
    r1400 = math.fmod(1370, ancho_placao)
    r1600 = math.fmod(1570, ancho_placao)
    
    bobina = min(r1000, r1200, r1400, r1600)
    
    if bobina == r1000:
        bobina = 1000
    elif bobina == r1200:
        bobina = 1200
    elif bobina == r1400:
        bobina = 1400
    elif bobina == r1600:
        bobina = 1600
    
    un_golpe = int((bobina - 30) / int(ancho_placao))
    ancho_placa = int(bobina / int(un_golpe))
    
    un_golpex = int((bobinax - 30) / int(ancho_placao))
    ancho_placax = int(bobinax / int(un_golpex))
    
    # Cálculo según tipo de cartón
    if tipocarton == "12":
        m2 = 400
        valor = valorkilo / 2.5
    elif tipocarton == "14":
        m2 = 450
        valor = valorkilo / 2.5 * 1.125
    elif tipocarton == "17":
        m2 = 500
        valor = valorkilo / 2.5 * 1.25
    elif tipocarton == "20":
        m2 = 600
        valor = valorkilo / 2.5 * 1.5
    elif tipocarton == "30":
        m2 = 800
        valor = valorkilo / 2.5 * 2
    else:
        return "Tipo de cartón no válido"
    
    peso = int(ancho_placa * largo_placa * m2 / 10000)
    
    if cantidad > 0:
        preciocaja = (valor * ancho_placa * largo_placa / 10000) + 10 + color * 30 + (matriz + clisse * color) / cantidad
        preciocajax = (valor * ancho_placax * largo_placa / 10000) + 10 + color * 30 + (matriz + clisse * color) / cantidad
    else:
        preciocaja = int(valor * ancho_placa * largo_placa / 10000) + 10 + color * 30
        preciocajax = (valor * ancho_placax * largo_placa / 10000) + 10 + color * 30
    
    resultado = f"""
📦 *COTIZACIÓN DE CAJA*

📏 Desarrollo: {desarrollo}
📐 Placa: {placa} ({placam2:.2f} m²)
⚖️ Peso: {peso} grs

💰 *Precio Bobina Óptima ({bobina}mm):* ${int(preciocaja)}
💰 *Precio Bobina Alternativa ({bobinax}mm):* ${int(preciocajax)}

🎯 Bobina óptima recomendada: {bobina}mm
"""
    return resultado

# ===== WEBHOOK ENDPOINTS =====
@app.get("/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

@app.post("/webhook")
def webhook():
    data = request.get_json()
    
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages", [])
        
        if messages:
            message = messages[0]
            from_number = message["from"]
            text = message.get("text", {}).get("body", "").strip()
            
            # Procesar mensaje
            respuesta = procesar_mensaje(from_number, text)
            
            # Enviar respuesta
            enviar_mensaje(from_number, respuesta)
    
    except Exception as e:
        print(f"Error: {e}")
    
    return "OK", 200

# ===== PROCESAMIENTO DE MENSAJES =====
def procesar_mensaje(usuario, texto):
    texto_lower = texto.lower()
    
    # Comando para iniciar cotización
    if "cotizar" in texto_lower or "hola" in texto_lower or "inicio" in texto_lower:
        usuarios[usuario] = {"paso": 1}
        return """¡Hola! 👋 Bienvenido al cotizador de cajas de cartón.

Para cotizar, envíame los datos en este formato:
`largo ancho alto tipo cantidad`

Ejemplo: `300 200 100 12 500`

Donde:
- Largo, ancho, alto en mm
- Tipo: 12, 14, 17, 20 o 30
- Cantidad de cajas

O escribe los datos separados por espacios."""
    
    # Intentar parsear datos
    try:
        partes = texto.split()
        if len(partes) >= 4:
            largo = int(partes[0])
            ancho = int(partes[1])
            alto = int(partes[2])
            tipocarton = partes[3]
            cantidad = int(partes[4]) if len(partes) > 4 else 0
            
            # Valores por defecto
            valorkilo = 1250
            matriz = 0
            clisse = 0
            color = 0
            bobinax = 1600
            
            resultado = calcular_caja(largo, ancho, alto, tipocarton, valorkilo, 
                                     matriz, clisse, color, cantidad, bobinax)
            return resultado
        else:
            return "❌ Formato incorrecto. Envía: `largo ancho alto tipo cantidad`\nEjemplo: `300 200 100 12 500`"
    
    except Exception as e:
        return f"❌ Error al procesar. Verifica el formato:\n`largo ancho alto tipo cantidad`\nEjemplo: `300 200 100 12 500`"

# ===== ENVIAR MENSAJE A WHATSAPP =====
def enviar_mensaje(to_number, mensaje):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "text": {"body": mensaje}
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

if __name__ == "__main__":
    # Solo para desarrollo local
    app.run(host="0.0.0.0", port=5000, debug=True)