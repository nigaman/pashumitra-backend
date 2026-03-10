from pymongo import MongoClient

MONGO_URI = "mongodb+srv://pashumitra_user:Cattle2024@cluster0.p4bec5t.mongodb.net/cattle_ai?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["cattle_ai"]
breeds_col = db["breeds"]

# Clear old data
breeds_col.delete_many({})

breed_data = [
    {
        "name": "Alambadi",
        "origin": "Tamil Nadu",
        "nature": "Hardy, active, aggressive",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Dry grass, crop residues", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Black Quarter"]}
    },
    {
        "name": "Amritmahal",
        "origin": "Karnataka",
        "nature": "Fierce, energetic, strong",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Grass, jowar", "dry_fodder": "Dry straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent endurance, disease resistant", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Black Quarter"]}
    },
    {
        "name": "Ayrshire",
        "origin": "Scotland (exotic breed used in India)",
        "nature": "Active, alert, hardy",
        "purpose": "Milk production",
        "lifespan": "10-12 years",
        "production": {"milk_per_day": "15-20 litres/day", "milk_fat": "3.9%"},
        "feed": {"green_fodder": "Berseem, napier, lucerne", "dry_fodder": "Wheat straw", "concentrate": "Balanced concentrate, minerals"},
        "medical": {"disease_resistance": "Moderate, needs tick control", "common_diseases": ["Mastitis", "Tick Fever", "Brucellosis", "Milk Fever"]}
    },
    {
        "name": "Bachur",
        "origin": "Bihar",
        "nature": "Docile, slow, sturdy",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Grass, crop residues", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Bloat"]}
    },
    {
        "name": "Badri",
        "origin": "Uttarakhand (Himalayan hills)",
        "nature": "Hardy, small, adaptable",
        "purpose": "Milk production",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "2-4 litres/day", "milk_fat": "4.5%"},
        "feed": {"green_fodder": "Mountain grass, alpine fodder", "dry_fodder": "Dry grass, hay", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent cold resistance, disease tolerant", "common_diseases": ["Foot and Mouth Disease", "Pneumonia", "Internal Parasites"]}
    },
    {
        "name": "Banni",
        "origin": "Gujarat (Kutch region)",
        "nature": "Hardy, docile, adaptable",
        "purpose": "Milk production",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "5-8 litres/day", "milk_fat": "4.5%"},
        "feed": {"green_fodder": "Dry grass, halophyte plants", "dry_fodder": "Dry straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent heat and drought tolerance", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Mastitis"]}
    },
    {
        "name": "Bargur",
        "origin": "Tamil Nadu",
        "nature": "Active, aggressive, fast",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Forest grass, crop residues", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance, hill adapted", "common_diseases": ["Foot and Mouth Disease", "Black Quarter", "Tick Fever"]}
    },
    {
        "name": "Bhadwari",
        "origin": "Uttar Pradesh & Uttarakhand",
        "nature": "Docile, hardy, sturdy",
        "purpose": "Milk & draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "3-5 litres/day", "milk_fat": "6-7%"},
        "feed": {"green_fodder": "Grass, berseem", "dry_fodder": "Wheat straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Mastitis"]}
    },
    {
        "name": "Bhelai",
        "origin": "Madhya Pradesh & Chhattisgarh",
        "nature": "Hardy, active",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Grass, crop residues", "dry_fodder": "Dry straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance", "common_diseases": ["Foot and Mouth Disease", "Black Quarter", "Hemorrhagic Septicemia"]}
    },
    {
        "name": "Dagari",
        "origin": "Rajasthan",
        "nature": "Hardy, docile",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Dry grass, bajra", "dry_fodder": "Dry straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Drought resistant, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Internal Parasites"]}
    },
    {
        "name": "Dangi",
        "origin": "Maharashtra & Gujarat",
        "nature": "Docile, sturdy, powerful",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "2-3 litres/day", "milk_fat": "4.2%"},
        "feed": {"green_fodder": "Forest grass, jowar", "dry_fodder": "Paddy straw, dry grass", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent in humid, hilly terrain", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Bloat"]}
    },
    {
        "name": "Deoni",
        "origin": "Karnataka & Maharashtra",
        "nature": "Calm, docile, hardy",
        "purpose": "Milk & draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "5-8 litres/day", "milk_fat": "4.2%"},
        "feed": {"green_fodder": "Jowar, napier, berseem", "dry_fodder": "Wheat straw, paddy straw", "concentrate": "Oil cakes, balanced feed"},
        "medical": {"disease_resistance": "Good disease resistance", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Tick Fever"]}
    },
    {
        "name": "Gangatri",
        "origin": "Uttar Pradesh (Gangetic plains)",
        "nature": "Docile, calm",
        "purpose": "Milk & draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "4-6 litres/day", "milk_fat": "4.2%"},
        "feed": {"green_fodder": "Berseem, jowar", "dry_fodder": "Wheat straw", "concentrate": "Standard concentrate"},
        "medical": {"disease_resistance": "Moderate disease resistance", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Bloat"]}
    },
    {
        "name": "Gaolao",
        "origin": "Maharashtra & Madhya Pradesh",
        "nature": "Calm, docile, medium sized",
        "purpose": "Milk & draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "3-5 litres/day", "milk_fat": "4.3%"},
        "feed": {"green_fodder": "Jowar, green grass", "dry_fodder": "Paddy straw, dry grass", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Black Quarter", "Tick Fever"]}
    },
    {
        "name": "Ghumsari",
        "origin": "Odisha",
        "nature": "Hardy, small, active",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Grass, crop residues", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good resistance in humid conditions", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Internal Parasites"]}
    },
    {
        "name": "Gir",
        "origin": "Gujarat",
        "nature": "Calm, heat tolerant, friendly",
        "purpose": "Milk production",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "10-15 litres/day", "milk_fat": "4.5%"},
        "feed": {"green_fodder": "Jowar, maize, hybrid napier", "dry_fodder": "Dry straw, bajra stover", "concentrate": "Oil cakes, balanced feed"},
        "medical": {"disease_resistance": "High disease resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Tick Fever"]}
    },
    {
        "name": "Hallikar",
        "origin": "Karnataka",
        "nature": "Active, energetic, strong",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "2-3 litres/day", "milk_fat": "4.2%"},
        "feed": {"green_fodder": "Jowar, green grass", "dry_fodder": "Dry straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent endurance, disease resistant", "common_diseases": ["Foot and Mouth Disease", "Black Quarter", "Hemorrhagic Septicemia"]}
    },
    {
        "name": "Hariana",
        "origin": "Haryana",
        "nature": "Calm, gentle, hardy",
        "purpose": "Milk & draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "6-10 litres/day", "milk_fat": "4.3%"},
        "feed": {"green_fodder": "Berseem, jowar, maize", "dry_fodder": "Wheat straw, paddy straw", "concentrate": "Mustard cake, wheat bran"},
        "medical": {"disease_resistance": "Good disease resistance", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Hemorrhagic Septicemia"]}
    },
    {
        "name": "Himachali Pahari",
        "origin": "Himachal Pradesh",
        "nature": "Hardy, small, adaptable",
        "purpose": "Milk & draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "2-4 litres/day", "milk_fat": "4.5%"},
        "feed": {"green_fodder": "Mountain grass, hay", "dry_fodder": "Dry grass, leaves", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent cold tolerance", "common_diseases": ["Pneumonia", "Foot and Mouth Disease", "Internal Parasites"]}
    },
    {
        "name": "Kangayam",
        "origin": "Tamil Nadu",
        "nature": "Hardy, active, strong",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "2-4 litres/day", "milk_fat": "4.3%"},
        "feed": {"green_fodder": "Dry grass, jowar", "dry_fodder": "Paddy straw, dry grass", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent heat tolerance, disease resistant", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Black Quarter"]}
    },
    {
        "name": "Kankrej",
        "origin": "Gujarat & Rajasthan border",
        "nature": "Strong, aggressive, powerful",
        "purpose": "Milk & draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "5-10 litres/day", "milk_fat": "4.7%"},
        "feed": {"green_fodder": "Jowar, maize, bajra", "dry_fodder": "Dry straw, bajra stover", "concentrate": "Oil cakes, grains"},
        "medical": {"disease_resistance": "Good disease resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Bloat"]}
    },
    {
        "name": "Kenkatha",
        "origin": "Uttar Pradesh & Madhya Pradesh",
        "nature": "Hardy, active, medium sized",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Grass, crop residues", "dry_fodder": "Dry straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Black Quarter"]}
    },
    {
        "name": "Kharia",
        "origin": "Jharkhand & Odisha",
        "nature": "Docile, small, hardy",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Forest grass, crop residues", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good resistance in tribal regions", "common_diseases": ["Foot and Mouth Disease", "Internal Parasites", "Tick Fever"]}
    },
    {
        "name": "Kherigarh",
        "origin": "Uttar Pradesh",
        "nature": "Hardy, docile",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "2-3 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Berseem, grass", "dry_fodder": "Wheat straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Moderate disease resistance", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Bloat"]}
    },
    {
        "name": "Khillari",
        "origin": "Maharashtra & Karnataka",
        "nature": "Active, fierce, powerful",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "2-3 litres/day", "milk_fat": "4.2%"},
        "feed": {"green_fodder": "Jowar, dry grass", "dry_fodder": "Paddy straw, dry straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent endurance, disease resistant", "common_diseases": ["Foot and Mouth Disease", "Black Quarter", "Tick Fever"]}
    },
    {
        "name": "Konkan Kapila",
        "origin": "Maharashtra (Konkan coast)",
        "nature": "Docile, small, adaptable",
        "purpose": "Milk production",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "2-4 litres/day", "milk_fat": "4.5%"},
        "feed": {"green_fodder": "Coconut leaves, grass", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good resistance in humid coastal areas", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Internal Parasites"]}
    },
    {
        "name": "Kosari",
        "origin": "Chhattisgarh",
        "nature": "Hardy, docile",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Grass, crop residues", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Black Quarter"]}
    },
    {
        "name": "Krishna Valley",
        "origin": "Karnataka & Andhra Pradesh",
        "nature": "Docile, massive, calm",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "3-5 litres/day", "milk_fat": "4.3%"},
        "feed": {"green_fodder": "Jowar, napier, green grass", "dry_fodder": "Paddy straw, crop residues", "concentrate": "Balanced concentrate"},
        "medical": {"disease_resistance": "Good disease resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Bloat"]}
    },
    {
        "name": "Ladakhi",
        "origin": "Ladakh (Jammu & Kashmir)",
        "nature": "Hardy, small, cold tolerant",
        "purpose": "Milk & draught",
        "lifespan": "10-12 years",
        "production": {"milk_per_day": "1-3 litres/day", "milk_fat": "5.0%"},
        "feed": {"green_fodder": "Alpine grass, hay", "dry_fodder": "Dry hay, leaves", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Exceptional cold tolerance, disease resistant", "common_diseases": ["Pneumonia", "Foot and Mouth Disease", "Internal Parasites"]}
    },
    {
        "name": "Lakhimi",
        "origin": "Assam",
        "nature": "Docile, small, adaptable",
        "purpose": "Milk & draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "2-4 litres/day", "milk_fat": "4.3%"},
        "feed": {"green_fodder": "Grass, crop residues", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good resistance in humid northeast climate", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Internal Parasites"]}
    },
    {
        "name": "Malnad Gidda",
        "origin": "Karnataka (Western Ghats)",
        "nature": "Small, docile, hardy",
        "purpose": "Milk production",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-3 litres/day", "milk_fat": "5.0%"},
        "feed": {"green_fodder": "Forest grass, coconut leaves", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent in high rainfall areas", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Internal Parasites"]}
    },
    {
        "name": "Malvi",
        "origin": "Madhya Pradesh",
        "nature": "Hardy, active, strong",
        "purpose": "Milk & draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "4-6 litres/day", "milk_fat": "4.5%"},
        "feed": {"green_fodder": "Jowar, green grass", "dry_fodder": "Wheat straw, dry grass", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Black Quarter", "Tick Fever"]}
    },
    {
        "name": "Mewati",
        "origin": "Haryana & Rajasthan",
        "nature": "Docile, calm, large",
        "purpose": "Milk & draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "5-8 litres/day", "milk_fat": "4.3%"},
        "feed": {"green_fodder": "Berseem, jowar", "dry_fodder": "Wheat straw", "concentrate": "Standard concentrate"},
        "medical": {"disease_resistance": "Good disease resistance", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Hemorrhagic Septicemia"]}
    },
    {
        "name": "Motu",
        "origin": "Odisha",
        "nature": "Hardy, small, active",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Grass, forest fodder", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good resistance in tribal terrain", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Tick Fever"]}
    },
    {
        "name": "Nari",
        "origin": "Rajasthan (Thar desert)",
        "nature": "Hardy, drought tolerant, active",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Desert grass, dry shrubs", "dry_fodder": "Minimal dry fodder", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Exceptional drought and heat resistance", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Internal Parasites"]}
    },
    {
        "name": "Nilli Ravi",
        "origin": "Punjab (Pakistan border region)",
        "nature": "Docile, large, calm",
        "purpose": "Milk production",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "8-12 litres/day", "milk_fat": "6.5%"},
        "feed": {"green_fodder": "Berseem, jowar, napier", "dry_fodder": "Wheat straw, paddy straw", "concentrate": "Oil cakes, balanced feed"},
        "medical": {"disease_resistance": "Good disease resistance", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Brucellosis"]}
    },
    {
        "name": "Nimari",
        "origin": "Madhya Pradesh",
        "nature": "Hardy, active, medium sized",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "2-4 litres/day", "milk_fat": "4.2%"},
        "feed": {"green_fodder": "Jowar, green grass", "dry_fodder": "Dry straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Black Quarter", "Hemorrhagic Septicemia"]}
    },
    {
        "name": "Ongole",
        "origin": "Andhra Pradesh",
        "nature": "Docile, massive, powerful",
        "purpose": "Draught & beef",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "3-5 litres/day", "milk_fat": "4.5%"},
        "feed": {"green_fodder": "Jowar, maize, napier", "dry_fodder": "Crop residues, paddy straw", "concentrate": "Balanced concentrate"},
        "medical": {"disease_resistance": "Excellent heat tolerance, tick resistant", "common_diseases": ["Foot and Mouth Disease", "Bloat", "Internal Parasites"]}
    },
    {
        "name": "Poda Thirupu",
        "origin": "Andhra Pradesh",
        "nature": "Hardy, active",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Grass, crop residues", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Black Quarter"]}
    },
    {
        "name": "Pulikulam",
        "origin": "Tamil Nadu",
        "nature": "Fierce, active, fast",
        "purpose": "Draught (Jallikattu breed)",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Dry grass, jowar", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent heat tolerance, disease resistant", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Hemorrhagic Septicemia"]}
    },
    {
        "name": "Punganur",
        "origin": "Andhra Pradesh",
        "nature": "Docile, small-sized, efficient",
        "purpose": "Milk production",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "3-5 litres/day", "milk_fat": "8%"},
        "feed": {"green_fodder": "Minimal, crop residues", "dry_fodder": "Paddy straw, groundnut haulms", "concentrate": "Minimal concentrate"},
        "medical": {"disease_resistance": "Low maintenance, disease resistant", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Tick Fever"]}
    },
    {
        "name": "Purnea",
        "origin": "Bihar",
        "nature": "Docile, small, hardy",
        "purpose": "Milk & draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "2-4 litres/day", "milk_fat": "4.2%"},
        "feed": {"green_fodder": "Grass, berseem", "dry_fodder": "Paddy straw, wheat straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good resistance in humid conditions", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Internal Parasites"]}
    },
    {
        "name": "Rathi",
        "origin": "Rajasthan",
        "nature": "Active, alert, hardy",
        "purpose": "Milk production",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "6-8 litres/day", "milk_fat": "4.2%"},
        "feed": {"green_fodder": "Bajra, jowar", "dry_fodder": "Dry fodder, minimal", "concentrate": "Cotton seed cake, bajra"},
        "medical": {"disease_resistance": "Drought resistant, disease tolerant", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Bloat"]}
    },
    {
        "name": "Red Kandhari",
        "origin": "Maharashtra",
        "nature": "Hardy, active, medium sized",
        "purpose": "Milk & draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "4-6 litres/day", "milk_fat": "4.5%"},
        "feed": {"green_fodder": "Jowar, green grass", "dry_fodder": "Dry straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Black Quarter", "Mastitis"]}
    },
    {
        "name": "Red Dane",
        "origin": "Denmark (exotic breed used in India)",
        "nature": "Calm, docile",
        "purpose": "Milk production",
        "lifespan": "10-12 years",
        "production": {"milk_per_day": "15-20 litres/day", "milk_fat": "4.1%"},
        "feed": {"green_fodder": "Berseem, napier, lucerne", "dry_fodder": "Wheat straw", "concentrate": "Balanced concentrate, minerals"},
        "medical": {"disease_resistance": "Moderate, needs veterinary support", "common_diseases": ["Mastitis", "Milk Fever", "Brucellosis", "Tick Fever"]}
    },
    {
        "name": "Red Sindhi",
        "origin": "Sindh region",
        "nature": "Hardy, adaptable",
        "purpose": "Milk production",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "6-10 litres/day", "milk_fat": "5%"},
        "feed": {"green_fodder": "Jowar, maize, napier", "dry_fodder": "Dry fodder, wheat straw", "concentrate": "Oil cakes, balanced feed"},
        "medical": {"disease_resistance": "Excellent disease resistance, heat tolerant", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Tick Fever"]}
    },
    {
        "name": "Sahiwal",
        "origin": "Punjab",
        "nature": "Docile, calm, heat tolerant",
        "purpose": "Milk production",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "10-16 litres/day", "milk_fat": "4.5-5%"},
        "feed": {"green_fodder": "Berseem, jowar, maize", "dry_fodder": "Wheat straw, paddy straw", "concentrate": "Oil cakes, balanced feed"},
        "medical": {"disease_resistance": "Excellent heat and disease resistance", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Tick Fever"]}
    },
    {
        "name": "Shweta Kapila",
        "origin": "Karnataka (Coastal)",
        "nature": "Docile, small, adaptable",
        "purpose": "Milk production",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "2-4 litres/day", "milk_fat": "4.5%"},
        "feed": {"green_fodder": "Grass, coconut leaves", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good resistance in coastal humid areas", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Internal Parasites"]}
    },
    {
        "name": "Surti",
        "origin": "Gujarat",
        "nature": "Calm, docile, medium sized",
        "purpose": "Milk production",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "4-6 litres/day", "milk_fat": "6%"},
        "feed": {"green_fodder": "Berseem, green grass", "dry_fodder": "Wheat straw, dry grass", "concentrate": "Oil cakes"},
        "medical": {"disease_resistance": "Good disease resistance", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Bloat"]}
    },
    {
        "name": "Tharparkar",
        "origin": "Thar Desert, Rajasthan and Gujarat",
        "nature": "Hardy, docile, drought resistant",
        "purpose": "Dual purpose (Milk and draught)",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "8-12 litres/day", "milk_fat": "4.5-5%"},
        "feed": {"green_fodder": "Jowar, bajra, guar", "dry_fodder": "Dry grass, wheat straw", "concentrate": "Groundnut cake, cotton seed cake"},
        "medical": {"disease_resistance": "Excellent heat and disease resistance", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Internal Parasites"]}
    },
    {
        "name": "Tode",
        "origin": "Rajasthan",
        "nature": "Hardy, small, drought tolerant",
        "purpose": "Draught",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Desert grass, dry shrubs", "dry_fodder": "Minimal dry fodder", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Excellent drought and heat resistance", "common_diseases": ["Foot and Mouth Disease", "Tick Fever", "Black Quarter"]}
    },
    {
        "name": "Umblachery",
        "origin": "Tamil Nadu",
        "nature": "Hardy, active, medium sized",
        "purpose": "Draught",
        "lifespan": "12-15 years",
        "production": {"milk_per_day": "1-2 litres/day", "milk_fat": "4.0%"},
        "feed": {"green_fodder": "Grass, paddy straw", "dry_fodder": "Paddy straw", "concentrate": "Minimal"},
        "medical": {"disease_resistance": "Good disease resistance, adapted to waterlogged areas", "common_diseases": ["Foot and Mouth Disease", "Hemorrhagic Septicemia", "Internal Parasites"]}
    },
    {
        "name": "Vechur",
        "origin": "Kerala (Kottayam district)",
        "nature": "Small, docile, intelligent",
        "purpose": "Milk production (dwarf breed)",
        "lifespan": "12-14 years",
        "production": {"milk_per_day": "2-4 litres/day", "milk_fat": "4.5-5.5%"},
        "feed": {"green_fodder": "Napier, guinea grass", "dry_fodder": "Paddy straw, coconut leaves", "concentrate": "Coconut cake, rice bran"},
        "medical": {"disease_resistance": "Excellent disease resistance, especially tropical diseases", "common_diseases": ["Foot and Mouth Disease", "Mastitis", "Internal Parasites"]}
    }
]

result = breeds_col.insert_many(breed_data)
print(f"Successfully added {len(result.inserted_ids)} breeds to Atlas!")

print("\nBreeds inserted:")
for breed in breeds_col.find({}, {"_id": 0, "name": 1}):
    print(f"  - {breed['name']}")

print("\nDatabase is ready!")

