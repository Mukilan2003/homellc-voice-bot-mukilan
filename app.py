import json
import os
import numpy as np
from flask import Flask, render_template, request, jsonify, Response
import google.generativeai as genai
import requests
from elevenlabs.client import ElevenLabs
from elevenlabs import Voice, VoiceSettings
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
import asyncio
import websockets
import base64

# Import AssemblyAI
import assemblyai as aai

app = Flask(__name__)

# Check if api_key.json exists, create it if not
if not os.path.exists("api_key.json"):
    print("Creating api_key.json with default values")
    default_keys = {
        "key": "your-gemini-api-key",  # Replace with actual key if available
        "eleven_labs": "your-elevenlabs-key",  # For ElevenLabs TTS
        "deepgram": "your-deepgram-key",  # Optional for additional speech recognition
        "assembly_ai": "your-assemblyai-key",  # AssemblyAI key - get from assemblyai.com
    }
    with open("api_key.json", "w") as file:
        json.dump(default_keys, file, indent=4)
    print("Please update api_key.json with your actual API keys")

# Load API keys
try:
    with open("api_key.json", "r") as file:
        api_keys = json.load(file)
except Exception as e:
    print(f"Error loading API keys: {str(e)}")
    # Fallback to defaults if file exists but can't be loaded
    api_keys = {
        "key": "your-gemini-api-key",
        "eleven_labs": "your-elevenlabs-key",
        "deepgram": "your-deepgram-key",
        "assembly_ai": "your-assemblyai-key"
    }

# Configure APIs
genai.configure(api_key=api_keys["key"])
client = ElevenLabs(api_key=api_keys["eleven_labs"])
dg_client = DeepgramClient(api_keys["deepgram"])

# Configure AssemblyAI
ASSEMBLY_AI_KEY = api_keys.get("assembly_ai")
if ASSEMBLY_AI_KEY and ASSEMBLY_AI_KEY != "your-assemblyai-key":
    aai.settings.api_key = ASSEMBLY_AI_KEY
    print("AssemblyAI configured")
else:
    print("WARNING: AssemblyAI key not set. Speech recognition will use browser-based recognition.")

# Load Mukilan's data
with open("resume_data.json", "r") as file:
    mukilan_data = json.load(file)

# Create personalized system prompt with error handling
def create_system_prompt(data):
    # Extract education information
    education = data.get('education', {})
    degree = education.get('degree', 'Degree not specified')
    university = education.get('university', 'University not specified')
    year = education.get('year', 'Year not specified')
    cgpa = education.get('cgpa', 'CGPA not specified')
    
    # Extract experience information
    experiences = data.get('experience', [])
    experience_text = ""
    for exp in experiences:
        role = exp.get('role', 'Role not specified')
        company = exp.get('company', 'Company not specified')
        duration = exp.get('duration', '')
        details = exp.get('details', '')
        
        if duration:
            experience_text += f"• {role} at {company} ({duration}): {details}\n"
        else:
            experience_text += f"• {role} at {company}: {details}\n"
    
    # Extract project information
    projects = data.get('projects', [])
    project_text = ""
    for proj in projects:
        title = proj.get('title', 'Title not specified')
        description = proj.get('description', '')
        project_text += f"• {title}: {description}\n"
    
    # Extract skills information
    skills = data.get('skills', [])
    skills_text = ""
    for skill in skills:
        category = skill.get('category', '')
        technologies = skill.get('technologies', '')
        if category and technologies:
            skills_text += f"• {category}: {technologies}\n"
    
    # Extract certifications and awards
    certifications = data.get('certifications', [])
    cert_text = ""
    for cert in certifications:
        title = cert.get('title', '')
        platform = cert.get('platform', '')
        if title and platform:
            cert_text += f"• {title} ({platform})\n"
    
    # Create the system prompt
    return f"""I am Mukilan S. A generative AI and ML enthusiast with experience in scalable AI solutions,

IDENTITY:
- {degree} from {university} ({year}), CGPA: {cgpa}
- Experience: {experience_text}
- Projects: {project_text}
- Skills: {skills_text}

RESPONSE STYLE:
I provide concise but friendly responses. I maintain a professional tone with a touch of enthusiasm about technology. My answers are direct and focused but include brief conversational elements when appropriate.

GUIDELINES:
- Keep responses under 150 words whenever possible
- Include a brief greeting or acknowledgment when appropriate
- Present information in clear, direct sentences
- Use technical terms naturally but explain them when needed
- Answer exactly what was asked with precision
- Include 1-2 polite phrases to maintain conversational flow
- For lists, use natural phrases instead of numbered points (avoid "1.", "2.", etc.)
- Use transition words like "First," "Also," "Additionally," "Finally" instead of numbers
- DO NOT end responses with questions to the user
- Make definitive statements rather than asking for more information
- Conclude with a brief, helpful statement rather than a question

IMPORTANT: Format responses for natural speech. Avoid numbers, symbols, or formatting that would sound awkward when read aloud.

I combine technical accuracy with a personable approach while avoiding unnecessary verbosity."""

# Configure Gemini model
generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 40,
    "max_output_tokens": 2048,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Create the initial system prompt
system_prompt = create_system_prompt(mukilan_data)

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    generation_config=generation_config,
    safety_settings=safety_settings
)

# Initialize chat with your persona
chat = model.start_chat(history=[])
chat.send_message(f"""You are Mukilan S. Respond as me with natural, conversational answers.

{system_prompt}

SPEECH-FRIENDLY FORMAT:
1. Avoid numbered lists or bullet points entirely - they sound unnatural when read aloud
2. Structure information in flowing paragraphs with natural transitions
3. Use phrases like "First," "Another thing," or "Also" instead of numbered points
4. Don't use asterisks, bullet points, or any special formatting characters
5. Format all responses as if you're speaking them aloud in conversation
6. Never include "1.", "2.", "3." in responses as they will be awkwardly read out loud
7. Don't use "**" for emphasis or formatting as it will be read verbatim

CRITICAL: DO NOT end your responses with questions like "What about you?" or "How about you?" 
Instead, make definitive closing statements. Never ask the user for more information or clarification.

Keep responses concise (under 150 words) but conversational, avoiding any formatting that would sound unnatural in speech.""")

# Audio settings (no longer dependent on PyAudio)
SAMPLE_RATE = 16000

executor = ThreadPoolExecutor(max_workers=2)

# Generate audio using free TTS API
def generate_free_tts(text):
    """Generate audio using a free TTS API"""
    try:
        url = "https://api.streamelements.com/kappa/v2/speech"
        params = {
            "voice": "Brian",
            "text": text
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"Free TTS API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error with free TTS: {str(e)}")
        return None

@app.route('/')
def index():
    intro_data = generate_introduction()
    return render_template('index.html', 
                         introduction=intro_data['text'],
                         intro_audio=intro_data['audio'])

def generate_introduction():
    """Generate Mukilan's natural self-introduction"""
    try:
        introduction = """I'm Mukilan, A generative AI and ML enthusiast with experience in scalable AI solutions, specializing in AI-ML and software development. My expertise includes LLMs, computer vision, and cloud deployment. I've built chatbots, proctoring systems,various other projects and won multiple hackathons."""
        
        # Try free TTS first
        try:
            audio_data = generate_free_tts(introduction)
            if audio_data:
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                return {
                    'text': introduction,
                    'audio': audio_b64
                }
        except Exception as free_error:
            print(f"Free TTS error: {str(free_error)}")
        
        # Try ElevenLabs as fallback
        try:
            # Use cached_text_to_speech which uses ElevenLabs
            audio_data = cached_text_to_speech(introduction)
            if audio_data:
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                return {
                    'text': introduction,
                    'audio': audio_b64
                }
        except Exception as el_error:
            print(f"ElevenLabs error: {str(el_error)}")
            
        # If all TTS options fail, return text only
        return {
            'text': introduction,
            'audio': None
        }
    except Exception as e:
        print(f"Error generating introduction: {str(e)}")
        # Fallback introduction if everything fails
        return {
            'text': "Hi! I'm Mukilan's AI assistant. I'm here to chat about tech, AI, and software development.",
            'audio': None
        }

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    user_message = request.json.get('message')
    
    try:
        # Limit incoming message length to reduce token usage
        if len(user_message) > 500:
            user_message = user_message[:500] + "..."
            
        response = chat.send_message(user_message)
        
        # Process response text
        response_text = response.text
        
        # Use the full response for voice synthesis since we now enforce brevity in the prompt
        audio_text = response_text
        
        # Generate audio in background to avoid delays
        def generate_audio():
            # Try free TTS first
            try:
                audio_data = generate_free_tts(audio_text)
                if audio_data:
                    return audio_data
            except Exception as free_error:
                print(f"Free TTS error in chat: {str(free_error)}")
            
            # Try ElevenLabs as fallback
            try:
                audio_data = cached_text_to_speech(audio_text)
                if audio_data:
                    return audio_data
            except Exception as el_error:
                print(f"ElevenLabs error in chat: {str(el_error)}")
                
            return None
    
        # Start audio generation in background
        with ThreadPoolExecutor() as executor:
            future = executor.submit(generate_audio)
        
        try:
            audio_data = future.result(timeout=10)  # Wait up to 10 seconds for audio
            if audio_data:
                # Convert audio to base64 for immediate playback
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                return jsonify({
                    'response': response_text,
                    'audio': audio_b64,
                    'status': 'success'
                })
            else:
                return jsonify({
                    'response': response_text,
                    'audio': None,
                    'status': 'no_audio'
                })
        except Exception as e:
            print(f"Error in audio generation: {str(e)}")
            return jsonify({
                'response': response_text,
                'audio': None,
                'status': 'audio_error'
            })
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        # Return a fallback response if the API call fails
        return jsonify({
            'response': "I'm sorry, I encountered an error processing your request. This might be due to API quota limitations. Please try again with a shorter message.",
            'audio': None,
            'status': 'api_error'
        })

@app.route('/audio/<text>')
def text_to_speech(text):
    try:
        audio_data = cached_text_to_speech(text)
        
        # Convert audio data to bytes if it's a generator
        if hasattr(audio_data, '__iter__') and not isinstance(audio_data, (bytes, bytearray)):
            audio_data = b''.join(audio_data)
        
        return Response(audio_data, mimetype="audio/mpeg")
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return jsonify({"error": "Failed to generate audio"}), 500

@lru_cache(maxsize=128)
def cached_text_to_speech(text):
    audio_data = client.generate(
        text=text,
        voice="xnx6sPTtvU635ocDt2j7",
        model="eleven_multilingual_v2",
        voice_settings=VoiceSettings(stability=0.75, similarity_boost=0.75)
    )
    
    # Convert audio data to bytes if it's a generator
    if hasattr(audio_data, '__iter__') and not isinstance(audio_data, (bytes, bytearray)):
        audio_data = b''.join(audio_data)
    
    return audio_data

# Legacy endpoint kept for compatibility, but now uses browser-based recording
@app.route('/record', methods=['POST'])
def record_audio():
    return jsonify({
        'transcript': "",
        'message': "This feature has been replaced with browser-based recording for better compatibility. Please use the microphone button in the interface."
    }), 200

# AssemblyAI transcription endpoint
@app.route('/transcribe_audio', methods=['POST'])
def transcribe_with_assemblyai():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']
    temp_file_path = "temp_recording.wav"
    audio_file.save(temp_file_path)
    
    try:
        # Initialize AssemblyAI if not already done
        if not ASSEMBLY_AI_KEY or ASSEMBLY_AI_KEY == "your-assemblyai-key":
            # If no valid API key, return a helpful error message
            print("No valid AssemblyAI API key found")
            
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
            return jsonify({
                'transcript': "",
                'error': "AssemblyAI API key is not configured. Please update api_key.json with your key.",
                'status': 'error'
            }), 400
        
        # Use AssemblyAI exclusively
        print("Using AssemblyAI for transcription")
        
        # Make sure AssemblyAI is configured
        aai.settings.api_key = ASSEMBLY_AI_KEY
        
        # Create transcriber and transcribe audio
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(temp_file_path)
        text = transcript.text or ""
        
        print(f"AssemblyAI transcription result: {text}")
        
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        # Return the transcript
        return jsonify({
            'transcript': text,
            'status': 'success'
        })
    except Exception as e:
        print(f"Error in AssemblyAI transcription: {str(e)}")
        
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return jsonify({
            'transcript': "",
            'error': f"AssemblyAI error: {str(e)}",
            'status': 'error'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)