import sys
import json
import os
from duckduckgo_search import DDGS
from apify_client import ApifyClient
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.', '.env'))

def search_ddg(keywords):
    results = []
    with DDGS() as ddgs:
        for keyword in keywords:
            print(f"Searching for: {keyword}...", file=sys.stderr)
            try:
                # Get top 3 result for each keyword
                search_res = list(ddgs.text(keyword, max_results=3))
                for r in search_res:
                    r['keyword_source'] = keyword
                    results.append(r)
                time.sleep(1) # sleep to avoid rate limits
            except Exception as e:
                print(f"Error searching for {keyword}: {e}", file=sys.stderr)
    return results

def search_ddg_apify(keywords):
    """Fallback search using Apify DuckDuckGo scraper (ivanvs/duckduckgo-scraper)."""
    print("Local DuckDuckGo search returned no results, trying Apify fallback...", file=sys.stderr)
    
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        raise ValueError("APIFY_API_TOKEN not found for fallback search")
    
    client = ApifyClient(api_token)
    results = []
    
    for keyword in keywords:
        print(f"Searching with Apify for: {keyword}...", file=sys.stderr)
        try:
            run_input = {
                "query": keyword,
                "maxRecords": 10
            }
        
            run = client.actor("ivanvs/duckduckgo-scraper").call(run_input=run_input)
            dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
            
            for item in dataset_items:
                # Adapt Apify output to match expected format
                results.append({
                    'title': item.get('title', ''),
                    'href': item.get('url', ''),
                    'body': item.get('description', ''),
                })
            
            time.sleep(1)
        except Exception as e:
            print(f"Apify search error for {keyword}: {e}", file=sys.stderr)
    
    return results

def main():
    if len(sys.argv) < 3:
        print("Usage: python search_references.py <analysis_json_path> [output_path]", file=sys.stderr)
        sys.exit(0)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        keywords = data.get("search_keywords", [])
        if not keywords:
            print("No keywords found to search", file=sys.stderr)
            result = data
        else:
            search_results = []
            # Try local search first
            try:
                search_results = search_ddg(keywords)
            except Exception as e:  
                print(f"Search failed: {e}", file=sys.stderr)
            # If no results, try Apify fallback
            if not search_results:
               try:
                   search_results = search_ddg_apify(keywords)
               except Exception as e:
                   print("Apify fallback also failed: except Exception as e:", file=sys.stderr)
                   search_results = []
                    
            
            # Deduplicate by URL
            seen_urls = set()
            unique_results = []
            for item in search_results:
                href = item.get('href')
                if href and href not in seen_urls:
                    unique_results.append(item)
                    seen_urls.add(href)
            
            # Limit to maximum 10 results
            result = data.copy()
            result['references'] = unique_results[:10]

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4)
            print(f"References saved to {output_path}")
        else:
            print(json.dumps(result, indent=4))

    except Exception as e:
        print(f"Error searching references: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
