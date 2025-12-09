import os
import ast
import re
import fitz  # PyMuPDF
import openai
from PIL import Image
import base64
import io

def extract_answers_from_pdf(pdf_path, api_key=None, model="gpt-4o", num_questions=None, max_chars=30000, question_types=None):
    """
    Extracts the answer list from an answer-key PDF using OpenAI vision API.
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

    # Load PDF and convert all pages to images
    doc = fitz.open(pdf_path)
    answer_key_pages = []

    # Step 1: Identify answer key pages using vision
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Encode image to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Ask if this is an answer key page
        try:
            check = openai.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""This is page {page_num+1} of a PDF. Does this page contain an answer key?
If yes, reply with 'Yes' followed by the extracted answer key content (question numbers and answers).
If not, reply with 'No'."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                            }
                        ]
                    }
                ],
                max_tokens=1500,
                temperature=0.0
            )

            result = check.choices[0].message.content.strip()
            if result.lower().startswith("yes"):
                answer_key_pages.append(result)
        except Exception as e:
            # Continue if a page fails
            continue

    doc.close()

    if not answer_key_pages:
        raise ValueError("No answer key pages detected in the PDF.")

    # Combine all answer key content
    combined_key = "\n\n".join(answer_key_pages)

    # Step 2: Convert to structured list based on question_types
    prompt = f"""The following is an answer key extracted from a PDF:

{combined_key}

Convert this into a JSON array of exactly {num_questions} items. Each item must be an object with:
{{"type": "mcq"|"numeric"|"text", "value": ...}}

Question types in order: {question_types}

Rules:
- For MCQ (type="mcq"): value should be a single uppercase letter A/B/C/D, or null if unknown
- For Numeric (type="numeric"): value should be the numeric answer as a string (e.g., "3.14", "1/3"), or null
- For Text (type="text"): value should be the text answer in uppercase, or null

Return ONLY the JSON array, no explanations."""

    try:
        step2 = openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=2000,
            temperature=0.0
        )
        list_text = step2.choices[0].message.content.strip()
    except Exception as e:
        raise ValueError(f"Failed to convert answer key to structured format: {e}")

    # Parse the JSON/list
    start = list_text.find('[')
    end = list_text.rfind(']') + 1
    if start == -1 or end == 0:
        raise ValueError("Model did not return a JSON array.")

    list_str = list_text[start:end]

    # Try to parse
    try:
        parsed = ast.literal_eval(list_str)
    except Exception:
        # Fallback: try JSON-like replacements
        try:
            coerced = list_str.replace("true", "True").replace("false", "False").replace("null", "None")
            parsed = ast.literal_eval(coerced)
        except Exception as e:
            raise ValueError(f"Failed to parse model output as list: {e}")

    # Normalize entries to required schema
    mapping_mcq = {"A": 0, "B": 1, "C": 2, "D": 3}

    def norm_item(item, qtype):
        if isinstance(item, dict):
            itype = str(item.get("type", qtype or "mcq")).lower()
            val = item.get("value", None)
        else:
            itype = qtype
            val = item

        if itype == "mcq":
            if val is None:
                return {"type": "mcq", "value": None}
            if isinstance(val, str):
                s = val.strip().upper()
                return {"type": "mcq", "value": mapping_mcq.get(s[:1], None)}
            if isinstance(val, (list, tuple)) and val:
                first = str(val[0]).strip().upper()
                return {"type": "mcq", "value": mapping_mcq.get(first[:1], None)}
            if isinstance(val, int) and 0 <= val <= 3:
                return {"type": "mcq", "value": val}
            return {"type": "mcq", "value": None}

        if itype == "numeric":
            if val is None:
                return {"type": "numeric", "value": None}
            s = str(val).strip().replace(" ", "")
            s = re.split(r'[^0-9\-\+\.\/]', s)[0] or s
            return {"type": "numeric", "value": s if s else None}

        if itype == "text":
            if val is None:
                return {"type": "text", "value": None}
            s = str(val).strip()
            s = re.sub(r'\s+', ' ', s).upper()
            return {"type": "text", "value": s if s else None}

        return {"type": "mcq", "value": None}

    structured = []
    for i in range(num_questions):
        qtype = question_types[i] if i < len(question_types) else "mcq"
        item = parsed[i] if i < len(parsed) else None
        structured.append(norm_item(item, qtype))

    # Ensure length matches
    if len(structured) < num_questions:
        for j in range(len(structured), num_questions):
            structured.append({"type": question_types[j], "value": None})
    elif len(structured) > num_questions:
        structured = structured[:num_questions]

    return structured


# CLI for testing
if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python fetch_answers_openai.py /path/to/file.pdf [num_questions]")
    pdf = sys.argv[1]
    nq = int(sys.argv[2]) if len(sys.argv) > 2 else None
    answers = extract_answers_from_pdf(pdf, num_questions=nq, question_types=(["mcq"] * (nq or 0)))
    sys.stdout.write(json.dumps(answers, indent=2))
