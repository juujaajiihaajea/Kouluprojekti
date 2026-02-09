import paho.mqtt.client as mqtt
import json
from flask import Flask
import threading
import os
from datetime import datetime
import statistics
from pymongo import MongoClient

# 1. MongoDB määritykset
# MUISTA VAIHTAA OMA SALASANASI TÄHÄN!
MONGO_URI = "mongodb+srv://mikkhama:Jeejeejee123@@cluster0.xrolxhu.mongodb.net/?appName=Cluster0"
client_db = MongoClient(MONGO_URI)
db = client_db["iot_projekti"]
kokoelma = db["sensoridata"]

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>IoT Tilastotyökalu (MongoDB Atlas)</h1><p>Katso laajat tilastot: <a href='/data'>/data</a></p>", 200

@app.route('/data')
def nayta_data():
    try:
        kaikki_data = list(kokoelma.find().sort("vastaanottoaika", -1))
    except Exception as e:
        return f"Tietokantavirhe: {e}"
    
    if not kaikki_data:
        return "Ei vielä dataa tietokannassa. Odota hetki."
    
    arvot = {"T": [], "H": [], "CO2": [], "p": []}
    
    for rivi in kaikki_data:
        t = rivi.get("T")
        h = rivi.get("H")
        co2 = rivi.get("CO2")
        p = rivi.get("pCount", rivi.get("person count"))
        if isinstance(t, (int, float)): arvot["T"].append(t)
        if isinstance(h, (int, float)): arvot["H"].append(h)
        if isinstance(co2, (int, float)): arvot["CO2"].append(co2)
        if isinstance(p, (int, float)): arvot["p"].append(p)

    def laske_tilastot(lista):
        if len(lista) < 1: return ["-"] * 5
        ka = round(statistics.mean(lista), 2)
        mini = round(min(lista), 2)
        maxi = round(max(lista), 2)
        med = round(statistics.median(lista), 2)
        hajonta = round(statistics.stdev(lista), 2) if len(lista) > 1 else 0
        return [ka, mini, maxi, med, hajonta]

    stats_t = laske_tilastot(arvot["T"])
    stats_h = laske_tilastot(arvot["H"])
    stats_co2 = laske_tilastot(arvot["CO2"])
    stats_p = laske_tilastot(arvot["p"])

    html = f"""
    <html>
    <head>
        <title>IoT MongoDB Stats</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; }}
            table {{ border-collapse: collapse; width: 100%; background: white; margin-bottom: 30px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
            th {{ background-color: #28a745; color: white; }}
            .summary {{ background: white; padding: 20px; border-radius: 8px; border-left: 5px solid #28a745; }}
        </style>
    </head>
    <body>
        <div class="summary">
            <h2>📊 Tilastot (MongoDB)</h2>
            <table>
                <tr><th>Suure</th><th>KA</th><th>Min</th><th>Max</th><th>Med</th><th>Hajonta</th></tr>
                <tr><td>T (°C)</td><td>{stats_t[0]}</td><td>{stats_t[1]}</td><td>{stats_t[2]}</td><td>{stats_t[3]}</td><td>{stats_t[4]}</td></tr>
                <tr><td>H (%)</td><td>{stats_h[0]}</td><td>{stats_h[1]}</td><td>{stats_h[2]}</td><td>{stats_h[3]}</td><td>{stats_h[4]}</td></tr>
                <tr><td>CO2</td><td>{stats_co2[0]}</td><td>{stats_co2[1]}</td><td>{stats_co2[2]}</td><td>{stats_co2[3]}</td><td>{stats_co2[4]}</td></tr>
                <tr><td>Ihmiset</td><td>{stats_p[0]}</td><td>{stats_p[1]}</td><td>{stats_p[2]}</td><td>{stats_p[3]}</td><td>{stats_p[4]}</td></tr>
            </table>
        </div>
        <table>
            <tr><th>Aikaleima</th><th>T</th><th>H</th><th>CO2</th><th>P</th></tr>
    """
    for rivi in kaikki_data:
        html += f"<tr><td>{rivi.get('vastaanottoaika')}</td><td>{rivi.get('T','-')}</td><td>{rivi.get('H','-')}</td><td>{rivi.get('CO2','-')}</td><td>{rivi.get('pCount', rivi.get('person count','-'))}</td></tr>"
    
    html += "</table></body></html>"
    return html

# 2. MQTT ja tallennus
MQTT_BROKER = "automaatio.cloud.shiftr.io"
MQTT_TOPIC = "automaatio"

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        payload["vastaanottoaika"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        kokoelma.insert_one(payload)
    except Exception as e:
        print(f"Virhe: {e}")

def start_mqtt():
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    c.username_pw_set("automaatio", "Z0od2PZF65jbtcXu")
    c.on_connect = lambda client, userdata, flags, rc: client.subscribe(MQTT_TOPIC)
    c.on_message = on_message
    c.connect(MQTT_BROKER, 1883, 60)
    c.loop_forever()

if __name__ == "__main__":
    threading.Thread(target=start_mqtt, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
