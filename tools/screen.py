import mss
import base64
import os
import io
import glob
import json
import httpx
from PIL import Image
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Global config for VLM
VLM_CONFIG = None

def load_vlm_config():
    """Load VLM configuration from config.json."""
    global VLM_CONFIG
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                VLM_CONFIG = data.get("vlm")
    except Exception as e:
        print(f"Warning: Failed to load VLM config: {e}")

def call_vlm_api(image_path: str) -> str:
    """
    Call VLM API to analyze image.
    Compatible with OpenAI format (e.g. GPT-4o, GLM-4V, local LLM).
    """
    if not VLM_CONFIG:
        load_vlm_config()

    if not VLM_CONFIG or not VLM_CONFIG.get("api_key"):
        return "Error: VLM API not configured in config.json."

    try:
        # Optimize image for AI analysis
        # Convert to JPEG and resize if too large to reduce base64 size and latency
        img = Image.open(image_path)

        # Convert to RGB if needed (e.g. RGBA from PNG)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Resize if dimension > 2000px (maintain aspect ratio)
        max_dim = 2000
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # Save to memory as JPEG with compression
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        # Encode
        base64_image = base64.b64encode(buffer.read()).decode('utf-8')
        mime_type = "image/jpeg" # Always sending optimized JPEG to API

        url = f"{VLM_CONFIG.get('base_url', '').rstrip('/')}/chat/completions"
        api_key = VLM_CONFIG.get("api_key")
        model = VLM_CONFIG.get("model", "glm-4.6v")
        prompt = VLM_CONFIG.get("prompt", "What is in this image?")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }

        # Use httpx for sync request with longer timeout
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            content = result['choices'][0]['message']['content']
            return content

    except httpx.TimeoutException:
        return "AI Analysis Error: Request timed out (image might be too large or network slow)."
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

def cleanup_screenshots(directory: str, max_files: int = 20):
    """
    Keep only the latest `max_files` images in the directory.
    """
    try:
        # Get list of all png and jpg files
        files = glob.glob(os.path.join(directory, "*.png")) + glob.glob(os.path.join(directory, "*.jpg"))

        # Sort by modification time (oldest first)
        files.sort(key=os.path.getmtime)

        # If we have more than max_files, delete the oldest ones
        if len(files) > max_files:
            files_to_delete = files[:-max_files]
            for f in files_to_delete:
                try:
                    os.remove(f)
                except Exception:
                    pass
    except Exception as e:
        print(f"Warning: Failed to cleanup screenshots: {e}")

def register_screen_tools(mcp: FastMCP, screenshots_dir: str, base_url: str):
    # Initial load of config
    load_vlm_config()

    @mcp.tool(name="MyPC-take_screenshot")
    def take_screenshot(display_index: int = 1, ai_analysis: bool = False) -> str:
        """
        Take a screenshot of the specified display.

        Args:
            display_index: The index of the display to capture (default: 1 for primary monitor).
                           Use 1 for first monitor, 2 for second, etc.
            ai_analysis: If True, use AI (VLM) to analyze image content and extract text (default: False).

        Returns:
            str: URL to the screenshot, and AI analysis if requested.
        """
        try:
            with mss.mss() as sct:
                monitors = sct.monitors

                if display_index >= len(monitors):
                    return f"Error: Display index {display_index} out of range. Available: 1-{len(monitors)-1}"

                # Debug info
                selected_monitor = monitors[display_index]
                info = f"Display {display_index}: {selected_monitor['width']}x{selected_monitor['height']} at ({selected_monitor['left']},{selected_monitor['top']})"

                # Capture screenshot
                sct_img = sct.grab(selected_monitor)

                # Convert to PIL Image
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                filepath = os.path.join(screenshots_dir, filename)
                os.makedirs(screenshots_dir, exist_ok=True)

                # Cleanup old screenshots before saving new one
                cleanup_screenshots(screenshots_dir)

                # Save to file (Full Resolution PNG)
                img.save(filepath)

                # Return URL only
                url = f"{base_url}/screenshots/{filename}"
                response = f"Screenshot captured successfully!\n\n[Info: {info}]\n\nURL: {url}"

                if ai_analysis:
                    # For API, we might want to save a temp JPEG to reduce size if PNG is huge
                    # But for now let's try sending the file we just saved
                    analysis = call_vlm_api(filepath)
                    response += f"\n\n=== AI Analysis (GLM-4V) ===\n{analysis}"

                return response

        except Exception as e:
            import traceback
            return f"Error taking screenshot: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"

    @mcp.tool(name="MyPC-list_monitors")
    def list_monitors() -> str:
        """
        List available monitors and their dimensions.

        Returns detailed information about each monitor including index,
        dimensions, and recommended index to use for screenshots.
        """
        with mss.mss() as sct:
            monitors = sct.monitors
            info = ["Available Monitors:"]

            for i, monitor in enumerate(monitors):
                if i == 0:
                    desc = "All Monitors Combined"
                    recommend = "❌ Not recommended"
                else:
                    desc = f"Monitor {i}"
                    # Check if this is the primary monitor (usually has coordinates 0,0)
                    is_primary = (monitor['left'] == 0 and monitor['top'] == 0)
                    if is_primary:
                        recommend = "✅ Primary (Recommended)"
                    else:
                        recommend = "✅ Available"

                info.append(f"\n{i}: {desc}")
                info.append(f"   Dimensions: {monitor['width']}x{monitor['height']}")
                info.append(f"   Position: ({monitor['left']}, {monitor['top']})")
                info.append(f"   {recommend}")

            info.append("\n💡 Tip: Use take_screenshot() without parameters for auto-detection of primary monitor.")
            return "\n".join(info)

    @mcp.tool(name="MyPC-take_webcam_photo")
    def take_webcam_photo(camera_index: int = 0, ai_analysis: bool = False) -> str:
        """
        Take a photo using the webcam.

        Args:
            camera_index: Index of the camera (default: 0 for primary webcam).
            ai_analysis: If True, use AI (VLM) to analyze image content (default: False).

        Returns:
            URL to the captured photo.
        """
        try:
            import cv2
        except ImportError:
            return "Error: opencv-python is not installed. Please install it to use webcam features."

        try:
            # Initialize camera
            cap = cv2.VideoCapture(camera_index)

            if not cap.isOpened():
                return f"Error: Could not open camera with index {camera_index}. Check if camera is connected and not in use."

            # Read a frame
            ret, frame = cap.read()

            # Release camera immediately
            cap.release()

            if not ret:
                return "Error: Failed to capture frame from webcam."

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"webcam_{timestamp}.jpg"
            filepath = os.path.join(screenshots_dir, filename)
            os.makedirs(screenshots_dir, exist_ok=True)

            # Cleanup old screenshots before saving new one
            cleanup_screenshots(screenshots_dir)

            # Save image using OpenCV
            cv2.imwrite(filepath, frame)

            # Return URL
            url = f"{base_url}/screenshots/{filename}"
            response = f"Webcam photo taken successfully!\n\nURL: {url}"

            if ai_analysis:
                analysis = call_vlm_api(filepath)
                response += f"\n\n=== AI Analysis (GLM-4V) ===\n{analysis}"

            return response

        except Exception as e:
            return f"Error taking webcam photo: {str(e)}"
