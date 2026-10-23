
import base64
import importlib
import os
from unittest.mock import patch
from app import create_app

routes = importlib.import_module("app")
app = create_app()
client = app.test_client()

with open("face_data/VOTER004.jpg", "rb") as f:
    image = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

with client.session_transaction() as s:
    s["user_id"] = 5
    s["voter_id"] = 5
    s["voter_name"] = "Duplicate Test Voter"

with patch.object(routes, "find_duplicate_face", return_value="VOTER001"):
    response = client.post("/face-registration", data={"image": image})

print("HTTP status:", response.status_code)
print("Response:", response.get_json())
print("Permanent image exists:", os.path.exists("face_data/TESTVOTER005.jpg"))
print("Temporary images:", [f for f in os.listdir("face_data") if f.lower().startswith("temp_")])
