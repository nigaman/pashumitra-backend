import os, gc, time, io, traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["TORCH_NUM_THREADS"] = "4"

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
# LOAD MODEL — try ONNX first (3x faster CPU), fallback to .pt
# ============================================================
print("🔄 Loading model...")
MODEL_DIR = os.path.join(os.getcwd(), "models")
ONNX_PATH = os.path.join(MODEL_DIR, "best.onnx")
PT_PATH   = os.path.join(MODEL_DIR, "best.pt")

if os.path.exists(ONNX_PATH):
    print("⚡ Using ONNX model (faster CPU inference)")
    model = YOLO(ONNX_PATH, task="classify")
else:
    print("📦 Using PyTorch model (.pt)")
    model = YOLO(PT_PATH)
    # Export to ONNX for next startup
    try:
        print("🔄 Exporting to ONNX for future speed...")
        model.export(format="onnx", imgsz=640, simplify=True, opset=12)
        import shutil
        exported = PT_PATH.replace(".pt", ".onnx")
        if os.path.exists(exported):
            shutil.move(exported, ONNX_PATH)
            print("✅ ONNX exported! Next restart will be faster.")
    except Exception as e:
        print(f"⚠️ ONNX export failed (will use .pt): {e}")

# Warmup — run 3 dummy inferences to heat up CPU cache
print("🔥 Warming up...")
dummy = Image.new("RGB", (640, 640), color=(110, 90, 70))
with torch.no_grad():
    for _ in range(3):
        model.predict(dummy, imgsz=640, verbose=False)
print(f"✅ Model ready! {len(model.names)} classes")

# ============================================================
# MONGODB — FULL CACHE IN RAM
# ============================================================
print("🔄 Connecting to MongoDB Atlas...")
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://pashumitra_user:Cattle2024@cluster0.p4bec5t.mongodb.net/cattle_ai?retryWrites=true&w=majority&appName=Cluster0"
)
client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=8000,
    connectTimeoutMS=8000,
    socketTimeoutMS=8000
)
db = client["cattle_ai"]
breed_cache = {}
for doc in db["breeds"].find({}, {"_id": 0}):
    name = doc.get("name", "")
    if name:
        breed_cache[name] = doc

print(f"✅ {len(breed_cache)} breeds cached from MongoDB")

# Thread pool for parallel image loading
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
# IMAGE LOAD (runs in thread pool)
# ============================================================
def load_image(file_storage):
    try:
        raw = file_storage.read()
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        # Already compressed to 640x640 by frontend — just enhance
        if img.size != (640, 640):
            img = img.resize((640, 640), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = ImageEnhance.Sharpness(img).enhance(1.12)
        return img
    except Exception as e:
        print(f"⚠️ Bad image: {e}")
        return None

# ============================================================
# PREDICT
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

        # Load all images in parallel
        futures = [executor.submit(load_image, f) for f in files[:5]]
        images  = [fut.result() for fut in futures if fut.result() is not None]

        t_load = round(time.time() - t0, 3)

        if not images:
            return jsonify({"valid_cattle": False, "message": "Could not read images. Please try again."})

        # ---- BATCH INFERENCE ----
        with torch.no_grad():
            results = model.predict(images, imgsz=640, verbose=False, half=False)

        t_infer = round(time.time() - t0, 3)

        predictions, confidences, prob_acc = [], [], {}

        for result in results:
            if result.probs is None:
                continue
            cls  = int(result.probs.top1)
            conf = float(result.probs.top1conf)
            name = model.names[cls]
            predictions.append(name)
            confidences.append(conf)
            print(f"  → {name}: {round(conf*100,1)}%")

            for idx, c in zip(result.probs.top5, result.probs.top5conf):
                n = model.names[int(idx)]
                prob_acc[n] = prob_acc.get(n, 0.0) + float(c)

        if not predictions:
            return jsonify({"valid_cattle": False, "message": "Model returned no results. Try a clearer image."})

        # Weighted ensemble: probability sum × vote count
        votes = Counter(predictions)
        scores = {n: prob_acc.get(n, 0.0) * (votes.get(n, 0) + 1) for n in set(predictions)}
        best = max(scores, key=scores.get)

        breed_confs = [c for p, c in zip(predictions, confidences) if p == best]
        avg_conf = sum(breed_confs) / len(breed_confs) if breed_confs else 0

        print(f"🏆 {best} | conf={round(avg_conf*100,1)}% | votes={votes.get(best)}/{len(images)} | load={t_load}s | infer={t_infer}s")

        # Only reject complete garbage (< 8% for 53-class model)
        if avg_conf < 0.08:
            return jsonify({
                "valid_cattle": False,
                "message": f"Could not identify breed (confidence too low: {round(avg_conf*100,1)}%). Please upload a clearer, closer photo."
            })

        final_conf = round(avg_conf * 100, 1)
        trust = "HIGH" if avg_conf >= 0.60 else "MEDIUM" if avg_conf >= 0.30 else "LOW"

        # Breed info from RAM cache — instant
        breed_info = breed_cache.get(best, {})

        elapsed = round(time.time() - t0, 2)

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
        "breeds": [{"name": v.get("name"), "origin": v.get("origin"), "purpose": v.get("purpose")} for v in breed_cache.values()]
    })

@app.route("/breed/<breed_name>")
def get_breed_details(breed_name):
    b = breed_cache.get(breed_name)
    if b: return jsonify(b)
    for k, v in breed_cache.items():
        if k.lower() == breed_name.lower(): return jsonify(v)
    return jsonify({"error": f"Breed '{breed_name}' not found"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port)