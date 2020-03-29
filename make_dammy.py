from app import db
from app import BeaconLog

# ダミーデータの生成
beacon_info = {}
beacon_info["user_id"] = "Udeadbeafdeadbeafdeadbeaf"
beacon_info["facility_id"] = 1
beacon_info["facility_name"] = "大阪府庁本館"
beacon_info["beacon_id"] = "eeeeeeeeeeee"
beacon_info["area_id"] = 1
beacon_info["area_name"] = "万博協力室"
beacon_info["timestamp"] = 1585477127
beacon_info["event_type"] = "enter"

starem_data = BeaconLog(beacon_info)
db.session.add(starem_data)
db.session.commit()
