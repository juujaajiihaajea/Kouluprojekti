import paho.mqtt.client as mqtt
import json
from flask import Flask
import threading
import os
from datetime import datetime

# 1. Perustetaan Flask-palvelin
app = Flask(__name__)

# Lista, johon tallennetaan viestit välimuistiin
data_historia = []

@app.route('/')
def home():
    return "<h1>Henkilölaskuri-kerääjä on käynnissä!</h1><p>Katso taulukko ja keskiarvot: <a href='/data'>/data</a></p>", 200

@app.route('/data')
def nayta_data():
    if not data_historia:
        return "Ei vielä dataa kerättynä. Odota hetki tai varmista että anturit ovat päällä."
    
    # Alustetaan laskurit keskiarvoja varten
    summat = {"T": 0, "H": 0, "CO2": 0, "p": 0}
    laskuri = 0

    # Haetaan aikaväli listan alusta ja lopusta
    aloitus_aika = data_historia[0].get("vastaanottoaika", "Ei tietoa")
    lopetus_aika = data_historia[-1].get("vastaanottoaika", "Ei tietoa")

    # Rakennetaan HTML-taulukko ja tyylit
    html = """
    <html>
    <head>
        <title>IoT Data Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; }
            table { border-collapse: collapse; width: 100%; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #007bff; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .summary { background-color: #ffffff; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #007bff; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            h2 { color: #333; margin-top: 0; }
            .time-range { color: #555; font-style: italic; margin-bottom: 15px; }
        </style>
    </head>
    <body>
    """

    taulukon_rivit = ""
    for rivi in data_historia:
        t = rivi.get("T", 0)
        h = rivi.get("H", 0)
        co2 = rivi.get("CO2", 0)
        p = rivi.get("pCount", rivi.get("person count", 0))
        aika = rivi.get("vastaanottoaika", rivi.get("Time", "Ei aikaa"))

        if isinstance(t, (int, float)): summat["T"] += t
        if isinstance(h, (int, float)): summat["H"] += h
        if isinstance(co2, (int, float)): summat["CO2"] += co2
        if isinstance(p, (int, float)): summat["p"] += p
        laskuri += 1

        taulukon_rivit += f"<tr><td>{aika}</td><td>{t} °C</td><td>{h} %</td><td>{co2} ppm</td><td>{p} hlö</td></tr>"

    ka_t = round(summat["T"] / laskuri, 2)
    ka_h = round(summat["H"] / laskuri, 2)
    ka_co2 = round(summat["CO2"] / laskuri, 1)
    ka_p = round(summat["p"] / laskuri, 1)
    
    html += f"""
    <div class="summary">
        <h2>📊 Kerätyn datan keskiarvot</h2>
        <p class="time-range">🕒 <b>Aikaväli:</b> {aloitus_aika}  &mdash;  {lopetus_aika}</p>
        <p><b>Näytteitä yhteensä:</b> {laskuri} kpl</p>
        <hr>
        <p><b>Lämpötila keskimäärin:</b> {ka_t} °C</p>
        <p><b>Kosteus keskimäärin:</b> {ka_h} %</p>
        <p><b>CO2-taso keskimäärin:</b> {ka_co2} ppm</p>
        <p><b>Ihmismäärä keskimäärin:</b> {ka_p} henkilöä</p>
    </div>
    """

    html += "<table><tr><th>Aikaleima</th><th>Lämpötila</th><th>Kosteus</th><th>CO2</th><th>Ihmismäärä</th></tr>"
    html += taulukon_rivit
    html += "</table></body></html>"
    
    return html

# 2. MQTT-asetukset
MQTT_BROKER = "automaatio.cloud.shiftr.io"
MQTT_PORT = 1883
MQTT_USER = "automaatio"
MQTT_PASS = "Z0od2PZF65jbtcXu"
MQTT_TOPIC = "automaatio"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        payload["vastaanottoaika"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_historia.append(payload)
    except Exception as e:
        print(f"Virhe: {e}")

def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    threading.Thread(target=start_mqtt, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
