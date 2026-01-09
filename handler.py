# handler.py - The Final, Definitive, and Correct Version

import os
import requests
import runpod

# We simplify the registry to reflect the models that expect a list of URLs
MODEL_REGISTRY = {
    "z_image_turbo_edit": {
        "url": "https://fal.run/fal-ai/bytedance/seedream/v4.5/edit", # Using the correct Seedream edit URL
        "type": "image-to-image"
    },
    # LTX-2 only takes one image, so it's temporarily incompatible with this multi-image logic.
    # We focus on getting the image editing working first.
    "ltx_2_i2v": {
        "url": "https://fal.run/fal-ai/ltx-2-19b/image-to-video",
        "type": "image-to-video"
    }
}

def call_fal_api(job_input):
    fal_key = os.environ.get("FAL_KEY")
    if not fal_key: raise ValueError("FAL_KEY environment variable not set.")

    model_id = job_input.get("model_id", "z_image_turbo_edit")
    if model_id not in MODEL_REGISTRY: raise ValueError(f"Unknown model_id: '{model_id}'.")

    model_info = MODEL_REGISTRY[model_id]
    api_url = model_info["url"]
    
    if not job_input.get("image_urls"): raise ValueError("This operation requires at least one image.")
    
    # --- THIS IS THE FINAL FIX ---
    # We now construct the payload with 'image_urls' (plural) and the full list.
    if model_id == "ltx_2_i2v":
         # Video model takes only the first image
        payload = {
            "prompt": job_input.get("prompt"),
            "image_url": job_input.get("image_urls")[0],
            "camera_lora": "static"
        }
    else: # This is for image editing
        payload = {
            "prompt": job_input.get("prompt"),
            "image_urls": job_input.get("image_urls") # Use the full list of URLs
        }
    # --- END OF FIX ---

    payload["enable_safety_checker"] = False
    headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
    
    response = requests.post(api_url, json=payload, headers=headers, timeout=600)
    
    if not response.ok:
        raise Exception(f"fal.ai API Error. Status: {response.status_code}. Details: {response.text}")

    data = response.json()
    
    # This parsing logic is correct based on the output you provided.
    result_url, content_type = None, "image"
    if "video" in data and isinstance(data["video"], dict):
        result_url, content_type = data.get("video", {}).get("url"), "video"
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
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
