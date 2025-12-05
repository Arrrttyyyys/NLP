# %% Minimal setup
# If needed (uncomment in a notebook):
# !pip install requests python-dotenv

import os, json, textwrap, re, time
import requests
from collections import Counter

API_KEY  = os.getenv("OPENAI_API_KEY", "cse476")
API_BASE = os.getenv("API_BASE", "http://10.4.58.53:41701/v1")  
MODEL    = os.getenv("MODEL_NAME", "bens_model")              

def call_model_chat_completions(prompt: str,
                                system: str = "You are a helpful assistant. Reply with only the final answer—no explanation.",
                                model: str = MODEL,
                                temperature: float = 0.0,
                                timeout: int = 60) -> dict:
    """
    Calls an OpenAI-style /v1/chat/completions endpoint and returns:
    { 'ok': bool, 'text': str or None, 'raw': dict or None, 'status': int, 'error': str or None, 'headers': dict }
    """
    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": 128,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        status = resp.status_code
        hdrs   = dict(resp.headers)
        if status == 200:
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"ok": True, "text": text, "raw": data, "status": status, "error": None, "headers": hdrs}
        else:
            # try best-effort to surface error text
            err_text = None
            try:
                err_text = resp.json()
            except Exception:
                err_text = resp.text
            return {"ok": False, "text": None, "raw": None, "status": status, "error": str(err_text), "headers": hdrs}
    except requests.RequestException as e:
        return {"ok": False, "text": None, "raw": None, "status": -1, "error": str(e), "headers": {}}





def route_question(question):
    q = question.lower()
    if re.search(r'\b[a-d]\)',question) or re.search(r'\bA\.\s)',question) or "option" in q:
        return "mcq"
    if any(sym in question for sym in ['+','$','-','*','/','=','^']) or re.search(r'\d',question):
        return "math"
    if len(question) > 500 or 'passage' in q or 'context' in q:
        return "rc"
    return "default"

def system_and_prompt(question:str, mode:str):
    if mode == "mcq":
        system = "You are a helpful assistant that answers multiple choice questions,Please think step by step but in the final line write 'Final Answer:<one of A,B,C,D,E>' and nothing else"
        prompt = question
    elif mode == "math":
        system = "You are a careful and expert mathematician,Please think step by step but in the final line write'Final answer: <expression>' and nothing else "
        prompt = question
    elif mode == "rc":
        system = "You are a helpful assistant that reads passages and answers questions,Please think step by step but in the final line write 'Final Answer:<short answer>' and nothing else"
        prompt = question
    else:
        system = "You are a helpful reasonsing assistant,Please think step by step but in the final line write 'Final Answer:<answer>' and nothing else"
        prompt = question
    return system, prompt

def parse_final(text:str) -> str:
    if not text:
        return "VOLCANO"
    m = re.search(r'Final Answer\s*:\s*(.+)',text, flags=re.IGNORECASE)
    if m:
        ans = m.group(1).strip()
    else:
        l = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        ans = l[-1] if l else "VOLCANO"
    if len(ans) > 200:
        ans = ans[:200]
    return ans

def self_cost_answer(question:str,mode:str,k:int =3) -> str:
    system, propmt = system_and_prompt(question,mode)
    answers = []
    for _ in range(k):
        r = call_model_chat_completions(propmt,system=system,temperature=0.7)
        text = (r.get('text') or "").strip()
        ans = parse_final(text)
        if ans:
            answers.append(ans)
    if not answers:
        return "VOLCANO"
    counts = Counter(answers)
    best, _ = counts.most_common(1)[0]
    return best


def answer_reflection(question:str,candidate:str) -> str:
    if not candidate:
        return candidate
    system = "you are the best grader and problem solver. If the answer given to you is correct, repeat the answer back. if the answer is worng, solve it step by step and output the corrected answer.in the final line write 'Final Answer:<answer>' and nothing else"
    propmt = ()






def run_agent(question_input: str) -> str:
   return "placeholder"