from app import db
from app import FacilityStream

# ダミーデータの生成
beacon_info = {}
beacon_info["facility_id"] = 1
beacon_info["facility_name"] = "大阪府庁本館"
beacon_info["beacon_id"] = "eeeeeeeeeeee"
beacon_info["area_name"] = "万博協力室"

starem_data = FacilityStream(beacon_info)
db.session.add(starem_data)
db.session.commit()
