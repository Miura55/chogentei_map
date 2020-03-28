# coding: utf-8
from flask import Flask, request, abort, render_template
from flask_sqlalchemy import SQLAlchemy
from time import time
import os
import json

from linebot import (
    LineBotApi, WebhookHandler
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

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__, static_folder='static')
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DB_URL')
db = SQLAlchemy(app)


class BeaconLog(db.Model):
    __tablename__ = 'FacilityBeaconEventLog'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.Integer, nullable=False, default=int(time()))
    facility_id = db.Column(db.Integer, nullable=False)
    area_id = db.Column(db.Integer, nullable=False)
    facility_name = db.Column(db.String(50), nullable=False)
    area_name = db.Column(db.String(50), nullable=False)
    event_type = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=int(time()))

    def __init__(self, data):
        self.user_id = data["user_id"]
        self.timestamp = data["timestamp"]
        self.facility_id = data["facility_id"]
        self.facility_name = data["facility_name"]
        self.area_id = data["area_id"]
        self.area_name = data["area_name"]
        self.event_type = data["event_type"]


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
    beacon_info = {}
    # イベントからデータを抽出
    beacon_info["user_id"] = event.source.user_id
    beacon_info["event_type"] = event.beacon.type
    beacon_info["timestamp"] = event.timestamp
    beacon_info["area_id"] = event.beacon.hwid
    # 施設情報の一覧のjson
    with open("deviceid2facilityid.json", "r", encoding="utf-8")as f:
        data = json.load(f)
        facility_id = data[event.beacon.hwid]["FacilityId"]
        area_id = data[event.beacon.hwid]["AreaId"]
        beacon_info["facility_id"] = facility_id
        beacon_info["facility_name"] = data["facility"][facility_id]
        beacon_info["area_id"] = area_id
        beacon_info["area_name"] = data["area"][facility_id][area_id]
    app.logger.info(beacon_info)
    # ログデータベース
    beaconLog = BeaconLog(beacon_info)
    db.session.add(beaconLog)
    db.session.commit()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.beacon.type))


if __name__ == "__main__":
    app.debug = True
    app.run()
