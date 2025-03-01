# Viral Clips Crew - Quick Start Guide

This quick start guide will help you get up and running with Viral Clips Crew in just a few minutes.

## Prerequisites

Before starting, make sure you have:

- Python 3.8 or newer
- FFmpeg installed
- OpenAI API key

## 5-Minute Setup

1. **Clone the repository**

```shell
git clone https://github.com/alexfazio/viral-clips-crew.git
cd viral-clips-crew
```

2. **Set up environment**

```shell
# Install Poetry
pip install poetry

# Install dependencies
poetry install

# Set up API key
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env
```

3. **Prepare your video**

Place your video file in the `input_files` directory.

4. **Run the program**

```shell
poetry run python app.py
```

5. **Find your results**

Your processed videos will be available in the `output` directory:
- Full segments: `output/segments`
- Platform-specific versions: `output/platform_versions`

## Command Line Options

Process a specific file:
```shell
python app.py --input-file /path/to/video.mp4
```

Target specific platforms:
```shell
python app.py --platforms instagram tiktok
```

Clean output directories:
```shell
python app.py --clean
```

## Common Issues

If you encounter problems:

- **API key errors**: Check that your `.env` file contains the correct API key
- **FFmpeg missing**: Make sure FFmpeg is installed and in your PATH
- **No output**: Verify that your video file is in the correct format (MP4, MOV, AVI)

For more detailed setup and usage information, see the comprehensive guide in the [README.md](../README.md).

## Next Steps

Once you're comfortable with the basic workflow, explore:

- Customizing agent behavior in `workflow.py`
- Adding new tools in the `tools/` directory
- Adjusting platform parameters in `PlatformStrategist`