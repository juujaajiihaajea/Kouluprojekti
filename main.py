import paho.mqtt.client as mqtt
import json
from flask import Flask
import threading
import os
from datetime import datetime
import statistics

# 1. Perustetaan Flask-palvelin
app = Flask(__name__)

# Tiedostopolku Renderin levylle (HUOM: vaatii "Disk"-asetuksen Renderissä)
# Jos et ole vielä luonut Disk-osiota, koodi käyttää oletuskansiota
DATA_DIR = "/data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, "data_arkisto.json")

# Lataa vanha data tiedostosta käynnistyksen yhteydessä
def lataa_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                content = f.read()
                return json.loads(content) if content else []
        except Exception as e:
            print(f"Virhe tiedoston luvussa: {e}")
            return []
    return []

# Tallenna data tiedostoon
def tallenna_data(lista):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(lista, f)
    except Exception as e:
        print(f"Tallennusvirhe: {e}")

# Alustetaan lista tallennetulla datalla
data_historia = lataa_data()

@app.route('/')
def home():
    return "<h1>IoT Tilastotyökalu (Pysyvä tallennus)</h1><p>Katso laajat tilastot: <a href='/data'>/data</a></p>", 200

@app.route('/data')
def nayta_data():
    if not data_historia:
        return "Ei vielä dataa kerättynä. Odota hetki tai varmista että anturit ovat päällä."
    
    arvot = {"T": [], "H": [], "CO2": [], "p": []}
    
    for rivi in data_historia:
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
        <title>IoT Laajat Tilastot</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f9; }}
            table {{ border-collapse: collapse; width: 100%; background: white; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
            th {{ background-color: #007bff; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .summary {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #28a745; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        </style>
    </head>
    <body>
        <div class="summary">
            <h2>📊 Tilastollinen yhteenveto (Pysyvä tallennus)</h2>
            <p><b>Näytteitä yhteensä:</b> {len(data_historia)} kpl</p>
            <p><b>Aikaväli:</b> {data_historia[0].get('vastaanottoaika', '-')} &mdash; {data_historia[-1].get('vastaanottoaika', '-')}</p>
            
            <table>
                <tr>
                    <th>Suure</th><th>Keskiarvo</th><th>Min</th><th>Max</th><th>Mediaani</th><th>Keskihajonta</th>
                </tr>
                <tr><td>Lämpötila (°C)</td><td>{stats_t[0]}</td><td>{stats_t[1]}</td><td>{stats_t[2]}</td><td>{stats_t[3]}</td><td>{stats_t[4]}</td></tr>
                <tr><td>Kosteus (%)</td><td>{stats_h[0]}</td><td>{stats_h[1]}</td><td>{stats_h[2]}</td><td>{stats_h[3]}</td><td>{stats_h[4]}</td></tr>
                <tr><td>CO2 (ppm)</td><td>{stats_co2[0]}</td><td>{stats_co2[1]}</td><td>{stats_co2[2]}</td><td>{stats_co2[3]}</td><td>{stats_co2[4]}</td></tr>
                <tr><td>Ihmismäärä</td><td>{stats_p[0]}</td><td>{stats_p[1]}</td><td>{stats_p[2]}</td><td>{stats_p[3]}</td><td>{stats_p[4]}</td></tr>
            </table>
        </div>
        <h3>📋 Kerätty arkisto</h3>
        <table>
            <tr><th>Aikaleima</th><th>Lämpötila</th><th>Kosteus</th><th>CO2</th><th>Ihmiset</th></tr>
    """
    
    for rivi in reversed(data_historia):
        html += f"<tr><td>{rivi.get('vastaanottoaika')}</td><td>{rivi.get('T', '-')}</td><td>{rivi.get('H', '-')}</td><td>{rivi.get('CO2', '-')}</td><td>{rivi.get('pCount', rivi.get('person count', '-'))}</td></tr>"
    
    html += "</table></body></html>"
    return html

# 2. MQTT-asetukset
MQTT_BROKER = "automaatio.cloud.shiftr.io"
MQTT_PORT = 1883
MQTT_USER = "automaatio"
MQTT_PASS = "Z0od2PZF65jbtcXu"
MQTT_TOPIC = "automaatio"

def on_connect(client, userdata, flags, rc):
    if rc == 0: client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        payload["vastaanottoaika"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_historia.append(payload)
        
        # Tallenna tiedostoon jokaisen viestin jälkeen
        tallenna_data(data_historia)
        
    except Exception as e: print(f"Virhe: {e}")

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
