import os
import shutil
import firebase_admin
from firebase_admin import credentials, storage
from glob import glob
from ultralytics import YOLO
from ultralytics.utils.plotting import Colors
import json


down_fol = 'origineImages'
up_fol = 'detectedImages'

for fol_ in [down_fol, up_fol]:
    if os.path.exists(f'./{fol_}'):
        shutil.rmtree(f'./{fol_}')
    os.mkdir(f'./{fol_}')

if not firebase_admin._apps:
    # cred = credentials.Certificate(glob('./seacrets/*-firebase-adminsdk-*.json')[0])
    firebase_admin.initialize_app(#cred, 
        options={"storageBucket": "myproducts-488109.firebasestorage.app"}
    )
bucket = storage.bucket()

model = YOLO('yolov8n.pt')


file_name = 'ATfCyM3WVHe8UhaFwkyN.jpg'

blob = bucket.blob(f'{down_fol}/{file_name}')
blob.download_to_filename(f'./{down_fol}/{file_name}')

results = model(f'./{down_fol}/{file_name}',save=True)
results[0].save(f'./{up_fol}/{file_name}')

labelColors = {}
colors = Colors()  # 公式パレット
for box in results[0].boxes:
    class_id = int(box.cls.item())
    cla_name = model.names[class_id]
    color = colors(class_id)  # ← これが描画に使われる色
    print("class:", class_id,',', cla_name, "RGB:", color)
    r,g,b = color
    labelColor = "#{:02x}{:02x}{:02x}".format(r,g,b)
    print(labelColor)
    labelColors[cla_name] = labelColor
    # labels.append(cla_name)
    # labelColors.append(labelColor)
print(labelColors)

with open("ATfCyM3WVHe8UhaFwkyN.json", "w", encoding="utf-8") as f:
    json.dump(labelColors, f, ensure_ascii=False, indent=4)


out_blob = bucket.blob(f'{up_fol}/{file_name}')
out_blob.upload_from_filename(f'./{up_fol}/{file_name}')

file_ = file_name.split('.')[0]
outJson_blob = bucket.blob(f'{up_fol}/{file_}.json')
outJson_blob.upload_from_filename(f'./{file_}.json')

# ゴミデータの削除
for fol_ in [down_fol, up_fol]:
    if os.path.exists(f'./{fol_}'):
        shutil.rmtree(f'./{fol_}')
    os.mkdir(f'./{fol_}')

if os.path.exists(f'./{file_}.json'):
    os.remove(f'./{file_}.json')