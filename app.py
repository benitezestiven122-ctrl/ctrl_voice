import os
import streamlit as st
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from PIL import Image
import time
import paho.mqtt.client as paho
import json
import random

# ==========================================
# 1. CONFIGURACIÓN Y ESTÉTICA (DARK STAGE)
# ==========================================
st.set_page_config(
    page_title="Vocal-Link | Stage Director",
    page_icon="🎤",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Teko:wght@400;600&family=Share+Tech+Mono&display=swap');

    html, body, [class*="css"] {
        font-family: 'Share Tech Mono', monospace;
        background-color: #05050A !important;
        color: #E0E0FF !important;
    }
    
    h1, h2, h3 { 
        font-family: 'Teko', sans-serif !important;
        color: #00FFCC !important; 
        letter-spacing: 1px;
    }
    
    .stButton > button {
        background-color: #000 !important;
        color: #FF0055 !important;
        border: 2px solid #FF0055 !important;
        border-radius: 5px !important;
        box-shadow: 0 0 10px rgba(255, 0, 85, 0.4);
        font-size: 1.2rem !important;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #FF0055 !important;
        color: #FFF !important;
        box-shadow: 0 0 20px rgba(255, 0, 85, 0.8);
    }
    
    .console-box {
        background-color: #0A0A14;
        border-left: 4px solid #00FFCC;
        padding: 15px;
        margin-top: 15px;
        font-family: 'Share Tech Mono', monospace;
        color: #00FFCC;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONFIGURACIÓN MQTT (BROKER IOT)
# ==========================================
BROKER = "broker.mqttdashboard.com"
PORT = 1883
TOPIC = "estiven_vj/stage_control"

# ID único para evitar desconexiones si abres múltiples pestañas
CLIENT_ID = f"VJ-Voice-Control-{random.randint(1000, 9999)}"

def on_publish(client, userdata, result):
    pass # Callback silencioso

# Inicializar cliente MQTT
try:
    client = paho.Client(CLIENT_ID)
    client.on_publish = on_publish
except Exception as e:
    st.error("Error al inicializar el cliente MQTT.")

# ==========================================
# 3. INTERFAZ Y COMANDOS RECONOCIDOS
# ==========================================
st.title("🎤 Vocal-Link: Stage Director")
st.markdown("Controlador escénico impulsado por voz. Habla para emitir señales (Triggers) a través del protocolo MQTT hacia sistemas de VJing como TouchDesigner o Resolume.")

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8659/8659223.png", width=100)
    st.subheader("📡 Enlace de Telemetría")
    st.write(f"**Broker:** `{BROKER}`")
    st.write(f"**Topic:** `{TOPIC}`")
    st.divider()
    
    st.subheader("📜 Comandos de Escenario (Guion)")
    st.write("Intenta decir estas frases:")
    st.code("- Activar glitch\n- Luces rojas\n- Blackout\n- Strobo\n- Iniciar visuales")

col1, col2 = st.columns([1, 1])

with col1:
    st.write("### 🎙️ Micrófono Abierto")
    st.write("Haz clic en el botón, permite el acceso al micrófono y dicta tu comando.")
    
    # Botón de grabación Bokeh (JS)
    stt_button = Button(label="🔴 REC / ESCUCHAR COMANDO", width=300, height=50)

    stt_button.js_on_event("button_click", CustomJS(code="""
        var recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'es-ES'; // Forzamos español para que entienda los comandos
     
        recognition.onresult = function (e) {
            var value = "";
            for (var i = e.resultIndex; i < e.results.length; ++i) {
                if (e.results[i].isFinal) {
                    value += e.results[i][0].transcript;
                }
            }
            if ( value != "") {
                document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
            }
        }
        recognition.start();
    """))

    result = streamlit_bokeh_events(
        stt_button,
        events="GET_TEXT",
        key="listen",
        refresh_on_update=False,
        override_height=75,
        debounce_time=0
    )

# ==========================================
# 4. LÓGICA DE PROCESAMIENTO Y ENVÍO (ROUTER)
# ==========================================
with col2:
    st.write("### 📟 Consola de Salida (MQTT)")
    
    if result and "GET_TEXT" in result:
        comando_voz = result.get("GET_TEXT").strip().lower()
        
        # Mapeo Inteligente (NLP básico) de voz a comandos de software
        payload = {"comando": "texto_libre", "valor": comando_voz, "vfx_id": 0}
        
        if "glitch" in comando_voz:
            payload = {"comando": "trigger_vfx", "valor": "glitch_heavy", "vfx_id": 1}
        elif "roja" in comando_voz or "rojas" in comando_voz:
            payload = {"comando": "cambio_color", "valor": "#FF0000", "vfx_id": 2}
        elif "blackout" in comando_voz or "apagar" in comando_voz:
            payload = {"comando": "master_opacity", "valor": 0.0, "vfx_id": 3}
        elif "strobo" in comando_voz:
            payload = {"comando": "trigger_vfx", "valor": "stroboscope", "vfx_id": 4}
        elif "iniciar" in comando_voz:
            payload = {"comando": "play_timeline", "valor": True, "vfx_id": 5}
            
        # Conectar y Enviar
        try:
            client.connect(BROKER, PORT)
            # Empaquetamos en JSON estándar de la industria
            mensaje_json = json.dumps(payload)
            client.publish(TOPIC, mensaje_json)
            client.disconnect()
            
            # Feedback Visual en la Consola
            st.markdown(f"""
            <div class="console-box">
                > Voz Detectada: "{comando_voz.upper()}"<br>
                > Paquete JSON enviado al Topic: {TOPIC}<br>
                > <span style="color: #FF0055;">{mensaje_json}</span><br>
                > Estado: TRANSMISIÓN EXITOSA ⚡
            </div>
            """, unsafe_allow_html=True)
            
            if payload["vfx_id"] != 0:
                st.success(f"¡Comando escénico '{payload['comando']}' disparado con éxito!")
            else:
                st.info("Comando no mapeado. Enviado como texto libre para generación generativa (Text-to-Video).")
                
        except Exception as e:
            st.error(f"Error de conexión MQTT: {e}")
    else:
        st.markdown("""
        <div class="console-box" style="border-color: #555; color: #555;">
            > Sistema en Standby...<br>
            > Esperando input de audio.
        </div>
        """, unsafe_allow_html=True)
