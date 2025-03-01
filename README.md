<a href="https://x.com/alxfazio" target="_blank">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="images/vcc-github-banner.png">
    <img alt="Viral Clips Crew Logo" src="images/vcc-github-banner.png" width="400px" style="max-width: 100%; margin-bottom: 20px;">
  </picture>
</a>

# Tribu IA Content Agent

This is a modified version of the original Viral Clips Generator project.

## Attribution
Original project by [Alex Fazio](https://github.com/alexfazio)
Original repository: [\[Original Project URL\]](https://github.com/alexfazio/viral-clips-crew)
Modified by TribuIA Co - Cristian Cordoba - ... 

A## bout This Version
This enhanced version of Viral Clips Crew has been specifically developed to address the scaling challenges faced by the Tribu Community. As our community continues to grow rapidly, we needed a solution that could keep pace with our expanding social media presence, increasing program initiatives, and the valuable contributions from our community members.
Our goal was to develop an intelligent content management system that could efficiently process and distribute the wealth of knowledge shared within our community across multiple platforms while maintaining our distinct brand voice and quality standards.

## Original Project
This project is based on the excellent work by Alex Fazio, whose original content extraction framework provided the foundation for our enhanced system.

## Tribu Extension
The Viral Clips Crew extension was born from the Tribu Community's increasing growth and the necessity to keep pace with our social media updates. As the quantity of initiatives in our programs and valuable interventions from our community members expanded, we needed a scalable, intelligent solution to manage our content pipeline effectively.
This extension aims to create a comprehensive content management ecosystem that can:

- Automatically identify high-value segments from our events and discussions
- Maintain brand consistency across all distributed content
- Optimize clips for platform-specific requirements
- Ensure quality through continuous evaluation
- Scale with our growing community needs

## Architecture Vision
The Viral Clips Crew Tribu Extension implements a sophisticated multi-agent architecture designed to transform raw video content into platform-optimized social media assets:


Your [CrewAI](https://github.com/joaomdmoura/crewAI) Powered Video Editing Assistant


>>>
[WIP]

>>>


## Features

- **AI-Powered Analysis**: Uses GPT-4o to identify the most viral-worthy segments in your videos
- **Multi-Platform Optimization**: Creates clips optimized for Instagram, TikTok, YouTube, and LinkedIn
- **Automatic Subtitling**: Burns subtitles directly into videos for better engagement
- **Custom Aspect Ratios**: Choose between original aspect ratio or square (1:1) format
- **Resume Processing**: Restart from any stage if processing is interrupted
- **Command-Line Interface**: Flexible options for both interactive and automated use

## Requirements

This project requires:

- Python 3.8+
- FFmpeg installed in your system
- OpenAI API key (for content analysis)
- Google Gemini API key (for subtitle processing)

## Installation

1. Clone this repository to your local machine:

    ```shell
    git clone https://github.com/alexfazio/viral-clips-crew.git
    cd viral-clips-crew
    ```

2. **Option 1**: Install with Poetry (recommended)

    ```shell
    # Install Poetry if you don't have it
    pip install poetry
    
    # Install dependencies
    poetry install
    
    # Update Pydantic
    poetry update pydantic
    ```

3. **Option 2**: Install with pip

    ```shell
    # Create a virtual environment
    python -m venv venv
    
    # Activate the virtual environment
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    ```

4. Set up your API keys:

    ```shell
    # Create .env file with your API keys
    echo "OPENAI_API_KEY=your-openai-api-key-here" > .env
    echo "GEMINI_API_KEY=your-gemini-api-key-here" >> .env
    ```

## Usage

### Basic Usage

Place your video in the `input_files` directory and run:

```shell
# Using Poetry
poetry run python app.py

# Or with standard Python (in activated virtual environment)
python app.py
```

The program will:
1. Transcribe the video using Whisper
2. Analyze the transcript to find viral-worthy segments
3. Match transcript segments with precise timing information
4. Extract video clips for each viral segment
5. Burn subtitles into the clips

Final output will be in the `subtitler_output` directory.

### Command Line Options

The program supports various command-line arguments for more control:

```shell
# Process a specific video file
python app.py --input-file /path/to/your/video.mp4

# Download and process a YouTube video
python app.py --youtube https://www.youtube.com/watch?v=your-video-id

# Set the aspect ratio (1=original, 2=square)
python app.py --aspect-ratio 2

# Clean output directories before processing
python app.py --clean

# Restart from last checkpoint if processing was interrupted
python app.py --restart

# Start from a specific processing stage
python app.py --stage extract
```

Run `python app.py --help` to see all available options.

## Understanding the Process

The workflow consists of six main stages:

1. **Setup**: Validates environment and dependencies
2. **Input**: Processes input video from file or YouTube
3. **Transcribe**: Generates transcript using Whisper
4. **Extract**: Identifies viral segments using GPT-4o
5. **Align**: Matches transcript segments with precise timing using Gemini
6. **Clip**: Extracts video segments based on timestamps
7. **Subtitle**: Burns subtitles into the final clips

If the process is interrupted, you can restart from any stage using the `--restart` or `--stage` options.

## Troubleshooting

### Common Issues

- **API Key Issues**: Ensure your API keys are correctly set in the `.env` file
- **FFmpeg Missing**: Install FFmpeg and make sure it's in your system PATH
- **No Videos Found**: Verify that your video files are in the `input_files` directory
- **NoneType Error**: May indicate an API call failure - check your API key quotas

### Debugging

For detailed logs, check the `viral_clips.log` file created in the project directory.

If you encounter a specific error, you can usually restart from the failed stage:

```shell
python app.py --stage [stage_name]
```

Where `stage_name` is one of: setup, input, transcribe, extract, align, clip, subtitle.

## Credits

- Original concept by [Alex Fazio](https://x.com/alxfazio)
- Additional development by [Rip&Tear](https://x.com/Cyb3rCh1ck3n)

## License

[MIT](https://opensource.org/licenses/MIT)

Copyright (c) 2024-present, Alex Fazio

---

[![Watch the video](https://i.imgur.com/TBD2bvj.png)](https://x.com/alxfazio/status/1791863931931078719)