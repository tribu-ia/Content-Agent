# Viral Clips Crew - Quick Start Guide

This guide will help you get up and running with Viral Clips Crew in just a few minutes.

## Prerequisites

Before starting, make sure you have:

- Python 3.8 or newer
- FFmpeg installed on your system
- OpenAI API key
- Google Gemini API key (optional but recommended)

## 5-Minute Setup

### 1. Clone the repository

```shell
git clone https://github.com/alexfazio/viral-clips-crew.git
cd viral-clips-crew
```

### 2. Set up environment and install dependencies

```shell
# Create virtual environment
python -m venv venv

# Activate the environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Set up API keys

```shell
# Create .env file with your API keys
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env
echo "GEMINI_API_KEY=your-gemini-api-key-here" >> .env
```

### 4. Add your video

Place your video file in the `input_files` directory.

### 5. Run the program

```shell
python app.py
```

You'll be prompted to:
1. Choose a video source (local or YouTube URL)
2. Select an aspect ratio (original or square)

The program will process your video automatically. Final output will be in the `subtitler_output` directory.

## Troubleshooting

If you encounter any issues:

1. Check that you have set up your API keys correctly
2. Verify that FFmpeg is installed and in your PATH
3. Try running with the clean option: `python app.py --clean`
4. Check the logs in `viral_clips.log` for detailed error information

## What's Next?

Once you're comfortable with the basic workflow:

- Try processing YouTube videos directly: `python app.py --youtube https://www.youtube.com/watch?v=your-video-id`
- Experiment with different aspect ratios: `python app.py --aspect-ratio 2`
- Read the full documentation in README.md for more advanced options