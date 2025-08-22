from rapidfuzz import process
from textblob import TextBlob
import nltk
from nltk.corpus import wordnet
import re
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')
    nltk.download('omw-1.4') 

greetings = {"hi", "hello", "hey", "hii", "hola"} 
book_keywords = {"book", "ride", "cab", "taxi"}
confirm_keywords = {"confirm", "yes", "okay", "ok", "sure"}
driver_complete_keywords = {"completed", "dropped", "finished", "done"}


known_locations = [
    "mg road", "koramangala", "indiranagar", "btm layout", "whitefield",
    "hebbal", "marathahalli", "banashankari", "rajajinagar", "jayanagar",
    "malleshwaram", "hsr layout", "yelachenahalli", "electronic city",
    "bommanahalli", "shivajinagar", "rt nagar", "kr puram", "airport",
    "yeshwanthpur", "kammanahalli", "bannerghatta road", "majestic"
]

def get_synonyms(word):
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace("_", " "))
    return synonyms

def fuzzy_match(word, keywords):
    for keyword in keywords:
        all_keywords = get_synonyms(keyword)
        if word.lower() in all_keywords or keyword in word.lower():
            return True
    return False

def correct_text(text):
    return str(TextBlob(text).correct())


def correct_location(input_text):
    """
    Uses fuzzy matching against known locations and safely handles cases
    where no match is found.
    """
    if not input_text or not input_text.strip():
        return "" 

    result = process.extractOne(input_text.lower(), known_locations, score_cutoff=60)

    if result:
        match, score, _ = result
        return match
    else:
        return input_text.lower()

def correct_spelling(text):
    blob = TextBlob(text)
    return str(blob.correct()).lower()


def detect_intent(text, session_state=None):
    text_lower = text.lower().strip()
    if text_lower in greetings:
        return "greeting"

    corrected_text = correct_spelling(text).lower()
    words = corrected_text.split()


    if any(word in driver_complete_keywords for word in words) and re.search(r'\d+', corrected_text):
        return "complete_ride_driver"

    if any(word in book_keywords for word in words):
        return "book_ride"
    if any(word in confirm_keywords for word in words):
        return "confirm_ride"

    if session_state == "awaiting_booking_date_option":
        return "booking_date_option_selection"
    if session_state == "awaiting_specific_date":
        return "specific_date_input"
    if session_state == "awaiting_booking_time":
        return "booking_time_input"
    if session_state == "awaiting_pickup":
        return "pickup_location"
    if session_state == "awaiting_destination":
        return "destination_location"
    if session_state == "awaiting_car_type":
        return "car_selection"
    if session_state == "awaiting_payment_option":
        return "payment_option_selection"

    return "unknown"

def extract_ride_id(text):
    """Extracts a numerical ride ID from the text."""
    match = re.search(r'\d+', text)
    if match:
        return int(match.group(0))
    return None
