import logging
from flask import current_app, jsonify
import json
import requests
import os

# from app.services.openai_service import generate_response
import re


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def generate_response(response):
    # Return text in uppercase
    return response.upper()


def send_message(data):
    try:
        # For testing only - replace with your actual values
        token = "your_whatsapp_token_here"
        phone_number_id = "your_phone_number_id_here"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"

        response = requests.post(url, json=data, headers=headers)

        if response.status_code != 200:
            logging.error(
                f"Request failed due to: {response.status_code} {response.reason} for url: {url}"
            )
            return None, response.status_code

        return response.json(), None

    except Exception as e:
        logging.error(f"Error in send_message: {str(e)}")
        return None, str(e)


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    try:
        wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
        name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        if "text" not in message:
            logging.warning("Received non-text message type")
            return

        message_body = message["text"]["body"]

        response = generate_response(message_body)
        data = get_text_message_input(wa_id, response)
        send_message(data)
    except (KeyError, IndexError) as e:
        logging.error(f"Error processing WhatsApp message: {str(e)}")
        raise


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
