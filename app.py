import os, gc, time, io, traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

import torch
torch.set_num_threads(4)

from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
from PIL import Image, ImageEnhance
from pymongo import MongoClient
from chatbot import chatbot_bp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ============================================================
# LOAD MODEL — always use .pt (stable, no ONNX crash risk)
# ============================================================
print("🔄 Loading YOLO model...")
MODEL_PATH = os.path.join(os.getcwd(), "models", "best.pt")
model = YOLO(MODEL_PATH)

print("🔥 Warming up model (3x)...")
dummy = Image.new("RGB", (640, 640), color=(110, 90, 70))
with torch.no_grad():
    for _ in range(3):
        model.predict(dummy, imgsz=640, verbose=False)

print(f"✅ Model ready! {len(model.names)} classes loaded.")
print(f"📋 Classes: {list(model.names.values())}")

# ============================================================
# MONGODB — FULL CACHE IN RAM AT STARTUP
# ============================================================
print("🔄 Connecting to MongoDB Atlas...")
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://pashumitra_user:Cattle2024@cluster0.p4bec5t.mongodb.net/cattle_ai?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client["cattle_ai"]

breed_cache = {}
for doc in db["breeds"].find({}, {"_id": 0}):
    name = doc.get("name", "")
    if name:
        breed_cache[name] = doc

print(f"✅ {len(breed_cache)} breeds cached from MongoDB.")
print(f"📋 Cached breeds: {list(breed_cache.keys())[:10]}...")

executor = ThreadPoolExecutor(max_workers=5)
app.register_blueprint(chatbot_bp, url_prefix='/api')

# ============================================================
# CORS
# ============================================================
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
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
        "breeds_loaded": len(breed_cache),
        "model_classes": len(model.names)
    })

# ============================================================
# IMAGE LOADER
# ============================================================
def load_image(file_bytes):
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        if img.size != (640, 640):
            img = img.resize((640, 640), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = ImageEnhance.Sharpness(img).enhance(1.12)
        return img
    except Exception as e:
        print(f"⚠️ Bad image: {e}")
        return None

# ============================================================
# PREDICT — NEVER REJECTS, ALWAYS RETURNS BEST BREED
# ============================================================
@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    t0 = time.time()

    try:
        files = request.files.getlist("images")
        if not files:
            return jsonify({"valid_cattle": False, "message": "No images received."}), 400

        # Read all file bytes first (must happen in request context)
        all_bytes = []
        for f in files[:5]:
            try:
                all_bytes.append(f.read())
            except Exception as e:
                print(f"⚠️ Read error: {e}")

        # Load images in parallel
        futures = [executor.submit(load_image, b) for b in all_bytes]
        images  = [f.result() for f in futures if f.result() is not None]

        if not images:
            return jsonify({
                "valid_cattle": False,
                "message": "Could not read the uploaded images. Please try again."
            })

        t_load = round(time.time() - t0, 3)
        print(f"📸 {len(images)} images loaded in {t_load}s")

        # ---- BATCH INFERENCE ----
        with torch.no_grad():
            results = model.predict(images, imgsz=640, verbose=False, half=False)

        t_infer = round(time.time() - t0, 3)

        predictions, confidences, prob_acc = [], [], {}

        for i, result in enumerate(results):
            if result.probs is None:
                print(f"⚠️ Image {i}: no probs returned")
                continue

            cls  = int(result.probs.top1)
            conf = float(result.probs.top1conf)
            name = model.names[cls]

            predictions.append(name)
            confidences.append(conf)
            print(f"  Image {i+1}: {name} = {round(conf*100,1)}%")

            # Accumulate top-5 for ensemble
            for idx, c in zip(result.probs.top5, result.probs.top5conf):
                n = model.names[int(idx)]
                prob_acc[n] = prob_acc.get(n, 0.0) + float(c)

        if not predictions:
            return jsonify({
                "valid_cattle": False,
                "message": "Model could not process images. Please try different images."
            })

        # ---- WEIGHTED ENSEMBLE ----
        votes = Counter(predictions)
        # Score = accumulated_prob × (vote_count + 1)
        scores = {
            n: prob_acc.get(n, 0.0) * (votes.get(n, 0) + 1)
            for n in set(predictions)
        }
        best = max(scores, key=scores.get)

        breed_confs = [c for p, c in zip(predictions, confidences) if p == best]
        avg_conf    = sum(breed_confs) / len(breed_confs) if breed_confs else 0

        final_conf = round(avg_conf * 100, 1)

        # Trust level — calibrated for 53-class model
        # Even 15-20% can be correct with 53 classes (random = 1.9%)
        if avg_conf >= 0.55:
            trust = "HIGH"
        elif avg_conf >= 0.25:
            trust = "MEDIUM"
        elif avg_conf >= 0.05:
            trust = "LOW"
        else:
            trust = "VERY LOW"

        # Get breed info from RAM (instant)
        breed_info = breed_cache.get(best, {})

        # Check if we even have this breed in MongoDB
        if not breed_info:
            print(f"⚠️ '{best}' not found in MongoDB cache. Available: {list(breed_cache.keys())[:5]}")

        elapsed = round(time.time() - t0, 2)
        print(f"✅ RESULT: {best} | {final_conf}% | {trust} | {len(images)} imgs | load={t_load}s | total={elapsed}s")

        # ALWAYS return a result — never show "Invalid Image"
        return jsonify({
            "valid_cattle": True,
            "breed": best,
            "confidence": final_conf,
            "trust": trust,
            "images_used": len(images),
            "inference_time": elapsed,
            "breed_info": breed_info
        })

    except Exception as e:
        gc.collect()
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
    b = breed_cache.get(breed_name)
    if b: return jsonify(b)
    for k, v in breed_cache.items():
        if k.lower() == breed_name.lower(): return jsonify(v)
    return jsonify({"error": f"'{breed_name}' not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 PashuMitra on port {port}")
    app.run(host="0.0.0.0", port=port)