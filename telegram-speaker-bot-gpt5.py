#!/usr/bin/env python3
# Telegram Bot - Direct to Speaker with Azure OpenAI + Brave Search
# Listens for messages, searches the web, and speaks the LLM response

import os
import json
import subprocess
import requests
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# Azure OpenAI Configuration
AZURE_ENDPOINT = "https://gai-443-openai.openai.azure.com/openai"
AZURE_API_KEY = "YOUR_AZURE_OPENAI_API_KEY"
AZURE_MODEL = "gpt-5-mini"
AZURE_DEPLOYMENT = "gpt-5-mini"
AZURE_API_VERSION = "2025-04-01-preview"

# Brave Search API
BRAVE_API_KEY = "YOUR_BRAVE_SEARCH_API_KEY"

MQTT_BIN = "/usr/local/bin/mosquitto_pub"

def brave_search(query):
    """Search the web using Brave Search API"""
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "X-Subscription-Token": BRAVE_API_KEY,
        "Accept": "application/json"
    }
    params = {
        "q": query,
        "count": 5
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        results = response.json()

        search_results = []
        if "web" in results and "results" in results["web"]:
            for item in results["web"]["results"][:5]:
                title = item.get("title", "")
                url = item.get("url", "")
                description = item.get("description", "")
                if title and url:
                    search_results.append(f"{title}: {description}")

        return search_results
    except Exception as e:
        print(f"Brave search error: {e}")
        return []

def call_azure_llm(user_message, search_context="", image_url=None):
    """Call Azure OpenAI with Responses API (GPT-5)"""
    # Build instructions
    if image_url:
        instructions = "When analyzing images: If there is text or words in the image, transcribe ONLY the text exactly as it appears. Do NOT add descriptions, explanations, or any additional content beyond the transcribed text. Only respond with the text found in the image."
    else:
        instructions = "You are a friendly helper. Explain things in a simple way that a 7 year old can understand. Use short sentences and easy words."

    if search_context:
        instructions += f"\n\nHere is some context from web search:\n{search_context}"

    # Build input for Responses API - use role/content format
    if image_url:
        input_content = [
            {"role": "user", "content": [
                {"type": "input_text", "text": user_message},
                {"type": "input_image", "image_url": image_url}
            ]}
        ]
    else:
        input_content = [{"role": "user", "content": user_message}]

    try:
        # Use Responses API for GPT-5
        url = f"{AZURE_ENDPOINT}/responses?api-version={AZURE_API_VERSION}"

        payload = {
            "model": AZURE_MODEL,
            "instructions": instructions,
            "input": input_content,
            "max_output_tokens": 500,
            "reasoning": {"effort": "minimal"}
        }

        response = requests.post(
            url,
            headers={
                "api-key": AZURE_API_KEY,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )

        result = response.json()
        print(f"Azure response: {result}")

        # Parse Responses API format
        if "output" in result and len(result["output"]) > 0:
            for item in result["output"]:
                if item.get("type") == "message":
                    for content in item.get("content", []):
                        if content.get("type") == "output_text":
                            return content.get("text", "")
        return None

    except Exception as e:
        print(f"Azure API error: {e}")
        return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a message or image and I'll search the web and speak the response on your Google Home Mini.")


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image messages - download and analyze"""
    await update.message.chat.send_action("typing")

    try:
        # Get the photo (highest resolution)
        photo = update.message.photo[-1]

        # Get the file from Telegram
        file = await context.bot.get_file(photo.file_id)

        # Create a bytes buffer to download the image
        image_buffer = io.BytesIO()
        await file.download_to_memory(out=image_buffer)
        image_buffer.seek(0)

        # Convert to base64 for Azure OpenAI
        import base64
        image_base64 = base64.b64encode(image_buffer.read()).decode('utf-8')
        image_data_url = f"data:image/jpeg;base64,{image_base64}"

        # Call Azure OpenAI with image
        llm_response = call_azure_llm(
            "Transcribe all text visible in this image exactly as it appears.",
            image_url=image_data_url
        )

        if llm_response:
            # Publish to MQTT (will trigger speaker)
            subprocess.run([MQTT_BIN, "-t", "openclaw/tts", "-m", llm_response])

            # Also send to Telegram
            await update.message.reply_text(llm_response)
        else:
            await update.message.reply_text("Sorry, I couldn't analyze the image.")

    except Exception as e:
        print(f"Image error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    # Send "typing" action
    await update.message.chat.send_action("typing")

    try:
        # First, do a Brave search
        await update.message.chat.send_action("typing")
        search_results = brave_search(user_message)

        search_context = ""
        if search_results:
            search_context = "\n\n".join(search_results[:3])
            print(f"Search context: {search_context}")

        # Call Azure OpenAI with search context
        await update.message.chat.send_action("typing")
        llm_response = call_azure_llm(user_message, search_context)

        if llm_response:
            # Publish to MQTT (will trigger speaker)
            subprocess.run([MQTT_BIN, "-t", "openclaw/tts", "-m", llm_response])

            # Also send to Telegram
            await update.message.reply_text(llm_response)
        else:
            await update.message.reply_text("Sorry, I didn't get a response from the LLM.")

    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Telegram bot running with Azure GPT-5 Mini + Brave Search + Image Vision...")
    app.run_polling(poll_interval=1)

if __name__ == "__main__":
    main()
