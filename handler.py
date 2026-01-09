# handler.py - The Final, Definitive Version with Asynchronous Polling for Long Jobs

import os
import requests
import time # We need the time library for sleeping
import runpod

# --- THIS IS THE NEW ASYNC URL STRUCTURE ---
FAL_API_HOST = "https://fal.run"

# We now use the base model ID, not the full URL
MODEL_REGISTRY = {
    "z_image_turbo_edit": {"id": "fal-ai/z-image/turbo", "type": "image-to-image", "image_key": "image_url"},
    "ltx_2_i2v": {"id": "fal-ai/ltx-2-19b/image-to-video", "type": "image-to-video", "image_key": "image_url"}
}

def call_fal_api(job_input):
    """
    This is the final, correct version with a robust asynchronous polling client.
    """
    fal_key = os.environ.get("FAL_KEY")
    if not fal_key: raise ValueError("FAL_KEY not set.")

    model_id = job_input.get("model_id", "z_image_turbo_edit")
    if model_id not in MODEL_REGISTRY: raise ValueError(f"Unknown model_id: '{model_id}'.")

    model_info = MODEL_REGISTRY[model_id]
    
    # Construct the payload (this logic is correct)
    if not job_input.get("image_urls"): raise ValueError("This operation requires an input image.")
    payload = {
        "prompt": job_input.get("prompt"),
        "image_url": job_input.get("image_urls")[0]
    }
    if model_id == "ltx_2_i2v": payload["camera_lora"] = "static"
    payload["enable_safety_checker"] = False
    
    headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
    
    # --- THIS IS THE NEW, ASYNCHRONOUS WORKFLOW ---
    
    # 1. SUBMIT the job to the queue endpoint
    submit_url = f"{FAL_API_HOST}/{model_info['id']}/"
    print(f"--- Submitting ASYNC job to: {submit_url} ---")
    response = requests.post(submit_url, json=payload, headers=headers)
    if not response.ok: raise Exception(f"Failed to submit job. Status: {response.status_code}. Details: {response.text}")
    
    response_data = response.json()
    request_id = response_data.get("request_id")
    if not request_id: raise Exception(f"API did not return a request_id. Response: {response_data}")
        
    status_url = f"{submit_url}requests/{request_id}/status"
    result_url = f"{submit_url}requests/{request_id}"
    
    # 2. POLLING LOOP to check the status
    print(f"--- Job submitted with ID: {request_id}. Now polling for status... ---")
    start_time = time.time()
    while True:
        if time.time() - start_time > 540: # 9 minute overall timeout
            raise Exception("Polling for result timed out after 9 minutes.")

        status_response = requests.get(status_url, headers=headers)
        if not status_response.ok: raise Exception(f"Failed to get job status. Details: {status_response.text}")
        
        status_data = status_response.json()
        status = status_data.get("status")
        
        print(f"Current job status: {status}")
        
        if status == "COMPLETED":
            # 3. FETCH the final result
            print("--- Job completed! Fetching result... ---")
            result_response = requests.get(result_url, headers=headers)
            if not result_response.ok: raise Exception(f"Failed to fetch result. Details: {result_response.text}")
            
            result_data = result_response.json()
            
            final_url, content_type = None, "image"
            if model_info["type"] == "image-to-video":
                final_url = result_data.get("video", {}).get("url")
                content_type = "video"
            elif "images" in result_data and result_data["images"]:
                final_url = result_data["images"][0].get("url")

            if not final_url: raise RuntimeError(f"Job completed but result URL not found. Full result: {result_data}")
            return {"result_url": final_url, "content_type": content_type}
        
        elif status == "FAILED" or status == "ERROR":
            raise Exception(f"Job failed on fal.ai. Details: {status_data}")

        time.sleep(10) # Wait 10 seconds before checking again

def handler(job):
    # This function is correct and does not need to be changed.
    job_input = job.get('input', {})
    if not (job_input.get('prompt') and job_input.get('image_urls')):
        return {"error": "Input must include a 'prompt' and at least one 'image_url'"}
    try:
        result = call_fal_api(job_input)
        return result
    except Exception as e:
        print(f"ERROR: {e}")
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
