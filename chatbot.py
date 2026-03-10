# chatbot.py - Add this new file to your backend

from flask import Blueprint, request, jsonify
from difflib import get_close_matches
import re

chatbot_bp = Blueprint('chatbot', __name__)

# Knowledge Base for the Chatbot
CHATBOT_KNOWLEDGE = {
    # App Related Questions
    "what is this app": {
        "answer": "PashuMitra is an AI-powered cattle breed identification system. You can upload up to 5 images of cattle, and our AI will identify the breed with detailed information about milk production, feeding, and healthcare.",
        "keywords": ["app", "pashumitra", "what is", "about", "purpose"]
    },
    "how to use": {
        "answer": "Simply go to the 'Detect' page, upload or capture up to 5 images of the cattle, and click 'Detect Breed'. Our AI will analyze the images and provide you with the breed name, confidence level, and detailed breed information.",
        "keywords": ["how to use", "how does it work", "tutorial", "guide", "steps"]
    },
    "how many images": {
        "answer": "You can upload up to 5 images for better accuracy. Using multiple images from different angles helps our AI make a more accurate prediction.",
        "keywords": ["how many", "images", "photos", "pictures", "upload"]
    },
    
    # Breed Related Questions
    "best milk breed": {
        "answer": "The top milk-producing Indian cattle breeds are:\n1. Gir (10-15 litres/day)\n2. Sahiwal (10-16 litres/day)\n3. Red Sindhi (6-10 litres/day)\n4. Tharparkar (8-12 litres/day)\n\nSahiwal is considered one of the best for consistent high milk production.",
        "keywords": ["best milk", "highest milk", "most milk", "milk production", "dairy"]
    },
    "smallest breed": {
        "answer": "Vechur cattle from Kerala is the world's smallest cattle breed. Males weigh only 90-130 kg and females 80-120 kg. Despite their small size, they produce 2-4 litres of milk per day with 4.5-5.5% fat content.",
        "keywords": ["smallest", "dwarf", "tiny", "little", "small breed", "vechur"]
    },
    "drought resistant": {
        "answer": "The most drought-resistant breeds are:\n1. Tharparkar - Excellent for desert conditions\n2. Rathi - Minimal water requirements\n3. Kankrej - Heat and drought tolerant\n4. Nari - Survives on minimal water\n\nThese breeds have adapted to arid and semi-arid climates.",
        "keywords": ["drought", "desert", "dry", "arid", "water", "resistance"]
    },
    "dual purpose breed": {
        "answer": "Best dual-purpose breeds (milk + draught):\n1. Tharparkar - 8-12 litres/day + excellent draught power\n2. Hariana - 6-10 litres/day + strong for field work\n3. Kankrej - 5-10 litres/day + powerful draught\n4. Deoni - 5-8 litres/day + good for farming",
        "keywords": ["dual purpose", "milk and draught", "farming and milk", "multipurpose"]
    },
    
    # Feeding Questions
    "what to feed": {
        "answer": "Cattle feeding generally includes:\n\n🌱 Green Fodder: Jowar, maize, napier grass, berseem\n🌾 Dry Fodder: Wheat straw, paddy straw, hay\n🥜 Concentrates: Oil cakes (cotton seed, groundnut), balanced feed, mineral mixture\n\nProvide fresh water at all times. The exact amount depends on the breed, age, and milk production.",
        "keywords": ["feed", "feeding", "food", "fodder", "diet", "nutrition"]
    },
    "green fodder": {
        "answer": "Best green fodder options:\n- Hybrid Napier (high yielding)\n- Berseem (protein rich)\n- Jowar/Sorghum (easy to grow)\n- Maize (high energy)\n- Lucerne/Alfalfa (excellent nutrition)\n\nRotate crops for year-round availability.",
        "keywords": ["green fodder", "grass", "fresh fodder", "grazing"]
    },
    
    # Health Questions
    "common diseases": {
        "answer": "Common cattle diseases:\n\n🦠 FMD (Foot and Mouth Disease) - Vaccinate every 6 months\n🦟 Tick Fever - Regular tick control needed\n🥛 Mastitis - Keep udders clean, regular check-ups\n💨 Bloat - Avoid sudden diet changes\n🌡️ Heat Stress - Provide shade and cool water\n\nAlways consult a veterinarian for proper diagnosis and treatment.",
        "keywords": ["disease", "sick", "illness", "health", "medical", "infection"]
    },
    "vaccination schedule": {
        "answer": "Standard vaccination schedule:\n\n✅ FMD (Foot & Mouth Disease) - Every 6 months\n✅ HS (Hemorrhagic Septicemia) - Annually\n✅ BQ (Black Quarter) - Annually\n✅ Deworming - Every 3 months\n\nMaintain a health record book for each animal.",
        "keywords": ["vaccination", "vaccine", "immunization", "shot", "prevent"]
    },
    "mastitis prevention": {
        "answer": "Mastitis Prevention Tips:\n\n1. Clean udders before and after milking\n2. Use clean milking equipment\n3. Milk completely - don't leave residual milk\n4. Check for swelling or heat in udders daily\n5. Isolate infected animals immediately\n6. Provide clean, dry bedding\n7. Maintain proper nutrition\n\nEarly detection is key!",
        "keywords": ["mastitis", "udder", "infection", "milk infection"]
    },
    
    # Climate Questions
    "hot climate breed": {
        "answer": "Best breeds for hot climates:\n\n☀️ Gir - Excellent heat tolerance\n☀️ Red Sindhi - Adapts to hot conditions\n☀️ Sahiwal - Heat resistant\n☀️ Tharparkar - Desert adapted\n☀️ Ongole - Coastal heat tolerance\n\nAll Indian native breeds are generally more heat-tolerant than exotic breeds.",
        "keywords": ["hot", "heat", "summer", "warm", "tropical"]
    },
    "cold climate breed": {
        "answer": "Breeds suitable for cold climates:\n\n❄️ Ladakhi - Extreme cold tolerance\n❄️ Badri - Hill regions, cold resistant\n❄️ Himachali Pahari - Mountain breed\n\nProvide proper shelter, warm bedding, and increase energy-rich feed in winter.",
        "keywords": ["cold", "winter", "snow", "mountain", "hill"]
    },
    
    # Economics
    "profitable breed": {
        "answer": "Most profitable breeds depend on your goals:\n\n💰 For Milk: Sahiwal, Gir (high yield)\n💰 For Small Farmers: Vechur, Punganur (low input, high fat content)\n💰 For Dual Purpose: Tharparkar, Hariana\n💰 For Draught: Hallikar, Kangayam\n\nConsider: local climate, available resources, market demand, and maintenance costs.",
        "keywords": ["profitable", "money", "income", "business", "economic"]
    },
    "cost of maintaining": {
        "answer": "Monthly maintenance cost per cattle (approximate):\n\n🌾 Feed: ₹3,000-5,000\n💊 Healthcare: ₹500-1,000\n🏠 Shelter maintenance: ₹200-500\n👨‍⚕️ Veterinary: ₹300-800\n\nTotal: ₹4,000-7,300/month\n\nCosts vary by breed, location, and production level. High-yielding breeds require better nutrition.",
        "keywords": ["cost", "expense", "price", "maintain", "budget"]
    },
    
    # Breeding
    "breeding age": {
        "answer": "Ideal breeding age:\n\n🐄 Most breeds: 3 years (after 2nd heat cycle)\n🐄 Small breeds (Vechur, Punganur): 2.5-3 years\n🐄 Large breeds (Ongole): 3-4 years\n\n⏱️ Gestation period: 280 days (9 months)\n⏱️ Calving interval: 400-450 days (ideal)\n\nDon't breed too early - it affects growth and milk production.",
        "keywords": ["breeding", "mating", "pregnancy", "calving", "reproduction"]
    },
    
    # General Care
    "water requirement": {
        "answer": "Daily water requirements:\n\n💧 Dry cattle: 30-40 litres\n💧 Milking cattle: 60-80 litres\n💧 Lactating cattle: 80-100 litres\n💧 Hot weather: +30-40% more\n\nProvide clean, fresh water 24/7. Water quality is as important as quantity!",
        "keywords": ["water", "drinking", "hydration", "thirst"]
    },
    "shelter requirements": {
        "answer": "Cattle shelter essentials:\n\n🏠 Space: 3-4 sq.m per adult cattle\n🌬️ Ventilation: Good airflow, avoid drafts\n☀️ Shade: Protection from direct sun\n🌧️ Roof: Leak-proof, insulated\n🧹 Flooring: Sloped for drainage, non-slip\n💨 Direction: East-West orientation\n\nKeep shelter clean and dry. Remove dung daily.",
        "keywords": ["shelter", "shed", "housing", "barn", "stable"]
    },
    
    # Contact/Support
    "contact": {
        "answer": "📧 Email: vaibhavgangurde139@email.com\n📱 Phone: +91 9867616633\n💼 LinkedIn: https://www.linkedin.com/in/vaibhav139/\n\nFeel free to reach out for any queries or support!",
        "keywords": ["contact", "support", "help", "email", "phone", "reach"]
    },
    
    # Default responses
    "greeting": {
        "answer": "Namaste! 🙏 Welcome to PashuMitra AI. I'm here to help you with cattle breed information, farming practices, and app guidance. How can I assist you today?",
        "keywords": ["hello", "hi", "hey", "namaste", "greetings"]
    },
    "thanks": {
        "answer": "You're welcome! 😊 Feel free to ask me anything about cattle breeds, farming, or our app. Happy farming! 🐄",
        "keywords": ["thank", "thanks", "thank you", "appreciated"]
    }
}

def find_best_match(user_query):
    """Find the best matching answer from knowledge base"""
    user_query = user_query.lower().strip()
    
    # Direct keyword matching
    for topic, data in CHATBOT_KNOWLEDGE.items():
        for keyword in data["keywords"]:
            if keyword in user_query:
                return data["answer"]
    
    # Fuzzy matching on topics
    topics = list(CHATBOT_KNOWLEDGE.keys())
    matches = get_close_matches(user_query, topics, n=1, cutoff=0.4)
    
    if matches:
        return CHATBOT_KNOWLEDGE[matches[0]]["answer"]
    
    # Check for breed-specific questions
    breed_keywords = ["gir", "sahiwal", "red sindhi", "tharparkar", "kankrej", 
                     "ongole", "hariana", "rathi", "punganur", "vechur"]
    for breed in breed_keywords:
        if breed in user_query:
            return f"For detailed information about {breed.title()}, please visit the 'Breeds' section or use the detection feature to get comprehensive details including milk production, feeding requirements, and healthcare."
    
    return None

@chatbot_bp.route("/chat", methods=["POST"])
def chat():
    """Handle chat requests"""
    data = request.get_json()
    
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400
    
    user_message = data["message"]
    
    # Find answer
    answer = find_best_match(user_message)
    
    if answer:
        return jsonify({
            "response": answer,
            "success": True
        })
    else:
        return jsonify({
            "response": "I'm not sure about that. You can ask me about:\n\n🐄 Cattle breeds and their characteristics\n🥛 Milk production and dairy farming\n🌾 Feeding and nutrition\n💊 Common diseases and healthcare\n🌡️ Climate-specific breeds\n💰 Economics and profitability\n📱 How to use this app\n\nWhat would you like to know?",
            "success": False
        })

@chatbot_bp.route("/chat/suggestions", methods=["GET"])
def get_suggestions():
    """Get suggested questions for quick access"""
    suggestions = [
        "What is the best milk breed?",
        "How to prevent mastitis?",
        "What should I feed my cattle?",
        "Which breed is best for hot climate?",
        "What is the vaccination schedule?",
        "How many images should I upload?",
        "Which is the smallest cattle breed?",
        "What are drought-resistant breeds?"
    ]
    
    return jsonify({
        "suggestions": suggestions
    })

