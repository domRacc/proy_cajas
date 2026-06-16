# proy_cajas

Bot de WhatsApp para cotización automática de cajas de cartón personalizadas según las medidas ingresadas por el usuario.

## Descripción
Este proyecto permite recibir mensajes desde WhatsApp, guiar al usuario por un flujo conversacional y generar una cotización referencial de cajas de cartón según:
- largo interno
- ancho interno
- alto interno
- tipo de cartón
- color del cartón
- cantidad de colores de impresión
- cantidad de cajas

## Requisitos
- Python 3.10 o superior
- Cuenta de WhatsApp Business API
- Token de acceso de Meta
- Phone Number ID configurado
- Webhook accesible públicamente

## Variables de entorno

Antes de ejecutar el proyecto, debes definir las siguientes variables:

    VERIFY_TOKEN: token usado para verificar el webhook con Meta

    WHATSAPP_TOKEN: token de acceso de WhatsApp Business API

    PHONE_NUMBER_ID: identificador del número de teléfono conectado a la API


Debes entrar a tu configuración de WhatsApp Business API en Meta y obtener:

    el token de acceso

    el Phone Number ID

    la configuración del webhook, se recomienda usar ngrok 
    