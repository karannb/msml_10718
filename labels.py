"""The 5 pooled labels (condition only, plant omitted) and how each dataset's own classes map to them."""

LABELS = ["healthy", "watering", "fungal_bacterial", "pest", "other"]

# Indoor Plant Disease Detection: 16 classes (5 plants x condition).
INDOOR = {
    "Aloe_Healthy": "healthy",
    "Cactus_Healthy": "healthy",
    "Money_Plant_Healthy": "healthy",
    "Snake_Plant_Healthy": "healthy",
    "Spider_Plant_Healthy": "healthy",
    "Snake_Plant_Leaf_Withering": "watering",  # judgment call
    "Aloe_Anthracnose": "fungal_bacterial",
    "Aloe_LeafSpot": "fungal_bacterial",
    "Aloe_Rust": "fungal_bacterial",
    "Snake_Plant_Anthracnose": "fungal_bacterial",
    "Spider_Plant_Fungal_leaf_spot": "fungal_bacterial",
    "Money_Plant_Bacterial_wilt_disease": "fungal_bacterial",
    "Cactus_Dactylopius_Opuntia": "pest",  # cochineal scale insect
    "Aloe_Sunburn": "other",
    "Money_Plant_Manganese_Toxicity": "other",
    "Spider_Plant_Leaf_Tip_Necrosis": "other",  # judgment call: salts/fluoride
}

# Healthy and Wilted Houseplant Images: 2 classes.
WILTED = {"healthy": "healthy", "wilted": "watering"}


def plantseg_label(disease):
    """PlantSeg: 115 diseases. Viruses and blossom end rot (calcium deficiency) are 'other', the rest fungal/bacterial."""
    virus = any(k in disease for k in ["virus", "mosaic", "bunchy top", "leafroll"])
    return "other" if virus or disease == "bell pepper blossom end rot" else "fungal_bacterial"


# PlantDoc: 28 classes, photos from the web of real plants (13 crops).
PLANTDOC = {
    "Apple leaf": "healthy",
    "Bell_pepper leaf": "healthy",
    "Blueberry leaf": "healthy",
    "Cherry leaf": "healthy",
    "Peach leaf": "healthy",
    "Raspberry leaf": "healthy",
    "Soyabean leaf": "healthy",
    "Strawberry leaf": "healthy",
    "Tomato leaf": "healthy",
    "grape leaf": "healthy",
    "Apple Scab Leaf": "fungal_bacterial",
    "Apple rust leaf": "fungal_bacterial",
    "Bell_pepper leaf spot": "fungal_bacterial",
    "Corn Gray leaf spot": "fungal_bacterial",
    "Corn leaf blight": "fungal_bacterial",
    "Corn rust leaf": "fungal_bacterial",
    "Potato leaf early blight": "fungal_bacterial",
    "Potato leaf late blight": "fungal_bacterial",
    "Squash Powdery mildew leaf": "fungal_bacterial",
    "Tomato Early blight leaf": "fungal_bacterial",
    "Tomato Septoria leaf spot": "fungal_bacterial",
    "Tomato leaf bacterial spot": "fungal_bacterial",
    "Tomato leaf late blight": "fungal_bacterial",
    "Tomato mold leaf": "fungal_bacterial",
    "grape leaf black rot": "fungal_bacterial",
    "Tomato two spotted spider mites leaf": "pest",
    "Tomato leaf mosaic virus": "other",
    "Tomato leaf yellow virus": "other",
}
