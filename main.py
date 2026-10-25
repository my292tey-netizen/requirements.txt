import os
import sys
import json
import base64
import re
import requests
import google.generativeai as genai

PINTEREST_TOKEN = os.getenv("PINTEREST_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
EARNKARO_EMAIL = os.getenv("EARNKARO_EMAIL")
EARNKARO_PASSWORD = os.getenv("EARNKARO_PASSWORD")

# Board details
PINTEREST_USERNAME = "my292tey"
BOARD_SLUG = "trending-fashion-finds"

def get_board_id_direct():
    board_url = f"https://www.pinterest.com/{PINTEREST_USERNAME}/{BOARD_SLUG}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(board_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            # Look for 18-digit board ID in html data
            match = re.search(r'"board_id":\s*"(\d{18})"', resp.text)
            if not match:
                match = re.search(r'"id":\s*"(\d{18})"', resp.text)
            if match:
                b_id = match.group(1)
                print(f"Board ID successfully extracted: {b_id}")
                return b_id
    except Exception as e:
        print(f"Direct scrape fallback warning: {e}")

    # Fallback to Pinterest v5 API
    url = "https://api.pinterest.com/v5/boards"
    api_headers = {"Authorization": f"Bearer {PINTEREST_TOKEN}"}
    response = requests.get(url, headers=api_headers)
    
    if response.status_code == 200:
        boards = response.json().get("items", [])
        if boards:
            print(f"Using board from API: {boards[0]['id']}")
            return boards[0]["id"]
            
    print("Pinterest board ID fetch nahi ho saka. Checking if Pinterest Business Account is active.")
    sys.exit(1)

def generate_pin_content():
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = """
    Create a trending fashion outfit recommendation for Pinterest.
    Return ONLY a valid JSON object with these keys:
    {
      "title": "Catchy title under 50 chars",
      "description": "Aesthetic outfit description with 4 trending hashtags under 300 chars",
      "image_prompt": "Fashion catalog photo of trendy outfit, clean studio lighting, realistic, high resolution"
    }
    Return raw JSON only, no markdown formatting.
    """
    response = model.generate_content(prompt)
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

def generate_image(image_prompt):
    hf_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": f"vogue fashion photography, {image_prompt}, high detail, 8k"}
    
    response = requests.post(hf_url, headers=headers, json=payload)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode("utf-8")
    else:
        print(f"HF Image error: {response.status_code} - {response.text}")
        sys.exit(1)

def create_pinterest_pin(board_id, title, description, base64_img, link="https://earnkaro.com"):
    url = "https://api.pinterest.com/v5/pins"
    headers = {
        "Authorization": f"Bearer {PINTEREST_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "board_id": board_id,
        "title": title,
        "description": description,
        "link": link,
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/jpeg",
            "data": base64_img
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        print("Success! Pin successfully created on Pinterest:", response.json().get("id"))
    else:
        print(f"Pinterest Pin creation error: {response.status_code} - {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    print("Board ID retrieve kar rahe hain...")
    board_id = get_board_id_direct()
    
    print("Gemini se content generate ho raha hai...")
    content = generate_pin_content()
    print("Title:", content["title"])
    
    print("Hugging Face se image generate ho rahi hai...")
    img_base64 = generate_image(content["image_prompt"])
    
    print("Pinterest par pin publish kar rahe hain...")
    create_pinterest_pin(board_id, content["title"], content["description"], img_base64)
