import os
import sys
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.', '.env'))

def synthesize_report(transcript, keywords, search_results):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env")
        sys.exit(1)

    model = "gemini-3-flash-preview"
    client = genai.Client(api_key=api_key)

    # Prepare context
    # Truncate transcript to avoid context limit issues if it's massive
    # Let's be safe but generous.
    safe_transcript = transcript[:50000] 

    prompt = f"""
    You are an expert analyst. Your goal is to write a "Deep Dive Report" based on a YouTube video and supplemental web research.

    **Instructions**
    1.  Write a comprehensive report in Markdown format.
    2.  Start with a "Executive Summary" of the video.
    3.  For each Key Topic, provide a "Deep Dive" section.
        - Combine information from the video with the "Web Search Findings".
        - Cite the sources from the web search (e.g., [Source Name]).
        - Explain *why* this matters, adding depth beyond just the video content.
    4.  Conclude with "Key Takeaways".

    **Format**
    Return ONLY the Markdown text. Do not wrap in ```markdown``` code blocks.
    """
    
    context = f"""    **Context**
    - **Key Topics**: {json.dumps(keywords)}
    - **Web Search Findings**: {json.dumps(search_results)}
    """

    system_templateA = f"{context}\nsystem_response: {safe_transcript}"

    try:
        response = client.models.generate_content(
            model=model,
            contents=system_templateA,
            config=types.GenerateContentConfig(
                system_instruction=prompt,
                                                  safety_settings=[
                                                                    types.SafetySetting(
                                                                                        category='HARM_CATEGORY_HATE_SPEECH',
                                                                                        threshold='BLOCK_ONLY_HIGH',
                                                                    )
                                                                   ],
                temperature=0.1,
                top_p=0.95,
                top_k=20,                                                                        
            ),
        )
        return response.text
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "Error generating report."

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python synthesize_report.py <context_json_path> <output_md_path>")
        sys.exit(0)
        
    input_path = sys.argv[1]
    output_path = sys.argv[2]
        
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        transcript = data.get("transcript", "")
        keywords = data.get("keywords", [])
        search_results = data.get("search_results", {})
        
        report = synthesize_report(transcript, keywords, search_results)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(0)
