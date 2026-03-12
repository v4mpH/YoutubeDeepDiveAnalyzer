import sys
import json
import os
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from apify_client import ApifyClient
from dotenv import load_dotenv

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), '.', '.env'))

def get_transcript_apify(video_url):
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        # Fallback to check if it's set in system env
        if "APIFY_API_TOKEN" not in os.environ:
             raise ValueError("APIFY_API_TOKEN not found in environment variables.")
        api_token = os.environ["APIFY_API_TOKEN"]

    client = ApifyClient(api_token)
    
    # Prepare the Actor input
    run_input = {
        "videoUrl": video_url,
    }

    run = client.actor("pintostudio/youtube-transcript-scraper").call(run_input=run_input)
    
    # Fetch results from the dataset
    dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
    
    if not dataset_items:
        raise ValueError("No transcript found for this video via Apify.")
        
    # The output format depends on the actor.
    # Usually it returns an object with video info and transcript.
    # dtrungtin/youtube-transcript-scraper typically returns:
    # { "url": "...", "title": "...", "date": "...", "transcript": [ { "text": "...", "start": 0.0, "duration": 1.0 } ] }
    
    item = dataset_items[0]
    
    segments = []
    full_text = ""
    
    # Handle variations in output
    # Handle pinterest/youtube-transcript-scraper output structure
    # Expected structure: { "data": [ {"text": "...", "start": "...", "dur": "..."} ], ... }
    
    raw_transcript = item.get("data", [])
    if not raw_transcript:
         # Fallback to 'transcript' just in case
         raw_transcript = item.get("transcript", [])

    if isinstance(raw_transcript, str):
        full_text = raw_transcript
    elif isinstance(raw_transcript, list):
         full_text = " ".join([seg.get('text', '') for seg in raw_transcript])
         segments = raw_transcript
         
    return {
        "video_id": item.get("id", video_url), # Actor might not return ID separately
        "title": item.get("title", ""),
        "transcript_text": full_text,
        "segments": segments
    }

def get_video_id(url):
    try:
        if "youtu.be" in url:
            return url.split("/")[-1]
        
        parsed_url = urlparse(url)
        if "youtube.com" in parsed_url.netloc:
            # handle v= param
            qs = parse_qs(parsed_url.query)
            if 'v' in qs:
                return qs['v'][0]
        
        return url 
    except Exception as e:
        return None

def get_transcript_local(video_url):
    """Fallback using youtube_transcript_api locally."""
    print(f"Apify failed, falling back to local youtube_transcript_api for {video_url}...", file=sys.stderr)
    video_id = get_video_id(video_url)
    if not video_id:
        raise ValueError("Could not extract video ID for fallback.")
        
    try:
        yttf = YouTubeTranscriptApi()
        transcript_list = yttf.fetch(video_id, languages=['it', 'en'])
        
        full_text = " ".join([t['text'] for t in transcript_list])
        
        return {
            "video_id": video_id,
            "title": "Unknown (Fallback)",
            "transcript_text": full_text,
            "segments": transcript_list
        }
    except Exception as e:
        raise Exception(f"Local fallback also failed: {e}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python get_transcript.py <youtube_url> [output_path]", file=sys.stderr)
        sys.exit(1)

    video_url = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = get_transcript_apify(video_url)
        # Check if empty result from Apify (it returns structure but empty text if fails silently)
        if not result.get("transcript_text") or result.get("transcript_text") == "":
             raise ValueError("Apify returned empty transcript.")
    except Exception as e:
        print(f"Apify error: {e}", file=sys.stderr)
        try:
            result = get_transcript_local(video_url)
        except Exception as e2:
             print(f"Error getting transcript (both methods failed): {e2}", file=sys.stderr)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)
        print(f"Transcript saved to {output_path}")
    else:
        print(json.dumps(result, indent=4))

if __name__ == "__main__":
    main()
