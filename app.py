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
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
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

print("🔥 Warming up model (3x)...")
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
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client["cattle_ai"]

breed_cache = {}
for doc in db["breeds"].find({}, {"_id": 0}):
    name = doc.get("name", "")
    if name:
        breed_cache[name] = doc

print(f"✅ {len(breed_cache)} breeds cached from MongoDB.")

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
# TTA — TEST TIME AUGMENTATION
# Each input image is turned into 6 variants.
# All variants are run through the model in one batch.
# Probabilities are averaged → much more stable prediction.
#
# Why TTA works:
#   The model sees the same cow from slightly different
#   "perspectives" (flipped, brighter, higher contrast, etc).
#   If the breed prediction is consistent across all variants
#   it means the model is genuinely confident — not just lucky.
#   This gives 3–6% accuracy boost with ZERO retraining.
# ============================================================
def apply_tta(img):
    """
    Generate 6 augmented versions of a single PIL image.
    All variants are 640x640 RGB — ready for YOLO directly.
    """
    variants = []

    # 1. Original (baseline)
    variants.append(img)

    # 2. Horizontal flip — catches left/right asymmetry bias
    variants.append(img.transpose(Image.FLIP_LEFT_RIGHT))

    # 3. Slightly brighter — helps dark/underexposed field photos
    variants.append(ImageEnhance.Brightness(img).enhance(1.18))

    # 4. Slightly darker — helps overexposed/blown-out photos
    variants.append(ImageEnhance.Brightness(img).enhance(0.84))

    # 5. Higher contrast — sharpens coat texture, hump definition
    variants.append(ImageEnhance.Contrast(img).enhance(1.22))

    # 6. Sharpened — helps blurry phone camera images
    variants.append(ImageEnhance.Sharpness(img).enhance(1.8))

    return variants  # returns list of 6 PIL images

# ============================================================
# IMAGE LOADER (runs in thread pool)
# ============================================================
def load_image(file_bytes):
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        if img.size != (640, 640):
            img = img.resize((640, 640), Image.LANCZOS)
        return img
    except Exception as e:
        print(f"⚠️ Bad image: {e}")
        return None

# ============================================================
# PREDICT — WITH TTA
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

        # Read all bytes inside request context (must happen here)
        all_bytes = []
        for f in files[:5]:
            try:
                all_bytes.append(f.read())
            except Exception as e:
                print(f"⚠️ Read error: {e}")

        # Load images in parallel
        futures = [executor.submit(load_image, b) for b in all_bytes]
        base_images = [f.result() for f in futures if f.result() is not None]

        if not base_images:
            return jsonify({
                "valid_cattle": False,
                "message": "Could not read images. Please try again."
            })

        t_load = round(time.time() - t0, 3)
        print(f"📸 {len(base_images)} base images loaded in {t_load}s")

        # ── APPLY TTA ──
        # Each input image → 6 variants
        # 1 image  → 6  variants in batch
        # 5 images → 30 variants in batch
        # All sent to YOLO in ONE single batch call = fast
        tta_batch = []
        image_variant_map = []  # tracks which base image each variant came from

        for img_idx, img in enumerate(base_images):
            variants = apply_tta(img)
            for v in variants:
                tta_batch.append(v)
                image_variant_map.append(img_idx)

        print(f"🔀 TTA batch size: {len(tta_batch)} variants from {len(base_images)} images")

        # ── SINGLE BATCH INFERENCE over all TTA variants ──
        with torch.no_grad():
            results = model.predict(tta_batch, imgsz=640, verbose=False, half=False)

        t_infer = round(time.time() - t0, 3)
        print(f"⚡ Inference done in {t_infer}s")

        # ── AGGREGATE RESULTS ──
        # Accumulate probability scores across ALL variants
        # This is the core of TTA — average out noise
        prob_accumulator = {}   # breed_name → total accumulated prob
        vote_list = []          # top-1 per variant (for majority vote)

        for variant_idx, result in enumerate(results):
            if result.probs is None:
                continue

            top1_cls  = int(result.probs.top1)
            top1_conf = float(result.probs.top1conf)
            top1_name = model.names[top1_cls]
            vote_list.append(top1_name)

            # Add top-5 probabilities to accumulator (weighted by variant position)
            # Variant 0 (original) gets 1.5x weight — it's the most reliable
            img_idx     = image_variant_map[variant_idx]
            variant_pos = variant_idx % len(apply_tta(base_images[0]))  # 0–5
            weight      = 1.5 if variant_pos == 0 else 1.0

            for cls_idx, conf in zip(result.probs.top5, result.probs.top5conf):
                name = model.names[int(cls_idx)]
                prob_accumulator[name] = prob_accumulator.get(name, 0.0) + (float(conf) * weight)

        if not vote_list:
            return jsonify({
                "valid_cattle": False,
                "message": "Model returned no results. Try a clearer image."
            })

        # ── FINAL DECISION ──
        # Winner = highest accumulated probability (not just most votes)
        # This is more robust than plain majority voting
        vote_counts = Counter(vote_list)
        best_breed  = max(prob_accumulator, key=prob_accumulator.get)

        # Confidence = votes for winner / total variants (as percentage)
        winner_votes  = vote_counts.get(best_breed, 0)
        total_variants = len(vote_list)
        vote_ratio    = winner_votes / total_variants  # 0.0 to 1.0

        # Also get the raw avg top-1 confidence for the winning breed
        raw_confs = [
            float(results[i].probs.top1conf)
            for i, name in enumerate(vote_list) if name == best_breed
        ]
        avg_raw_conf = sum(raw_confs) / len(raw_confs) if raw_confs else 0

        # Combined score: blend vote ratio + raw confidence
        combined_score = (vote_ratio * 0.5) + (avg_raw_conf * 0.5)
        final_conf     = round(combined_score * 100, 1)

        # Trust calibrated for 53-class TTA model
        # vote_ratio > 0.5 means >50% of 30 variants agree = very reliable
        if vote_ratio >= 0.60 and avg_raw_conf >= 0.40:
            trust = "HIGH"
        elif vote_ratio >= 0.35 or avg_raw_conf >= 0.25:
            trust = "MEDIUM"
        else:
            trust = "LOW"

        # Get breed info from RAM cache (instant)
        breed_info = breed_cache.get(best_breed, {})

        elapsed = round(time.time() - t0, 2)

        print(f"✅ RESULT: {best_breed}")
        print(f"   vote_ratio={round(vote_ratio*100,1)}% ({winner_votes}/{total_variants} variants)")
        print(f"   avg_raw_conf={round(avg_raw_conf*100,1)}%")
        print(f"   combined_score={final_conf}% | trust={trust}")
        print(f"   total_time={elapsed}s")

        return jsonify({
            "valid_cattle": True,
            "breed": best_breed,
            "confidence": final_conf,
            "trust": trust,
            "images_used": len(base_images),
            "tta_variants": total_variants,
            "vote_agreement": f"{round(vote_ratio*100,1)}%",
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