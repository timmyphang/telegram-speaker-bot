# Telegram Speaker Bot

A Telegram bot that responds to messages using Azure OpenAI and Brave Search, with responses spoken aloud on a Google Home Mini speaker via Home Assistant and MQTT.

## Architecture

```
User → Telegram Bot → Azure OpenAI (LLM) → Brave Search (context) → MQTT → Home Assistant → Google Home Mini Speaker
```

## Prerequisites

### 1. Hardware/Software Requirements
- Mac (or any machine running the bot)
- Google Home Mini speaker
- Home Assistant (running in Docker)
- Mosquitto MQTT broker

### 2. Accounts & API Keys Required

| Service | How to Get | Config Variable |
|---------|------------|-----------------|
| **Telegram Bot** | @BotFather on Telegram | `BOT_TOKEN` |
| **Azure OpenAI** | Azure Portal → AI Studio → Deployments | `AZURE_ENDPOINT`, `AZURE_API_KEY`, `AZURE_DEPLOYMENT` |
| **Brave Search** | https://brave.com/search/api/ | `BRAVE_API_KEY` |
| **Home Assistant** | Running on your network | MQTT integration configured |
| **MQTT Broker** | Mosquitto on localhost:1883 | Default config |

## Setup Steps

### Step 1: Install Python Dependencies

```bash
pip3 install python-telegram-bot requests
```

### Step 2: Configure Mosquitto (MQTT Broker)

Install and run Mosquitto:

```bash
# On macOS
brew install mosquitto
brew services start mosquitto

# Verify it's running
netstat -an | grep 1883
```

### Step 3: Set Up Home Assistant

1. Run Home Assistant in Docker:
```bash
docker run -d --name homeassistant \
  -p 8123:8123 \
  -v /path/to/config:/config \
  --restart unless-stopped \
  homeassistant/amd64-homeassistant:latest
```

2. Configure MQTT in Home Assistant:
   - Go to Settings → Devices & Services → Add Integration
   - Search for "MQTT"
   - Enter broker: `host.docker.internal` (or your Mac's IP)
   - Port: `1883`

3. Create MQTT Automation (`/config/automations/openclaw_tts_mqtt.yaml`):
```yaml
- alias: OpenClaw TTS via MQTT
  trigger:
    - platform: mqtt
      topic: openclaw/tts
  action:
    - service: tts.google_translate_say
      data:
        entity_id: media_player.your_speaker_name
        message: "{{ trigger.payload }}"
```

4. Reload automations in Home Assistant

### Step 4: Configure the Bot

Edit `telegram-speaker-bot.py` and update these variables:

```python
# Telegram Bot Token (from @BotFather)
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Azure OpenAI Configuration
AZURE_ENDPOINT = "https://your-resource.openai.azure.com/openai"
AZURE_API_KEY = "YOUR_AZURE_API_KEY"
AZURE_DEPLOYMENT = "gpt-4o-mini"  # Your deployment name
AZURE_API_VERSION = "2025-04-01-preview"

# Brave Search API
BRAVE_API_KEY = "YOUR_BRAVE_SEARCH_API_KEY"

# MQTT Binary (path to mosquitto_pub)
MQTT_BIN = "/usr/local/bin/mosquitto_pub"
```

### Step 5: Run the Bot

```bash
cd /path/to/telegram-speaker-bot
python3 telegram-speaker-bot.py
```

To run in background:
```bash
nohup python3 telegram-speaker-bot.py > bot.log 2>&1 &
```

### Step 6: Test

1. Open Telegram and message your bot (@your_bot_username)
2. The bot will:
   - Search the web for context
   - Generate a response using Azure OpenAI
   - Speak the response on your Google Home Mini
   - Also reply in Telegram

## Troubleshooting

### Bot says "Conflict: terminated by other getUpdates request"
Another instance of the bot is running. Kill it:
```bash
pkill -f "telegram-speaker-bot"
```

### No response from LLM
Check your Azure credentials and deployment name. Test with:
```bash
curl -X POST "https://YOUR_ENDPOINT/openai/deployments/YOUR_DEPLOYMENT/chat/completions?api-version=2025-04-01-preview" \
  -H "api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"system","content":"You are helpful."},{"role":"user","content":"Hi"}],"max_tokens":50}'
```

### Speaker not speaking
Check MQTT is working:
```bash
mosquitto_pub -t "openclaw/tts" -m "test message"
```

Check Home Assistant logs:
```bash
docker logs homeassistant
```

## File Structure

```
telegram-speaker-bot/
├── telegram-speaker-bot.py   # Main bot script
├── README.md                # This file
└── .env                    # (optional) Store API keys here
```
