<a href="https://x.com/alxfazio" target="_blank">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="images/vcc-github-banner.png">
    <img alt="OpenAI Cookbook Logo" src="images/vcc-github-banner.png" width="400px" style="max-width: 100%; margin-bottom: 20px;">
  </picture>
</a>

Your [CrewAI](https://github.com/joaomdmoura/crewAI) Powered Video Editing Assistant

Are you a social media content curator? Skip the tedious editing process and get polished video highlights in minutes. `viral-clips-crew` watches and listens to long-form content, extracting the most striking and potentially viral segments, ready for publication on social media.

## Content Repurposing Made Easy

<div align="center">
  <img src="https://github.com/alexfazio/viral-clips-crew/assets/34505954/c69da629-06eb-4279-a5cb-0d8d7fc1dfee" width="600px" height="auto">
</div>

`viral-clips-crew` helps you repackage your valuable content in new and engaging ways to capture attention on social media and drive traffic back to the original long-form piece. Whether you're looking to refresh your own content or recycle content from other creators, this tool streamlines the process, making content repurposing effortless and efficient.

## Requirements

This project requires:

- Python 3.7+
- CrewAI
- OpenAI API key and Google Gemini API key

All required Python libraries are listed in `pyproject.toml`.

## Installation

1. Clone this repository to your local machine:

    ```shell
    git clone https://github.com/alexfazio/viral-clips-crew.git
    ```

2. Install Poetry to automatically manage project dependencies:

    ```shell
    pip install poetry
    ```

3. Install the required Python packages using Poetry:

    ```shell
    poetry install
    ```

4. Update Pydantic:

    ```shell
    poetry update pydantic
    ```

5. Open `.env` and insert your OpenAI API key and Google Gemini API key.

    ```shell
   echo -e "OPENAI_API_KEY=<your-api-key>\nGEMINI_API_KEY=<your-api-key>" > .env
    ```

## Usage

After setting up, drag your desired clip into the `input_files` directory. 

**Gemini can process videos up to 1 hour in length. If you are using the OpenAI API, please ensure that the clip is less than 15 minutes in length. The current LLM context windows are approximately 15 minutes.**

Run `viral-clips-crew` using Poetry with the following command:

```shell
poetry run python app.py
```

This will kickstart the process from beginning to completion.

Final output will be in the `output` directory, with platform-specific versions in `output/platform_versions`.

## Comprehensive Setup and Usage Guide

### Prerequisites

1. **System Requirements**
   - Python 3.8 or newer
   - FFmpeg installed (required for video processing)
   - Git
   - 8GB+ RAM recommended for processing longer videos

2. **API Keys**
   - OpenAI API key (required for content analysis)
   - Google Gemini API key (optional, for enhanced analysis)

### Step-by-Step Setup

1. **Clone the Repository**
   ```shell
   git clone https://github.com/alexfazio/viral-clips-crew.git
   cd viral-clips-crew
   ```

2. **Set Up Python Environment**

   **Option 1: Using Poetry (Recommended)**
   ```shell
   # Install Poetry if not already installed
   pip install poetry

   # Install dependencies
   poetry install

   # Update Pydantic to latest version
   poetry update pydantic
   ```

   **Option 2: Using pip with virtualenv**
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
   
   # Note: For the whisper package, you might need to install additional dependencies:
   # On Ubuntu/Debian:
   # sudo apt update && sudo apt install ffmpeg
   # On macOS:
   # brew install ffmpeg
   ```

3. **Set Up Environment Variables**
   ```shell
   # Create .env file with your API keys
   echo "OPENAI_API_KEY=your-openai-api-key-here" > .env
   echo "GEMINI_API_KEY=your-gemini-api-key-here" >> .env
   ```

4. **Install FFmpeg**

   **On macOS (using Homebrew)**
   ```shell
   brew install ffmpeg
   ```

   **On Ubuntu/Debian**
   ```shell
   sudo apt update
   sudo apt install ffmpeg
   ```

   **On Windows**
   - Download from [FFmpeg official website](https://ffmpeg.org/download.html)
   - Add FFmpeg to your PATH environment variable

5. **Verify Installation**
   ```shell
   # Verify FFmpeg is installed
   ffmpeg -version

   # Verify Python dependencies
   poetry run python -c "import openai; print('OpenAI SDK installed')"
   ```

### Running the Program

#### Basic Usage

1. **Prepare Your Video**
   - Place your video file(s) in the `input_files` directory
   - Supported formats: MP4, MOV, AVI

2. **Run the Program**
   ```shell
   # Using Poetry
   poetry run python app.py

   # OR if using virtualenv
   python app.py
   ```

3. **Locate Output**
   - Processed video segments will be in `output/segments`
   - Platform-optimized versions will be in `output/platform_versions`

#### Advanced Usage

The program supports various command-line options for more control:

```shell
# Process a specific video file
python app.py --input-file /path/to/your/video.mp4

# Target specific platforms
python app.py --platforms instagram tiktok

# Clean output directories before processing
python app.py --clean

# Process all videos in a custom directory
python app.py --input-dir /path/to/videos

# Load a previously saved workflow state
python app.py --state-file state/workflow_state.json
```

Run `python app.py --help` to see all available options.

### Understanding the Workflow

The program follows this workflow:

1. **Content Analysis**: The video is analyzed to identify themes and potential viral segments
2. **Brand Voice Definition**: Guidelines for consistent messaging are created
3. **Platform Strategy**: Requirements for each target platform are determined
4. **Segmentation Planning**: The best points to cut the video are identified
5. **Video Processing**: Segments are cut and enhanced for each platform
6. **Quality Evaluation**: Content is checked for quality at each stage

### Debugging Common Issues

#### API Key Issues

```
EnvironmentError: Required environment variable OPENAI_API_KEY is not set or is set to 'None'.
```

**Solution**: Ensure your API key is correctly set in the `.env` file and the file is in the project root.

#### FFmpeg Missing

```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**Solution**: Install FFmpeg and ensure it's in your system PATH.

#### No Videos Found

```
ERROR - No video files found in directory: ./input_files
```

**Solution**: Make sure your video files are in the correct directory and have a supported extension (.mp4, .mov, .avi).

#### Memory Issues

If the program crashes with memory errors:

**Solution**: 
- Process shorter videos
- Close other memory-intensive applications
- Increase system swap space

#### Debugging Mode

For more detailed logs and debugging information:

```shell
# Set DEBUG environment variable before running
export DEBUG=1
python app.py

# On Windows PowerShell
$env:DEBUG=1; python app.py
```

### Extending the Project

To extend the project with new features:

1. **Add New Tools**: Create new tool modules in the `tools/` directory
2. **Create New Agents**: Extend the Agent base class in `workflow.py`
3. **Modify Processing Steps**: Adjust the workflow in `WorkflowController.process_video()`

## Support

If you like this project and want to support it, please consider leaving a star. Every contribution helps keep the project running. Thank you!

## Troubleshooting

For common issues and their solutions, see the [Debugging Common Issues](#debugging-common-issues) section in the comprehensive guide above.

If you encounter a `TypeError: 'NoneType' object is not iterable`, please check the following:  
- Ensure your API keys are correctly set in the `.env` file.  
- Verify that you have enough pay-as-you-go credits in your OpenAI account and Google Cloud account.

## Note

The code for `viral-clips-crew` is intended for demonstrative purposes and is not meant for production use. The API keys are hardcoded and need to be replaced with your own. Always ensure your keys are kept secure.

## Credits

Thank you to [Rip&Tear](https://x.com/Cyb3rCh1ck3n) for his ongoing assistance in improving this tool.

## License

[MIT](https://opensource.org/licenses/MIT)

Copyright (c) 2024-present, Alex Fazio

---

[![Watch the video](https://i.imgur.com/TBD2bvj.png)](https://x.com/alxfazio/status/1791863931931078719)
