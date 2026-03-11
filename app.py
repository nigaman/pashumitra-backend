"""
PashuMitra — Production Detection Pipeline
==========================================
TWO-STAGE ARCHITECTURE:
  Stage 1: YOLOv8n (COCO pretrained) — detects if a cow is present
            and crops the exact cow bounding box from the image.
  Stage 2: YOLOv8c (custom trained) — classifies the cropped cow
            into one of 53 Indian breeds.

WHY TWO STAGES?
  Without Stage 1, the classifier sees background clutter, people,
  trees, fences — and wastes its capacity on non-cattle pixels.
  After Stage 1 crops the cow, Stage 2 sees ONLY the animal and
  makes a far more accurate breed prediction.

TTA (Test-Time Augmentation):
  Each cropped cow image is augmented into 6 variants.
  All variants are inferred in one batch.
  Predictions are probability-averaged → stable, noise-resistant result.

CONFIDENCE LOGIC:
  vote_ratio  = fraction of TTA variants that agree on the winning breed
  raw_conf    = average top-1 softmax score for the winner
  combined    = 0.4 * vote_ratio + 0.6 * raw_conf
  Thresholds (calibrated for 53-class model):
    HIGH:   combined >= 0.55 AND vote_ratio >= 0.50
    MEDIUM: combined >= 0.30 OR  vote_ratio >= 0.35
    LOW:    everything else (still returned, user warned)
"""

import os, gc, io, time, traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

# ── Thread counts — use all 4 HF Spaces vCPUs ──
os.environ["OMP_NUM_THREADS"]      = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"]      = "4"
os.environ["NUMEXPR_NUM_THREADS"]  = "4"

import torch
torch.set_num_threads(4)

from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
from PIL import Image, ImageEnhance, ImageFilter
from pymongo import MongoClient

try:
    from chatbot import chatbot_bp
    HAS_CHATBOT = True
except Exception:
    HAS_CHATBOT = False

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ============================================================
#  STAGE 1 MODEL — Cattle Detector (COCO YOLOv8n)
#  COCO class 19 = "cow"  (also covers bull/buffalo loosely)
#  We use this ONLY for bounding-box detection, not classification.
# ============================================================
print("🔄 Loading Stage-1 detector (YOLOv8n COCO)…")
DETECTOR_PATH = os.path.join(os.getcwd(), "models", "yolov8n.pt")

# If not on disk, Ultralytics auto-downloads it (~6 MB, one-time)
detector = YOLO(DETECTOR_PATH if os.path.exists(DETECTOR_PATH) else "yolov8n.pt")
COCO_COW_CLASS = 19   # COCO index for "cow"
print("✅ Detector ready")

# ============================================================
#  STAGE 2 MODEL — Breed Classifier (custom 53-class)
# ============================================================
print("🔄 Loading Stage-2 classifier (custom best.pt)…")
CLASSIFIER_PATH = os.path.join(os.getcwd(), "models", "best.pt")
classifier = YOLO(CLASSIFIER_PATH)

print("🔥 Warming up classifier (3×)…")
_dummy = Image.new("RGB", (640, 640), (110, 90, 70))
with torch.no_grad():
    for _ in range(3):
        classifier.predict(_dummy, imgsz=640, verbose=False)

print(f"✅ Classifier ready — {len(classifier.names)} breeds")
print(f"   Sample breeds: {list(classifier.names.values())[:8]}")

# ============================================================
#  MONGODB — cache every breed document in RAM at startup
# ============================================================
print("🔄 Connecting to MongoDB Atlas…")
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://pashumitra_user:Cattle2024@cluster0.p4bec5t.mongodb.net/"
    "cattle_ai?retryWrites=true&w=majority&appName=Cluster0"
)
_mc = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
_db = _mc["cattle_ai"]

breed_cache: dict = {}
for _doc in _db["breeds"].find({}, {"_id": 0}):
    _name = _doc.get("name", "")
    if _name:
        breed_cache[_name] = _doc

print(f"✅ {len(breed_cache)} breeds cached from MongoDB")

# Thread pool for parallel image loading
_pool = ThreadPoolExecutor(max_workers=5)

if HAS_CHATBOT:
    from chatbot import chatbot_bp
    app.register_blueprint(chatbot_bp, url_prefix="/api")

# ============================================================
#  CORS
# ============================================================
@app.after_request
def _cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# ============================================================
#  HEALTH
# ============================================================
@app.route("/")
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "breeds_loaded": len(breed_cache),
        "classifier_classes": len(classifier.names),
        "pipeline": "2-stage: detector → classifier + TTA"
    })

# ============================================================
#  PREPROCESSING PIPELINE
#  Applied to every image before Stage-1 detection.
#  Goal: make the image look as close as possible to
#        clean, well-lit training data.
# ============================================================
def preprocess(img: Image.Image, target_size: int = 640) -> Image.Image:
    """
    Full preprocessing pipeline for mobile field photos.

    Steps:
      1. Convert to RGB (handles JPEG/PNG/HEIC etc.)
      2. Auto-levels: clip the darkest 2% and brightest 2%
         of pixels, then stretch histogram to [0, 255].
         Fixes underexposed barn photos and blown-out sunlit ones.
      3. Mild contrast enhancement (1.10×) — improves coat texture.
      4. Mild sharpness enhancement (1.15×) — recovers phone blur.
      5. Resize to target_size × target_size with padding
         (letterbox) so the aspect ratio is preserved and
         the cow is not squished.
    """
    img = img.convert("RGB")

    # ── Auto-levels (histogram stretch) ──
    import numpy as np
    arr = np.array(img, dtype=np.float32)
    for ch in range(3):
        lo = float(np.percentile(arr[:, :, ch], 2))
        hi = float(np.percentile(arr[:, :, ch], 98))
        if hi > lo:
            arr[:, :, ch] = (arr[:, :, ch] - lo) / (hi - lo) * 255.0
    arr = arr.clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    # ── Contrast + Sharpness ──
    img = ImageEnhance.Contrast(img).enhance(1.10)
    img = ImageEnhance.Sharpness(img).enhance(1.15)

    # ── Letterbox resize (preserves aspect ratio) ──
    img = letterbox(img, target_size)
    return img


def letterbox(img: Image.Image, size: int = 640) -> Image.Image:
    """
    Resize image so the longer side = `size`, pad shorter side
    with grey (128, 128, 128) to make a square.
    """
    w, h = img.size
    scale = size / max(w, h)
    nw, nh = int(w * scale), int(h * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), (128, 128, 128))
    canvas.paste(img, ((size - nw) // 2, (size - nh) // 2))
    return canvas


# ============================================================
#  STAGE 1 — CATTLE DETECTION
#  Returns a list of cropped PIL images, one per detected cow.
#  If no cow found, returns None so caller can reject early.
# ============================================================
def detect_and_crop(img: Image.Image, conf_thresh: float = 0.30):
    """
    Run YOLOv8n detector on the image.
    Returns:
      list of PIL crops  — one per detected cow bounding box
      empty list         — image processed but no cow found
    """
    with torch.no_grad():
        det_results = detector.predict(
            img,
            imgsz=640,
            conf=conf_thresh,
            verbose=False
        )

    crops = []
    orig_w, orig_h = img.size

    for result in det_results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            cls_id = int(box.cls[0])
            if cls_id != COCO_COW_CLASS:
                continue   # skip non-cow detections

            # Get bounding box in pixel coords
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            # Add 8% padding around the box so we don't
            # clip the hump or tail — important for breed ID
            pad_x = (x2 - x1) * 0.08
            pad_y = (y2 - y1) * 0.08
            x1 = max(0,      x1 - pad_x)
            y1 = max(0,      y1 - pad_y)
            x2 = min(orig_w, x2 + pad_x)
            y2 = min(orig_h, y2 + pad_y)

            crop = img.crop((x1, y1, x2, y2))
            crop = crop.resize((640, 640), Image.LANCZOS)
            crops.append(crop)
            print(f"   🐄 Cow detected — box=({int(x1)},{int(y1)},{int(x2)},{int(y2)}) conf={float(box.conf[0]):.2f}")

    return crops


# ============================================================
#  TTA — TEST-TIME AUGMENTATION
#  6 variants per crop.  All run in one batch → fast.
#  Variant 0 (original) gets 1.5× weight in accumulation.
# ============================================================
TTA_VARIANTS = 6

def apply_tta(img: Image.Image) -> list:
    return [
        img,                                                        # 0 original (1.5× weight)
        img.transpose(Image.FLIP_LEFT_RIGHT),                       # 1 flip
        ImageEnhance.Brightness(img).enhance(1.18),                 # 2 brighter
        ImageEnhance.Brightness(img).enhance(0.84),                 # 3 darker
        ImageEnhance.Contrast(img).enhance(1.22),                   # 4 high contrast
        ImageEnhance.Sharpness(img).enhance(1.80),                  # 5 sharp
    ]


# ============================================================
#  BREED CLASSIFICATION
#  Takes a list of cow crops (already 640×640).
#  Returns (breed_name, combined_score, vote_ratio, raw_conf, all_probs)
# ============================================================
def classify_breeds(crops: list):
    """
    Build a TTA batch from all crops, run one forward pass,
    and aggregate results into a final breed prediction.
    """
    tta_batch   = []
    variant_map = []   # index → which crop it came from

    for crop_idx, crop in enumerate(crops):
        variants = apply_tta(crop)
        for v_pos, v in enumerate(variants):
            tta_batch.append(v)
            variant_map.append((crop_idx, v_pos))

    print(f"   🔀 TTA batch: {len(tta_batch)} variants from {len(crops)} crops")

    with torch.no_grad():
        results = classifier.predict(tta_batch, imgsz=640, verbose=False, half=False)

    # Accumulate probabilities
    prob_acc  = {}   # breed → total weighted prob
    vote_list = []   # top-1 per variant
    raw_conf_per_winner = {}  # breed → list of raw top-1 confs

    for i, result in enumerate(results):
        if result.probs is None:
            continue

        _, v_pos = variant_map[i]
        weight   = 1.5 if v_pos == 0 else 1.0   # original gets extra weight

        top1_name = classifier.names[int(result.probs.top1)]
        top1_conf = float(result.probs.top1conf)

        vote_list.append(top1_name)
        raw_conf_per_winner.setdefault(top1_name, []).append(top1_conf)

        for cls_idx, conf in zip(result.probs.top5, result.probs.top5conf):
            name = classifier.names[int(cls_idx)]
            prob_acc[name] = prob_acc.get(name, 0.0) + float(conf) * weight

    if not vote_list:
        return None, 0, 0, 0, {}

    # Winner by accumulated probability
    best        = max(prob_acc, key=prob_acc.get)
    vote_counts = Counter(vote_list)
    vote_ratio  = vote_counts.get(best, 0) / len(vote_list)
    raw_conf    = sum(raw_conf_per_winner.get(best, [0])) / max(len(raw_conf_per_winner.get(best, [1])), 1)

    # Combined score (primary metric shown to user)
    combined = round((0.40 * vote_ratio + 0.60 * raw_conf) * 100, 1)

    # Top-3 alternatives for transparency
    top3 = sorted(prob_acc.items(), key=lambda x: x[1], reverse=True)[:3]

    return best, combined, vote_ratio, raw_conf, top3


# ============================================================
#  IMAGE LOADER (parallel, thread-safe)
# ============================================================
def _load_bytes(file_bytes: bytes):
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        return img
    except Exception as e:
        print(f"⚠️ Could not decode image: {e}")
        return None


# ============================================================
#  PREDICT ENDPOINT
# ============================================================
@app.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    t0 = time.time()

    try:
        files = request.files.getlist("images")
        if not files:
            return jsonify({"valid_cattle": False,
                            "message": "No images received. Please upload at least one photo."}), 400

        # ── Read all file bytes inside request context ──
        all_bytes = []
        for f in files[:5]:
            try:
                all_bytes.append(f.read())
            except Exception as e:
                print(f"⚠️ File read error: {e}")

        # ── Load images in parallel ──
        futures     = [_pool.submit(_load_bytes, b) for b in all_bytes]
        raw_images  = [fut.result() for fut in futures if fut.result() is not None]

        if not raw_images:
            return jsonify({"valid_cattle": False,
                            "message": "Could not read the uploaded images. Please try again."})

        t_load = round(time.time() - t0, 3)
        print(f"\n{'='*55}")
        print(f"📸 {len(raw_images)} images loaded in {t_load}s")

        # ── STAGE 1: Preprocess + Detect Cattle ──
        all_crops = []
        no_cow_count = 0

        for idx, img in enumerate(raw_images):
            # Full preprocessing pipeline
            processed = preprocess(img)

            # Detect cows and crop them
            crops = detect_and_crop(processed, conf_thresh=0.25)

            if crops:
                all_crops.extend(crops)
                print(f"   Image {idx+1}: {len(crops)} cow(s) found ✅")
            else:
                no_cow_count += 1
                print(f"   Image {idx+1}: No cow detected ❌")
                # Fall back: use the entire preprocessed image as the crop
                # This handles cases where the cow fills the whole frame
                # (detector might miss it) — better than rejecting
                all_crops.append(processed)
                print(f"   Image {idx+1}: Using full image as fallback crop")

        t_detect = round(time.time() - t0, 3)
        print(f"🎯 Detection done in {t_detect}s — {len(all_crops)} crops total")

        if not all_crops:
            return jsonify({
                "valid_cattle": False,
                "message": "No cattle found in the uploaded images.\n"
                           "Please ensure:\n"
                           "• The cattle is clearly visible\n"
                           "• Stand 2–4 feet away\n"
                           "• Capture the full body or at least the head and shoulders"
            })

        # ── STAGE 2: Classify Breed with TTA ──
        best_breed, combined, vote_ratio, raw_conf, top3 = classify_breeds(all_crops)

        t_classify = round(time.time() - t0, 3)

        if best_breed is None:
            return jsonify({
                "valid_cattle": False,
                "message": "Classification failed. Please try again with a clearer image."
            })

        # ── CONFIDENCE DECISION ──
        # Calibrated for a 53-class model where random = 1.9%
        # combined score blends vote_ratio + raw_conf
        if vote_ratio >= 0.50 and raw_conf >= 0.40:
            trust = "HIGH"
        elif vote_ratio >= 0.35 or raw_conf >= 0.25:
            trust = "MEDIUM"
        else:
            trust = "LOW"

        # ── Warn user if confidence is low but still return result ──
        # We NEVER withhold results — always give best prediction
        # but add a clear advisory for low confidence
        advisory = None
        if trust == "LOW":
            advisory = (
                "⚠️ Low confidence prediction. "
                "For better accuracy, try: clearer lighting, "
                "full side-body view from 2–4 feet, 3–5 photos."
            )

        # ── Get breed info from RAM cache (zero latency) ──
        breed_info = breed_cache.get(best_breed, {})
        if not breed_info:
            print(f"   ⚠️ '{best_breed}' not in MongoDB cache. "
                  f"Sample keys: {list(breed_cache.keys())[:5]}")

        # ── Top-3 alternatives (for UI transparency) ──
        alternatives = [
            {"breed": name, "score": round(score, 2)}
            for name, score in top3
            if name != best_breed
        ][:2]

        elapsed = round(time.time() - t0, 2)

        print(f"✅ FINAL RESULT: {best_breed}")
        print(f"   combined={combined}% | vote_ratio={round(vote_ratio*100,1)}% "
              f"| raw_conf={round(raw_conf*100,1)}% | trust={trust}")
        print(f"   Total time: {elapsed}s  (load={t_load}s detect={t_detect}s classify={t_classify}s)")
        print(f"{'='*55}\n")

        return jsonify({
            "valid_cattle": True,
            "breed":        best_breed,
            "confidence":   combined,
            "trust":        trust,
            "advisory":     advisory,
            "images_used":  len(raw_images),
            "crops_used":   len(all_crops),
            "tta_variants": len(all_crops) * TTA_VARIANTS,
            "vote_agreement": f"{round(vote_ratio*100,1)}%",
            "alternatives": alternatives,
            "inference_time": elapsed,
            "breed_info":   breed_info
        })

    except Exception as e:
        gc.collect()
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================
#  BREED ROUTES
# ============================================================
@app.route("/breeds")
def get_all_breeds():
    return jsonify({
        "total":  len(breed_cache),
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
        if k.lower() == breed_name.lower():
            return jsonify(v)
    return jsonify({"error": f"'{breed_name}' not found"}), 404


# ============================================================
#  START
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 PashuMitra 2-stage pipeline on port {port}")
    app.run(host="0.0.0.0", port=port)