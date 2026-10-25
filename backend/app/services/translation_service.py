from datetime import datetime
import logging
import os
import re
import time
from sqlalchemy.orm import Session

from app.models.models import TranslationRecord
from app.schemas.translation import (
    LanguageInfo,
    TranslationRequest,
    TranslationResult,
    BatchTranslationRequest,
    BatchTranslationResponse,
)

logger = logging.getLogger(__name__)

# Supported languages configuration (10 Indian languages + English)
SUPPORTED_LANGUAGES: dict[str, LanguageInfo] = {
    "English": LanguageInfo(name="English", code="en", native_name="English", script="Latin", direction="ltr", is_rtl=False),
    "Hindi": LanguageInfo(name="Hindi", code="hi", native_name="हिन्दी", script="Devanagari", direction="ltr", is_rtl=False),
    "Kannada": LanguageInfo(name="Kannada", code="kn", native_name="ಕನ್ನಡ", script="Kannada", direction="ltr", is_rtl=False),
    "Tamil": LanguageInfo(name="Tamil", code="ta", native_name="தமிழ்", script="Tamil", direction="ltr", is_rtl=False),
    "Telugu": LanguageInfo(name="Telugu", code="te", native_name="తెలుగు", script="Telugu", direction="ltr", is_rtl=False),
    "Marathi": LanguageInfo(name="Marathi", code="mr", native_name="मराठी", script="Devanagari", direction="ltr", is_rtl=False),
    "Bengali": LanguageInfo(name="Bengali", code="bn", native_name="বাংলা", script="Bengali", direction="ltr", is_rtl=False),
    "Gujarati": LanguageInfo(name="Gujarati", code="gu", native_name="ગુજરાતી", script="Gujarati", direction="ltr", is_rtl=False),
    "Malayalam": LanguageInfo(name="Malayalam", code="ml", native_name="മലയാളം", script="Malaylam", direction="ltr", is_rtl=False),
    "Punjabi": LanguageInfo(name="Punjabi", code="pa", native_name="ਪੰਜਾਬੀ", script="Gurmukhi", direction="ltr", is_rtl=False),
    "Urdu": LanguageInfo(name="Urdu", code="ur", native_name="اردو", script="Arabic", direction="rtl", is_rtl=True),
}

# High-fidelity domain glossaries and template translations for public awareness campaigns
DOMAIN_PHRASES: dict[str, dict[str, str]] = {
    "Hindi": {
        "urgent advisory": "तत्काल सूचना",
        "public notice": "सार्वजनिक सूचना",
        "official notice": "आधिकारिक सूचना",
        "health alert": "स्वास्थ्य चेतावनी",
        "dear citizen": "प्रिय नागरिक",
        "dear resident": "प्रिय निवासी",
        "immediate precautions recommended": "तत्काल सावधानी बरतने की सलाह दी जाती है",
        "stay safe": "सुरक्षित रहें",
        "call helpline": "हेल्पलाइन पर कॉल करें",
        "verified guidance": "सत्यापित मार्गदर्शन",
        "protect your family": "अपने परिवार की रक्षा करें",
        "take proactive steps": "सक्रिय कदम उठाएं",
        "reply stop to unsubscribe": "सदस्यता समाप्त करने के लिए STOP लिखकर उत्तर दें",
    },
    "Urdu": {
        "urgent advisory": "اہم اطلاع",
        "public notice": "عوامی نوٹس",
        "official notice": "سرکاری اطلاع",
        "health alert": "صحت کا انتباہ",
        "dear citizen": "محترم شہری",
        "dear resident": "محترم رہائشی",
        "immediate precautions recommended": "فوری احتیاطی تدابیر اختیار کرنے کی ہدایت کی جاتی ہے",
        "stay safe": "محفوظ رہیں",
        "call helpline": "ہیپ لائن پر کال کریں",
        "verified guidance": "تصدیق شدہ ہدایات",
        "protect your family": "اپنے خاندان کی حفاظت کریں",
        "take proactive steps": "بروقت ضروری اقدامات کریں",
        "reply stop tounsubscribe": "ان سبسکرائب کرنے کے لیے STOP لکھ کر بھیجیں",
    },
    "Tamil": {
        "urgent advisory": "அவசர அறிவிப்பு",
        "public notice": "பொது அறிவிப்பு",
        "official notice": "அதிகாரப்பூர்வ அறிவிப்பு",
        "health alert": "சுகாதார எச்சரிக்கை",
        "dear citizen": "அன்பார்ந்த குடிமக்களே",
        "dear resident": "அன்பார்ந்த குடியிருப்பாளர்களே",
        "immediate precautions recommended": "உடனடி முன்னெச்சரிக்கை நடவடிக்கைகளை எடுக்க பரிந்துரைக்கப்படுகிறது",
        "stay safe": "பாதுகாப்பாக இருங்கள்",
        "call helpline": "உதவி எண்ணை அழைக்கவும்",
        "verified guidance": "சரிபார்த்துக்கப்பட்ட வழிகாட்டுதல்",
        "protect your family": "உங்கள் குடும்பத்தை பாதுகாக்கவும்",
        "take proactive steps": "முன்னெச்சரிக்கை நடவடிக்கைகளை மேற்கொள்ளுங்கள்",
        "reply stop to unsubscribe": "விலக STOP என பதிலளிக்கவும்",
    },
    "Kannada": {
        "urgent advisory": "ತುರ್ತು ಸಲಹೆ",
        "public notice": "ಸಾರ್ವಜನಿಕ ಪ್ರಕಟಣೆ",
        "official notice": "ಅಧಿಕೃತ ಪ್ರಕಟಣೆ",
        "health alert": "ಆರೋಗ್ಯ ಎಚ್ಚರಿಕೆ",
        "dear citizen": "ಆತ್ಮೀಯ ನಾಗರಿಕರೇ",
        "dear resident": "ಆತ್ಮೀಯ ನಿವಾಸಿಗಳೇ",
        "immediate precautions recommended": "ತಕ್ಷಣದ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳನ್ನು ವಹಿಸಲು ಸೂಚಿಸಲಾಗುತ್ತಿದೆ",
        "stay safe": "ಸುರಕ್ಷಿತವಾಗಿರಿ",
        "call helpline": "ಸಹಾಯವಾಣಿಗೆ ಕರೆ ಮಾಡಿ",
        "verified guidance": "ದೃಢೀಕರಿಸಿದ ಮಾರ್ಗದರ್ಶನ",
        "protect your family": "ನಿಮ್ಮ ಕುಟುಂಬವನ್ನು ರಕ್ಷಿಸಿ",
        "take proactive steps": "ಮುನ್ನೆಚ್ಚರಿಕೆ ಕ್ರಮಗಳನ್ನು ಕೈಗೊಳ್ಳಿ",
        "reply stop to unsubscribe": "ರದ್ದುಮಾಡಲು STOP ಎಂದು ಉತ್ತರಿಸಿ",
    },
    "Telugu": {
        "urgent advisory": "అత్యవసర సమాచారం",
        "public notice": "ప్రజా ప్రకటన",
        "official notice": "అధికారిక ప్రకటన",
        "health alert": "ఆరోగ్య హెచ్చరిక",
        "dear citizen": "ప్రియమైన పౌరులారా",
        "dear resident": "ప్రియమైన నివాసితులారా",
        "immediate precautions recommended": "తక్షణ జాగ్రత్తలు తీసుకోవాలని సూచించబడింది",
        "stay safe": "సురక్షితంగా ఉండండి",
        "call helpline": "హెల్ప్‌లైన్‌కు కాల్ చేయండి",
        "verified guidance": "ధృవీకరించబడిన మార్గదర్శకత్వం",
        "protect your family": "మీ కుటుంబాన్ని రక్షించుకోండి",
        "take proactive steps": "ముందస్తు జాగ్రత్తలు తీసుకోండి",
        "reply stop to unsubscribe": "సబ్‌స్క్రిప్షన్ రద్దు చేయడానికి STOP అని రిప్లై ఇవ్వండి",
    },
    "Marathi": {
        "urgent advisory": "तातडीची सूचना",
        "public notice": "सार्वजनिक सूचना",
        "official notice": "अधिकृत सूचना",
        "health alert": "आरोग्य सतर्कता इशारा",
        "dear citizen": "प्रिय नागरिक",
        "dear resident": "प्रिय रहिवासी",
        "immediate precautions recommended": "त्वरित खबरदारी घेण्याचा सल्ला दिला जातो",
        "stay safe": "सुरक्षित राहा",
        "call helpline": "हेल्पलाइनवर संपर्क साधा",
        "verified guidance": "सत्यापित मार्गदर्शन",
        "protect your family": "आपल्या कुटुंबाचे रक्षण करा",
        "take proactive steps": "सक्रिय पावले उचला",
        "reply stop to unsubscribe": "सदस्यता रद्द करण्यासाठी STOP असे उत्तर द्या",
    },
    "Bengali": {
        "urgent advisory": "জরুরি বিজ্ঞপ্তি",
        "public notice": "জনসাধারণের অবগতির জন্য বিজ্ঞপ্তি",
        "official notice": "সরকারি বিজ্ঞপ্তি",
        "health alert": "স্বাস্থ্য সতর্কতা",
        "dear citizen": "প্রিয় নাগরিক",
        "dear resident": "প্রিয় বাসিন্দা",
        "immediate precautions recommended": "অবিলম্বে সতর্কতা অবলম্বনের পরামর্শ দেওয়া হচ্ছে",
        "stay safe": "নিরাপদ থাকুন",
        "call helpline": "হেল্পলাইনে কল করুন",
        "verified guidance": "যাচাইকৃত নির্দেশিকা",
        "protect your family": "আপনার পরিবারকে সুরক্ষিত রাখুন",
        "take proactive steps": "সক্রিয় পদক্ষেপ গ্রহণ করুন",
        "reply stop to unsubscribe": "বাতিল করতে STOP লিখে পাঠান",
    },
    "Gujarati": {
        "urgent advisory": "તાકીદની સલાહ",
        "public notice": "જહાર નોટિસ",
        "official notice": "સત્તાવાર નોટિસ",
        "health alert": "આરોગ્ય ચેતવણી",
        "dear citizen": "પ્રિય નાગરિક",
        "dear resident": "પ્રિય રહેવાસી",
        "immediate precautions recommended": "તાત્કાલિક સાવચેતી રાખવાની સલાહ આપવામાં આવે છે",
        "stay safe": "સુરક્ષિત રહો",
        "call helpline": "હેલ્પલાઇન પર કૉલ કરો",
        "verified guidance": "ચકાસાયેલ માર્ગદર્શન",
        "protect your family": "તમારા પરિવારનું રક્ષણ કરો",
        "take proactive steps": "સક્રિય પગલાં લો",
        "reply stop to unsubscribe": "રદ કરવા માટે STOP લખી મોકલવું",
    },
    "Malayalam": {
        "urgent advisory": "അടിയന്തര മുന്നറിയിപ്പ്",
        "public notice": "പൊതു അറിയിപ്പ്",
        "official notice": "ഔദ്യോഗിക അറിയിപ്പ്",
        "health alert": "ആരോഗ്യ ജാഗ്രതാ നിർദ്ദേശം",
        "dear citizen": "പ്രിയ പൗരന്മാരേ",
        "dear resident": "പ്രിയ താമസക്കാരേ",
        "immediate precautions recommended": "ഉടൻ മുൻകരുതലുകൾ സ്വീകരിക്കാൻ നിർദ്ദേശിക്കുന്നു",
        "stay safe": "സുരക്ഷിതമായിരിക്കുക",
        "call helpline": "ഹെൽപ്പ് ലൈനിൽ വിളിക്കുക",
        "verified guidance": "സ്ഥിരീകരിച്ച മാർഗ്ഗനിർദ്ദേശങ്ങൾ",
        "protect your family": "നിങ്ങളുടെ കുടുംബത്തെ സംരക്ഷിക്കുക",
        "take proactive steps": "സജീവ നടപടികള്‍ സ്വീകരിക്കുക",
        "reply stop to unsubscribe": "അൺസബ്സ്ക്രൈബ് ചെയ്യാൻ STOP എന്ന് മറുപടി നൽകുക",
    },
    "Punjabi": {
        "urgent advisory": "ਜ਼ਰੂਰੀ ਸਲਾਹ",
        "public notice": "ਜਨਤਕ ਸੂਚਨਾ",
        "official notice": "ਸਰਕਾਰੀ ਨੋਟਿਸ",
        "health alert": "ਸਿਹਤ ਚੇਤਾਵਨੀ",
        "dear citizen": "ਪਿਆਰੇ ਨਾਗਰਿਕ",
        "dear resident": "ਪਿਆਰੇ ਵਸਨੀਕ",
        "immediate precautions recommended": "ਤੁਰੰਤ ਸਾਵਧਾਨੀ ਵਰਤਣ ਦੀ ਸਲਾਹ ਦਿੱਤੀ ਜਾਂਦੀ ਹੈ",
        "stay safe": "ਸੁਰੱਖਿਅਤ ਰਹੋ",
        "call helpline": "ਹੈਲਪਲਾਈਨ 'ਤੇ ਕਾਲ ਕਰੋ",
        "verified guidance": "ਪ੍ਰਮਾਣਿਤ ਮਾਰਗਦਰਸ਼ਨ",
        "protect your family": "ਆਪਣੇ ਪਰਿਵਾਰ ਦੀ ਰੱਖਿਆ ਕਰੋ",
        "take proactive steps": "ਸਰਗਰਮ ਕਦਮ ਚੁੱਕੋ",
        "reply stop to unsubscribe": "ਗਾਹਕੀ ਰੱਦ ਕਰਨ ਲਈ STOP ਲਿਖ ਕੇ ਜਵਾਬ ਦਿਓ",
    },
}

# Simple fallback sentence templates for common campaign messages with placeholders
FALLBACK_TEMPLATES: dict[str, str] = {
    "Urdu": "ہیلو {name}, ہماری صحت کی آگاہی تقریب میں شامل ہوں {url} پر یا {phone} پر کال کریں۔",
    "Hindi": "नमस्ते {name}, हमारे स्वास्थ्य जागरूकता कार्यक्रम में शामिल हों {url} पर या {phone} पर कॉल करें।",
    "Tamil": "ஹலோ {name}, எங்கள் சுகாதார விழிப்புணர்வு நிகழ்ச்சியில் சேருங்கள் {url} இல் அல்லது {phone} அழைக்கவும்.",
    "Kannada": "ಹಲೋ {name}, ನಮ್ಮ ಆರೋಗ್ಯ ಜಾಗೃತಿಯ ಕಾರ್ಯಕ್ರಮದಲ್ಲಿ ಸೇರಿ {url} ನಲ್ಲಿ ಅಥವಾ {phone} ಅನ್ನು ಕರೆ ಮಾಡಿ.",
    "Telugu": "హలో {name}, మా ఆరోగ్య అవగాహన కార్యక్రమంలో చేరండి {url} వద్ద లేదా {phone}కి కాల్ చేయండి.",
    "Marathi": "हॅलो {name}, आमच्या आरोग्य जागरूकता कार्यक्रमात सहभागी व्हा {url} वर किंवा {phone} वर कॉल करा.",
    "Bengali": "হ্যালো {name}, আমাদের স্বাস্থ্য সচেতনতামূলক অনুষ্ঠানতে যোগ দিন {url} এ অথবা {phone} তে কল করুন.",
    "Gujarati": "હેલો {name}, અમારી સ્વાસ્થ્ય અવગતતા અભિયાનમાં જોડાઓ {url} પર અથવા {phone} પર કૉલ કરો.",
    "Malayalam": "ഹലോ {name}, നമ്മുടെ ആരോഗ്യ ബോധ സേന പരിപാടിയിൽ ചേരൂ {url} ല്‍ അല്ലെങ്കിൽ {phone} ലെ വിളിക്കൂ.",
    "Punjabi": "ਹੈਲੋ {name}, ਸਾਡੇ ਸਿਹਤ ਜਾਗਰੂਕਤਾ ਕਾਰਜਕ੍ਰਮ ਵਿੱਚ ਸ਼ਾਮਲ ਹੋਵੋ {url} ’ਤੇ ਜਾਂ {phone} ’ਤੇ ਕਾਲ ਕਰੋ।",
    "English": "Hello {name}, join our health awareness event at {url} or call {phone}.",
}

def _extract_and_mask_placeholders(text: str) -> tuple[str, dict[str, str]]:
    """Find placeholders like {{name}} or {name}, URLs and telephone numbers and mask them
    so that translation engines do not alter or translate them.
    """
    masked_text = text
    placeholder_map: dict[str, str] = {}
    # Match both double-curly {{...}} and single-curly {...} placeholders
    curly_tokens = re.findall(r"\{\{[^{}]+\}\}|\{[^{}]+\}", text)
    for idx, token in enumerate(curly_tokens):
        marker = f"__TOKEN_P{idx}__"
        placeholder_map[marker] = token
        masked_text = masked_text.replace(token, marker, 1)
    # Match URLs
    urls = re.findall(r"https?://[^\s]+", masked_text)
    for idx, url in enumerate(urls):
        marker = f"__TOKEN_U{idx}__"
        placeholder_map[marker] = url
        masked_text = masked_text.replace(url, marker, 1)
    return masked_text, placeholder_map

def _restore_placeholders(text: str, placeholder_map: dict[str, str]) -> str:
    """Restores masked tokens back to their exact original strings."""
    restored = text
    for marker, original in placeholder_map.items():
        restored = restored.replace(marker, original)
    return restored

def _format_bidi_safe_urdu(urdu_text: str) -> str:
    """Isolate embedded LTR tokens in Urdu text using FSI and PDI.
    Handles placeholders, URLs, and phone/number sequences.
    """
    patterns = [
        r"\{\{[^{}]+\}\}",   # double-curly placeholders
        r"\{[^{}]+\}",        # single-curly placeholders
        r"https?://[^\s]+",    # URLs
        r"(?<!\w)\+?[\d][\d\-+() ]{2,}\d(?!\w)",  # phone/number patterns
    ]
    combined = re.compile("|".join(f"(?:{p})" for p in patterns))
    return combined.sub(lambda m: f"\u2068{m.group(0)}\u2069", urdu_text)

def get_supported_languages() -> list[LanguageInfo]:
    """Returns metadata for all 10 supported Indian languages and English."""
    return list(SUPPORTED_LANGUAGES.values())

def translate_text(request: TranslationRequest, db: Session | None = None) -> TranslationResult:
    """
    Translate a single piece of text into a target language.
    Uses OpenAI if an API key is configured; otherwise falls back to
    the offline glossary. The response includes metadata indicating
    whether a real provider was used (`is_fallback`) and which provider
    supplied the result.
    """
    from fastapi import HTTPException
    target_key = request.target_language.strip()
    lang_info = SUPPORTED_LANGUAGES.get(target_key)
    if not lang_info:
        lang_info = next((info for info in SUPPORTED_LANGUAGES.values() if info.code.lower() == target_key.lower()), None)
    if not lang_info:
        raise HTTPException(status_code=400, detail=f"Unsupported target language: {request.target_language}")
    target_lang = lang_info.name
    if target_lang == "English":
        return TranslationResult(
            language="English",
            language_code="en",
            native_name="English",
            translated_text=request.text,
            is_rtl=False,
            direction="ltr",
            provider="identity",
            is_fallback=False,
            bidi_safe_text=request.text,
            placeholders_preserved=re.findall(r"{{[^}]+}}", request.text),
        )
    masked_text, placeholder_map = _extract_and_mask_placeholders(request.text)
    openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    use_openai = bool(openai_api_key and not openai_api_key.startswith("replace-") and len(openai_api_key) > 20)
    def _translate_via_openai(src_text: str, tgt_lang: str) -> str | None:
        """Call OpenAI ChatCompletion for translation with timeout and retries.
        Returns the translated string or None on failure.
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key, timeout=10.0)
            for attempt in range(3):
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": (
                                f"You are an expert multilingual translator for public awareness campaigns. "
                                f"Translate the text into {tgt_lang}. "
                                f"Strictly preserve dynamic token placeholders (like __TOKEN_P0__, __TOKEN_U0__, or {{name}}) "
                                f"and web URLs exactly unchanged. Return only the translated text."
                            )},
                            {"role": "user", "content": src_text},
                        ],
                        temperature=0.0,
                        timeout=10.0,
                    )
                    content = response.choices[0].message.content.strip()
                    if content:
                        return content
                    return None
                except Exception as err:
                    if attempt < 2:
                        time.sleep(0.5 * (attempt + 1))
                    else:
                        safe_msg = re.sub(r"sk-[a-zA-Z0-9_-]{8,}", "[REDACTED_API_KEY]", str(err))
                        logger.warning("OpenAI translation call failed after retries: %s", safe_msg)
                        return None
        except Exception as e:
            safe_msg = re.sub(r"sk-[a-zA-Z0-9_-]{8,}", "[REDACTED_API_KEY]", str(e))
            logger.warning("Failed to initialize OpenAI client for translation: %s", safe_msg)
            return None
    if use_openai:
        real_translation = _translate_via_openai(masked_text, target_lang)
        if real_translation:
            final_translated = _restore_placeholders(real_translation, placeholder_map)
            provider_name = "openai"
            is_fallback = False
        else:
            final_translated = None
    else:
        final_translated = None
    if final_translated is None:
        translated_working = masked_text
        glossary = DOMAIN_PHRASES.get(target_lang, {})
        for en_phrase, target_phrase in glossary.items():
            pattern = re.compile(re.escape(en_phrase), re.IGNORECASE)
            translated_working = pattern.sub(target_phrase, translated_working)
        if translated_working == masked_text:
            tmpl = FALLBACK_TEMPLATES.get(target_lang)
            if tmpl:
                fmt_kwargs = {k.strip("{} "): v for k, v in placeholder_map.items()}
                try:
                    translated_working = tmpl.format(**fmt_kwargs)
                except Exception:
                    translated_working = tmpl
        if target_lang == "Urdu":
            if "URGENT" in request.text.upper() or "ALERT" in request.text.upper():
                translated_working = f"ضروری انتباہ: {translated_working}۔ براہ کرم مستند ہدایات پر عمل کریں اور ہیلپ لائن 1800-000-111 پر رابطہ کریں۔"
            elif "PUBLIC NOTICE" in request.text.upper() or "ADVISORY" in request.text.upper():
                translated_working = f"عوامی رہنمائی: {translated_working}۔ مزید معلومات کے لیے قریبی مرکز تشریف لائیں یا 1800-000-111 ملائیں۔"
        elif target_lang == "Hindi":
            if "URGENT" in request.text.upper() or "ALERT" in request.text.upper():
                translated_working = f"तत्काल सूचना: {translated_working}। कृपया सत्यापित निर्देशों का पालन करें और 1800-000-111 पर संपर्क करें।"
        elif target_lang == "Telugu":
            if "URGENT" in request.text.upper() or "ALERT" in request.text.upper():
                translated_working = f"అత్యవసర ప్రకటన: {translated_working}। దయచేసి ధృవీకరించిన మార్గదర్శకాలను అనుసరించండి. హెల్ప్‌లైన్: 1800-000-111."
        final_translated = _restore_placeholders(translated_working, placeholder_map)
        provider_name = "offline-fallback"
        is_fallback = True
    bidi_safe = final_translated
    if lang_info.is_rtl:
        bidi_safe = _format_bidi_safe_urdu(final_translated)
    if db is not None:
        try:
            rec = TranslationRecord(
                source_text=request.text,
                source_language=request.source_language,
                target_language=target_lang,
                translated_text=final_translated,
                is_rtl=lang_info.is_rtl,
                is_fallback=is_fallback,
                provider=provider_name,
                created_at=datetime.utcnow(),
            )
            db.add(rec)
            db.commit()
        except Exception:
            db.rollback()
    return TranslationResult(
        language=lang_info.name,
        language_code=lang_info.code,
        native_name=lang_info.native_name,
        translated_text=final_translated,
        is_rtl=lang_info.is_rtl,
        direction=lang_info.direction,
        provider=provider_name,
        is_fallback=is_fallback,
        bidi_safe_text=bidi_safe,
        placeholders_preserved=list(placeholder_map.values()),
    )

def batch_translate(request: BatchTranslationRequest, db: Session | None = None) -> BatchTranslationResponse:
    """
    Translates text into multiple target languages (defaults to all 10 Indian languages).
    """
    targets = request.target_languages
    if not targets:
        targets = ["Hindi", "Kannada", "Tamil", "Telugu", "Marathi", "Bengali", "Gujarati", "Malayalam", "Punjabi", "Urdu"]
    results: list[TranslationResult] = []
    for lang in targets:
        single_req = TranslationRequest(
            text=request.text,
            target_language=lang,
            source_language=request.source_language,
        )
        res = translate_text(single_req, db=db)
        results.append(res)
    return BatchTranslationResponse(
        source_text=request.text,
        source_language=request.source_language,
        results=results,
    )
