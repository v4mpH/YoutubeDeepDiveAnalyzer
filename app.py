import gradio as gr
import requests
import time
import os
import json

# URL of the backend. In local dev, it's usually localhost:8000
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def analyze_video(url):
    if not url:
        yield "Please enter a valid URL.", ""
        return
    
    try:
        # Start analysis
        resp = requests.post(f"{BACKEND_URL}/analyze", json={"url": url})
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("task_id")
        
        status_text = "Processing"
        yield status_text, ""

        # Poll for results
        while True:
            time.sleep(2)
            try:
                res = requests.get(f"{BACKEND_URL}/results/{task_id}")
                res.raise_for_status()
                res_data = res.json()
                status = res_data.get("status")
                
                # Format current data
                current_report = format_results(res_data.get("data", {}), status)
                
                if status == "completed":
                    yield "Analysis Complete!", current_report
                    break
                elif status == "failed":
                    yield f"Error: {res_data.get('error')}", current_report
                    break
                else:
                    status_display = {
                        "processing": "Transcribing",
                        "transcribed": "Extracting Keywords",
                        "keywords_extracted": "Searching References",
                        "searched": "Synthesizing Report"
                    }.get(status, "Processing")
                    yield status_display, current_report
            except Exception as e:
                yield f"Polling Error: {e}", ""
                break

    except Exception as e:
        yield f"Request Error: {e}", ""

def format_results(data, status):
    if not data:
        return ""
    
    res = ""
    
    # Show report if completed
    if status == "completed":
        report_content = data.get("report", "")
        if report_content:
            # Try to extract Key Takeaways if present in the synthesized report
            takeaways = ""
            if "Key Takeaways" in report_content:
                parts = report_content.split("# Key Takeaways")
                if len(parts) > 1:
                    takeaways = "## 📌 Key Takeaways\n" + parts[1].strip()
            
            if takeaways:
                res += takeaways + "\n\n---\n\n"
            
            res += report_content
            return res

    # Fallback for partial results
    res += "# Partial Analysis Results\n\n"
    
    if "transcript_text" in data:
        res += "### 📝 Transcript (Snippet)\n"
        res += f"{data.get('transcript_text', '')[:1000]}...\n\n"
        
    if "search_keywords" in data:
        res += "### 🔍 Key Topics\n"
        res += ", ".join(data.get('search_keywords', [])) + "\n\n"
        
    if "references" in data:
        res += "### 📚 References\n"
        for r in data.get('references', [])[:3]:
            res += f"- {r.get('title')} # {r.get('href')}\n"
            
    return res

with gr.Blocks() as demo:
    gr.Markdown("# YouTube Deep Dive Analyzer (Incremental)")
    
    with gr.Row():
        url_input = gr.Textbox(label="YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
        submit_btn = gr.Button("Analyze", variant="primary")
    
    status_output = gr.Label(label="Current Step")
    result_output = gr.Markdown(label="Report")
    
    submit_btn.click(fn=analyze_video, inputs=url_input, outputs=[status_output, result_output])

if __name__ == "__main__":
    demo.queue().launch(server_name="127.0.0.1", server_port=7860, theme=gr.themes.Soft(), css=".container { max-width: 800px; margin: auto; }")
