import os
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "food101.keras")
IMG_SIZE = (224, 224)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}

# Food-101 class names in alphabetical order (matches sparse label encoding)
CLASS_NAMES = [
    "apple_pie", "baby_back_ribs", "baklava", "beef_carpaccio", "beef_tartare",
    "beet_salad", "beignets", "bibimbap", "bread_pudding", "breakfast_burrito",
    "bruschetta", "caesar_salad", "cannoli", "caprese_salad", "carrot_cake",
    "ceviche", "cheese_plate", "cheesecake", "chicken_curry", "chicken_quesadilla",
    "chicken_wings", "chocolate_cake", "chocolate_mousse", "churros", "clam_chowder",
    "club_sandwich", "crab_cakes", "creme_brulee", "croque_madame", "cup_cakes",
    "deviled_eggs", "donuts", "dumplings", "edamame", "eggs_benedict",
    "escargots", "falafel", "filet_mignon", "fish_and_chips", "foie_gras",
    "french_fries", "french_onion_soup", "french_toast", "fried_calamari", "fried_rice",
    "frozen_yogurt", "garlic_bread", "gnocchi", "greek_salad", "grilled_cheese_sandwich",
    "grilled_salmon", "guacamole", "gyoza", "hamburger", "hot_and_sour_soup",
    "hot_dog", "huevos_rancheros", "hummus", "ice_cream", "lasagna",
    "lobster_bisque", "lobster_roll_sandwich", "macaroni_and_cheese", "macarons", "miso_soup",
    "mussels", "nachos", "omelette", "onion_rings", "oysters",
    "pad_thai", "paella", "pancakes", "panna_cotta", "peking_duck",
    "pho", "pizza", "pork_chop", "poutine", "prime_rib",
    "pulled_pork_sandwich", "ramen", "ravioli", "red_velvet_cake", "risotto",
    "samosa", "sashimi", "scallops", "seaweed_salad", "shrimp_and_grits",
    "spaghetti_bolognese", "spaghetti_carbonara", "spring_rolls", "steak",
    "strawberry_shortcake", "sushi", "tacos", "takoyaki", "tiramisu",
    "tuna_tartare", "waffles",
]

# ---------------------------------------------------------------------------
# Global model reference (loaded once at startup)
# ---------------------------------------------------------------------------
model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load Keras model once at application startup."""
    global model
    # Lazy-import tensorflow so the module loads fast if tf is missing
    import tensorflow as tf

    print(f"Loading model from {MODEL_PATH} …")
    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    print("Model loaded successfully.")
    yield
    model = None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Food-101 Classifier API", version="1.0.0", lifespan=lifespan)

# CORS — allow localhost during dev; override with FRONTEND_ORIGIN in production
frontend_origin = os.getenv("FRONTEND_ORIGIN", "")
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
if frontend_origin:
    origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _format_class_name(name: str) -> str:
    """Convert snake_case class name to Title Case."""
    return name.replace("_", " ").title()


def _preprocess_image(image: Image.Image) -> np.ndarray:
    """Resize to 224×224, convert to RGB, and prepare batch array.

    EfficientNetB0's preprocess_input is identity for this model (pixel values
    stay in 0-255 range).
    """
    image = image.convert("RGB")
    image = image.resize(IMG_SIZE, Image.LANCZOS)
    arr = np.array(image, dtype=np.float32)  # shape: (224, 224, 3), range 0-255
    return np.expand_dims(arr, axis=0)  # batch dim → (1, 224, 224, 3)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "message": "Food-101 Classifier API"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    # --- Validate content type ---
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {file.content_type}. Allowed: JPEG, PNG, WebP, GIF, BMP.",
        )

    # --- Read & validate size ---
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large ({len(contents) / 1024 / 1024:.1f} MB). Maximum is 10 MB.",
        )

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # --- Open image ---
    try:
        from io import BytesIO

        image = Image.open(BytesIO(contents))
        image.load()  # Force full decode to catch corrupt files
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read the uploaded file as an image.")

    # --- Predict ---
    try:
        batch = _preprocess_image(image)
        predictions = model.predict(batch, verbose=0)
        probs = predictions[0]  # shape: (101,)
    except Exception:
        raise HTTPException(status_code=500, detail="Prediction failed. Please try again.")

    # --- Top-5 ---
    top5_indices = probs.argsort()[::-1][:5]
    top_predictions = [
        {"class": _format_class_name(CLASS_NAMES[i]), "confidence": round(float(probs[i]), 4)}
        for i in top5_indices
    ]

    return {
        "prediction": top_predictions[0],
        "top_predictions": top_predictions,
    }
