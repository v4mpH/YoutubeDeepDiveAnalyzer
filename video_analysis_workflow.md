# Video Analysis Workflow

## Objective
Analyze a YouTube video to extract topics and find reference articles.

## Inputs
- YouTube Video URL

## Outputs
- Analysis Report (JSON) containing:
  - Transcription (intro)
  - Main Topics
  - Keywords
  - Reference Articles (Title, URL)
  - Final Report

## Steps
1. **Transcribe Video**
   - **Tool**: `get_transcript.py`
   - **Input**: YouTube URL
   - **Output**: Transcript text file in `.tmp/`
   - **Note**: Now uses Apify `youtube-transcript-scraper` actors.

2. **Extract Topics & Keywords**
   - **Tool**: `extract_keyword.py`
   - **Input**: Extract main topic and keyword
   - **Output**: JSON file with topics and keywords in `.tmp/`
   - **Note**: Uses LLM (Gemini) to analyze the text.

3. **Find Reference Articles**
   - **Tool**: `search_references.py`
   - **Input**: Topics/Keywords JSON
   - **Output**: JSON with reference articles in `.tmp/`.
   - **Note**: Uses local DuckDuckGo search first, falls back to Apify scraper (`ivanvs/duckduckgo-scraper`) if no results.

4. **Final sinthesize report**
  - **Tool**: `search_references.py`
  - **Input**: Topics/Keywords/Reference Article JSON files.
  - **Output**: JSON with report and Key Takeways
  - **Note**: Uses LLM (Gemini) to analyze the JSON files.
  
## Edge Cases
- Video has no transcript -> Return error.
- LLM API failure -> Retry or return error.
- No search results -> Return empty list for references.
