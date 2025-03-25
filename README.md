# Mukilan's AI Assistant

A personalized AI chatbot that simulates conversations with Mukilan using natural language processing and voice capabilities. Talk to an AI version of Mukilan anytime, anywhere - no scheduling, no delays.

## Features

- **Conversational AI**: Powered by Google's Gemini 2.0 Flash model for natural, context-aware responses
- **Voice Interaction**: Both text-to-speech and speech-to-text capabilities for a hands-free experience
- **Personalized Responses**: AI trained on Mukilan's background, experience, and communication style
- **Modern UI**: Clean, responsive interface with attractive animations and visual feedback
- **Offline Capability**: Fallback mechanisms when API services are unavailable

## Prerequisites

- Python 3.8+
- Flask web framework
- Internet connection for API access
- Modern web browser (Chrome, Firefox, Safari, Edge)

## API Keys

This application uses several AI services that require API keys:

- **Google Gemini API**: For conversation generation
- **AssemblyAI**: For speech recognition 
- **ElevenLabs** (optional): For high-quality text-to-speech

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd chatbot
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure your API keys by creating/editing `api_key.json`:
   ```json
   {
     "key": "your-gemini-api-key",
     "eleven_labs": "your-elevenlabs-key",
     "deepgram": "your-deepgram-key",
     "assembly_ai": "your-assemblyai-key"
   }
   ```

## Usage

1. Start the Flask application:
   ```
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

3. Click "Start Conversation" to begin chatting with Mukilan's AI

4. Use the microphone button to speak your questions or type them directly

## Voice Features

- **Text-to-Speech**: AI responses are automatically converted to speech
- **Speech-to-Text**: Click the microphone button and speak to enter your message
- **Voice Controls**: Easily toggle recording on/off with visual feedback

## Technology Stack

- **Backend**: Flask (Python)
- **AI/ML**: Google Gemini 2.0 Flash
- **Speech Recognition**: AssemblyAI
- **Text-to-Speech**: StreamElements API (primary), ElevenLabs (backup)
- **Frontend**: HTML, CSS, JavaScript with modern animations

## Project Structure

- `app.py`: Main Flask application with routes and API integration
- `templates/index.html`: Frontend interface with JavaScript functionality
- `resume_data.json`: Mukilan's profile data for AI personalization
- `api_key.json`: Configuration file for API credentials
- `requirements.txt`: Python dependencies

## Troubleshooting

- **Microphone Issues**: Ensure your browser has permission to access your microphone
- **Missing Audio**: Check that your API keys are correctly configured
- **API Errors**: Some services may have usage limits; check console for error messages


## Author

Mukilan S 