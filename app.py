import os
import gc

# Minimize memory before importing torch
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

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
CORS(app, resources={r"/*": {"origins": "*"}})

# ---- LOAD MODEL ONCE (half precision = 2x less memory) ----
print("🔄 Loading YOLO model...")
MODEL_PATH = os.path.join(os.getcwd(), "models", "best.pt")
model = YOLO(MODEL_PATH)
model.model.half()  # FP16 = half the memory usage
print("✅ YOLO model loaded!")

# ---- MONGODB ----
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

# ---- CORS HEADERS ON EVERY RESPONSE ----
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    return response

# ---- HEALTH ----
@app.route("/")
@app.route("/health")
def health():
    return jsonify({"status": "ok", "message": "PashuMitra Running!"})

# ---- PREDICT ----
@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    try:
        files = request.files.getlist("images")
        if not files:
            return jsonify({"valid_cattle": False, "message": "No images received."}), 400

        images = []
        for f in files[:3]:  # Max 3 images to save memory
            try:
                img = Image.open(io.BytesIO(f.read())).convert("RGB")
                # Resize to reduce memory during inference
                img = img.resize((320, 320))
                images.append(img)
            except Exception as e:
                print(f"Image error: {e}")
                continue

        if not images:
            return jsonify({"valid_cattle": False, "message": "Could not read images."}), 400

        predictions = []
        confidences = []

        # Run ONE image at a time to save memory
        with torch.no_grad():
            for img in images:
                try:
                    result = model(img, imgsz=320, verbose=False)[0]
                    if result.probs is not None:
                        cls = int(result.probs.top1)
                        conf = float(result.probs.top1conf)
                        predictions.append(model.names[cls])
                        confidences.append(conf)
                except Exception as e:
                    print(f"Inference error: {e}")
                    continue
                finally:
                    gc.collect()  # Free memory after each image

        if not predictions:
            return jsonify({"valid_cattle": False, "message": "No cattle detected."})

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
        breed_info = breeds_col.find_one({"name": final_breed}, {"_id": 0})

        # Force garbage collection after prediction
        gc.collect()

        return jsonify({
            "valid_cattle": True,
            "breed": final_breed,
            "confidence": final_confidence,
            "trust": trust,
            "images_used": len(images),
            "breed_info": breed_info
        })

    except Exception as e:
        gc.collect()
        print(f"Predict error: {e}")
        return jsonify({"error": str(e)}), 500

# ---- BREEDS ----
@app.route("/breeds")
def get_all_breeds():
    breeds = list(breeds_col.find({}, {"_id": 0, "name": 1, "origin": 1, "purpose": 1}))
    return jsonify({"total": len(breeds), "breeds": breeds})

@app.route("/breed/<breed_name>")
def get_breed_details(breed_name):
    breed = breeds_col.find_one({"name": breed_name}, {"_id": 0})
    if breed:
        return jsonify(breed)
    return jsonify({"error": "Breed not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting on port {port}")
    app.run(host="0.0.0.0", port=port)