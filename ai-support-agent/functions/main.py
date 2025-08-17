import logging

logging.basicConfig(level=logging.INFO)
logging.info("Loading functions...")

from email_processor.main import email_processor
from follow_up_agent.main import follow_up_agent
from chat_processor.main import chat_processor, get_chat_history

logging.info("Functions loaded: email_processor, follow_up_agent")
