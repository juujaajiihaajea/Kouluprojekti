import paho.mqtt.client as mqtt
import json
from flask import Flask
import threading
import os
from datetime import datetime
import statistics
from pymongo import MongoClient
import urllib.parse

# 1. MongoDB määritykset
username = "mikkhama"
# KIRJOITA TÄHÄN SALASANASI (vaikka siinä olisi se @-merkki)
password = "Jeejeejee123@"

# Tämä koodaa salasanan oikein (erityisesti se @-merkki)
safe_password = urllib.parse.quote_plus(password)

# Lisätty tlsAllowInvalidCertificates=true korjaamaan SSL-virhe
MONGO_URI = f"mongodb+srv://{username}:{safe_password}@cluster0.xrolxhu.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"

client_db = MongoClient(MONGO_URI)
db = client_db["iot_projekti"]
kokoelma = db["sensoridata"]

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>IoT Tilastotyökalu</h1><p><a href='/data'>Katso data tästä</a></p>", 200

@app.route('/data')
def nayta_data():
    try:
        # Haetaan data tietokannasta
        kaikki_data = list(kokoelma.find().sort("vastaanottoaika", -1))
    except Exception as e:
        return f"Tietokantavirhe: {e}"
    
    if not kaikki_data:
        return "Ei vielä dataa tietokannassa. Odota hetki, että ensimmäinen viesti saapuu."
    
    arvot = {"T": [], "H": [], "CO2": [], "p": []}
    for rivi in kaikki_data:
        for k in ["T", "H", "CO2"]:
            v = rivi.get(k)
            if isinstance(v, (int, float)): arvot[k].append(v)
        p = rivi.get("pCount", rivi.get("person count"))
        if isinstance(p, (int, float)): arvot["p"].append(p)

    def stats(l):
        if not l: return ["-"] * 5
        return [round(statistics.mean(l),2), min(l), max(l), round(statistics.median(l),2), round(statistics.stdev(l),2) if len(l)>1 else 0]

    st = {k: stats(arvot[k]) for k in arvot}

    html = f"""
    <html>
    <head>
        <title>IoT MongoDB Stats</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; }}
            table {{ border-collapse: collapse; width: 100%; background: white; margin-bottom: 30px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
            th {{ background-color: #28a745; color: white; }}
            .summary {{ background: white; padding: 20px; border-radius: 8px; border-left: 5px solid #28a745; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="summary">
            <h2>📊 Tilastollinen yhteenveto (Pysyvä MongoDB)</h2>
            <table>
                <tr><th>Suure</th><th>KA</th><th>Min</th><th>Max</th><th>Med</th><th>Hajonta</th></tr>
                <tr><td>Lämpötila (°C)</td><td>{st['T'][0]}</td><td>{st['T'][1]}</td><td>{st['T'][2]}</td><td>{st['T'][3]}</td><td>{st['T'][4]}</td></tr>
                <tr><td>Ihmismäärä</td><td>{st['p'][0]}</td><td>{st['p'][1]}</td><td>{st['p'][2]}</td><td>{st['p'][3]}</td><td>{st['p'][4]}</td></tr>
            </table>
        </div>
        <h3>📋 Kaikki kerätyt rivit</h3>
        <table>
            <tr><th>Aikaleima</th><th>T</th><th>H</th><th>CO2</th><th>P</th></tr>
    """
    for r in kaikki_data:
        html += f"<tr><td>{r.get('vastaanottoaika')}</td><td>{r.get('T','-')}</td><td>{r.get('H','-')}</td><td>{r.get('CO2','-')}</td><td>{r.get('pCount', r.get('person count','-'))}</td></tr>"
    
    html += "</table></body></html>"
    return html

# 2. MQTT ja tallennus
MQTT_BROKER = "automaatio.cloud.shiftr.io"
MQTT_TOPIC = "automaatio"

def on_message(client, userdata, msg):
    try:
        p = json.loads(msg.payload.decode())
        p["vastaanottoaika"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        kokoelma.insert_one(p)
    except Exception as e:
        print(f"Tallennusvirhe: {e}")

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
