import os
import sys
import json
import base64
import requests
import google.generativeai as genai

PINTEREST_TOKEN = os.getenv("PINTEREST_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

def get_target_board():
    url = "https://api.pinterest.com/v5/boards"
    headers = {"Authorization": f"Bearer {PINTEREST_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    print(f"Board fetch status: {response.status_code}")
    print(f"Board fetch response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        if items:
            print(f"Board mil gaya: {items[0]['name']} (ID: {items[0]['id']})")
            return items[0]["id"]
            
    # Agar boards nahi mile toh naya board create karne ki koshish
    create_url = "https://api.pinterest.com/v5/boards"
    payload = {
        "name": "Trending Fashion Finds",
        "description": "Daily curated aesthetic fashion looks",
        "privacy": "PUBLIC"
    }
    create_resp = requests.post(create_url, headers=headers, json=payload)
    print(f"Board create status: {create_resp.status_code}")
    print(f"Board create response: {create_resp.text}")
    
    if create_resp.status_code in [200, 201]:
        b_id = create_resp.json().get("id")
        return b_id
        
    sys.exit(1)

def generate_pin_content():
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = """
    Create a trending fashion outfit recommendation for Pinterest.
    Return ONLY a valid JSON object:
    {
      "title": "Catchy title under 50 chars",
      "description": "Aesthetic outfit description with 4 hashtags under 300 chars",
      "image_prompt": "Editorial fashion model wearing trendy chic clothing, daylight, aesthetic, 8k"
    }
    Return raw JSON only, no markdown.
    """
    res = model.generate_content(prompt)
    clean_text = res.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)

def generate_image(prompt):
    hf_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": prompt}
    res = requests.post(hf_url, headers=headers, json=payload)
    if res.status_code == 200:
        return base64.b64encode(res.content).decode("utf-8")
    print(f"HF Error: {res.status_code} - {res.text}")
    sys.exit(1)

def create_pin(board_id, title, desc, img_b64):
    url = "https://api.pinterest.com/v5/pins"
    headers = {
        "Authorization": f"Bearer {PINTEREST_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "board_id": board_id,
        "title": title,
        "description": desc,
        "link": "https://earnkaro.com",
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/jpeg",
            "data": img_b64
        }
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code in [200, 201]:
        print("Success! Pinterest Pin Published:", res.json().get("id"))
    else:
        print(f"Pin Creation Error: {res.status_code} - {res.text}")
        sys.exit(1)

if __name__ == "__main__":
    b_id = get_target_board()
    content = generate_pin_content()
    img_data = generate_image(content["image_prompt"])
    create_pin(b_id, content["title"], content["description"], img_data)
