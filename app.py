# coding: utf-8
from flask import Flask, request, abort, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import datetime as dt
import os
import json
import base64
import urllib.parse

from linebot import (
    LineBotApi, WebhookParser, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    FollowEvent, 
    MessageEvent, 
    TextMessage, 
    TextSendMessage,
    StickerSendMessage,
    BeaconEvent
)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except:
    pass

CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
app = Flask(__name__, static_folder='static')

@app.route('/')
def connect():
    return render_template("Hello from Flask")

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    
    # Connect Check
    data = json.loads(body)
    userId = data["events"][0]["source"]["userId"]
    if userId == "Udeadbeefdeadbeefdeadbeefdeadbeef":
        return "OK"

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))

@handler.add(FollowEvent)
def handle_follow(event):
    message = '友だち追加ありがとうございます！このbotで施設の混み具合をチェックして感染対策していきましょう'
    line_bot_api.reply_message(
        event.reply_token,
        [
            TextSendMessage(text=message),
            StickerSendMessage(
                package_id=11537,
                sticker_id=52002739
            )
        ]
    )

@handler.add(BeaconEvent)
def handle_beacon(event):
    # イベントからデータを抽出
    print("userId:", event.source.user_id)
    print("type:", event.beacon.type)
    print("timestamp:", event.timestamp)
    print("area_id:", event.beacon.hwid)
    
    
    with open("deviceid2facilityid.json", "r", encoding="utf-8")as f:
        data = json.load(f)
        print("facility_name:", data[event.beacon.hwid]["Facility"])
        print("area_name:", data[event.beacon.hwid]["AreaName"])
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='Hello World'))

if __name__ == "__main__":
    app.debug = True
    app.run()

