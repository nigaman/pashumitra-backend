import os
os.environ["OMP_NUM_THREADS"] = "1"

import torch
torch.set_num_threads(1)

from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
from PIL import Image
import io
from collections import Counter
from pymongo import MongoClient
from chatbot import chatbot_bp

app = Flask(__name__)

# ---- CORS FIXED ----
CORS(app, resources={r"/*": {"origins": "*"}}, 
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

# ---- LOAD MODEL AT STARTUP ----
print("🔄 Loading YOLO model...")
MODEL_PATH = os.path.join(os.getcwd(), "models", "best.pt")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
model = YOLO(MODEL_PATH)
print("✅ YOLO model loaded!")

# ---- MONGODB ATLAS ----
print("🔄 Connecting to MongoDB...")
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://pashumitra_user:Cattle2024@cluster0.p4bec5t.mongodb.net/cattle_ai?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["cattle_ai"]
breeds_col = db["breeds"]
print("✅ MongoDB connected!")

# ---- CHATBOT ----
app.register_blueprint(chatbot_bp, url_prefix='/api')

# ---- AFTER REQUEST: ADD CORS HEADERS TO EVERY RESPONSE ----
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    return response

# ---- HOME / HEALTH ----
@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "message": "PashuMitra Backend Running!",
        "endpoints": {
            "predict": "/predict",
            "breeds": "/breeds",
            "breed_detail": "/breed/<name>",
            "chat": "/api/chat",
            "suggestions": "/api/chat/suggestions"
        }
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

# ---- PREDICT ----
@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        files = request.files.getlist("images")

        if not files or len(files) == 0:
            return jsonify({
                "valid_cattle": False,
                "message": "No images received."
            }), 400

        images = []
        for f in files[:5]:
            try:
                img_bytes = f.read()
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                images.append(img)
            except Exception as img_err:
                print(f"⚠️ Skipping bad image: {img_err}")
                continue

        if not images:
            return jsonify({
                "valid_cattle": False,
                "message": "Could not process images. Please upload valid cattle photos."
            }), 400

        # Run YOLO prediction
        results = model(images)

        predictions = []
        confidences = []

        for r in results:
            if r.probs is None:
                continue
            cls = int(r.probs.top1)
            conf = float(r.probs.top1conf)
            predictions.append(model.names[cls])
            confidences.append(conf)

        if not predictions:
            return jsonify({
                "valid_cattle": False,
                "message": "Invalid image. No cattle detected."
            })

        final_breed, count = Counter(predictions).most_common(1)[0]
        agreement = count / len(predictions)
        avg_conf = sum(confidences) / len(confidences)

        if avg_conf < 0.55 or agreement < 0.5:
            return jsonify({
                "valid_cattle": False,
                "message": "Invalid image. This does not appear to be genuine cattle."
            })

        final_confidence = round(avg_conf * agreement * 100, 2)
        trust = "HIGH" if agreement >= 0.8 else "MEDIUM" if agreement >= 0.5 else "LOW"

        # Fetch breed info from MongoDB
        breed_info = breeds_col.find_one({"name": final_breed}, {"_id": 0})

        return jsonify({
            "valid_cattle": True,
            "breed": final_breed,
            "confidence": final_confidence,
            "trust": trust,
            "images_used": len(images),
            "breed_info": breed_info
        })

    except Exception as e:
        print(f"❌ Predict error: {e}")
        return jsonify({"error": str(e)}), 500


# ---- BREEDS ----
@app.route("/breeds", methods=["GET"])
def get_all_breeds():
    try:
        breeds = list(breeds_col.find({}, {"_id": 0, "name": 1, "origin": 1, "purpose": 1}))
        return jsonify({"total": len(breeds), "breeds": breeds})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/breed/<breed_name>", methods=["GET"])
def get_breed_details(breed_name):
    try:
        breed = breeds_col.find_one({"name": breed_name}, {"_id": 0})
        if breed:
            return jsonify(breed)
        return jsonify({"error": f"Breed '{breed_name}' not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---- START ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 PashuMitra starting on port {port}...")
    app.run(host="0.0.0.0", port=port)