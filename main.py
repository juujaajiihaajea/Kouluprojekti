import paho.mqtt.client as mqtt
import json
from flask import Flask
import threading
import os

# 1. Perustetaan Flask-palvelin Renderiä varten
app = Flask(__name__)

@app.route('/')
def home():
    return "Henkilölaskuri-kerääjä on käynnissä!", 200

# 2. MQTT-asetukset materiaalin sivulta 20
MQTT_BROKER = "automaatio.cloud.shiftr.io"
MQTT_PORT = 1883
MQTT_USER = "automaatio"
MQTT_PASS = "Z0od2PZF65jbtcXu"
MQTT_TOPIC = "automaatio"

def on_connect(client, userdata, flags, rc):
    print(f"Yhdistetty välittäjään koodilla {rc}")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # Tässä kohdassa data tulostuu lokiin. 
        # Projektia varten tämä data kannattaisi tallentaa esim. tiedostoon tai tietokantaan.
        print(f"Vastaanotettu data: {payload}")
    except Exception as e:
        print(f"Virhe viestin käsittelyssä: {e}")

def start_mqtt():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    # Käynnistetään MQTT-kuuntelija omaan säikeeseensä
    threading.Thread(target=start_mqtt, daemon=True).start()
    
    # Käynnistetään Flask-palvelin
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
