import os
import sys
import json
from google import genai 
from google.genai import types
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.', '.env'))

def extract_keywords(transcript):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env")
        sys.exit(0)

    
    model = "gemini-3-flash-preview"
    client = genai.Client(api_key=api_key)


    prompt = """
    Analyze the following YouTube video transcript and identify the top 3-5 most important technical keywords or topics that would be suitable for a deep web search explanation.
    Return ONLY a JSON array of strings, e.g. ["topic1", "topic2"]. Do not add markdown or backticks.
    """



    try:
        response = client.models.generate_content(
                                                  model=model,
                                                  contents={'text': "Yotube video text transcript:/n" + f"{transcript[:50000]}... (truncated if too long)"},
                                                  config=types.GenerateContentConfig(
                                                  system_instruction=prompt,
                                                  safety_settings=[
                                                                    types.SafetySetting(
                                                                                        category='HARM_CATEGORY_HATE_SPEECH',
                                                                                        threshold='BLOCK_ONLY_HIGH',
                                                                    )
                                                                   ],
                                                  temperature=1.0,
                                                  top_p=0.95,
                                                  top_k=20,                                                                        
                                                 ),
                                                 )
        
        # basic cleanup just in case
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        return json.loads(text)
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return ["Error extracting keywords"]

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_keywords.py <transcript_json_path> <output_json_path>")
        sys.exit(0)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        transcript = data.get("transcript_text", "")
        if not transcript:
            # Maybe it's just raw text in the file?
            f.seek(0)
            transcript = f.read()

        keywords = extract_keywords(transcript)
        
        result = {
            "search_keywords": keywords
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)
        print(f"Keywords saved to {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(0)
