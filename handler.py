# handler.py - The Correct, Reverted, and Simplified Version

import os
import requests
import runpod

# We only need the two endpoints you are using.
IMAGE_EDIT_URL = "https://fal.run/fal-ai/z-image/turbo"
VIDEO_GEN_URL = "https://fal.run/fal-ai/ltx-2-19b/image-to-video"

def call_fal_api(job_input):
    fal_key = os.environ.get("FAL_KEY")
    if not fal_key: raise ValueError("FAL_KEY environment variable not set.")

    model_id = job_input.get("model_id")
    
    # Simple logic: if the model is video, use the video URL. Otherwise, use the image URL.
    if model_id == "ltx_2_i2v":
        api_url = VIDEO_GEN_URL
        payload = {
            "prompt": job_input.get("prompt"),
            "image_url": job_input.get("image_urls")[0], # Video model takes one image
            "camera_lora": "static"
        }
    else: # Default to image editing
        api_url = IMAGE_EDIT_URL
        payload = {
            "prompt": job_input.get("prompt"),
            "image_url": job_input.get("image_urls")[0] # Z-Image-Turbo also takes one image
        }
        # If you were to add back Seedream, you'd need logic to handle the plural "image_urls" here.

    payload["enable_safety_checker"] = False
    headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
    
    response = requests.post(api_url, json=payload, headers=headers, timeout=600)
    
    if not response.ok:
        raise Exception(f"fal.ai API Error. Status: {response.status_code}. Details: {response.text}")

    data = response.json()
    
    result_url, content_type = None, "image"
    if model_id == "ltx_2_i2v":
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
        return {"error": str(e)}

runpod.serverless.start({"handler": handler})
