import subprocess
import os
import uuid
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


app = FastAPI()

class VideoRequest(BaseModel):
    url: str

class AnalysisResponse(BaseModel):
    task_id: str
    status: str
    message: str

# Store results in memory for simplicity (in production use DB)
results_store = {}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_video(request: VideoRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    results_store[task_id] = {"status": "processing", "data": None}
    
    background_tasks.add_task(run_analysis_pipeline, request.url, task_id)
    
    return {"task_id": task_id, "status": "processing", "message": "Analysis started"}

@app.get("/results/{task_id}")
async def get_results(task_id: str):
    if task_id not in results_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return results_store[task_id]

@app.get("/export/{task_id}")
async def export_report(task_id: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(base_dir, '.tmp', f"report_{task_id}.md")
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report file not found")
        
    return FileResponse(
        path=report_path,
        filename=f"report_{task_id}.md",
        media_type="text/markdown"
    )

def run_analysis_pipeline(url: str, task_id: str):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tmp_dir = os.path.join(base_dir, '.tmp')
        
        # Paths
        transcript_path = os.path.join(tmp_dir, f"transcript_{task_id}.json")
        analysis_path = os.path.join(tmp_dir, f"analysis_{task_id}.json")
        search_results_path = os.path.join(tmp_dir, f"search_results_{task_id}.json")
        context_path = os.path.join(tmp_dir, f"context_{task_id}.json")
        final_report_path = os.path.join(tmp_dir, f"report_{task_id}.md")

        # Ensure tmp dir exists
        os.makedirs(tmp_dir, exist_ok=True)

        # Step 1: Transcribe
        print(f"[{task_id}] Starting transcription...")
        subprocess.run(
            ["python", os.path.join(base_dir, "get_transcript.py"), url, transcript_path],
            check=True, capture_output=True
        )
        
        # Update with transcript
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        results_store[task_id] = {
            "status": "transcribed", 
            "data": {"transcript_text": transcript_data.get("transcript_text", "")}
        }

        # Step 2: Analyze
        print(f"[{task_id}] Starting analysis...")
        subprocess.run(
            ["python", os.path.join(base_dir, "extract_keywords.py"), transcript_path, analysis_path],
            check=True, capture_output=True
        )
        
        # Update with keywords
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        results_store[task_id]["status"] = "keywords_extracted"
        results_store[task_id]["data"]["search_keywords"] = analysis_data.get("search_keywords", [])

        # Step 3: Search
        print(f"[{task_id}] Starting search...")
        subprocess.run(
            ["python", os.path.join(base_dir, "search_references.py"), analysis_path, search_results_path],
            check=True, capture_output=True
        )
        
        # Update with search results
        with open(search_results_path, 'r', encoding='utf-8') as f:
            search_data = json.load(f)
        results_store[task_id]["status"] = "searched"
        results_store[task_id]["data"]["references"] = search_data.get("references", [])

        # Step 4: Prepare Context for Synthesis
        print(f"[{task_id}] Preparing context...")
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        with open(search_results_path, 'r', encoding='utf-8') as f:
            search_data = json.load(f)
            
        context = {
            "transcript": transcript_data.get("transcript_text", ""),
            "keywords": analysis_data.get("search_keywords", []),
            "search_results": search_data.get("references", [])
        }
        
        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=2)

        # Step 5: Synthesize Final Report
        print(f"[{task_id}] Starting synthesis...")
        subprocess.run(
            ["python", os.path.join(base_dir, "synthesize_report.py"), context_path, final_report_path],
            check=True, capture_output=True
        )

        # Load final result (Markdown)
        with open(final_report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()

        results_store[task_id] = {
            "status": "completed", 
            "data": {
                "report": report_content,
                "metadata": context
            },
            "export_url": f"{tmp_dir}"
        }
        print(f"Exported to results_store[task_id][export_url] --> Pipeline completed.")

    except subprocess.CalledProcessError as e:
        print(f"[{task_id}] Pipeline failed: {e.stderr.decode() if e.stderr else str(e)}")
        results_store[task_id] = {"status": "failed", "error": f"Script execution failed: {e}"}
    except Exception as e:
        print(f"[{task_id}] Internal error: {e}")
        results_store[task_id] = {"status": "failed", "error": str(e)}
