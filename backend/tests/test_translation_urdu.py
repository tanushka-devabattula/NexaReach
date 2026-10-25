import pytest
from app.services.translation_service import translate_text, FALLBACK_TEMPLATES
from app.schemas.translation import TranslationRequest

@pytest.mark.parametrize(
    "input_text,expected_substring",
    [
        ("Join our health awareness event.", "ہماری صحت کی آگاہی تقریب میں شامل ہوں"),
        ("Follow verified health guidance.", "تصدیق شدہ صحت کے رہنما اصولوں کی پیروی کریں"),
        ("Call the helpline for more information.", "مزید معلومات کے لیے ہیلپ لائن پر کال کریں"),
        ("Protect your family and stay safe.", "اپنے خاندان کی حفاظت کریں اور محفوظ رہیں"),
    ],
)
def test_urdu_generic_fallback(input_text: str, expected_substring: str):
    req = TranslationRequest(
        text=input_text,
        target_language="Urdu",
        source_language="en",
    )
    result = translate_text(req, db=None)
    assert result.is_fallback is True
    # Ensure some Urdu script appears and not just the original English
    assert expected_substring in result.translated_text
    assert result.translated_text != input_text

def test_urdu_placeholder_preservation():
    input_text = "Hello {name}, join our health awareness event at https://example.com or call 1800-000-111."
    req = TranslationRequest(
        text=input_text,
        target_language="Urdu",
        source_language="en",
    )
    result = translate_text(req, db=None)
    # Placeholder {name} should remain unchanged
    assert "{name}" in result.translated_text
    # URL should remain unchanged
    assert "https://example.com" in result.translated_text
    # Phone number should remain unchanged
    assert "1800-000-111" in result.translated_text
    # The rest of the sentence should be translated via fallback template
    assert "ہماری صحت کی آگاہی تقریب میں شامل ہوں" in result.translated_text

