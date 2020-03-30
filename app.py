# coding: utf-8
from flask import Flask, request, abort, jsonify
from flask_cors import CORS
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

# LINE APIの設定
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# アプリケーションの設定
app = Flask(__name__, static_folder='static')
CORS(app)

# データベースの設定
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL')
db = SQLAlchemy(app)


class BeaconLog(db.Model):
    __tablename__ = 'BeaconEventLog'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.Integer, nullable=False, default=int(time()))
    facility_id = db.Column(db.Integer, nullable=False)
    area_id = db.Column(db.Integer, nullable=False)
    facility_name = db.Column(db.String(100), nullable=False)
    area_name = db.Column(db.String(100), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=int(time()))

    def __init__(self, data):
        self.user_id = data["user_id"]
        self.facility_id = data["facility_id"]
        self.facility_name = data["facility_name"]
        self.area_id = data["area_id"]
        self.area_name = data["area_name"]
        self.event_type = data["event_type"]

    def __repr__(self):
        return '<BeaconLog %r>' % self.user_id


class FacilityStream(db.Model):
    __tablename__ = "FacilityStream"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, nullable=False)
    area_id = db.Column(db.String(50), nullable=False)
    facility_name = db.Column(db.String(50), nullable=False)
    area_name = db.Column(db.String(50), nullable=False)
    number_of_person = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=int(time()))
    updated_at = db.Column(db.Integer, nullable=False, default=int(time()))

    def __init__(self, data):
        self.facility_id = data["facility_id"]
        self.area_id = data["beacon_id"]
        self.area_name = data["area_name"]
        self.facility_name = data["facility_name"]
        self.number_of_person = 1

    def __repr__(self):
        return '<FacilityArea %r>' % self.area_id


@app.route('/')
def connect():
    return "Hello from Flask"


# 施設の混み具合を取得するAPI
@app.route("/api/facility")
def get_facility():
    facility_id = request.args.get('facility_id')
    Query = FacilityStream.facility_id == facility_id
    facility_info = db.session.query(FacilityStream).filter(Query).all()
    response = {
        "values": []
    }
    for data_line in facility_info:
        response["values"].append({
            "facility_id": data_line.facility_id,
            "area_id": data_line.area_id,
            "facility_name": data_line.facility_name,
            "area_name": data_line.area_name,
            "number_of_person": data_line.number_of_person
        })
    app.logger.info(response)
    return jsonify(response)


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
    message = "{}{}".format(
        '友だち追加ありがとうございます！このbotで施設の混み具合をチェックして感染対策していきましょう！',
        '\n※このアカウントはハッカソン用のプロトタイプなので、実際の挙動とは異なります')
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
    beacon_info["beacon_id"] = event.beacon.hwid
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
    # ログデータベースに記録
    beaconLog = BeaconLog(beacon_info)
    db.session.add(beaconLog)
    db.session.commit()

    # Queryでビーコンの人数をカウント(leaveイベントのときはカウントを引く)
    Query = FacilityStream.area_id == beacon_info["beacon_id"]
    user_info = db.session.query(FacilityStream).filter(Query).all()
    if len(user_info):
        area_info = user_info[0]
        app.logger.info("Got area beacon: " + area_info.area_id)
        if event.beacon.type == "enter":
            area_info.number_of_person += 1
        elif event.beacon.type == "leave":
            area_info.number_of_person -= 1
        area_info.updated_at = int(time())
        db.session.commit()
    else:
        # エリア情報がないときは追加
        starem_data = FacilityStream(beacon_info)
        db.session.add(starem_data)
        db.session.commit()
    # デバッグ用にメッセージを送信（ビーコンのイベントタイプを送信する）
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.beacon.type))


if __name__ == "__main__":
    app.debug = True
    app.run()
