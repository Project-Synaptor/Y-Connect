"""Query Processor component for Y-Connect WhatsApp Bot

Processes user queries to extract intent, entities, and context.
Handles ambiguity detection and generates clarification questions.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from app.models import ProcessedQuery, IntentType, UserSession, SchemeCategory

logger = logging.getLogger(__name__)


class QueryProcessor:
    """
    Processes user queries to extract structured information.
    
    Extracts:
    - Intent (search_schemes, get_details, help, feedback, category_browse)
    - Entities (age, location, occupation, income, category, gender)
    - Ambiguity detection
    - Conversation context
    """
    
    # Intent keywords mapping
    INTENT_KEYWORDS = {
        IntentType.HELP: [
            "help", "मदद", "உதவி", "సహాయం", "সাহায্য", "मदत", "મદદ", "ಸಹಾಯ", "സഹായം", "ਮਦਦ",
            "how to use", "guide", "instructions"
        ],
        IntentType.FEEDBACK: [
            "feedback", "report", "wrong", "incorrect", "issue", "problem",
            "फीडबैक", "गलत", "தவறு", "తప్పు", "ভুল", "चूक", "ખોટું", "ತಪ್ಪು", "തെറ്റ്", "ਗਲਤ"
        ],
        IntentType.GET_DETAILS: [
            "details", "more info", "tell me more", "explain",
            "विवरण", "விவரங்கள்", "వివరాలు", "বিস্তারিত", "तपशील", "વિગતો", "ವಿವರಗಳು", "വിശദാംശങ്ങൾ", "ਵੇਰਵੇ"
        ],
        IntentType.CATEGORY_BROWSE: [
            "show", "list", "browse", "categories", "menu",
            "दिखाओ", "காட்டு", "చూపించు", "দেখাও", "दाखवा", "બતાવો", "ತೋರಿಸು", "കാണിക്കുക", "ਦਿਖਾਓ"
        ]
    }
    
    # Scheme categories keywords
    CATEGORY_KEYWORDS = {
        SchemeCategory.AGRICULTURE: [
            "farm", "farmer", "agriculture", "crop", "किसान", "खेती", "விவசாயம்", "రైతు", "কৃষক", "शेतकरी", "ખેડૂત", "ರೈತ", "കർഷകൻ", "ਕਿਸਾਨ"
        ],
        SchemeCategory.EDUCATION: [
            "education", "student", "school", "college", "scholarship", "शिक्षा", "छात्र", "கல்வி", "విద్య", "শিক্ষা", "शिक्षण", "શિક્ષણ", "ಶಿಕ್ಷಣ", "വിദ്യാഭ്യാസം", "ਸਿੱਖਿਆ"
        ],
        SchemeCategory.HEALTH: [
            "health", "medical", "hospital", "doctor", "स्वास्थ्य", "चिकित्सा", "சுகாதாரம்", "ఆరోగ్యం", "স্বাস্থ্য", "आरोग्य", "આરોગ્ય", "ಆರೋಗ್ಯ", "ആരോഗ്യം", "ਸਿਹਤ"
        ],
        SchemeCategory.HOUSING: [
            "house", "housing", "home", "shelter", "घर", "आवास", "வீடு", "గృహం", "বাড়ি", "घर", "ઘર", "ಮನೆ", "വീട്", "ਘਰ"
        ],
        SchemeCategory.WOMEN: [
            "women", "girl", "female", "महिला", "लड़की", "பெண்", "మహిళ", "মহিলা", "महिला", "સ્ત્રી", "ಮಹಿಳೆ", "സ്ത്രീ", "ਔਰਤ"
        ],
        SchemeCategory.SENIOR_CITIZENS: [
            "senior", "elderly", "old age", "pension", "वरिष्ठ", "बुजुर्ग", "முதியவர்", "వృద్ధులు", "বয়স্ক", "ज्येष्ठ", "વરિષ્ઠ", "ಹಿರಿಯ", "മുതിർന്ന", "ਬਜ਼ੁਰਗ"
        ],
        SchemeCategory.EMPLOYMENT: [
            "job", "employment", "work", "unemployment", "रोजगार", "नौकरी", "வேலை", "ఉద్యోగం", "চাকরি", "रोजगार", "રોજગાર", "ಉದ್ಯೋಗ", "തൊഴിൽ", "ਨੌਕਰੀ"
        ],
        SchemeCategory.FINANCIAL_INCLUSION: [
            "loan", "bank", "finance", "credit", "ऋण", "बैंक", "கடன்", "రుణం", "ঋণ", "कर्ज", "લોન", "ಸಾಲ", "വായ്പ", "ਕਰਜ਼ਾ"
        ],
        SchemeCategory.SOCIAL_WELFARE: [
            "welfare", "social", "benefit", "कल्याण", "सामाजिक", "நலன்", "సంక్షేమం", "কল্যাণ", "कल्याण", "કલ્યાણ", "ಕಲ್ಯಾಣ", "ക്ഷേമം", "ਭਲਾਈ"
        ],
        SchemeCategory.SKILL_DEVELOPMENT: [
            "skill", "training", "course", "कौशल", "प्रशिक्षण", "திறன்", "నైపుణ్యం", "দক্ষতা", "कौशल्य", "કૌશલ્ય", "ಕೌಶಲ್ಯ", "വൈദഗ്ദ്ധ്യം", "ਹੁਨਰ"
        ]
    }
    
    # Indian states mapping
    INDIAN_STATES = {
        "andhra pradesh": "AP", "arunachal pradesh": "AR", "assam": "AS", "bihar": "BR",
        "chhattisgarh": "CG", "goa": "GA", "gujarat": "GJ", "haryana": "HR",
        "himachal pradesh": "HP", "jharkhand": "JH", "karnataka": "KA", "kerala": "KL",
        "madhya pradesh": "MP", "maharashtra": "MH", "manipur": "MN", "meghalaya": "ML",
        "mizoram": "MZ", "nagaland": "NL", "odisha": "OD", "punjab": "PB",
        "rajasthan": "RJ", "sikkim": "SK", "tamil nadu": "TN", "telangana": "TS",
        "tripura": "TR", "uttar pradesh": "UP", "uttarakhand": "UK", "west bengal": "WB",
        "delhi": "DL", "jammu and kashmir": "JK", "ladakh": "LA"
    }
    
    # Occupation keywords
    OCCUPATION_KEYWORDS = {
        "farmer": ["farmer", "agriculture", "किसान", "விவசாயி", "రైతు", "কৃষক", "शेतकरी", "ખેડૂત", "ರೈತ", "കർഷകൻ", "ਕਿਸਾਨ"],
        "student": ["student", "छात्र", "மாணவர்", "విద్యార్థి", "ছাত্র", "विद्यार्थी", "વિદ્યાર્થી", "ವಿದ್ಯಾರ್ಥಿ", "വിദ്യാർത്ഥി", "ਵਿਦਿਆਰਥੀ"],
        "entrepreneur": ["entrepreneur", "business", "उद्यमी", "தொழிலதிபர்", "వ్యాపారి", "উদ্যোক্তা", "उद्योजक", "ઉદ્યોગસાહસિક", "ಉದ್ಯಮಿ", "സംരംഭകൻ", "ਉੱਦਮੀ"],
        "unemployed": ["unemployed", "jobless", "बेरोजगार", "வேலையில்லாத", "నిరుద్యోగి", "বেকার", "बेरोजगार", "બેરોજગાર", "ನಿರುದ್ಯೋಗಿ", "തൊഴിലില്ലാത്ത", "ਬੇਰੁਜ਼ਗਾਰ"],
        "worker": ["worker", "labour", "मजदूर", "தொழிலாளி", "కార్మికుడు", "শ্রমিক", "कामगार", "કામદાર", "ಕಾರ್ಮಿಕ", "തൊഴിലാളി", "ਮਜ਼ਦੂਰ"]
    }
    
    # Gender keywords
    GENDER_KEYWORDS = {
        "male": ["male", "man", "boy", "men", "पुरुष", "ஆண்", "పురుషుడు", "পুরুষ", "पुरुष", "પુરુષ", "ಪುರುಷ", "പുരുഷൻ", "ਮਰਦ"],
        "female": ["female", "woman", "girl", "women", "महिला", "பெண்", "స్త్రీ", "মহিলা", "स्त्री", "સ્ત્રી", "ಮಹಿಳೆ", "സ്ത്രീ", "ਔਰਤ"]
    }
    
    def __init__(self):
        """Initialize QueryProcessor"""
        logger.info("QueryProcessor initialized")
    
    def process_query(self, text: str, session: UserSession) -> ProcessedQuery:
        """
        Process user query and extract structured information.
        
        Args:
            text: User's message text
            session: Current user session with context
            
        Returns:
            ProcessedQuery with intent, entities, and context
        """
        text_lower = text.lower().strip()
        
        # Detect intent
        intent = self._detect_intent(text_lower)
        
        # Extract entities
        entities = self.extract_entities(text, session.language)
        
        # Merge with session context (entities from previous messages)
        merged_entities = {**session.user_context, **entities}
        
        # Detect ambiguity and generate clarification questions
        needs_clarification, clarification_questions = self._detect_ambiguity(
            intent, merged_entities, text_lower
        )
        
        processed_query = ProcessedQuery(
            original_text=text,
            language=session.language,
            intent=intent,
            entities=merged_entities,
            needs_clarification=needs_clarification,
            clarification_questions=clarification_questions
        )
        
        logger.info(
            f"Processed query: intent={intent}, entities={list(merged_entities.keys())}, "
            f"needs_clarification={needs_clarification}"
        )
        
        return processed_query
    
    def extract_entities(self, text: str, language: str) -> Dict[str, Any]:
        """
        Extract entities like age, location, occupation, income, category, gender.
        
        Args:
            text: User's message text
            language: Detected language code
            
        Returns:
            Dictionary of extracted entities
        """
        entities: Dict[str, Any] = {}
        text_lower = text.lower()
        
        # Extract age
        age = self._extract_age(text_lower)
        if age is not None:
            entities["age"] = age
        
        # Extract location (state)
        location = self._extract_location(text_lower)
        if location:
            entities["location"] = location
        
        # Extract occupation
        occupation = self._extract_occupation(text_lower)
        if occupation:
            entities["occupation"] = occupation
        
        # Extract income
        income = self._extract_income(text_lower)
        if income:
            entities["income"] = income
        
        # Extract scheme category
        category = self._extract_category(text_lower)
        if category:
            entities["category"] = category
        
        # Extract gender
        gender = self._extract_gender(text_lower)
        if gender:
            entities["gender"] = gender
        
        logger.debug(f"Extracted entities: {entities}")
        return entities
    
    def _detect_intent(self, text_lower: str) -> IntentType:
        """Detect user intent from query text"""
        # Check for help intent
        for keyword in self.INTENT_KEYWORDS[IntentType.HELP]:
            if keyword.lower() in text_lower:
                return IntentType.HELP
        
        # Check for feedback intent
        for keyword in self.INTENT_KEYWORDS[IntentType.FEEDBACK]:
            if keyword.lower() in text_lower:
                return IntentType.FEEDBACK
        
        # Check for get details intent (usually with numbers like "details 2" or "tell me more")
        for keyword in self.INTENT_KEYWORDS[IntentType.GET_DETAILS]:
            if keyword.lower() in text_lower:
                return IntentType.GET_DETAILS
        
        # Check for category browse intent
        for keyword in self.INTENT_KEYWORDS[IntentType.CATEGORY_BROWSE]:
            if keyword.lower() in text_lower:
                return IntentType.CATEGORY_BROWSE
        
        # Default to search schemes
        return IntentType.SEARCH_SCHEMES
    
    def _extract_age(self, text_lower: str) -> Optional[int]:
        """Extract age from text using regex"""
        # Pattern: "age 25", "25 years old", "I am 30", "My age is 25", etc.
        patterns = [
            r'age\s+is\s+(\d+)',
            r'my\s+age\s+is\s+(\d+)',
            r'age\s+(\d+)',
            r'(\d+)\s+years?\s+old',
            r'i\s+am\s+(\d+)',
            r'मैं\s+(\d+)',
            r'நான்\s+(\d+)',
            r'నేను\s+(\d+)',
            r'আমি\s+(\d+)',
            r'मी\s+(\d+)',
            r'હું\s+(\d+)',
            r'ನಾನು\s+(\d+)',
            r'ഞാൻ\s+(\d+)',
            r'ਮੈਂ\s+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                age = int(match.group(1))
                if 0 < age < 120:  # Reasonable age range
                    return age
        
        return None
    
    def _extract_location(self, text_lower: str) -> Optional[str]:
        """Extract location (Indian state) from text"""
        # Check for state names
        for state_name, state_code in self.INDIAN_STATES.items():
            if state_name in text_lower:
                return state_code
        
        # Check for "all india" or similar
        if any(phrase in text_lower for phrase in ["all india", "anywhere", "any state", "पूरे भारत", "எல்லா இந்தியா"]):
            return "ALL"
        
        return None
    
    def _extract_occupation(self, text_lower: str) -> Optional[str]:
        """Extract occupation from text"""
        for occupation, keywords in self.OCCUPATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return occupation
        
        return None
    
    def _extract_income(self, text_lower: str) -> Optional[str]:
        """Extract income information from text"""
        # Check for BPL (Below Poverty Line)
        if any(phrase in text_lower for phrase in ["bpl", "below poverty", "गरीबी रेखा", "வறுமை"]):
            return "BPL"
        
        # Check for APL (Above Poverty Line)
        if any(phrase in text_lower for phrase in ["apl", "above poverty"]):
            return "APL"
        
        # Extract income ranges (in lakhs or thousands)
        income_patterns = [
            r'(\d+)\s*lakh',
            r'(\d+)\s*thousand',
            r'income\s+(\d+)',
            r'earn\s+(\d+)',
            r'आय\s+(\d+)',
            r'வருமானம்\s+(\d+)'
        ]
        
        for pattern in income_patterns:
            match = re.search(pattern, text_lower)
            if match:
                amount = match.group(1)
                if "lakh" in text_lower:
                    return f"{amount} lakh"
                elif "thousand" in text_lower:
                    return f"{amount} thousand"
                else:
                    return amount
        
        return None
    
    def _extract_category(self, text_lower: str) -> Optional[str]:
        """Extract scheme category from text"""
        matched_categories = []
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matched_categories.append(category.value)
                    break
        
        # Return first matched category (ambiguity handled separately)
        return matched_categories[0] if matched_categories else None
    
    def _extract_gender(self, text_lower: str) -> Optional[str]:
        """Extract gender from text"""
        # Check for exact word matches to avoid false positives
        # Use word boundaries to match whole words
        for gender, keywords in self.GENDER_KEYWORDS.items():
            for keyword in keywords:
                # Use word boundary regex for better matching
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    return gender
        
        return None
    
    def _detect_ambiguity(
        self, intent: IntentType, entities: Dict[str, Any], text_lower: str
    ) -> tuple[bool, List[str]]:
        """
        Detect if query is ambiguous and generate clarification questions.
        
        Returns:
            Tuple of (needs_clarification, clarification_questions)
        """
        clarification_questions = []
        
        # Only check ambiguity for search_schemes intent
        if intent != IntentType.SEARCH_SCHEMES:
            return False, []
        
        # Check for multiple matching categories
        matched_categories = []
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matched_categories.append(category.value)
                    break
        
        if len(matched_categories) > 1:
            clarification_questions.append(
                f"I found schemes in multiple categories: {', '.join(matched_categories)}. "
                "Which category are you most interested in?"
            )
        
        # Check for missing critical information
        # If no category and no occupation specified, ask for more info
        if "category" not in entities and "occupation" not in entities:
            clarification_questions.append(
                "Could you tell me more about what type of scheme you're looking for? "
                "For example: education, health, agriculture, employment, etc."
            )
        
        needs_clarification = len(clarification_questions) > 0
        return needs_clarification, clarification_questions

