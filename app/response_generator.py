"""Response Generator for Y-Connect WhatsApp Bot

This module handles formatting responses for WhatsApp delivery, including:
- Formatting scheme information with proper structure
- Creating welcome and help messages in multiple languages
- Splitting long messages at logical boundaries
- Adding emoji and visual formatting
"""

from typing import List, Dict, Optional
from app.models import SchemeDocument, OutgoingMessage, Scheme
import re


class ResponseGenerator:
    """Generates and formats responses for WhatsApp delivery"""
    
    # Maximum characters per WhatsApp message (best practice)
    MAX_MESSAGE_LENGTH = 1600
    
    # Language-specific welcome messages
    WELCOME_MESSAGES = {
        "en": "🙏 Welcome to Y-Connect!\n\nI help you find government schemes in your language.\n\nTry asking:\n• \"Show me farmer schemes\"\n• \"Education schemes for girls\"\n• \"Senior citizen benefits\"\n\nType 'help' anytime for guidance.",
        "hi": "🙏 Y-Connect में आपका स्वागत है!\n\nमैं आपकी भाषा में सरकारी योजनाएं खोजने में मदद करता हूं।\n\nपूछने का प्रयास करें:\n• \"किसान योजनाएं दिखाएं\"\n• \"लड़कियों के लिए शिक्षा योजनाएं\"\n• \"वरिष्ठ नागरिक लाभ\"\n\nमार्गदर्शन के लिए किसी भी समय 'help' टाइप करें।",
        "ta": "🙏 Y-Connect-க்கு வரவேற்கிறோம்!\n\nஉங்கள் மொழியில் அரசு திட்டங்களைக் கண்டறிய நான் உதவுகிறேன்.\n\nகேட்க முயற்சிக்கவும்:\n• \"விவசாயி திட்டங்களைக் காட்டு\"\n• \"பெண்களுக்கான கல்வி திட்டங்கள்\"\n• \"மூத்த குடிமக்கள் நலன்கள்\"\n\nவழிகாட்டுதலுக்கு எந்த நேரத்திலும் 'help' என தட்டச்சு செய்யவும்.",
        "te": "🙏 Y-Connect కు స్వాగతం!\n\nమీ భాషలో ప్రభుత్వ పథకాలను కనుగొనడంలో నేను సహాయం చేస్తాను.\n\nఅడగడానికి ప్రయత్నించండి:\n• \"రైతు పథకాలను చూపించు\"\n• \"బాలికల కోసం విద్యా పథకాలు\"\n• \"వృద్ధ పౌరుల ప్రయోజనాలు\"\n\nమార్గదర్శకత్వం కోసం ఎప్పుడైనా 'help' టైప్ చేయండి.",
        "bn": "🙏 Y-Connect-এ স্বাগতম!\n\nআমি আপনার ভাষায় সরকারি প্রকল্প খুঁজে পেতে সাহায্য করি।\n\nজিজ্ঞাসা করার চেষ্টা করুন:\n• \"কৃষক প্রকল্প দেখান\"\n• \"মেয়েদের জন্য শিক্ষা প্রকল্প\"\n• \"প্রবীণ নাগরিক সুবিধা\"\n\nনির্দেশনার জন্য যেকোনো সময় 'help' টাইপ করুন।",
        "mr": "🙏 Y-Connect मध्ये आपले स्वागत आहे!\n\nमी तुमच्या भाषेत सरकारी योजना शोधण्यात मदत करतो.\n\nविचारण्याचा प्रयत्न करा:\n• \"शेतकरी योजना दाखवा\"\n• \"मुलींसाठी शिक्षण योजना\"\n• \"ज्येष्ठ नागरिक लाभ\"\n\nमार्गदर्शनासाठी कधीही 'help' टाइप करा.",
        "gu": "🙏 Y-Connect માં આપનું સ્વાગત છે!\n\nહું તમારી ભાષામાં સરકારી યોજનાઓ શોધવામાં મદદ કરું છું.\n\nપૂછવાનો પ્રયાસ કરો:\n• \"ખેડૂત યોજનાઓ બતાવો\"\n• \"છોકરીઓ માટે શિક્ષણ યોજનાઓ\"\n• \"વરિષ્ઠ નાગરિક લાભો\"\n\nમાર્ગદર્શન માટે કોઈપણ સમયે 'help' ટાઇપ કરો.",
        "kn": "🙏 Y-Connect ಗೆ ಸ್ವಾಗತ!\n\nನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಲು ನಾನು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ.\n\nಕೇಳಲು ಪ್ರಯತ್ನಿಸಿ:\n• \"ರೈತ ಯೋಜನೆಗಳನ್ನು ತೋರಿಸಿ\"\n• \"ಹುಡುಗಿಯರಿಗೆ ಶಿಕ್ಷಣ ಯೋಜನೆಗಳು\"\n• \"ಹಿರಿಯ ನಾಗರಿಕರ ಪ್ರಯೋಜನಗಳು\"\n\nಮಾರ್ಗದರ್ಶನಕ್ಕಾಗಿ ಯಾವಾಗ ಬೇಕಾದರೂ 'help' ಟೈಪ್ ಮಾಡಿ.",
        "ml": "🙏 Y-Connect-ലേക്ക് സ്വാഗതം!\n\nനിങ്ങളുടെ ഭാഷയിൽ സർക്കാർ പദ്ധതികൾ കണ്ടെത്താൻ ഞാൻ സഹായിക്കുന്നു.\n\nചോദിക്കാൻ ശ്രമിക്കുക:\n• \"കർഷക പദ്ധതികൾ കാണിക്കുക\"\n• \"പെൺകുട്ടികൾക്കുള്ള വിദ്യാഭ്യാസ പദ്ധതികൾ\"\n• \"മുതിർന്ന പൗരന്മാരുടെ ആനുകൂല്യങ്ങൾ\"\n\nമാർഗ്ഗനിർദ്ദേശത്തിനായി എപ്പോൾ വേണമെങ്കിലും 'help' ടൈപ്പ് ചെയ്യുക.",
        "pa": "🙏 Y-Connect ਵਿੱਚ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ!\n\nਮੈਂ ਤੁਹਾਡੀ ਭਾਸ਼ਾ ਵਿੱਚ ਸਰਕਾਰੀ ਯੋਜਨਾਵਾਂ ਲੱਭਣ ਵਿੱਚ ਮਦਦ ਕਰਦਾ ਹਾਂ.\n\nਪੁੱਛਣ ਦੀ ਕੋਸ਼ਿਸ਼ ਕਰੋ:\n• \"ਕਿਸਾਨ ਯੋਜਨਾਵਾਂ ਦਿਖਾਓ\"\n• \"ਲੜਕੀਆਂ ਲਈ ਸਿੱਖਿਆ ਯੋਜਨਾਵਾਂ\"\n• \"ਬਜ਼ੁਰਗ ਨਾਗਰਿਕ ਲਾਭ\"\n\nਮਾਰਗਦਰਸ਼ਨ ਲਈ ਕਿਸੇ ਵੀ ਸਮੇਂ 'help' ਟਾਈਪ ਕਰੋ."
    }
    
    # Language-specific help messages
    HELP_MESSAGES = {
        "en": "📚 How to use Y-Connect:\n\n1️⃣ Ask about schemes:\n   \"Show me farmer schemes\"\n   \"Education help for students\"\n\n2️⃣ Provide your details:\n   \"I am a farmer in Punjab\"\n   \"I am 65 years old\"\n\n3️⃣ Browse by category:\n   Type 'categories' to see all\n\n4️⃣ Get scheme details:\n   Reply with number from list\n\n💡 Tip: The more details you share, the better I can help!\n\nType 'categories' to browse schemes.",
        "hi": "📚 Y-Connect का उपयोग कैसे करें:\n\n1️⃣ योजनाओं के बारे में पूछें:\n   \"किसान योजनाएं दिखाएं\"\n   \"छात्रों के लिए शिक्षा सहायता\"\n\n2️⃣ अपना विवरण दें:\n   \"मैं पंजाब में किसान हूं\"\n   \"मैं 65 साल का हूं\"\n\n3️⃣ श्रेणी के अनुसार ब्राउज़ करें:\n   सभी देखने के लिए 'categories' टाइप करें\n\n4️⃣ योजना विवरण प्राप्त करें:\n   सूची से नंबर के साथ उत्तर दें\n\n💡 सुझाव: जितना अधिक विवरण आप साझा करेंगे, उतना बेहतर मैं मदद कर सकता हूं!\n\nयोजनाओं को ब्राउज़ करने के लिए 'categories' टाइप करें।",
        "ta": "📚 Y-Connect ஐ எவ்வாறு பயன்படுத்துவது:\n\n1️⃣ திட்டங்களைப் பற்றி கேளுங்கள்:\n   \"விவசாயி திட்டங்களைக் காட்டு\"\n   \"மாணவர்களுக்கு கல்வி உதவி\"\n\n2️⃣ உங்கள் விவரங்களை வழங்கவும்:\n   \"நான் பஞ்சாபில் விவசாயி\"\n   \"எனக்கு 65 வயது\"\n\n3️⃣ வகையின்படி உலாவவும்:\n   அனைத்தையும் பார்க்க 'categories' என தட்டச்சு செய்யவும்\n\n4️⃣ திட்ட விவரங்களைப் பெறவும்:\n   பட்டியலிலிருந்து எண்ணுடன் பதிலளிக்கவும்\n\n💡 குறிப்பு: நீங்கள் எவ்வளவு அதிக விவரங்களைப் பகிர்கிறீர்களோ, அவ்வளவு சிறப்பாக நான் உதவ முடியும்!\n\nதிட்டங்களை உலாவ 'categories' என தட்டச்சு செய்யவும்.",
        "te": "📚 Y-Connect ను ఎలా ఉపయోగించాలి:\n\n1️⃣ పథకాల గురించి అడగండి:\n   \"రైతు పథకాలను చూపించు\"\n   \"విద్యార్థులకు విద్యా సహాయం\"\n\n2️⃣ మీ వివరాలను అందించండి:\n   \"నేను పంజాబ్‌లో రైతును\"\n   \"నాకు 65 సంవత్సరాలు\"\n\n3️⃣ వర్గం ద్వారా బ్రౌజ్ చేయండి:\n   అన్నింటినీ చూడటానికి 'categories' టైప్ చేయండి\n\n4️⃣ పథకం వివరాలను పొందండి:\n   జాబితా నుండి సంఖ్యతో ప్రత్యుత్తరం ఇవ్వండి\n\n💡 చిట్కా: మీరు ఎంత ఎక్కువ వివరాలను పంచుకుంటారో, అంత మెరుగ్గా నేను సహాయం చేయగలను!\n\nపథకాలను బ్రౌజ్ చేయడానికి 'categories' టైప్ చేయండి.",
        "bn": "📚 Y-Connect কীভাবে ব্যবহার করবেন:\n\n1️⃣ প্রকল্প সম্পর্কে জিজ্ঞাসা করুন:\n   \"কৃষক প্রকল্প দেখান\"\n   \"শিক্ষার্থীদের জন্য শিক্ষা সহায়তা\"\n\n2️⃣ আপনার বিবরণ প্রদান করুন:\n   \"আমি পাঞ্জাবে একজন কৃষক\"\n   \"আমার বয়স 65 বছর\"\n\n3️⃣ বিভাগ অনুসারে ব্রাউজ করুন:\n   সব দেখতে 'categories' টাইপ করুন\n\n4️⃣ প্রকল্পের বিবরণ পান:\n   তালিকা থেকে নম্বর দিয়ে উত্তর দিন\n\n💡 পরামর্শ: আপনি যত বেশি বিবরণ শেয়ার করবেন, তত ভাল আমি সাহায্য করতে পারব!\n\nপ্রকল্প ব্রাউজ করতে 'categories' টাইপ করুন।",
        "mr": "📚 Y-Connect कसे वापरावे:\n\n1️⃣ योजनांबद्दल विचारा:\n   \"शेतकरी योजना दाखवा\"\n   \"विद्यार्थ्यांसाठी शिक्षण मदत\"\n\n2️⃣ तुमचे तपशील द्या:\n   \"मी पंजाबमध्ये शेतकरी आहे\"\n   \"माझे वय 65 वर्षे आहे\"\n\n3️⃣ श्रेणीनुसार ब्राउझ करा:\n   सर्व पाहण्यासाठी 'categories' टाइप करा\n\n4️⃣ योजना तपशील मिळवा:\n   यादीतील क्रमांकासह उत्तर द्या\n\n💡 टीप: तुम्ही जितके अधिक तपशील शेअर कराल, तितके चांगले मी मदत करू शकतो!\n\nयोजना ब्राउझ करण्यासाठी 'categories' टाइप करा.",
        "gu": "📚 Y-Connect નો ઉપયોગ કેવી રીતે કરવો:\n\n1️⃣ યોજનાઓ વિશે પૂછો:\n   \"ખેડૂત યોજનાઓ બતાવો\"\n   \"વિદ્યાર્થીઓ માટે શિક્ષણ સહાય\"\n\n2️⃣ તમારી વિગતો આપો:\n   \"હું પંજાબમાં ખેડૂત છું\"\n   \"મારી ઉંમર 65 વર્ષ છે\"\n\n3️⃣ શ્રેણી પ્રમાણે બ્રાઉઝ કરો:\n   બધું જોવા માટે 'categories' ટાઇપ કરો\n\n4️⃣ યોજના વિગતો મેળવો:\n   સૂચિમાંથી નંબર સાથે જવાબ આપો\n\n💡 ટિપ: તમે જેટલી વધુ વિગતો શેર કરશો, તેટલું સારું હું મદદ કરી શકું!\n\nયોજનાઓ બ્રાઉઝ કરવા માટે 'categories' ટાઇપ કરો.",
        "kn": "📚 Y-Connect ಅನ್ನು ಹೇಗೆ ಬಳಸುವುದು:\n\n1️⃣ ಯೋಜನೆಗಳ ಬಗ್ಗೆ ಕೇಳಿ:\n   \"ರೈತ ಯೋಜನೆಗಳನ್ನು ತೋರಿಸಿ\"\n   \"ವಿದ್ಯಾರ್ಥಿಗಳಿಗೆ ಶಿಕ್ಷಣ ಸಹಾಯ\"\n\n2️⃣ ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಒದಗಿಸಿ:\n   \"ನಾನು ಪಂಜಾಬ್‌ನಲ್ಲಿ ರೈತ\"\n   \"ನನಗೆ 65 ವರ್ಷ\"\n\n3️⃣ ವರ್ಗದ ಪ್ರಕಾರ ಬ್ರೌಸ್ ಮಾಡಿ:\n   ಎಲ್ಲವನ್ನೂ ನೋಡಲು 'categories' ಟೈಪ್ ಮಾಡಿ\n\n4️⃣ ಯೋಜನೆ ವಿವರಗಳನ್ನು ಪಡೆಯಿರಿ:\n   ಪಟ್ಟಿಯಿಂದ ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಉತ್ತರಿಸಿ\n\n💡 ಸಲಹೆ: ನೀವು ಹೆಚ್ಚು ವಿವರಗಳನ್ನು ಹಂಚಿಕೊಳ್ಳುತ್ತೀರಿ, ನಾನು ಉತ್ತಮವಾಗಿ ಸಹಾಯ ಮಾಡಬಹುದು!\n\nಯೋಜನೆಗಳನ್ನು ಬ್ರೌಸ್ ಮಾಡಲು 'categories' ಟೈಪ್ ಮಾಡಿ.",
        "ml": "📚 Y-Connect എങ്ങനെ ഉപയോഗിക്കാം:\n\n1️⃣ പദ്ധതികളെക്കുറിച്ച് ചോദിക്കുക:\n   \"കർഷക പദ്ധതികൾ കാണിക്കുക\"\n   \"വിദ്യാർത്ഥികൾക്ക് വിദ്യാഭ്യാസ സഹായം\"\n\n2️⃣ നിങ്ങളുടെ വിശദാംശങ്ങൾ നൽകുക:\n   \"ഞാൻ പഞ്ചാബിലെ കർഷകനാണ്\"\n   \"എനിക്ക് 65 വയസ്സ്\"\n\n3️⃣ വിഭാഗം അനുസരിച്ച് ബ്രൗസ് ചെയ്യുക:\n   എല്ലാം കാണാൻ 'categories' ടൈപ്പ് ചെയ്യുക\n\n4️⃣ പദ്ധതി വിശദാംശങ്ങൾ നേടുക:\n   പട്ടികയിൽ നിന്ന് നമ്പർ ഉപയോഗിച്ച് മറുപടി നൽകുക\n\n💡 നുറുങ്ങ്: നിങ്ങൾ എത്രയധികം വിശദാംശങ്ങൾ പങ്കിടുന്നുവോ അത്രയും നന്നായി എനിക്ക് സഹായിക്കാൻ കഴിയും!\n\nപദ്ധതികൾ ബ്രൗസ് ചെയ്യാൻ 'categories' ടൈപ്പ് ചെയ്യുക.",
        "pa": "📚 Y-Connect ਦੀ ਵਰਤੋਂ ਕਿਵੇਂ ਕਰੀਏ:\n\n1️⃣ ਯੋਜਨਾਵਾਂ ਬਾਰੇ ਪੁੱਛੋ:\n   \"ਕਿਸਾਨ ਯੋਜਨਾਵਾਂ ਦਿਖਾਓ\"\n   \"ਵਿਦਿਆਰਥੀਆਂ ਲਈ ਸਿੱਖਿਆ ਸਹਾਇਤਾ\"\n\n2️⃣ ਆਪਣੇ ਵੇਰਵੇ ਦਿਓ:\n   \"ਮੈਂ ਪੰਜਾਬ ਵਿੱਚ ਕਿਸਾਨ ਹਾਂ\"\n   \"ਮੇਰੀ ਉਮਰ 65 ਸਾਲ ਹੈ\"\n\n3️⃣ ਸ਼੍ਰੇਣੀ ਦੁਆਰਾ ਬ੍ਰਾਊਜ਼ ਕਰੋ:\n   ਸਭ ਦੇਖਣ ਲਈ 'categories' ਟਾਈਪ ਕਰੋ\n\n4️⃣ ਯੋਜਨਾ ਵੇਰਵੇ ਪ੍ਰਾਪਤ ਕਰੋ:\n   ਸੂਚੀ ਤੋਂ ਨੰਬਰ ਨਾਲ ਜਵਾਬ ਦਿਓ\n\n💡 ਸੁਝਾਅ: ਤੁਸੀਂ ਜਿੰਨੇ ਜ਼ਿਆਦਾ ਵੇਰਵੇ ਸਾਂਝੇ ਕਰੋਗੇ, ਮੈਂ ਓਨੀ ਹੀ ਬਿਹਤਰ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ!\n\nਯੋਜਨਾਵਾਂ ਬ੍ਰਾਊਜ਼ ਕਰਨ ਲਈ 'categories' ਟਾਈਪ ਕਰੋ."
    }
    
    def __init__(self):
        """Initialize the ResponseGenerator"""
        pass
    
    def create_welcome_message(self, language: str = "en") -> str:
        """
        Generate welcome message for new users
        
        Args:
            language: User's preferred language code
            
        Returns:
            Localized welcome message
        """
        return self.WELCOME_MESSAGES.get(language, self.WELCOME_MESSAGES["en"])
    
    def create_help_message(self, language: str = "en") -> str:
        """
        Generate help message with usage instructions
        
        Args:
            language: User's preferred language code
            
        Returns:
            Localized help message
        """
        return self.HELP_MESSAGES.get(language, self.HELP_MESSAGES["en"])
    
    def create_scheme_summary(
        self,
        schemes: List[SchemeDocument],
        language: str = "en"
    ) -> str:
        """
        Create summary list when multiple schemes match
        
        Args:
            schemes: List of matching scheme documents
            language: Target language for response
            
        Returns:
            Formatted summary with numbered list
        """
        if not schemes:
            return self._get_no_results_message(language)
        
        # Header based on language
        headers = {
            "en": f"Found {len(schemes)} scheme{'s' if len(schemes) > 1 else ''} for you:\n\n",
            "hi": f"आपके लिए {len(schemes)} योजना{'एं' if len(schemes) > 1 else ''} मिली:\n\n",
            "ta": f"உங்களுக்காக {len(schemes)} திட்ட{'ங்கள்' if len(schemes) > 1 else 'ம்'} கண்டறியப்பட்டது:\n\n",
            "te": f"మీ కోసం {len(schemes)} పథక{'ాలు' if len(schemes) > 1 else 'ం'} కనుగొనబడింది:\n\n",
            "bn": f"আপনার জন্য {len(schemes)} টি প্রকল্প পাওয়া গেছে:\n\n",
            "mr": f"तुमच्यासाठी {len(schemes)} योजना{'ं' if len(schemes) > 1 else ''} सापडल्या:\n\n",
            "gu": f"તમારા માટે {len(schemes)} યોજના{'ઓ' if len(schemes) > 1 else ''} મળી:\n\n",
            "kn": f"ನಿಮಗಾಗಿ {len(schemes)} ಯೋಜನೆ{'ಗಳು' if len(schemes) > 1 else ''} ಕಂಡುಬಂದಿದೆ:\n\n",
            "ml": f"നിങ്ങൾക്കായി {len(schemes)} പദ്ധതി{'കൾ' if len(schemes) > 1 else ''} കണ്ടെത്തി:\n\n",
            "pa": f"ਤੁਹਾਡੇ ਲਈ {len(schemes)} ਯੋਜਨਾ{'ਵਾਂ' if len(schemes) > 1 else ''} ਮਿਲੀਆਂ:\n\n"
        }
        
        summary = headers.get(language, headers["en"])
        
        # Add each scheme with number
        for idx, scheme_doc in enumerate(schemes[:10], 1):  # Limit to 10 schemes
            scheme = scheme_doc.scheme
            scheme_name = scheme.get_translation("scheme_name", language)
            description = scheme.get_translation("description", language)
            
            # Truncate description to one line (max 80 chars)
            short_desc = description[:80] + "..." if len(description) > 80 else description
            
            summary += f"{idx}. {scheme_name}\n   {short_desc}\n\n"
        
        # Footer based on language
        footers = {
            "en": f"Reply with number (1-{min(len(schemes), 10)}) for full details.",
            "hi": f"पूर्ण विवरण के लिए नंबर (1-{min(len(schemes), 10)}) के साथ उत्तर दें।",
            "ta": f"முழு விவரங்களுக்கு எண் (1-{min(len(schemes), 10)}) உடன் பதிலளிக்கவும்.",
            "te": f"పూర్తి వివరాల కోసం సంఖ్య (1-{min(len(schemes), 10)}) తో ప్రత్యుత్తరం ఇవ్వండి.",
            "bn": f"সম্পূর্ণ বিবরণের জন্য নম্বর (1-{min(len(schemes), 10)}) দিয়ে উত্তর দিন।",
            "mr": f"संपूर्ण तपशीलांसाठी क्रमांक (1-{min(len(schemes), 10)}) सह उत्तर द्या।",
            "gu": f"સંપૂર્ણ વિગતો માટે નંબર (1-{min(len(schemes), 10)}) સાથે જવાબ આપો.",
            "kn": f"ಸಂಪೂರ್ಣ ವಿವರಗಳಿಗಾಗಿ ಸಂಖ್ಯೆ (1-{min(len(schemes), 10)}) ನೊಂದಿಗೆ ಉತ್ತರಿಸಿ.",
            "ml": f"പൂർണ്ണ വിശദാംശങ്ങൾക്കായി നമ്പർ (1-{min(len(schemes), 10)}) ഉപയോഗിച്ച് മറുപടി നൽകുക.",
            "pa": f"ਪੂਰੇ ਵੇਰਵਿਆਂ ਲਈ ਨੰਬਰ (1-{min(len(schemes), 10)}) ਨਾਲ ਜਵਾਬ ਦਿਓ।"
        }
        
        summary += footers.get(language, footers["en"])
        
        return summary
    
    def format_response(
        self,
        generated_text: str,
        schemes: List[SchemeDocument],
        language: str = "en"
    ) -> List[str]:
        """
        Format response for WhatsApp delivery
        
        Args:
            generated_text: LLM-generated response text
            schemes: Source schemes for citations
            language: Target language
            
        Returns:
            List of WhatsApp messages (split if needed)
        """
        # If the response is already short enough, return as-is
        if len(generated_text) <= self.MAX_MESSAGE_LENGTH:
            return [generated_text]
        
        # Otherwise, split the message
        return self.split_message(generated_text)
    
    def format_scheme_details(
        self,
        scheme: Scheme,
        language: str = "en"
    ) -> str:
        """
        Format detailed scheme information
        
        Args:
            scheme: Scheme object to format
            language: Target language
            
        Returns:
            Formatted scheme details with all sections
        """
        # Get translated content
        scheme_name = scheme.get_translation("scheme_name", language)
        description = scheme.get_translation("description", language)
        benefits = scheme.get_translation("benefits", language)
        application_process = scheme.get_translation("application_process", language)
        
        # Build formatted response
        response = f"📋 {scheme_name}\n\n"
        
        # Description section
        response += f"{description}\n\n"
        
        # Eligibility section
        eligibility_headers = {
            "en": "✅ Eligibility:",
            "hi": "✅ पात्रता:",
            "ta": "✅ தகுதி:",
            "te": "✅ అర్హత:",
            "bn": "✅ যোগ্যতা:",
            "mr": "✅ पात्रता:",
            "gu": "✅ પાત્રતા:",
            "kn": "✅ ಅರ್ಹತೆ:",
            "ml": "✅ യോഗ്യത:",
            "pa": "✅ ਯੋਗਤਾ:"
        }
        response += eligibility_headers.get(language, eligibility_headers["en"]) + "\n"
        
        # Format eligibility criteria
        if scheme.eligibility_criteria:
            for key, value in scheme.eligibility_criteria.items():
                response += f"• {key}: {value}\n"
        response += "\n"
        
        # Benefits section
        benefits_headers = {
            "en": "💰 Benefits:",
            "hi": "💰 लाभ:",
            "ta": "💰 நன்மைகள்:",
            "te": "💰 ప్రయోజనాలు:",
            "bn": "💰 সুবিধা:",
            "mr": "💰 लाभ:",
            "gu": "💰 લાભો:",
            "kn": "💰 ಪ್ರಯೋಜನಗಳು:",
            "ml": "💰 ആനുകൂല്യങ്ങൾ:",
            "pa": "💰 ਲਾਭ:"
        }
        response += benefits_headers.get(language, benefits_headers["en"]) + "\n"
        response += f"{benefits}\n\n"
        
        # Application process section
        application_headers = {
            "en": "📝 How to Apply:",
            "hi": "📝 आवेदन कैसे करें:",
            "ta": "📝 எவ்வாறு விண்ணப்பிப்பது:",
            "te": "📝 ఎలా దరఖాస్తు చేయాలి:",
            "bn": "📝 কীভাবে আবেদন করবেন:",
            "mr": "📝 अर्ज कसा करावा:",
            "gu": "📝 અરજી કેવી રીતે કરવી:",
            "kn": "📝 ಹೇಗೆ ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು:",
            "ml": "📝 എങ്ങനെ അപേക്ഷിക്കാം:",
            "pa": "📝 ਅਰਜ਼ੀ ਕਿਵੇਂ ਕਰੀਏ:"
        }
        response += application_headers.get(language, application_headers["en"]) + "\n"
        response += f"{application_process}\n\n"
        
        # Official link
        response += f"🔗 {scheme.official_url}\n"
        
        # Helpline numbers
        if scheme.helpline_numbers:
            helpline_headers = {
                "en": "📞 Helpline:",
                "hi": "📞 हेल्पलाइन:",
                "ta": "📞 உதவி எண்:",
                "te": "📞 హెల్ప్‌లైన్:",
                "bn": "📞 হেল্পলাইন:",
                "mr": "📞 हेल्पलाइन:",
                "gu": "📞 હેલ્પલાઇન:",
                "kn": "📞 ಸಹಾಯವಾಣಿ:",
                "ml": "📞 ഹെൽപ്പ്‌ലൈൻ:",
                "pa": "📞 ਹੈਲਪਲਾਈਨ:"
            }
            response += helpline_headers.get(language, helpline_headers["en"]) + " "
            response += ", ".join(scheme.helpline_numbers)
        
        return response
    
    def _get_no_results_message(self, language: str = "en") -> str:
        """Get 'no results found' message in the specified language"""
        messages = {
            "en": "😔 Sorry, I couldn't find any schemes matching your query.\n\nTry:\n• Being more specific about your needs\n• Mentioning your location or occupation\n• Browsing by category (type 'categories')\n\nType 'help' for more guidance.",
            "hi": "😔 क्षमा करें, मुझे आपकी क्वेरी से मेल खाने वाली कोई योजना नहीं मिली।\n\nप्रयास करें:\n• अपनी आवश्यकताओं के बारे में अधिक विशिष्ट रहें\n• अपना स्थान या व्यवसाय बताएं\n• श्रेणी के अनुसार ब्राउज़ करें ('categories' टाइप करें)\n\nअधिक मार्गदर्शन के लिए 'help' टाइप करें।",
            "ta": "😔 மன்னிக்கவும், உங்கள் வினவலுக்கு பொருந்தும் எந்த திட்டங்களையும் என்னால் கண்டுபிடிக்க முடியவில்லை।\n\nமுயற்சிக்கவும்:\n• உங்கள் தேவைகளைப் பற்றி மேலும் குறிப்பிட்டு இருங்கள்\n• உங்கள் இடம் அல்லது தொழிலைக் குறிப்பிடுங்கள்\n• வகையின்படி உலாவவும் ('categories' என தட்டச்சு செய்யவும்)\n\nமேலும் வழிகாட்டுதலுக்கு 'help' என தட்டச்சு செய்யவும்.",
            "te": "😔 క్షమించండి, మీ ప్రశ్నకు సరిపోయే ఏ పథకాలను నేను కనుగొనలేకపోయాను।\n\nప్రయత్నించండి:\n• మీ అవసరాల గురించి మరింత నిర్దిష్టంగా ఉండండి\n• మీ స్థానం లేదా వృత్తిని పేర్కొనండి\n• వర్గం ద్వారా బ్రౌజ్ చేయండి ('categories' టైప్ చేయండి)\n\nమరింత మార్గదర్శకత్వం కోసం 'help' టైప్ చేయండి.",
            "bn": "😔 দুঃখিত, আমি আপনার প্রশ্নের সাথে মিলে এমন কোনো প্রকল্প খুঁজে পাইনি।\n\nচেষ্টা করুন:\n• আপনার প্রয়োজন সম্পর্কে আরও নির্দিষ্ট হন\n• আপনার অবস্থান বা পেশা উল্লেখ করুন\n• বিভাগ অনুসারে ব্রাউজ করুন ('categories' টাইপ করুন)\n\nআরও নির্দেশনার জন্য 'help' টাইপ করুন।",
            "mr": "😔 क्षमस्व, मला तुमच्या क्वेरीशी जुळणाऱ्या कोणत्याही योजना सापडल्या नाहीत।\n\nप्रयत्न करा:\n• तुमच्या गरजांबद्दल अधिक विशिष्ट व्हा\n• तुमचे स्थान किंवा व्यवसाय नमूद करा\n• श्रेणीनुसार ब्राउझ करा ('categories' टाइप करा)\n\nअधिक मार्गदर्शनासाठी 'help' टाइप करा।",
            "gu": "😔 માફ કરશો, હું તમારી ક્વેરી સાથે મેળ ખાતી કોઈ યોજનાઓ શોધી શક્યો નથી।\n\nપ્રયાસ કરો:\n• તમારી જરૂરિયાતો વિશે વધુ ચોક્કસ બનો\n• તમારું સ્થાન અથવા વ્યવસાય ઉલ્લેખ કરો\n• શ્રેણી પ્રમાણે બ્રાઉઝ કરો ('categories' ટાઇપ કરો)\n\nવધુ માર્ગદર્શન માટે 'help' ટાઇપ કરો.",
            "kn": "😔 ಕ್ಷಮಿಸಿ, ನಿಮ್ಮ ಪ್ರಶ್ನೆಗೆ ಹೊಂದಿಕೆಯಾಗುವ ಯಾವುದೇ ಯೋಜನೆಗಳನ್ನು ನಾನು ಕಂಡುಹಿಡಿಯಲಾಗಲಿಲ್ಲ।\n\nಪ್ರಯತ್ನಿಸಿ:\n• ನಿಮ್ಮ ಅಗತ್ಯಗಳ ಬಗ್ಗೆ ಹೆಚ್ಚು ನಿರ್ದಿಷ್ಟವಾಗಿರಿ\n• ನಿಮ್ಮ ಸ್ಥಳ ಅಥವಾ ವೃತ್ತಿಯನ್ನು ಉಲ್ಲೇಖಿಸಿ\n• ವರ್ಗದ ಪ್ರಕಾರ ಬ್ರೌಸ್ ಮಾಡಿ ('categories' ಟೈಪ್ ಮಾಡಿ)\n\nಹೆಚ್ಚಿನ ಮಾರ್ಗದರ್ಶನಕ್ಕಾಗಿ 'help' ಟೈಪ್ ಮಾಡಿ.",
            "ml": "😔 ക്ഷമിക്കണം, നിങ്ങളുടെ ചോദ്യവുമായി പൊരുത്തപ്പെടുന്ന ഒരു പദ്ധതിയും എനിക്ക് കണ്ടെത്താനായില്ല।\n\nശ്രമിക്കുക:\n• നിങ്ങളുടെ ആവശ്യങ്ങളെക്കുറിച്ച് കൂടുതൽ വ്യക്തമാകുക\n• നിങ്ങളുടെ സ്ഥലം അല്ലെങ്കിൽ തൊഴിൽ പരാമർശിക്കുക\n• വിഭാഗം അനുസരിച്ച് ബ്രൗസ് ചെയ്യുക ('categories' ടൈപ്പ് ചെയ്യുക)\n\nകൂടുതൽ മാർഗ്ഗനിർദ്ദേശത്തിനായി 'help' ടൈപ്പ് ചെയ്യുക.",
            "pa": "😔 ਮਾਫ਼ ਕਰਨਾ, ਮੈਨੂੰ ਤੁਹਾਡੀ ਪੁੱਛਗਿੱਛ ਨਾਲ ਮੇਲ ਖਾਂਦੀਆਂ ਕੋਈ ਯੋਜਨਾਵਾਂ ਨਹੀਂ ਮਿਲੀਆਂ।\n\nਕੋਸ਼ਿਸ਼ ਕਰੋ:\n• ਆਪਣੀਆਂ ਲੋੜਾਂ ਬਾਰੇ ਵਧੇਰੇ ਖਾਸ ਬਣੋ\n• ਆਪਣੀ ਸਥਿਤੀ ਜਾਂ ਪੇਸ਼ੇ ਦਾ ਜ਼ਿਕਰ ਕਰੋ\n• ਸ਼੍ਰੇਣੀ ਦੁਆਰਾ ਬ੍ਰਾਊਜ਼ ਕਰੋ ('categories' ਟਾਈਪ ਕਰੋ)\n\nਹੋਰ ਮਾਰਗਦਰਸ਼ਨ ਲਈ 'help' ਟਾਈਪ ਕਰੋ।"
        }
        return messages.get(language, messages["en"])
    
    def split_message(self, text: str) -> List[str]:
        """
        Split long messages at logical boundaries
        
        Args:
            text: Text content to split
            
        Returns:
            List of message chunks, each <= MAX_MESSAGE_LENGTH
        """
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return [text]
        
        messages = []
        remaining_text = text
        
        while remaining_text:
            if len(remaining_text) <= self.MAX_MESSAGE_LENGTH:
                messages.append(remaining_text)
                break
            
            # Find the best split point within the limit
            split_point = self._find_split_point(remaining_text, self.MAX_MESSAGE_LENGTH)
            
            # Extract the chunk
            chunk = remaining_text[:split_point].rstrip()
            messages.append(chunk)
            
            # Update remaining text
            remaining_text = remaining_text[split_point:].lstrip()
        
        return messages
    
    def _find_split_point(self, text: str, max_length: int) -> int:
        """
        Find the best logical split point within max_length
        
        Priority:
        1. Double newline (section break)
        2. Single newline
        3. Sentence end (. ! ?)
        4. Word boundary (space)
        5. Character boundary (last resort)
        
        Args:
            text: Text to find split point in
            max_length: Maximum length for the chunk
            
        Returns:
            Index where to split the text
        """
        if len(text) <= max_length:
            return len(text)
        
        # Search within the valid range
        search_text = text[:max_length]
        
        # Priority 1: Double newline (section break)
        double_newline = search_text.rfind('\n\n')
        if double_newline > max_length * 0.5:  # At least 50% through
            return double_newline + 2  # Include the newlines
        
        # Priority 2: Single newline
        single_newline = search_text.rfind('\n')
        if single_newline > max_length * 0.5:
            return single_newline + 1
        
        # Priority 3: Sentence end
        for punct in ['. ', '! ', '? ', '।', '॥']:  # Include Hindi punctuation
            sentence_end = search_text.rfind(punct)
            if sentence_end > max_length * 0.5:
                return sentence_end + len(punct)
        
        # Priority 4: Word boundary (space)
        space = search_text.rfind(' ')
        if space > max_length * 0.3:  # At least 30% through
            return space + 1
        
        # Priority 5: Character boundary (last resort)
        return max_length
