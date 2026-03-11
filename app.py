import os
import gc
import time

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

import torch
torch.set_num_threads(4)

from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
from PIL import Image, ImageEnhance, ImageFilter
import io
from collections import Counter
from pymongo import MongoClient
from chatbot import chatbot_bp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ============================================================
# LOAD MODEL
# ============================================================
print("🔄 Loading YOLO model...")
MODEL_PATH = os.path.join(os.getcwd(), "models", "best.pt")
model = YOLO(MODEL_PATH)

print("🔥 Warming up model...")
dummy = Image.new("RGB", (640, 640), color=(120, 100, 80))
with torch.no_grad():
    for _ in range(3):
        model.predict(dummy, imgsz=640, verbose=False)
print(f"✅ YOLO ready! Classes: {len(model.names)}")
print(f"📋 Sample classes: {list(model.names.values())[:5]}")

# ============================================================
# MONGODB — CACHE ALL BREEDS IN MEMORY
# ============================================================
print("🔄 Connecting to MongoDB Atlas...")
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://pashumitra_user:Cattle2024@cluster0.p4bec5t.mongodb.net/cattle_ai?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
db = client["cattle_ai"]
breeds_col = db["breeds"]

breed_cache = {}
for doc in breeds_col.find({}, {"_id": 0}):
    name = doc.get("name", "")
    if name:
        breed_cache[name] = doc

print(f"✅ MongoDB connected! {len(breed_cache)} breeds cached.")

# ============================================================
# CHATBOT
# ============================================================
app.register_blueprint(chatbot_bp, url_prefix='/api')

# ============================================================
# CORS
# ============================================================
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    return response

# ============================================================
# HEALTH
# ============================================================
@app.route("/")
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "message": "PashuMitra Running!",
        "breeds_loaded": len(breed_cache),
        "model_classes": len(model.names)
    })

# ============================================================
# IMAGE ENHANCEMENT
# ============================================================
def enhance_image(img):
    img = img.resize((640, 640), Image.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    img = ImageEnhance.Brightness(img).enhance(1.05)
    return img

# ============================================================
# PREDICT
# ============================================================
@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    t_start = time.time()

    try:
        files = request.files.getlist("images")
        if not files:
            return jsonify({
                "valid_cattle": False,
                "message": "No images received."
            }), 400

        # Load images
        images = []
        for f in files[:5]:
            try:
                raw = f.read()
                img = Image.open(io.BytesIO(raw)).convert("RGB")
                img = enhance_image(img)
                images.append(img)
                del raw
            except Exception as e:
                print(f"⚠️ Skipped bad image: {e}")
                continue

        if not images:
            return jsonify({
                "valid_cattle": False,
                "message": "Could not read images. Please try again."
            }), 400

        # ---- BATCH INFERENCE ----
        predictions = []
        confidences = []
        prob_accumulator = {}

        with torch.no_grad():
            results = model.predict(
                images,
                imgsz=640,
                verbose=False,
                half=False
            )

        for result in results:
            if result.probs is None:
                continue

            top1_cls  = int(result.probs.top1)
            top1_conf = float(result.probs.top1conf)
            top1_name = model.names[top1_cls]

            predictions.append(top1_name)
            confidences.append(top1_conf)

            # Print every result for debugging
            print(f"  → {top1_name}: {round(top1_conf*100,1)}%")

            # Accumulate top-5 probs
            for idx, conf in zip(result.probs.top5, result.probs.top5conf):
                name = model.names[int(idx)]
                prob_accumulator[name] = prob_accumulator.get(name, 0.0) + float(conf)

        if not predictions:
            return jsonify({
                "valid_cattle": False,
                "message": "Model returned no results. Please try a clearer image."
            })

        # ---- WEIGHTED ENSEMBLE ----
        vote_counts = Counter(predictions)
        scores = {
            name: prob_accumulator.get(name, 0.0) * (vote_counts.get(name, 0) + 1)
            for name in set(predictions)
        }
        best_breed = max(scores, key=scores.get)

        breed_confs = [c for p, c in zip(predictions, confidences) if p == best_breed]
        avg_conf = sum(breed_confs) / len(breed_confs) if breed_confs else 0

        print(f"🏆 Winner: {best_breed} | avg_conf={round(avg_conf*100,1)}% | votes={vote_counts.get(best_breed,0)}/{len(images)}")

        # ---- THRESHOLD: VERY LOW for 53-class model ----
        # With 53 classes, even correct predictions can be 20-40%
        # Only reject if truly garbage (< 8%)
        if avg_conf < 0.08:
            return jsonify({
                "valid_cattle": False,
                "message": f"Image unclear. Best guess was {best_breed} at only {round(avg_conf*100,1)}% confidence. Please upload a clearer, closer photo of the cattle."
            })

        final_confidence = round(avg_conf * 100, 1)

        # Honest trust levels for 53-class model
        if avg_conf >= 0.60:
            trust = "HIGH"
        elif avg_conf >= 0.30:
            trust = "MEDIUM"
        else:
            trust = "LOW"

        # Get breed info from cache (instant)
        breed_info = breed_cache.get(best_breed, {})

        elapsed = round(time.time() - t_start, 2)
        print(f"✅ Done: {best_breed} | {final_confidence}% | {trust} | {len(images)} imgs | {elapsed}s")

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
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================
# BREED ROUTES
# ============================================================
@app.route("/breeds")
def get_all_breeds():
    return jsonify({
        "total": len(breed_cache),
        "breeds": [
            {"name": v.get("name"), "origin": v.get("origin"), "purpose": v.get("purpose")}
            for v in breed_cache.values()
        ]
    })

@app.route("/breed/<breed_name>")
def get_breed_details(breed_name):
    breed = breed_cache.get(breed_name)
    if breed:
        return jsonify(breed)
    for key, val in breed_cache.items():
        if key.lower() == breed_name.lower():
            return jsonify(val)
    return jsonify({"error": f"Breed '{breed_name}' not found"}), 404


# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 PashuMitra starting on port {port}")
    app.run(host="0.0.0.0", port=port)