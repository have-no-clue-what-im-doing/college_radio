import logging
import logging.handlers
import socket
import requests

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set up syslog handler
syslog_handler = logging.handlers.SysLogHandler(address=('log.broderic.pro', 514))  # replace 'server_ip' with your server's IP
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
syslog_handler.setFormatter(formatter)
logger.addHandler(syslog_handler)

# Example log message
logger.info("This is a test log message from Python.")





# Configure logging
logging.basicConfig(filename='my_log_file.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s')

# Get the hostname and IP address
hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

# Create the log message
log_message = f"Hostname: {hostname}, IP Address: {ip_address}"

# Log the message
logging.info(log_message)

print("Log entry added:", log_message)

r = requests.get("https://ipecho.net/plain")

print(r.text)