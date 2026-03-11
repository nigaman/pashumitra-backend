import os
import gc
import time

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"

import torch
torch.set_num_threads(4)

from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
from PIL import Image, ImageEnhance
import io
from collections import Counter
from pymongo import MongoClient
from chatbot import chatbot_bp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ---- LOAD MODEL ONCE ----
print("🔄 Loading YOLO model...")
MODEL_PATH = os.path.join(os.getcwd(), "models", "best.pt")
model = YOLO(MODEL_PATH)

# Warmup with 3 dummy images so first real request is instant
print("🔥 Warming up model...")
dummy = Image.new("RGB", (640, 640), color=(128, 128, 128))
with torch.no_grad():
    for _ in range(3):
        model.predict(dummy, imgsz=640, verbose=False)
print("✅ YOLO model loaded and warmed up!")

# ---- MONGODB ----
print("🔄 Connecting to MongoDB...")
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://pashumitra_user:Cattle2024@cluster0.p4bec5t.mongodb.net/cattle_ai?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["cattle_ai"]
breeds_col = db["breeds"]

# Cache all breeds in memory for instant retrieval
print("📦 Caching breed data from MongoDB...")
breed_cache = {}
for breed in breeds_col.find({}, {"_id": 0}):
    breed_cache[breed.get("name", "")] = breed
print(f"✅ MongoDB connected! {len(breed_cache)} breeds cached in memory.")

# ---- CHATBOT ----
app.register_blueprint(chatbot_bp, url_prefix='/api')

# ---- CORS ----
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
    return jsonify({"status": "ok", "message": "PashuMitra Running!", "breeds_cached": len(breed_cache)})

# ---- IMAGE PREPROCESSING ----
def preprocess_image(img):
    """Enhance image quality before inference"""
    # Auto-enhance contrast slightly
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)
    # Resize to YOLO native size
    img = img.resize((640, 640), Image.LANCZOS)
    return img

# ---- PREDICT ----
@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    start_time = time.time()

    try:
        files = request.files.getlist("images")
        if not files:
            return jsonify({"valid_cattle": False, "message": "No images received."}), 400

        # Load and preprocess all images
        images = []
        for f in files[:5]:
            try:
                img_bytes = f.read()
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img = preprocess_image(img)
                images.append(img)
                del img_bytes
            except Exception as e:
                print(f"Image error: {e}")
                continue

        if not images:
            return jsonify({"valid_cattle": False, "message": "Could not read images."}), 400

        # Run batch inference (all images at once = fastest)
        with torch.no_grad():
            results = model.predict(
                images,
                imgsz=640,
                verbose=False,
                half=False  # FP32 for CPU accuracy
            )

        predictions = []
        confidences = []
        all_probs = {}  # Accumulate probabilities across all images

        for result in results:
            if result.probs is None:
                continue
            cls = int(result.probs.top1)
            conf = float(result.probs.top1conf)
            breed_name = model.names[cls]
            predictions.append(breed_name)
            confidences.append(conf)

            # Accumulate top-5 probs for better ensemble
            top5_idx = result.probs.top5
            top5_conf = result.probs.top5conf
            for idx, c in zip(top5_idx, top5_conf):
                name = model.names[int(idx)]
                all_probs[name] = all_probs.get(name, 0) + float(c)

        if not predictions:
            return jsonify({"valid_cattle": False, "message": "No cattle detected in the images."})

        # Weighted ensemble: combine majority vote + accumulated probabilities
        vote_counts = Counter(predictions)
        best_breed = max(all_probs, key=lambda k: all_probs[k] * (vote_counts.get(k, 0) + 1))

        avg_conf = sum(c for p, c in zip(predictions, confidences) if p == best_breed) / \
                   max(vote_counts.get(best_breed, 1), 1)

        # Reject very low confidence
        if avg_conf < 0.30:
            return jsonify({
                "valid_cattle": False,
                "message": "Could not identify the breed. Please upload a clearer, closer image of the cattle."
            })

        final_confidence = round(avg_conf * 100, 1)
        trust = "HIGH" if avg_conf >= 0.75 else "MEDIUM" if avg_conf >= 0.50 else "LOW"

        # Get breed info from cache (instant - no DB call needed)
        breed_info = breed_cache.get(best_breed)

        elapsed = round(time.time() - start_time, 2)
        print(f"✅ Predicted: {best_breed} ({final_confidence}%) in {elapsed}s using {len(images)} images")

        return jsonify({
            "valid_cattle": True,
            "breed": best_breed,
            "confidence": final_confidence,
            "trust": trust,
            "images_used": len(images),
            "inference_time": elapsed,
            "breed_info": breed_info
        })

    except Exception as e:
        gc.collect()
        print(f"❌ Predict error: {e}")
        return jsonify({"error": str(e)}), 500

# ---- BREEDS ----
@app.route("/breeds")
def get_all_breeds():
    breeds = [{"name": v.get("name"), "origin": v.get("origin"), "purpose": v.get("purpose")}
              for v in breed_cache.values()]
    return jsonify({"total": len(breeds), "breeds": breeds})

@app.route("/breed/<breed_name>")
def get_breed_details(breed_name):
    breed = breed_cache.get(breed_name)
    if breed:
        return jsonify(breed)
    return jsonify({"error": "Breed not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 Starting on port {port}")
    app.run(host="0.0.0.0", port=port)