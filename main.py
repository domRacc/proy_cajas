from flask import Flask, request
import os, math, requests

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "mi-token-secreto")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")  
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Guarda el estado de cada usuario
usuarios = {}

# ==== LÓGICA DE CÁLCULO ====
def calcular_caja(largo, ancho, alto, tipocarton, color_carton, valorkilo, matriz, clisse, color, cantidad, bobinax=1600):
    valorkilo = int(valorkilo)
    matriz = int(matriz)
    clisse = int(clisse)
    color = int(color)
    cantidad = int(cantidad)
    bobinax = int(bobinax)

    # Convertir cm a mm para el cálculo interno
    largo = int(largo) * 10
    ancho = int(ancho) * 10
    alto = int(alto) * 10

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

    if bobina == r1000: bobina = 1000
    elif bobina == r1200: bobina = 1200
    elif bobina == r1400: bobina = 1400
    elif bobina == r1600: bobina = 1600

    un_golpe = int((bobina - 30) / ancho_placao)
    ancho_placa = int(bobina / un_golpe)
    un_golpex = int((bobinax - 30) / ancho_placao)
    ancho_placax = int(bobinax / un_golpex)

    tipos = {
        "12": (400, valorkilo / 2.5),
        "14": (450, valorkilo / 2.5 * 1.125),
        "17": (500, valorkilo / 2.5 * 1.25),
        "20": (600, valorkilo / 2.5 * 1.5),
    }
    if tipocarton not in tipos:
        return " Tipo de cartón no válido."

    # Recargo del 25% si el cartón es blanco
    recargo_blanco = 1.25 if color_carton == "blanco" else 1.0
    IVA = 0.19

    m2, valor = tipos[tipocarton]
    peso = int(ancho_placa * largo_placa * m2 / 10000)

    if cantidad > 0:
        preciocaja  = ((valor * ancho_placa  * largo_placa / 10000) + 10 + color*30 + (matriz + clisse*color) / cantidad) * recargo_blanco
        preciocajax = ((valor * ancho_placax * largo_placa / 10000) + 10 + color*30 + (matriz + clisse*color) / cantidad) * recargo_blanco
    else:
        preciocaja  = ((valor * ancho_placa  * largo_placa / 10000) + 10 + color*30) * recargo_blanco
        preciocajax = ((valor * ancho_placax * largo_placa / 10000) + 10 + color*30) * recargo_blanco

    preciocaja_iva  = preciocaja  * (1 + IVA)
    preciocajax_iva = preciocajax * (1 + IVA)

    tipo_carton_label = " Blanco" if color_carton == "blanco" else " Café"

    return (
        f" *COTIZACIÓN DE CAJA*\n\n"
        f"Desarrollo: {desarrollo}\n"
        f" Placa: {placa} ({placam2:.2f} m²)\n"
        f" Peso teórico: {peso} grs\n"
        f" Cartón: {tipo_carton_label}\n\n"
        f" *Bobina óptima ({bobina}mm):*\n"
        f"   • Sin IVA: ${int(preciocaja)} c/u\n"
        f"   • Con IVA: ${int(preciocaja_iva)} c/u\n\n"
        f" *Bobina alternativa ({bobinax}mm):*\n"
        f"   • Sin IVA: ${int(preciocajax)} c/u\n"
        f"   • Con IVA: ${int(preciocajax_iva)} c/u\n\n"
        f"_IVA incluido: 19%_"
    )

# ==== MENSAJES FIJOS ====
MSG_BIENVENIDA = (
    " ¡Bienvenido a *Cartón Chile*!\n\n"
    "Soy tu asistente de cotizaciones. ¿En qué te puedo ayudar?\n\n"
    "1 Cotizar caja de cartón\n"
    "2 Consultar tipos de cartón\n"
    "0 Salir\n\n"
    "_Responde con el número de la opción._"
)

MSG_TIPOS_CARTON = (
    " *Tipos de cartón disponibles:*\n\n"
    "• *12* - Simple (liviano)\n"
    "• *14* - Reforzado\n"
    "• *17* - Doble cara\n"
    "• *20* - Extra resistente\n\n"
    " *Color de cartón:*\n"
    "• *Café* - Precio estándar\n"
    "• *Blanco* - Precio + 25%\n\n"
    "Escribe *menu* para volver al inicio."
)

# ==== FLUJO CONVERSACIONAL ====
def procesar_mensaje(numero, texto):
    texto = texto.strip()
    texto_lower = texto.lower()

    # Palabras que reinician el flujo
    if texto_lower in ["hola", "inicio", "menu", "menú", "start", "0"]:
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
            return " *Paso 1/7*\n¿Cuál es el *largo* de la caja? (en cm)\nEjemplo: `30`"
        elif texto == "2":
            return MSG_TIPOS_CARTON
        else:
            return " Opción no válida. Responde *1*, *2* o *0*."

    # ── RECOLECCIÓN DE DATOS ──
    elif paso == 1:
        if not texto.isdigit():
            return "⚠️ Ingresa solo números. ¿Cuál es el *largo*? (cm)"
        estado["largo"] = int(texto)
        estado["paso"] = 2
        return " *Paso 2/7*\n¿Cuál es el *ancho* de la caja? (en cm)\nEjemplo: `20`"

    elif paso == 2:
        if not texto.isdigit():
            return "⚠️ Ingresa solo números. ¿Cuál es el *ancho*? (cm)"
        estado["ancho"] = int(texto)
        estado["paso"] = 3
        return " *Paso 3/7*\n¿Cuál es el *alto* de la caja? (en cm)\nEjemplo: `10`"

    elif paso == 3:
        if not texto.isdigit():
            return "⚠️ Ingresa solo números. ¿Cuál es el *alto*? (cm)"
        estado["alto"] = int(texto)
        estado["paso"] = 4
        return (
            " *Paso 4/7*\n¿Qué *tipo de cartón* necesitas?\n\n"
            "• *12* - Simple\n"
            "• *14* - Reforzado\n"
            "• *17* - Doble cara\n"
            "• *20* - Extra resistente\n"
            
        )

    elif paso == 4:
        if texto not in ["12", "14", "17", "20", "30"]:
            return " Tipo no válido. Elige: *12*, *14*, *17*, *20* ."
        estado["tipocarton"] = texto
        estado["valorkilo"] = 1150
        estado["paso"] = 5
        return (
            " *Paso 5/6*\n¿De qué *color* es el cartón?\n\n"
            "• *1* - Café \n" #(precio estándar)
            "• *2* - Blanco \n\n" #(precio + 25%)
            "Responde con *1* o *2*."
        )

    elif paso == 5:
        if texto not in ["1", "2"]:
            return " Opción no válida. Responde *1* para Café o *2* para Blanco."
        estado["color_carton"] = "cafe" if texto == "1" else "blanco"
        estado["paso"] = 6
        return "*Paso 5/6*\n¿Cuántos *colores* de impresión lleva la caja?\n(0 si no lleva impresión)"

    elif paso == 6:
        if not texto.isdigit():
            return " Ingresa solo números. ¿Cuántos *colores*?"
        estado["color"] = int(texto)
        estado["paso"] = 7
        return "*Paso 6/6*\n¿Cuántas *cajas* necesitas?\n(0 si aún no lo sabes)"

    elif paso == 7:
        if not texto.isdigit():
            return "Ingresa solo números. ¿Cuántas *cajas*?"
        estado["cantidad"] = int(texto)

        # Calcular cotización
        try:
            resultado = calcular_caja(
                largo=estado["largo"],
                ancho=estado["ancho"],
                alto=estado["alto"],
                tipocarton=estado["tipocarton"],
                color_carton=estado["color_carton"],
                valorkilo=estado["valorkilo"],
                matriz=0,
                clisse=0,
                color=estado["color"],
                cantidad=estado["cantidad"]
            )
            # Resetear estado
            usuarios[numero] = {"paso": 0}
            return resultado + "\n\nEscribe *menu* para hacer otra cotización."
        except Exception as e:
            usuarios[numero] = {"paso": 0}
            return f"Error al calcular: {e}\nEscribe *menu* para intentar de nuevo."

    return MSG_BIENVENIDA

# ==== WEBHOOK ====
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
    print(f"DEBUG: Datos recibidos de Meta: {data}")
    try:
        messages = data["entry"][0]["changes"][0]["value"].get("messages", [])
        if messages:
            msg = messages[0]
            numero = msg["from"]
            texto = msg.get("text", {}).get("body", "")
            respuesta = procesar_mensaje(numero, texto)
            enviar_mensaje(numero, respuesta)
    except Exception as e:
        print(f"Error: {e}")
    return "OK", 200

# ==== ENVIAR MENSAJE ====

def enviar_mensaje(to_number, mensaje):
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
    respuesta=requests.post(url, headers=headers, json=payload)
    print(f"DEBUG: Respuesta de Meta al enviar: {respuesta.json()}")
    return respuesta.json()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)