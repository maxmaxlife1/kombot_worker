# handler.py - Final, simplified version with LTX-2 Image-to-Video

import os
import requests
import runpod

# --- THIS IS THE NEW, SIMPLIFIED MODEL REGISTRY ---
MODEL_REGISTRY = {
    "z_image_turbo_edit": {
        "url": "https://fal.run/fal-ai/z-image/turbo",
        "type": "image-to-image",
        "image_key": "image_url"
    },
    "ltx_2_i2v": {
        "url": "https://fal.run/fal-ai/ltx-2-19b/image-to-video",
        "type": "image-to-video",
        "image_key": "image_url"
    }
}

def call_fal_api(job_input):
    """
    This function now supports Z Image Turbo (edit) and LTX-2 (image-to-video).
    """
    fal_key = os.environ.get("FAL_KEY")
    if not fal_key: raise ValueError("FAL_KEY environment variable not set.")

    model_id = job_input.get("model_id", "z_image_turbo_edit") # Default to image editing
    if model_id not in MODEL_REGISTRY: raise ValueError(f"Unknown model_id: '{model_id}'.")

    model_info = MODEL_REGISTRY[model_id]
    api_url = model_info["url"]
    model_type = model_info["type"]
    
    # --- This is the corrected and simplified payload logic ---
    if not job_input.get("image_urls"): raise ValueError("This operation requires an input image.")
    
    # Base payload for all models, as both require prompt and an image
    payload = {
        "prompt": job_input.get("prompt"),
        "image_url": job_input.get("image_urls")[0] # Both models use a single 'image_url'
    }

    # Add model-specific parameters
    if model_id == "ltx_2_i2v":
        # As requested, force the camera to be static.
        payload["camera_lora"] = "static"
        
    payload["enable_safety_checker"] = False
    headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
    
    print(f"--- Calling Model: {model_id} ---")
    print(f"--- FINAL PAYLOAD SENT TO FAL: {payload} ---")
    
    response = requests.post(api_url, json=payload, headers=headers, timeout=300)
    
    if not response.ok:
        raise Exception(f"fal.ai API Error. Status: {response.status_code}. Details: {response.text}")

    data = response.json()
    
    result_url, content_type = None, "image"
    if model_type == "image-to-video":
        result_url = data.get("video", {}).get("url")
        content_type = "video"
    elif "images" in data and data["images"]:
        result_url = data["images"][0].get("url")
    
    if not result_url: raise RuntimeError(f"API response missing result URL. Response: {data}")
    return {"result_url": result_url, "content_type": content_type}

def handler(job):
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
