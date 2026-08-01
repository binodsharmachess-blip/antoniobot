import irc.bot
import threading
import time
from datetime import datetime
import pytz
import storage

NPT = pytz.timezone('Asia/Kathmandu')

class AntonioBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        super().__init__([(server, port)], nickname, "Bot Version of Antonio")
        self.channel = channel
        self.study_start_time = None
        self.session_seconds = 0
        self.note_playing = False
        self.last_tdl_reminder = time.time()

    def on_welcome(self, c, e):
        c.join(self.channel)
        print(f"[+] AntonioBOT joined {self.channel}")
        # Start background threads
        threading.Thread(target=self.bg_loop, daemon=True).start()

    def format_seconds(self, s):
        hours = s // 3600
        minutes = (s % 3600) // 60
        seconds = s % 60
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

    def bg_loop(self):
        """Reminders and Note looping"""
        while True:
            time.sleep(1)
            now_ts = time.time()
            data = storage.get_data()

            # TDL Reminder every 45 mins
            if now_ts - self.last_tdl_reminder > 2700: # 45 mins
                if data["tdl"]:
                    msg = "📝 **TO-DO LIST REMINDER:** " + " | ".join(data["tdl"])
                    self.connection.privmsg(self.channel, msg)
                    self.connection.privmsg("Antonio", msg)
                self.last_tdl_reminder = now_ts

    def play_notes(self):
        """Looping notes logic"""
        while self.note_playing:
            data = storage.get_data()
            if not data["notes"]: break
            for i, note in enumerate(data["notes"]):
                if not self.note_playing: break
                for _ in range(3): # Repeat thrice
                    if not self.note_playing: break
                    self.connection.privmsg(self.channel, f"📌 [Note {i+1}]: {note} 💡")
                    time.sleep(20)

    def on_pubmsg(self, c, e):
        msg = e.arguments[0].strip()
        author = e.source.nick
        cmd = msg.split()[0].lower() if msg else ""

        # Admin Control Check
        if cmd.startswith("!") and author.lower() != "antonio":
            c.privmsg(self.channel, f"🚫 Hey @{author}, only **Antonio** can command me! 🔒")
            return

        # Mention Check
        if "antonio" in msg.lower() and author.lower() != "antonio":
            data = storage.get_data()
            if data["status"] == "study":
                c.privmsg(self.channel, f"📚 Antonio is deep in study mode right now! 🎯 Please PM him; he'll get back to you later. ✨")
            elif data["status"] == "free":
                c.privmsg(self.channel, f"👋 Antonio is around! He might respond soon, or you can drop him a PM. 😊")
            elif data["status"] == "off":
                c.privmsg(self.channel, f"🌙 Antonio is currently offline. He'll be back later! 🕒")

        # --- COMMANDS ---

        if cmd == "!startstudy":
            self.study_start_time = datetime.now(NPT)
            c.privmsg(self.channel, f"🚀 **STUDY SESSION STARTED** at {self.study_start_time.strftime('%H:%M:%S')} (NPT). Let's go, Antonio! 💪🔥")

        elif cmd == "!pausestudy" or cmd == "!endstudy":
            if not self.study_start_time:
                c.privmsg(self.channel, "⚠️ No active session found!")
                return
            
            now = datetime.now(NPT)
            diff = (now - self.study_start_time).total_seconds()
            storage.update_study_record(diff)
            total_today = storage.get_data()["total_seconds_today"]
            
            report = (f"🛑 **{'PAUSED' if cmd == '!pausestudy' else 'ENDED'}** at {now.strftime('%H:%M:%S')}. "
                      f"Session: {self.format_seconds(diff)} | Total Today: {self.format_seconds(total_today)} 📊")
            c.privmsg(self.channel, report)
            
            if cmd == "!endstudy":
                c.privmsg(self.channel, "✅ Day complete! Records have been updated. Great work! 🌟")
            self.study_start_time = None

        elif cmd == "!resumestudy":
            self.study_start_time = datetime.now(NPT)
            c.privmsg(self.channel, f"🔄 **STUDY RESUMED** at {self.study_start_time.strftime('%H:%M:%S')}. Locking back in! 📚✨")

        elif cmd == "!dailyrec":
            data = storage.get_data()
            c.privmsg(self.channel, f"📅 **Daily Record:** You have studied {self.format_seconds(data['total_seconds_today'])} today! 🎯")

        elif cmd == "!tdl":
            data = storage.get_data()
            parts = msg.split(maxsplit=1)
            if len(parts) > 1:
                sub = parts[1].lower()
                if sub == "y-":
                    c.privmsg(self.channel, "🎉 Awesome! You completed your To-Do list! 🏆")
                    data["tdl"] = []
                elif sub == "clear":
                    data["tdl"] = []
                    c.privmsg(self.channel, "🗑️ TDL cleared.")
                else:
                    data["tdl"].append(parts[1])
                    c.privmsg(self.channel, f"📝 Added to TDL: {parts[1]}")
                storage.save_json(storage.DATA_FILE, data)

        elif cmd == "!snote":
            data = storage.get_data()
            parts = msg.split(maxsplit=1)
            if len(parts) > 1:
                sub = parts[1].lower()
                if sub == "clearall":
                    data["notes"] = []
                    c.privmsg(self.channel, "🗑️ All notes deleted.")
                elif sub == "play-":
                    self.note_playing = True
                    threading.Thread(target=self.play_notes, daemon=True).start()
                    c.privmsg(self.channel, "🎶 Playing notes loop started...")
                elif sub == "stop-":
                    self.note_playing = False
                    c.privmsg(self.channel, "⏹️ Notes loop stopped.")
                else:
                    data["notes"].append(parts[1])
                    c.privmsg(self.channel, f"📌 Note added: {parts[1]}")
                storage.save_json(storage.DATA_FILE, data)

        elif cmd == "!time":
            now = datetime.now(NPT)
            c.privmsg(self.channel, f"🕒 **Current Nepal Time:** {now.strftime('%Y-%m-%d %H:%M:%S')} 🇳🇵")

        elif cmd == "!streak":
            data = storage.get_data()
            # logic: if today > 5hrs, show fire.
            fire = "🔥" if data["total_seconds_today"] >= 18000 else "🕒"
            c.privmsg(self.channel, f"✨ **Achievements:** Streak: {data['streak']} {fire} | Stars: {data['stars']} ⭐")

        elif cmd == "!mystatus":
            parts = msg.split()
            if len(parts) > 1:
                status_type = parts[1].lower()
                data = storage.get_data()
                if status_type in ["study", "free", "off"]:
                    data["status"] = status_type
                    c.privmsg(self.channel, f"✅ Status updated to: **{status_type.upper()}**")
                elif status_type == "clear":
                    data["status"] = None
                    c.privmsg(self.channel, "🧹 Status cleared.")
                storage.save_json(storage.DATA_FILE, data)

        elif cmd == "!sresetall":
            storage.save_json(storage.DATA_FILE, {})
            storage.save_json(storage.RECORDS_FILE, {})
            c.privmsg(self.channel, "⚠️ **SYSTEM RESET** complete. All data wiped. 🛑")

    def on_ping(self, c, e):
        """Ensure bot responds to PING/PONG to stay alive"""
        self.connection.pong(e.target)
