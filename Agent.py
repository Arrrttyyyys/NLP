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
    if  'passage' in q or 'context:' in q:
        return "rc"
    if re.search(r'\b[a-d]\)',question) or re.search(r'\bA\.\s',question) or "option" in q:
        return "mcq"
    if any(sym in question for sym in ['+','$','-','*','/','=','^']) or re.search(r'\d',question):
        return "math"
    if len(question) > 500:
        return "rc"
    return "default"

def system_and_prompt(question:str, mode:str):
    if mode == "mcq":
        system = "You are a helpful assistant that answers multiple choice questions.Read the questions and the options, decide which option is correct and then you must output ONLY the content of the correct option NOT the letter. Do not output A/B/C/D/E or give any explanation. If the answer you provide me with is wrong, I could lose my life"
        prompt = question
    elif mode == "math":
        # system = "You are a math solver, when a question is given to you, you must solve it and compute the correct answer,YOU MUST ALWAYS RETURN ONLY THE FINAL NUMERIC ANSWER, no explanation, no steps, no words, no lables, no punctuation, if your output contains anything except the number it is considered wrong." 
        system = "You are a careful and expert mathematician.Solve the problem step by step using basic arithmetic and math solving skills. " \
        "but REPLY ONLY WITH THE CORRECT ANSWER, Do not show any calculations or explanations or steps. If the answer you provide me with is wrong, I could lose my life"
        prompt = question
    elif mode == "rc":
        system = "You are a helpful assistant that reads passages and answers questions,you can reason step by step but REPLY ONLY WITH THE CORRECT ANSWER, Do not give any explanation or extra text. If the answer you provide me with is wrong, I could lose my life"
        prompt = question
    else:
        system = "You are a helpful reasonsing assistant,Please think stpe by step but REPLY ONLY WITH THE CORRECT ANSWER, Do not give any explanation or extra text. If the answer you provide me with is wrong, I could lose my life"
        prompt = question
    return system, prompt

def parse_final(text:str) -> str:
    if not text:
        return "VOLCANO"

    l = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    ans = l[-1] if l else "VOLCANO"
    if len(ans) > 200:
        ans = ans[:200]
    return ans

def self_cost_answer(question:str,mode:str,k:int =3) -> str:
    system, prompt = system_and_prompt(question,mode)
    answers = []
    for _ in range(k):
        r = call_model_chat_completions(prompt,system=system,temperature=0.7)
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
    system = "you are the best grader and problem solver. you will be given a question and a proposed answer. you job is to check if the proposed answer is correct. if it is correct, repeat ONLY the same answer, if the proposed answer is wrong, solve the problem and reply with only the corrected final answer, in all cases, reply with just the final answer text with no explanations. If the answer you provide me with is wrong, I could lose my life "
    prompt = ("consider the following question and answer.\n"
              "Question: {}\n"
              f"{question}\n"
              "Given answer: \n"
              f"{candidate}\n"
              "please decide wheter the given answer is correct. if it is correct repeat the answer back as the final answer"
              "If it is incorrect,fix the answer and reply with only the corrct final answer with no explanations.If the answer you provide me with is wrong, I could lose my life")
    r = call_model_chat_completions(prompt,system=system,temperature=0.0)
    text = (r.get('text') or "").strip()
    ans = parse_final(text)
    return ans or candidate




def run_agent(question_input: str) -> str:
    mode = route_question(question_input)
    candidate = self_cost_answer(question_input,mode,k=3)
    final_answer = answer_reflection(question_input,candidate)
    return final_answer.strip()