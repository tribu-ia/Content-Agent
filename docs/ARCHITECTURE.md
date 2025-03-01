# Viral Clips Crew - Architecture Overview

This document provides a detailed overview of the Viral Clips Crew architecture, explaining how the different components work together to process videos and extract viral-worthy segments.

## System Architecture

Viral Clips Crew follows a modular, pipeline-based architecture where each stage builds upon the output of the previous stage. The system is designed to be robust, with checkpointing and restart capabilities to handle interruptions.

### High-Level Architecture

```
┌─────────────┐   ┌──────────────┐   ┌──────────────┐   ┌────────────┐
│ Input Video │──▶│ Transcription │──▶│ AI Analysis  │──▶│  CrewAI    │
└─────────────┘   │   (Whisper)   │   │   (GPT-4o)   │   │  Agents    │
                  └──────────────┘   └──────────────┘   └────────────┘
                                                               │
                                                               ▼
┌─────────────┐   ┌──────────────┐                      ┌────────────┐
│   Output    │◀──│   Subtitler  │◀─────────────────────│  Clipper   │
│   Videos    │   │              │                      │            │
└─────────────┘   └──────────────┘                      └────────────┘
```

### Processing Stages

The system processes videos through these sequential stages:

1. **Setup**: Environment validation and dependency checking
2. **Input**: Video acquisition (local file or YouTube)
3. **Transcription**: Speech-to-text processing using Whisper
4. **Extract**: Content analysis to identify viral segments
5. **Align**: Aligning transcript segments with precise timing
6. **Clip**: Extracting video segments based on timestamps
7. **Subtitle**: Burning subtitles into the final clips

## Components

### 1. Environment and Setup

The system performs initial validation of the environment to ensure all dependencies are available, including:
- API keys for OpenAI and Gemini
- FFmpeg installation
- Required Python packages

### 2. Input Processing

The system can acquire input videos from two main sources:
- Local video files in the `input_files` directory
- YouTube URLs via `ytdl.py`

### 3. Transcription Engine (Whisper)

OpenAI's Whisper model is used for transcription through `local_transcribe.py`:
- Produces both .txt (full transcript) and .srt (timed subtitles) files
- Supports multiple languages
- Adaptive based on video length and complexity

### 4. Viral Content Analysis

The `extracts.py` module communicates with OpenAI's GPT-4o to:
- Analyze the full transcript
- Identify 3-4 segments with high viral potential
- Rank segments by their viral potential
- Calculate word counts for each segment

### 5. CrewAI Agent System

The system uses CrewAI in `crew.py` to create specialized agents:
- Three subtitler agents powered by Google's Gemini
- Each agent matches a transcript segment with corresponding timing information in the SRT file
- Produces individual SRT files for each viral segment

### 6. Video Processing Engine

The video processing consists of two main components:

#### 6.1 Clipper (`clipper.py`)
- Extracts video segments based on subtitle timestamps
- Can maintain original aspect ratio or convert to square format
- Handles duration validation and trimming

#### 6.2 Subtitler (`subtitler.py`)
- Adjusts subtitle timing to match the clip
- Converts subtitle encoding for compatibility
- Burns subtitles directly into video using FFmpeg

### 7. Checkpoint System

The checkpoint system provides robustness through:
- State tracking at each processing stage
- Ability to restart from any stage if interrupted
- Error tracking and logging for debugging

## Error Handling

The system implements several error handling mechanisms:
- Exception catching at each stage
- Detailed logging to file and console
- Retry mechanism for API calls with exponential backoff
- Error information stored in checkpoints

## Command Line Interface

The CLI is implemented in `app.py` with the following features:
- Support for various input sources (YouTube, local files)
- Options for aspect ratio selection
- Clean restart and intermediate file handling
- Stage selection for restarting interrupted processes

## Data Flow

1. Input video → Transcription output (whisper_output directory)
2. Transcription → API analysis → Extract data (crew_output directory)
3. Extract data → Crew agents → SRT files with timing (crew_output directory)
4. Input video + SRT files → Clipper → Trimmed videos (clipper_output directory)
5. Trimmed videos + SRT files → Subtitler → Final videos (subtitler_output directory)

## Future Architecture Considerations

Potential enhancements to the architecture include:
- Parallel processing of multiple segments
- Webhook support for integration with other systems
- API interface for programmatic access
- Enhanced error recovery mechanisms
- Support for additional video sources and output formats