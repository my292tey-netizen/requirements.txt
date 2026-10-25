import os
import sys
import json
import base64
import requests
import google.generativeai as genai

PINTEREST_TOKEN = os.getenv("PINTEREST_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
EARNKARO_EMAIL = os.getenv("EARNKARO_EMAIL")
EARNKARO_PASSWORD = os.getenv("EARNKARO_PASSWORD")

BOARD_NAME = "Trending Fashion Finds"

def get_board_id():
    url = "https://api.pinterest.com/v5/boards"
    headers = {"Authorization": f"Bearer {PINTEREST_TOKEN}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching boards: {response.text}")
        sys.exit(1)
        
    boards = response.json().get("items", [])
    for b in boards:
        if b.get("name", "").strip().lower() == BOARD_NAME.lower():
            print(f"Found Board ID for '{BOARD_NAME}': {b['id']}")
            return b["id"]
            
    # Agar match na mile toh pehla board use kar lein
    if boards:
        print(f"Exact match nahi mila. Using first board: {boards[0]['name']} ({boards[0]['id']})")
        return boards[0]["id"]
        
    print("Koi Pinterest board nahi mila!")
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
      "image_prompt": "Fashion editorial photo prompt of stylish streetwear or ethnic outfit, cinematic lighting, 8k resolution"
    }
    Return raw JSON only, no markdown formatting.
    """
    response = model.generate_content(prompt)
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

def generate_image(image_prompt):
    hf_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": f"vogue fashion photography, {image_prompt}, high detail, photorealistic"}
    
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
        print("Success! Pin create ho gaya:", response.json().get("id"))
    else:
        print("Pinterest Pin creation error:", response.status_code, response.text)
        sys.exit(1)

if __name__ == "__main__":
    print("Board dhoondh rahe hain...")
    board_id = get_board_id()
    
    print("Gemini se content generate kar rahe hain...")
    content = generate_pin_content()
    print("Title:", content["title"])
    
    print("Image generate ho rahi hai...")
    img_base64 = generate_image(content["image_prompt"])
    
    print("Pinterest par pin post kar rahe hain...")
    create_pinterest_pin(board_id, content["title"], content["description"], img_base64)
