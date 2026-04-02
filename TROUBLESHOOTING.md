# Telegram Speaker Bot - Troubleshooting Guide

## Overview
This bot listens for Telegram messages, uses Azure OpenAI (or GPT) to generate responses, and speaks them via a Google Home Mini speaker using Home Assistant's TTS.

## System Architecture
```
Telegram → Python Bot → MQTT → Home Assistant → Google Cast → Speaker
```

## Components
1. **Telegram Bot** - Receives messages, calls Azure OpenAI, publishes to MQTT
2. **MQTT (mosquitto)** - Message broker running on localhost:1883
3. **Home Assistant** - Docker container, receives MQTT messages, triggers TTS
4. **Google Cast** - Casts TTS audio to Google Home Mini speaker

## Common Issues & Solutions

### Issue 1: Speaker Not Speaking

**Symptoms:** You send a message but hear nothing from the speaker.

**Diagnosis Steps:**

1. **Check if bot is running:**
   ```bash
   ps aux | grep telegram
   ```
   Should show: `telegram-speaker-bot.py`

2. **Check MQTT is running:**
   ```bash
   ps aux | grep mosquitto
   ```

3. **Check Home Assistant is running:**
   ```bash
   docker ps | grep homeassistant
   ```

4. **Test MQTT manually:**
   ```bash
   /usr/local/bin/mosquitto_pub -t "openclaw/tts" -m "Test message"
   ```

5. **Check Home Assistant logs:**
   ```bash
   docker logs homeassistant --tail 20
   ```

### Issue 2: "Failed to cast media" Error in Home Assistant

**Symptoms:** Logs show: `Failed to cast media http://192.168.x.x:8123/api/tts_proxy/...`

**Cause:** Your Mac's IP address changed (router DHCP lease).

**Fix:**

1. **Find your current Mac IP:**
   ```bash
   ifconfig | grep "192.168.68" | head -1
   ```

2. **Update Home Assistant config:**
   ```bash
   # Edit the config file
   nano /Users/timphang/homeassistant/config/configuration.yaml
   ```
   Change:
   ```yaml
   homeassistant:
     external_url: "http://192.168.68.XX:8123"
     internal_url: "http://192.168.68.XX:8123"
   ```
   Replace `XX` with your current IP.

3. **Restart Home Assistant:**
   ```bash
   docker restart homeassistant
   ```

### Issue 3: MQTT Connection Refused

**Symptoms:** Home Assistant logs show: `Failed to connect to MQTT server: Connection refused`

**Fix:**

1. **Check MQTT broker setting in Home Assistant:**
   ```bash
   cat /Users/timphang/homeassistant/config/.storage/core.config_entries | python3 -c "
   import json,sys
   d=json.load(sys.stdin)
   for e in d['data']['entries']:
       if e.get('domain')=='mqtt':
           print('Broker:', e['data'].get('broker'))
   "
   ```

2. **Fix MQTT broker (should be `host.docker.internal`):**
   ```bash
   cat /Users/timphang/homeassistant/config/.storage/core.config_entries | python3 -c "
   import json,sys
   d=json.load(sys.stdin)
   for e in d['data']['entries']:
       if e.get('domain')=='mqtt':
           e['data']['broker'] = 'host.docker.internal'
           print('Fixed to host.docker.internal')
   json.dump(d, open('/Users/timphang/homeassistant/config/.storage/core.config_entries', 'w'))
   "
   ```

3. **Restart Home Assistant:**
   ```bash
   docker restart homeassistant
   ```

### Issue 4: Bot Not Responding to Telegram

**Fix:**

1. **Kill old bot processes:**
   ```bash
   pkill -f telegram-speaker-bot
   ```

2. **Start the bot:**
   ```bash
   cd /Users/timphang/telegram-speaker-bot
   python3 telegram-speaker-bot.py &
   ```

### Issue 5: Home Assistant Not Reachable

**Check:**
```bash
curl http://localhost:8123
```

If not reachable:
```bash
docker restart homeassistant
```

## Important Files

- **Bot script:** `/Users/timphang/telegram-speaker-bot/telegram-speaker-bot.py`
- **Bot logs:** `/Users/timphang/telegram-speaker-bot/bot.log`
- **HA config:** `/Users/timphang/homeassistant/config/configuration.yaml`
- **HA automations:** `/Users/timphang/homeassistant/config/automations/openclaw_tts_mqtt.yaml`

## Quick Restart Commands

```bash
# Restart everything
pkill -f telegram-speaker-bot
docker restart homeassistant
cd /Users/timphang/telegram-speaker-bot && python3 telegram-speaker-bot.py &
```

## IP Address Note

Your router assigns IP addresses via DHCP. If your Mac's IP changes, you'll need to update the Home Assistant config. To prevent this, you can:
1. Set a static DHCP reservation on your router
2. Or use a static IP on your Mac

## Testing TTS

```bash
# Publish directly to MQTT (bypasses bot)
/usr/local/bin/mosquitto_pub -t "openclaw/tts" -m "Hello, this is a test"
```

If this works but Telegram doesn't speak, the issue is in the bot.
If this doesn't work, the issue is in Home Assistant or the Cast device.
