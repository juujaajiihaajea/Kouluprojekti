import paho.mqtt.client as mqtt
import json
from flask import Flask
import threading
import os
from datetime import datetime
import statistics
from pymongo import MongoClient

# 1. MongoDB määritykset
# VAIHDA OMA SALASANASI tähän riville
MONGO_URI = "mongodb+srv://mikkhama:Jeejeejee123@ @cluster0.xrolxhu.mongodb.net/?appName=Cluster0"
client_db = MongoClient(MONGO_URI)
db = client_db["iot_projekti"]
kokoelma = db["sensoridata"]

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>IoT Tilastotyökalu (MongoDB Atlas)</h1><p>Katso laajat tilastot: <a href='/data'>/data</a></p>", 200

@app.route('/data')
def nayta_data():
    # Haetaan kaikki data tietokannasta, uusin ensin
    try:
        kaikki_data = list(kokoelma.find().sort("vastaanottoaika", -1))
    except Exception as e:
        return f"Tietokantavirhe: {e}"
    
    if not kaikki_data:
        return "Ei vielä dataa tietokannassa. Odota hetki, että ensimmäinen viesti saapuu."
    
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
            table {{ border-collapse: collapse; width: 100%; background: white; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
            th {{ background-color: #28a745; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .summary {{ background: white; padding: 20px; border-radius: 8px; border-left: 5px solid #28a745; box-shadow:
