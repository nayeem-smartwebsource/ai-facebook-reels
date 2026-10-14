import os
import time
import requests
from google import genai
from gtts import gTTS
from moviepy.editor import AudioFileClip, CompositeVideoClip, ImageClip, ColorClip
from PIL import Image, ImageDraw, ImageFont
import textwrap

# Initialize Gemini Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

def generate_story():
    print("Generating story script with Gemini...")
    prompt = (
        "Write a short, gripping, 30-to-45-second moral, historical, or psychological "
        "story script suitable for a video voiceover. Keep it engaging, fast-paced, "
        "and return ONLY the raw script text without markdown formatting or headings."
    )
    
    # Try preferred model first, then fallback model if 503 server error occurs
    models_to_try = ["gemini-3.8-flash", "gemini-1.5-flash"]
    
    for model_name in models_to_try:
        print(f"Trying model: {model_name}...")
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[{model_name}] Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    print(f"Switching away from {model_name} due to persistent errors...")
                    
    raise Exception("All Gemini models are currently unavailable due to high server demand. Please try again later.")

def create_text_image(text, image_path="text_overlay.png", img_size=(1080, 1920)):
    img = Image.new("RGBA", img_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    wrapped_text = textwrap.fill(text, width=32)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
    except IOError:
        font = ImageFont.load_default()

    left, top, right, bottom = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=15, align="center")
    text_width = right - left
    text_height = bottom - top
    
    x = (img_size[0] - text_width) / 2
    y = (img_size[1] - text_height) / 2

    padding = 40
    draw.rounded_rectangle(
        [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
        radius=20,
        fill=(15, 23, 42, 220)
    )

    draw.multiline_text((x, y), wrapped_text, fill="white", font=font, spacing=15, align="center")
    img.save(image_path)
    return image_path

def create_video(script_text):
    print("Synthesizing voiceover audio...")
    tts = gTTS(text=script_text, lang='en', slow=False)
    audio_path = "voiceover.mp3"
    tts.save(audio_path)
    
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    print("Rendering video file (Vertical 1080x1920 format)...")
    bg_clip = ColorClip(size=(1080, 1920), color=(15, 23, 42), duration=duration)
    
    text_img_path = create_text_image(script_text)
    txt_clip = ImageClip(text_img_path).set_duration(duration).set_position('center')

    video = CompositeVideoClip([bg_clip, txt_clip])
    video = video.set_audio(audio_clip)
    
    output_path = "final_output.mp4"
    video.write_videofile(
        output_path, 
        fps=24, 
        codec='libx264', 
        audio_codec='aac',
        preset='veryfast',
        logger='bar'
    )
    return output_path

def upload_to_facebook_as_draft(video_path):
    print("Uploading video to Facebook as an Unpublished Draft...")
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/videos"
    
    with open(video_path, 'rb') as f:
        payload = {
            'description': '🤖 AI Generated Story #shorts #stories #motivation',
            'published': 'false',
            'access_token': FB_PAGE_ACCESS_TOKEN
        }
        files = {'source': f}
        response = requests.post(url, data=payload, files=files)
        
        print(f"Facebook API Status Code: {response.status_code}")
        print(f"Facebook API Raw Response: {response.text}")
        
        result = response.json()
        
        if "id" in result:
            video_id = result['id']
            print(f"\n==================================================")
            print(f"✅ SUCCESS! Your Video ID is: {video_id}")
            print(f"👉 Direct Link to Review/Publish: https://www.facebook.com/{FB_PAGE_ID}/videos/{video_id}")
            print(f"==================================================\n")
        else:
            print("❌ Failed to get Video ID. Check error message above.")

if __name__ == "__main__":
    story_script = generate_story()
    print(f"Generated Script Snippet: {story_script[:120]}...")
    
    video_file = create_video(story_script)
    upload_to_facebook_as_draft(video_file)
