from flask import Flask
import threading
from bot import AntonioBot

app = Flask(__name__)

@app.route('/')
def home():
    return "AntonioBOT is running! 🚀"

def run_irc():
    # IRC config
    IRC_SERVER = "irc.hybridirc.com"
    IRC_PORT = 6667
    IRC_CHANNEL = "#ChatWithWorld"
    IRC_NICK = "AntonioBOT"
    
    bot = AntonioBot(IRC_CHANNEL, IRC_NICK, IRC_SERVER, IRC_PORT)
    bot.start()

if __name__ == "__main__":
    # Start IRC bot in a separate thread
    irc_thread = threading.Thread(target=run_irc)
    irc_thread.daemon = True
    irc_thread.start()
    
    # Run Flask app (Render uses the PORT env var)
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
