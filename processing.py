import os
import shutil
import librosa
import soundfile as sf
from yt_dlp import YoutubeDL, DownloadError
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


def find_audio_files(path, extension=".mp3"):
    """Recursively find all files with extension in path."""
    audio_files = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(extension):
                audio_files.append(os.path.join(root, f))
    return audio_files

def youtube_to_mp3(youtube_url: str, output_dir: str) -> str:
    """Download the audio from a YouTube video, save it to output_dir as an .mp3 file."""

    ydl_config = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "verbose": True,
    }

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Downloading video from {youtube_url}")

    try:
        with YoutubeDL(ydl_config) as ydl:
            ydl.download([youtube_url])
    except DownloadError:
        print("Initial download failed, retrying...")
        with YoutubeDL(ydl_config) as ydl:
            ydl.download([youtube_url])

    audio_filename = find_audio_files(output_dir)[0]
    return audio_filename

# Example usage:
#youtube_to_mp3('https://www.youtube.com/watch?v=Tx3xJxE20uk', '/Users/pavlo.tsiselskyi/Documents/hackaton/assets/audio_files/')

def chunk_audio(filename, segment_length: int, output_dir):
    """segment lenght is in seconds"""

    print(f"Chunking audio to {segment_length} second segments...")

    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    # load audio file
    audio, sr = librosa.load(filename, sr=44100)

    # calculate duration in seconds
    duration = librosa.get_duration(y=audio, sr=sr)

    # calculate number of segments
    num_segments = int(duration / segment_length) + 1

    print(f"Chunking {num_segments} chunks...")

    # iterate through segments and save them
    for i in range(num_segments):
        start = i * segment_length * sr
        end = (i + 1) * segment_length * sr
        segment = audio[start:end]
        sf.write(os.path.join(output_dir, f"segment_{i}.mp3"), segment, sr)

    chunked_audio_files = find_audio_files(output_dir)
    return sorted(chunked_audio_files)

def transcribe_audio(audio_files: list, output_file=None, model="whisper-1", segment_length=20) -> list:
    print("Converting audio to text...")

    transcripts = []
    for i, audio_file in enumerate(audio_files):
        start_time = i * segment_length
        end_time = start_time + segment_length

        with open(audio_file, "rb") as audio:
            whisper_response = client.audio.transcriptions.create(
                model=model,
                file=audio
            )
            raw_transcript = whisper_response.text

        transcript_with_timestamp = f"[{start_time}s - {end_time}s]: {raw_transcript}"
        transcripts.append(transcript_with_timestamp)

    if output_file is not None:
        with open(output_file, "w") as file:
            for transcript in transcripts:
                file.write(transcript + "\n")

    return transcripts

def summarize_youtube_video(youtube_url, outputs_dir):
    raw_audio_dir = f"{outputs_dir}/raw_audio/"
    chunks_dir = f"{outputs_dir}/chunks"
    transcripts_file = f"{outputs_dir}/transcripts.txt"
    segment_length = 20  # chunk to 20 seconds

    if os.path.exists(outputs_dir):
        shutil.rmtree(outputs_dir)
        os.mkdir(outputs_dir)

    audio_filename = youtube_to_mp3(youtube_url, output_dir=raw_audio_dir)

    chunked_audio_files = chunk_audio(
        audio_filename, segment_length=segment_length, output_dir=chunks_dir
    )

    transcriptions = transcribe_audio(
        chunked_audio_files, output_file=transcripts_file, segment_length=segment_length
    )

    return transcriptions

def ask_gpt(prompt, system_msg="You are a helpful assistant trained in ethical analysis.", model="gpt-3.5-turbo"):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    return response.choices[0].message.content.strip()

def segment_transcript(transcript):
    prompt = f"""
    You are analyzing a police officer's interaction based on this transcript.

    Segment the Transcript into Logical Parts
    Goal: Break the transcript into logical, scene-based segments that reflect distinct phases of the
    interaction (e.g., "Initial Encounter," "Conflict Escalation," "Medical Aid," etc.).
    These segments form the foundation for behavior evaluation in the next prompt.

    1. Read the entire transcript.
    2. Divide the transcript into logical segments based on changes in activity, tone, scene, or
    interaction focus.
    3. For each segment:
    a. Assign a clear, concise title (e.g., "Scene Arrival & Commands Issued")
    b. Provide an estimated timestamp range (use "start," "middle," "end" if no
    timestamps are available)
    c. Summarize the main actions or exchanges in that segment
    d. Number the segments for reference
    Example Output:
    ### Segment 1: Scene Arrival & Commands Issued
    - Estimated Timestamp: Start of transcript
    - Summary:
    - Officer responds to a domestic disturbance.
    - Commands are issued to the suspect to get on the ground.
    - Taser is deployed after non-compliance.
    ---
    ### Segment 2: Suspect Secured & Interviewed
    - Estimated Timestamp: Early-Midpoint
    - Summary:
    - Officer successfully restrains the suspect.
    - Suspect admits to holding a knife.
    - Officer requests medical evaluation and interviews bystanders.




    Transcript:
    \"\"\"
    {transcript}
    \"\"\"
    """

    return ask_gpt(prompt)


def evaluate_officer_behavior(segmented_summary):
    prompt = f"""
    Based on this analysis of the officer's actions:

    Identify and Label Officer Behavior by Domain (Using Segments)
    Goal: Evaluate each segment for officer actions that demonstrate excellence behaviors, using the
    domains and subdomains below.
    Domains and their subdomains:
    - Maximum Engagement: [Calls for Service,Arrests,Time to Engage,Self-initiated / Proactive]
    - Minimal Harm: [Officer Injury Avoidance,Citizen Injury Avoidance,External Complaint Reduction,Citizen Recognition]
    - Disciplined Conduct: [Attendance,Infractions,Accidents]
    - Team Player: [Showing Up First,Showing Up for Team,Balance of Call Types]
    - Skillful Actions: [Time to Resolve,De-escalation,Force Avoidance]
    1. For each segment, assess whether the officer demonstrates one or more excellence
    behaviors.
    2. If a behavior is present:
    a. Label the behavior domain and subdomain
    b. Quote the relevant transcript excerpt
    c. Summarize why the behavior fits the domain/subdomain
    d. Reference the segment number and estimated timestamp
    Example Output:
    **Domain**: Minimal Harm
    **Subdomain**: Citizen Injury Avoidance
    **Quote**: Can you stand up if I assist you?
    **Summary**: The officer physically assists the suspect off the sidewalk
    while avoiding further harm, showing care during restraint.
    **Reference**: Segment 2 – Suspect Secured & Interviewed (Early-Midpoint)

    \"\"\"
    {segmented_summary}
    \"\"\"
    """

    return ask_gpt(prompt)
