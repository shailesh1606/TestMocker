import os
import ast
import re
import fitz  # PyMuPDF
import openai

def extract_answers_from_pdf(pdf_path, api_key=None, model="gpt-4o", num_questions=None, max_chars=30000, question_types=None):
    """
    Extracts the answer list from an answer-key PDF using OpenAI chat completions.
    Returns a structured list like:
      [{"type":"mcq","value":0..3}, {"type":"numeric","value":"3.14"}, {"type":"text","value":"SODIUM"}, ...]
    - question_types: list of "mcq" | "numeric" | "text" of length num_questions (defaults to mcq for all)
    """
    if api_key:
        openai.api_key = api_key
    else:
        openai.api_key = os.getenv("OPENAI_API_KEY", "")

    if not openai.api_key:
        raise ValueError("OpenAI API key not provided (api_key param or OPENAI_API_KEY env var required).")

    # Read PDF text
    doc = fitz.open(pdf_path)
    full_text = []
    for page in doc:
        try:
            full_text.append(page.get_text("text"))
        except Exception:
            continue
    doc.close()
    text = "\n\n".join(full_text)
    if not text.strip():
        raise ValueError("No extractable text found in PDF. OCR required for scanned PDFs.")

    # Truncate to avoid token limits
    text = text[:max_chars]

    # Default question types
    if question_types is None:
        if num_questions is None:
            raise ValueError("question_types or num_questions must be provided.")
        question_types = ["mcq"] * num_questions
    else:
        if num_questions is None:
            num_questions = len(question_types)
        elif len(question_types) != num_questions:
            # Normalize length
            if len(question_types) < num_questions:
                question_types = question_types + ["mcq"] * (num_questions - len(question_types))
            else:
                question_types = question_types[:num_questions]

    # Build a strict instruction so the model returns JSON with type/value per question
    prompt = (
        "You are given text from an answer-key PDF. Extract the correct answers in order and return ONLY a JSON array.\n"
        "Each array item MUST be an object with two keys: {\"type\": \"mcq\"|\"numeric\"|\"text\", \"value\": ...}.\n"
        "- For mcq: value must be a single uppercase letter A/B/C/D (or null if unknown).\n"
        "- For numeric: value must be the numeric string as-is (support integers, decimals, fractions like 1/3). Use null if unknown.\n"
        "- For text: value must be the answer text string (uppercase preferred). Use null if unknown.\n"
        "Do NOT include any explanatory text. Return strictly a JSON array of length N.\n\n"
        "Answer-key text:\n"
        f"{text}\n\n"
        f"N = {num_questions}\n"
        f"Question types in order: {question_types}\n"
        "Return exactly N items. If you cannot determine an answer, set value to null for that item."
    )

    resp = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You extract answer keys and return strict JSON with type/value per question."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=2000
    )

    # Extract text from response
    try:
        raw = resp.choices[0].message.content.strip()
    except Exception:
        raw = str(resp)

    # Extract JSON-like list from model output
    start = raw.find('[')
    end = raw.rfind(']') + 1
    if start == -1 or end == 0:
        raise ValueError("Model did not return a JSON array.")

    list_str = raw[start:end]

    # Try to parse JSON/py-literal
    try:
        parsed = ast.literal_eval(list_str)
    except Exception:
        # Fallback: try to coerce with simple replacements (true/false/null)
        try:
            coerced = list_str.replace("true", "True").replace("false", "False").replace("null", "None")
            parsed = ast.literal_eval(coerced)
        except Exception as e:
            raise ValueError(f"Failed to parse model output as list: {e}")

    # Normalize entries to required schema and align with question_types
    mapping_mcq = {"A": 0, "B": 1, "C": 2, "D": 3}

    def norm_item(item, qtype):
        # Expect dict {"type": "...", "value": ...}; tolerate strings for mcq
        if isinstance(item, dict):
            itype = str(item.get("type", qtype or "mcq")).lower()
            val = item.get("value", None)
        else:
            # If not dict, coerce based on qtype
            itype = qtype
            val = item

        if itype == "mcq":
            if val is None:
                return {"type": "mcq", "value": None}
            if isinstance(val, str):
                s = val.strip().upper()
                return {"type": "mcq", "value": mapping_mcq.get(s[:1], None)}
            # If list like ["A"], take first
            if isinstance(val, (list, tuple)) and val:
                first = str(val[0]).strip().upper()
                return {"type": "mcq", "value": mapping_mcq.get(first[:1], None)}
            return {"type": "mcq", "value": None}

            # Numeric: keep as string, allow -, ., and fraction formats
        if itype == "numeric":
            if val is None:
                return {"type": "numeric", "value": None}
            s = str(val).strip()
            # Basic sanitize: remove spaces; keep +/- . digits and / for fractions
            s = s.replace(" ", "")
            # If model returns "5 (approx)", strip non-core part
            s = re.split(r'[^0-9\-\+\.\/]', s)[0] or s
            return {"type": "numeric", "value": s if s else None}

        if itype == "text":
            if val is None:
                return {"type": "text", "value": None}
            s = str(val).strip()
            # Normalize to uppercase for consistency
            s = re.sub(r'\s+', ' ', s).upper()
            return {"type": "text", "value": s if s else None}

        # Fallback to mcq if unknown type
        return {"type": "mcq", "value": None}

    structured = []
    for i in range(num_questions):
        qtype = question_types[i] if i < len(question_types) else "mcq"
        item = parsed[i] if i < len(parsed) else None
        structured.append(norm_item(item, qtype))

    # Ensure length matches num_questions
    if len(structured) < num_questions:
        for j in range(len(structured), num_questions):
            structured.append({"type": question_types[j], "value": None})
    elif len(structured) > num_questions:
        structured = structured[:num_questions]

    return structured


# If run as script, provide simple CLI for testing
if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python fetch_answers_openai.py /path/to/file.pdf [num_questions]")
    pdf = sys.argv[1]
    nq = int(sys.argv[2]) if len(sys.argv) > 2 else None
    answers = extract_answers_from_pdf(pdf, num_questions=nq, question_types=(["mcq"] * (nq or 0)))
    sys.stdout.write(json.dumps(answers))
