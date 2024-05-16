import requests

def summarize_text(text):
    api_url = "https://api.groq.com/summarize"
    headers = {"Authorization": "Bearer YOUR_GROQ_API_KEY"}
    payload = {"text": text}
    
    response = requests.post(api_url, json=payload, headers=headers)
    if response.status_code == 200:
        summary = response.json().get("summary")
        return summary
    else:
        raise Exception("Failed to summarize text")
