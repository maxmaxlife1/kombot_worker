# handler.py - The Complete, Final, and Correct Multi-Modal Version

import os
import requests
import runpod
# --- THIS IS THE NEW DEBUG LINE ---
print("--- RUNNING HANDLER.PY VERSION 2.0 (with corrected URLs) ---")
# ------------------------------------

# The MODEL_REGISTRY is the corrected version from our last message
# --- THE FINAL, EXPANDED MODEL REGISTRY ---
# This dictionary is the "source of truth" for all models the bot can use.
MODEL_REGISTRY = {
    "z_image_turbo_text": {
        "url": "https://fal.run/fal-ai/z-image/turbo",
        "type": "text-to-image"
    },
    "z_image_turbo_edit": {
        "url": "https://fal.run/fal-ai/z-image/turbo",
        "type": "image-to-image",
        "image_key": "image_url" # This model expects a single URL with the singular key
    },
    "seedream_v4_text": {
        "url": "https://fal.run/fal-ai/bytedance/seedream/v4.5/text-to-image",
        "type": "text-to-image"
    },
    "seedream_v4_edit": {
        "url": "https://fal.run/fal-ai/bytedance/seedream/v4.5/edit",
        "type": "image-to-image",
        "image_key": "image_urls" # This model expects a list with the plural key
    },
    "kling_ai_video": {
        "url": "https://fal.run/fal-ai/kuaishou/kling",
        "type": "text-to-video"
    },
    "kling_ai_avatar": {
        "url": "https://fal.run/fal-ai/kling-video/ai-avatar/v2/pro",
        "type": "image-to-video" # This model takes an image, not just text
    }
}

def call_fal_api(job_input):
    """
    This function now correctly routes to all model types based on the registry.
    """
    fal_key = os.environ.get("FAL_KEY")
    if not fal_key: raise ValueError("FAL_KEY environment variable not set.")

    model_id = job_input.get("model_id", "z_image_turbo_text")
    if model_id not in MODEL_REGISTRY: raise ValueError(f"Unknown model_id: '{model_id}'.")

    model_info = MODEL_REGISTRY[model_id]
    api_url = model_info["url"]
    model_type = model_info["type"]
    
    payload = {}

    # --- This is the final, corrected payload logic for all types ---
    if model_type == "text-to-image":
        payload = {"prompt": job_input.get("prompt")}
    
    elif model_type == "image-to-image":
        if not job_input.get("image_urls"): raise ValueError("This model requires at least one image.")
        
        image_key = model_info.get("image_key", "image_url") # Default to singular if not specified
        
        if image_key == "image_urls":
            payload = {"prompt": job_input.get("prompt"), "image_urls": job_input.get("image_urls")}
        else:
            payload = {"prompt": job_input.get("prompt"), "image_url": job_input.get("image_urls")[0]}

    elif model_type == "text-to-video":
        payload = {"prompt": job_input.get("prompt")}
        
    elif model_type == "image-to-video":
        if not job_input.get("image_urls"): raise ValueError("This model requires an input image.")
        # As per docs, Kling Avatar takes a single 'image_url'.
        payload = {
            "image_url": job_input.get("image_urls")[0] # Use the first image from the buffer
        }
        # The prompt is optional for this model, but we can add it if provided.
        if job_input.get("prompt"):
             payload["prompt"] = job_input.get("prompt")
        
    # Add the safety checker flag to all payloads.
    payload["enable_safety_checker"] = False
        
    headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
    
    print(f"--- Calling Model: {model_id} ---")
    print(f"--- FINAL PAYLOAD SENT TO FAL: {payload} ---")
    
    response = requests.post(api_url, json=payload, headers=headers, timeout=300)
    
    if not response.ok:
        raise Exception(f"fal.ai API Error. Status: {response.status_code}. Details: {response.text}")

    data = response.json()
    
    # Correctly parse the response for either an image or a video.
    result_url = None
    content_type = "image"
    if "images" in data and data["images"]: result_url = data["images"][0].get("url")
    elif "image" in data and isinstance(data["image"], dict): result_url = data["image"].get("url")
    elif "video" in data and isinstance(data["video"], dict): result_url = data["video"].get("url"); content_type = "video"
    if not result_url: raise RuntimeError(f"API response missing result URL. Response: {data}")
    
    return {"result_url": result_url, "content_type": content_type}

def handler(job):
    """ The main entrypoint for the RunPod worker. """
    job_input = job.get('input', {})
    # A prompt is no longer strictly required, as image-to-video models might not need one.
    # We check for either prompt or image_urls.
    if not (job_input.get('prompt') or job_input.get('image_urls')):
        return {"error": "Input must include a 'prompt' or 'image_urls'"}
    try:
        result = call_fal_api(job_input)
        return result
    except Exception as e:
        print(f"ERROR: {e}")
        return {"error": str(e)}

# Starts the worker as per the official RunPod guide.
runpod.serverless.start({"handler": handler})

