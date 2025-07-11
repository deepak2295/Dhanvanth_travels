# utils/nlp.py

from rapidfuzz import process

# Bangalore-specific known locations
known_locations = [
    "mg road", "koramangala", "indiranagar", "btm layout", "whitefield",
    "hebbal", "marathahalli", "banashankari", "rajajinagar", "jayanagar",
    "malleshwaram", "hsr layout", "yelachenahalli", "electronic city",
    "bommanahalli", "shivajinagar", "rt nagar", "kr puram", "airport",
    "yeshwanthpur", "kammanahalli", "bannerghatta road", "majestic"
]

# Intents the bot should recognize
booking_keywords = ["book", "ride", "cab", "taxi"]
pickup_keywords = ["from", "pickup", "pick up"]
drop_keywords = ["to", "drop", "destination"]

# Spelling correction for locations
def correct_location(input_text):
    match, score, _ = process.extractOne(input_text.lower(), known_locations, score_cutoff=60)
    return match if match else input_text.lower()

# Detect intent based on keywords
def detect_intent(text):
    text = text.lower()

    if any(word in text for word in booking_keywords):
        return "booking"
    elif any(word in text for word in pickup_keywords):
        return "pickup"
    elif any(word in text for word in drop_keywords):
        return "drop"
    else:
        return "unknown"

# Extract potential location from sentence
def extract_location(text):
    words = text.lower().split()
    locations = []
    for word in words:
        corrected = correct_location(word)
        if corrected in known_locations:
            locations.append(corrected)
    return locations
