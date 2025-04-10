import streamlit as st
import json
from processing import summarize_youtube_video, segment_transcript, evaluate_officer_behavior

outputs_dir = "assets/"

# Load existing data or initialize a new dictionary
def load_data():
    try:
        with open(f'{outputs_dir}officers_data.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    return data

# Save the data back to a JSON file
def save_data(data):
    with open('officers_data.json', 'w') as file:
        json.dump(data, file, indent=4)

# Streamlit UI
st.title("Police Officer Video Manager")

# Load existing data
officer_data = load_data()

# Input for officer's name (or selection from the dropdown)
officer_name = st.selectbox("Select Officer", options=[""] + list(officer_data.keys()))

# Initialize placeholders
selected_video_url = ""
selected_video_transcript = ""
selected_video_segments = ""
selected_video_evaluation = ""

if officer_name:
    if officer_data.get(officer_name):
        video_titles = [f"{video['title']} - {video['url']}" for video in officer_data[officer_name]]
        selected_video = st.selectbox("Select Video", options=[""] + video_titles)

        selected_video_entry = next(
            (video for video in officer_data[officer_name]
             if f"{video['title']} - {video['url']}" == selected_video),
            None
        )

        if selected_video_entry:
            selected_video_url = selected_video_entry.get('url', '')
            selected_video_transcript = selected_video_entry.get('transcript', '')
            selected_video_segments = selected_video_entry.get('segments', '')
            selected_video_evaluation = selected_video_entry.get('evaluation', '')

# Show the YouTube video using the URL if selected
if selected_video_url:
    st.subheader("Body Cam Footage")
    st.video(selected_video_url)

    # Display transcript
    if selected_video_transcript:
        st.subheader("Existing Transcript")
        st.text_area("Transcript", selected_video_transcript, height=300)

        # Display segments
        if selected_video_segments:
            st.subheader("Segmented Transcript")
            st.text_area("Segments", selected_video_segments, height=400)

            # Display evaluation or show evaluation button
            if selected_video_evaluation:
                st.subheader("Officer Behavior Evaluation")
                st.text_area("Evaluation", selected_video_evaluation, height=400)
            else:
                if st.button("Evaluate Officer Behavior"):
                    with st.spinner("Evaluating officer behavior..."):
                        evaluation = evaluate_officer_behavior(selected_video_segments)
                        st.subheader("Officer Behavior Evaluation")
                        st.text_area("Evaluation", evaluation, height=400)

                        # Save evaluation to JSON
                        for video in officer_data[officer_name]:
                            if video['url'] == selected_video_url:
                                video['evaluation'] = evaluation
                                break
                        save_data(officer_data)
        else:
            # Button to generate segments (only if no segments exist)
            if st.button("Segment Transcript"):
                with st.spinner("Segmenting transcript..."):
                    segments = segment_transcript(selected_video_transcript)
                    st.subheader("Segmented Transcript")
                    st.text_area("Segments", segments, height=400)

                    # Save segments to JSON
                    for video in officer_data[officer_name]:
                        if video['url'] == selected_video_url:
                            video['segments'] = segments
                            break
                    save_data(officer_data)

                    # Force a rerun to show the segment button immediately after generation
                    st.rerun()

    else:
        # Button to generate transcript
        if st.button("Generate Transcript"):
            with st.spinner("Transcripting... Please wait."):
                transcriptions = summarize_youtube_video(selected_video_url, outputs_dir)
                st.text_area("Transcript", transcriptions, height=500)

                for video in officer_data[officer_name]:
                    if video['url'] == selected_video_url:
                        video['transcript'] = transcriptions
                        break
                save_data(officer_data)

                # Force a rerun to display the "Segment Transcript" button after generating the transcript
                st.rerun()
