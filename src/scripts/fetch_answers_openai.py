import os
import ast
import re
import fitz  # PyMuPDF
import openai

def extract_answers_from_pdf(pdf_path, api_key=None, model="gpt-4o", num_questions=None, max_chars=30000):
    """
    Extracts the answer list from an answer-key PDF using OpenAI chat completions.
    Returns a list like ["A","B","C", ...] (or list entries can be lists for multi-answer questions).
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

    # Prompt the model to return only a JSON array of answers
    prompt = (
        "You are given an answer key extracted from a test paper. "
        "Extract the correct answers in order and return ONLY a JSON array. "
        "Each array item should be a single uppercase letter (A, B, C, D) or a list of such letters "
        "for multiple-correct answers. Use null for unknown. "
        "Do NOT include any explanatory text. "
        f"Here is the text:\n\n{text}\n\n"
    )
    if num_questions:
        prompt += f"Return exactly {num_questions} items in the array. If you cannot determine an answer for a question, use null."

    # Use chat completions API as requested
    resp = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an assistant that extracts answer keys and returns strict JSON arrays."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=1500
    )

    # Extract text from response
    try:
        raw = resp.choices[0].message.content.strip()
    except Exception:
        # Fallback to stringified response
        raw = str(resp)

    # Extract JSON-like list from model output
    start = raw.find('[')
    end = raw.rfind(']') + 1
    if start == -1 or end == 0:
        raise ValueError("Model did not return a JSON array.")

    list_str = raw[start:end]

    try:
        parsed = ast.literal_eval(list_str)
    except Exception as e:
        raise ValueError(f"Failed to parse model output as list: {e}")

    # Normalize entries: convert single-letter strings to uppercase letters, lists to uppercase, None -> None
    def normalize_item(item):
        if item is None:
            return None
        if isinstance(item, str):
            s = item.strip().upper()
            if len(s) == 0:
                return None
            if any(sep in s for sep in "/,;"):
                parts = [p.strip().upper() for p in re.split(r'[,/;]+', s) if p.strip()]
                return [p[0] for p in parts]
            return s[0] if s[0] in "ABCD" else s
        if isinstance(item, (list, tuple)):
            out = []
            for it in item:
                if isinstance(it, str) and it.strip():
                    out.append(it.strip().upper()[0])
            return out if out else None
        return item

    normalized = [normalize_item(x) for x in parsed]

    # If num_questions provided, adjust length: pad with None or trim
    if num_questions is not None:
        if len(normalized) < num_questions:
            normalized += [None] * (num_questions - len(normalized))
        elif len(normalized) > num_questions:
            normalized = normalized[:num_questions]

    return normalized


# If run as script, provide a simple functional interface (no prints); returns list via exit code not supported,
# so this block is only for manual testing when invoked in REPL or imported by other code.
if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python fetch_answers_openai.py /path/to/file.pdf [num_questions]")
    pdf = sys.argv[1]
    nq = int(sys.argv[2]) if len(sys.argv) > 2 else None
    answers = extract_answers_from_pdf(pdf, num_questions=nq)
    # For convenience during direct runs, write JSON to stdout
    sys.stdout.write(json.dumps(answers))
