import os
import requests
from google import genai
from gtts import gTTS
from moviepy.editor import AudioFileClip, CompositeVideoClip, ColorClip, TextClip

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
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
    )
    return response.text.strip()

def create_video(script_text):
    print("Synthesizing voiceover audio...")
    tts = gTTS(text=script_text, lang='en', slow=False)
    audio_path = "voiceover.mp3"
    tts.save(audio_path)
    
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    print("Rendering video file (Vertical 1080x1920 format)...")
    bg_clip = ColorClip(size=(1080, 1920), color=(15, 23, 42), duration=duration)
    
    txt_clip = TextClip(
        script_text, 
        fontsize=48, 
        color='white', 
        size=(900, None), 
        method='caption',
        font='Arial'
    )
    txt_clip = txt_clip.set_duration(duration).set_position('center')

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
            'published': 'false',  # <--- Keeps it as an unpublished draft!
            'access_token': FB_PAGE_ACCESS_TOKEN
        }
        files = {'source': f}
        response = requests.post(url, data=payload, files=files)
        result = response.json()
        
        if "id" in result:
            print(f"Success! Video uploaded as draft. Facebook Video ID: {result['id']}")
        else:
            print("Failed to upload to Facebook:", result)

if __name__ == "__main__":
    story_script = generate_story()
    print(f"Generated Script Snippet: {story_script[:120]}...")
    
    video_file = create_video(story_script)
    upload_to_facebook_as_draft(video_file)
