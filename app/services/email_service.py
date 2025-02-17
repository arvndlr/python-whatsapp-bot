import imaplib
import email
import re
from datetime import datetime
import logging
from .openai_service import generate_response
from app.utils.whatsapp_utils import (
    get_text_message_input,
    send_message,
    process_text_for_whatsapp,
)
from flask import current_app


class EmailMonitor:
    def __init__(self, email_address, password, imap_server="imap.gmail.com"):
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.mail = None
        self.app = current_app._get_current_object()  # Store the app instance

    def connect(self):
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            return True
        except Exception as e:
            logging.error(f"Failed to connect to email: {str(e)}")
            return False

    def extract_phone_number(self, content):
        """Extract phone number from email content."""
        try:
            # Look for phone number patterns
            # This pattern looks for numbers that might start with + or numbers
            phone_pattern = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
            matches = re.findall(phone_pattern, content)

            if matches:
                # Take the first match
                phone_number = matches[0]
                logging.info(f"Found phone number: {phone_number}")
                return phone_number
            else:
                logging.warning("No phone number found in content")
                return None

        except Exception as e:
            logging.error(f"Error extracting phone number: {str(e)}")
            return None

    def process_emails(self, subject_trigger="WHATSAPP_NOTIFICATION"):
        with self.app.app_context():  # Use stored app instance
            self.mail = None
            try:
                # Create new connection for each check
                self.mail = imaplib.IMAP4_SSL(self.imap_server)
                self.mail.login(self.email_address, self.password)

                # Select the inbox and log mailbox status
                status, messages = self.mail.select("INBOX")
                logging.info(f"Mailbox select status: {status}")
                logging.info(f"Total messages in inbox: {messages[0].decode()}")

                # First, let's check ALL unread messages to debug
                _, all_unread = self.mail.search(None, "UNSEEN")
                logging.info(f"Total unread messages: {len(all_unread[0].split())}")

                # Now check messages with our specific subject
                _, message_numbers = self.mail.search(
                    None, f'(UNSEEN SUBJECT "{subject_trigger}")'
                )
                logging.info(
                    f"Search criteria used: UNSEEN SUBJECT '{subject_trigger}'"
                )
                logging.info(
                    f"Messages matching criteria: {len(message_numbers[0].split())}"
                )

                # List some recent message subjects for debugging
                _, recent_msgs = self.mail.search(None, "ALL")
                recent_numbers = recent_msgs[0].split()[-5:]  # Last 5 messages
                for num in recent_numbers:
                    _, msg_data = self.mail.fetch(num, "(RFC822)")
                    email_message = email.message_from_bytes(msg_data[0][1])
                    logging.info(f"Recent message subject: {email_message['subject']}")

                # Continue with regular processing...
                for num in message_numbers[0].split():
                    _, msg_data = self.mail.fetch(num, "(RFC822)")
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)

                    # Extract content
                    content = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/plain":
                                content = part.get_payload(decode=True).decode()
                                break
                    else:
                        content = email_message.get_payload(decode=True).decode()

                    logging.info(f"Email content: {content}")

                    # Extract phone number
                    phone_number = self.extract_phone_number(content)
                    logging.info(f"Extracted phone number: {phone_number}")

                    if phone_number:
                        logging.info(
                            f"Attempting to send WhatsApp message to: {phone_number}"
                        )
                        # Process the content to make it WhatsApp friendly
                        formatted_content = process_text_for_whatsapp(content)
                        self.send_whatsapp_notification(phone_number, formatted_content)
                    else:
                        logging.warning("No valid phone number found in email content")

                    # Mark email as read
                    self.mail.store(num, "+FLAGS", "\\Seen")

            except Exception as e:
                logging.error(f"Error processing emails: {str(e)}")
                logging.error(f"Error details: {str(e.__class__.__name__)}")
            finally:
                if self.mail is not None:
                    try:
                        if self.mail.state == "SELECTED":
                            try:
                                self.mail.close()
                            except:
                                pass
                        try:
                            self.mail.logout()
                        except:
                            pass
                        self.mail = None
                    except Exception as e:
                        logging.error(f"Error during cleanup: {str(e)}")
                        self.mail = None

    def send_whatsapp_notification(self, phone_number, content):
        with current_app.app_context():
            try:
                # Clean the phone number - remove any spaces, dashes, or parentheses
                clean_number = re.sub(r"[\s\-\(\)]", "", phone_number)

                # Ensure the number starts with '+'
                if not clean_number.startswith("+"):
                    clean_number = "+" + clean_number

                logging.info(f"Preparing to send WhatsApp message to: {clean_number}")

                # Format the message for WhatsApp
                data = get_text_message_input(
                    recipient=clean_number,
                    text=content,  # Send the formatted content directly
                )

                # Send the message and unpack the tuple
                response, error = send_message(data)

                if error:
                    logging.error(f"Failed to send WhatsApp message: {error}")
                    raise Exception(f"WhatsApp API error: {error}")

                logging.info(f"Successfully sent WhatsApp message to {clean_number}")

            except Exception as e:
                logging.error(f"Error sending WhatsApp notification: {str(e)}")
                logging.error(f"Phone number: {phone_number}")
                logging.error(f"Content: {content}")
                raise
