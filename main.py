import paho.mqtt.client as mqtt
import json
from flask import Flask
import threading
import os
from datetime import datetime

# 1. Perustetaan Flask-palvelin
app = Flask(__name__)

# Lista, johon tallennetaan viestit välimuistiin analyysia varten
data_historia = []

@app.route('/')
def home():
    return "<h1>Henkilölaskuri-kerääjä on käynnissä!</h1><p>Katso kerätty data osoitteesta: <a href='/data'>/data</a></p>", 200

@app.route('/data')
def nayta_data():
    # Palauttaa kaikki kerätyt viestit JSON-muodossa selaimelle
    return json.dumps(data_historia, indent=4)

# 2. MQTT-asetukset kurssimateriaalin mukaan
MQTT_BROKER = "automaatio.cloud.shiftr.io"
MQTT_PORT = 1883
MQTT_USER = "automaatio"
MQTT_PASS = "Z0od2PZF65jbtcXu"
MQTT_TOPIC = "automaatio" # Kuuntelee pääaihetta

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Yhdistetty välittäjään onnistuneesti!")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Yhteysvirhe, koodi: {rc}")

def on_message(client, userdata, msg):
    try:
        # Dekoodataan viesti
        payload = json.loads(msg.payload.decode())
        
        # Lisätään aikaleima, jos sitä ei ole viestissä
        if "DateTime" not in payload:
            payload["vastaanottoaika"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Tallennetaan listaan
        data_historia.append(payload)
        
        # Tulostetaan lokiin, jotta näet sen Renderissä
        print(f"ANTURIDATA VASTAANOTETTU: {payload}")
        
    except Exception as e:
        print(f"Virhe viestin käsittelyssä: {e}")

def start_mqtt():
    # Käytetään uusinta API-versiota
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"MQTT-yhteysvirhe: {e}")

if __name__ == "__main__":
    # Käynnistetään MQTT-kuuntelija omaan säikeeseensä
    threading.Thread(target=start_mqtt, daemon=True).start()
    
    # Käynnistetään Flask-palvelin Renderin porttiin
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
