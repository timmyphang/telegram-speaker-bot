#!/usr/bin/env python3
"""Local TTS using macOS say command"""
import subprocess
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected to MQTT with result code {rc}")
    client.subscribe("openclaw/tts")

def on_message(client, userdata, msg):
    message = msg.payload.decode('utf-8')
    print(f"Speaking: {message[:50]}...")
    # Use macOS say command
    subprocess.run(["say", "-v", "Samantha", message])

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print("Starting local TTS listener...")
client.connect("localhost", 1883, 60)
client.loop_forever()
