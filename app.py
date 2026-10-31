"""מסכם טקסטים ארוכים עם ניתוח נקודות מפתח - Streamlit + Google Gemini API."""

import json
import os
import time

import streamlit as st
from google import genai
from google.genai import errors

MODEL = "gemini-flash-latest"
MAX_CHARS = 100_000

LENGTHS = {
    "קצר": "2-3 sentences",
    "בינוני": "one paragraph of 4-6 sentences",
    "מפורט": "two to three paragraphs",
}

DEMO_SUMMARIES = {
    "קצר": "זהו סיכום לדוגמה. הטקסט המקורי נותח, והרעיונות המרכזיים שלו הוצגו בקצרה.",
    "בינוני": (
        "זהו סיכום לדוגמה שנוצר במצב הדגמה, ללא פנייה ל-API. "
        "במצב רגיל, המודל קורא את הטקסט המלא ומזקק ממנו את הרעיון המרכזי."
    ),
    "מפורט": "זהו סיכום לדוגמה שנוצר במצב הדגמה, ללא פנייה ל-API.",
}

DEMO_POINTS = [
    {"title": "הרעיון המרכזי", "detail": "הטענה הבסיסית שסביבה בנוי הטקסט כולו."},
    {"title": "הקשר ורקע", "detail": "הרקע שנדרש כדי להבין את הנושא ואת חשיבותו."},
    {"title": "טיעון עיקרי", "detail": "הנימוק החשוב ביותר שהכותב מציג לטובת עמדתו."},
    {"title": "נתונים וראיות", "detail": "העובדות, המספרים או הדוגמאות שתומכים בטיעונים."},
    {"title": "אתגרים וקשיים", "detail": "החסמים או הביקורות שהטקסט מזכיר ומתמודד איתם."},
]


def demo_summarize(num_points: int, length: str) -> dict:
    time.sleep(1.0)
    return {
        "summary": DEMO_SUMMARIES[length],
        "key_points": DEMO_POINTS[:num_points],
    }


def summarize(client: genai.Client, text: str, num_points: int, length: str) -> dict:
    prompt = f"""
Analyze the following text.
1. Provide a summary with length: {LENGTHS[length]}.
2. Extract exactly {num_points} key points, each with a short 'title' and a descriptive 'detail'.
Write the summary and details in the exact same language as the input text.

Respond ONLY with valid JSON in this format, with no markdown codeblocks:
{{"summary": "...", "key_points": [{{"title": "...", "detail": "..."}}]}}

Text:
{text}
"""
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    clean_text = response.text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]

    return json.loads(clean_text.strip())


def main() -> None:
    st.set_page_config(page_title="מסכם טקסטים", page_icon="📝")
    st.title("📝 מסכם טקסטים חכם")
    st.caption("הדביקו טקסט ארוך וקבלו סיכום וניתוח נקודות מפתח.")

    with st.sidebar:
        st.header("הגדרות")
        demo_mode = st.toggle("מצב הדגמה (ללא API Key)")
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            value=os.environ.get("GEMINI_API_KEY", ""),
            disabled=demo_mode,
        )
        num_points = st.slider("מספר נקודות מפתח", 3, 10, 5)
        length = st.select_slider("אורך הסיכום", options=list(LENGTHS), value="בינוני")

    text = st.text_area("הדביקו כאן את הטקסט", height=300)
    st.caption(f"{len(text.split()):,} מילים · {len(text):,} תווים")

    if not st.button("סכם", type="primary"):
        return

    if not demo_mode and not api_key:
        st.error("חסר Gemini API Key בסרגל הצד (או הפעילו מצב הדגמה).")
        return

    if len(text.strip()) < (1 if demo_mode else 50):
        st.warning("הטקסט קצר מדי לסיכום משמעותי.")
        return

    with st.spinner("מנתח את הטקסט..."):
        try:
            if demo_mode:
                result = demo_summarize(num_points, length)
            else:
                client = genai.Client(api_key=api_key)
                result = summarize(client, text, num_points, length)
        except errors.APIError as e:
            st.error(f"שגיאת API: {e}")
            return
        except Exception as e:
            st.error(f"שגיאה בעיבוד התוצאה: {e}")
            return

    if demo_mode:
        st.info("זוהי תוצאת הדגמה: לא נשלחה פנייה ל-API והתוכן אינו קשור לטקסט שהוזן.")

    st.subheader("סיכום")
    st.write(result["summary"])

    st.subheader("נקודות מפתח")
    for i, point in enumerate(result["key_points"], start=1):
        with st.expander(f"{i}. {point['title']}", expanded=True):
            st.write(point["detail"])


if __name__ == "__main__":
    main()