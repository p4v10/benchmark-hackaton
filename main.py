import streamlit as st
import json
from processing import summarize_youtube_video, segment_transcript, evaluate_officer_behavior

outputs_dir = "assets/"

# Streamlit UI
st.set_page_config(page_title="Officer Excellence Tool", layout="wide")
st.image("img/benchmark_logo.png", width=300)
st.title("Officer Excellence Tool")
st.caption("Select an officer and choose a body-worn camera video from an incident. Once the video is transcribed, our system will analyze the transcript and highlight key moments that demonstrate excellence across five performance categories. Use this tool to recognize outstanding conduct, identify coaching opportunities, and support ongoing professional development through real-world examples.")

tabs = st.tabs(["📺 Manage Videos", "👮 Officer Summary", "➕ Add New Video"])
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
    with open(f'{outputs_dir}officers_data.json', 'w') as file:
        json.dump(data, file, indent=4)

with tabs[0]:
    # Load existing data
    officer_data = load_data()
    st.subheader("Manage Officer Video and Generate Insights")
    st.caption("Use this tab to select an officer, view their body cam footage, generate transcripts, segment dialogue, and evaluate behavior—all in one streamlined workflow with data saved automatically.")
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

            # Join transcript list into a string with line breaks
            formatted_transcript = "\n".join(selected_video_transcript)

            # Estimate height: 20 pixels per line, minimum of 300
            num_lines = len(selected_video_transcript)
            calculated_height = max(300, num_lines * 20)

            st.text_area("Transcript", formatted_transcript, height=calculated_height)

            # Display segments
            if selected_video_segments:
                st.subheader("Segmented Transcript")
                st.text_area("Segments", selected_video_segments, height=700)

                # Display evaluation or show evaluation button
                if selected_video_evaluation:
                    st.subheader("Officer Behavior Evaluation")
                    st.text_area("Evaluation", selected_video_evaluation, height=300)
                else:
                    if st.button("Evaluate Officer Behavior"):
                        with st.spinner("Evaluating officer behavior..."):
                            evaluation = evaluate_officer_behavior(selected_video_segments)
                            st.subheader("Officer Behavior Evaluation")
                            st.text_area("Evaluation", evaluation, height=300)

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
                        st.text_area("Segments", segments, height=300)

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
                    st.text_area("Transcript", transcriptions, height=300)

                    for video in officer_data[officer_name]:
                        if video['url'] == selected_video_url:
                            video['transcript'] = transcriptions
                            break
                    save_data(officer_data)

                    # Force a rerun to display the "Segment Transcript" button after generating the transcript
                    st.rerun()

def extract_matching_evaluation(evaluation_text, target_category, target_subcategory):
    lines = evaluation_text.splitlines()
    capture = False
    result_lines = []

    for line in lines:
        if line.startswith("**Category**:"):
            capture = target_category in line
            result_lines = [line] if capture else []
        elif capture and line.startswith("**Subcategory**:"):
            capture = target_subcategory in line
            if capture:
                result_lines.append(line)
            else:
                result_lines = []
        elif capture:
            if line.strip() == "":
                break  # End of this evaluation section
            result_lines.append(line)

    return "\n".join(result_lines)

with tabs[1]:
    st.subheader("Officer Behavior Summary")
    st.caption("Select an officer to review a summary of behavior evaluations across all uploaded videos, categorized by performance area.")

    officer_data = load_data()
    # Show Descriptions Button
    show_descriptions = st.checkbox("Show Category Descriptions")

    if show_descriptions:
        try:
            with open("extras/category_descriptions.json", "r") as f:
                descriptions = json.load(f)
            st.markdown("### 📘 Category Descriptions")
            for cat, desc in descriptions.items():
                with st.expander(cat):
                    st.markdown(desc)
        except FileNotFoundError:
            st.error("Category descriptions file not found. Please ensure it's in the correct directory.")

    summary_officer_name = st.selectbox("Select Officer", options=[""] + list(officer_data.keys()), key="summary_select")

    # Categories and Subcategories
    category_subcategories = {
        "Maximum Engagement": ["Calls for Service", "Arrests", "Time to Engage", "Self-initiated / Proactive"],
        "Minimal Harm": ["Officer Injury Avoidance", "Citizen Injury Avoidance", "External Complaint Reduction", "Citizen Recognition"],
        "Disciplined Conduct": ["Attendance", "Infractions", "Accidents"],
        "Team Player": ["Showing Up First", "Showing Up for Team", "Balance of Call Types"],
        "Skillful Actions": ["Time to Resolve", "De-escalation", "Force Avoidance"]
    }

    selected_category = st.selectbox("Select Category (Required)", [""] + list(category_subcategories.keys()))
    selected_subcategories = []

    if selected_category:
        selected_subcategories = st.multiselect(
            "Select Subcategories (Required)",
            options=category_subcategories[selected_category]
        )

    # Only process if officer, category, and subcategories are selected
    if summary_officer_name and selected_category and selected_subcategories:
        evaluations = []

        for video in officer_data.get(summary_officer_name, []):
            evaluation = video.get("evaluation", "")
            if evaluation:
                lines = evaluation.splitlines()
                current_eval = {}
                all_evals = []

                for line in lines:
                    if line.startswith("**Category**:"):
                        current_eval["category"] = line.replace("**Category**:", "").strip()
                    elif line.startswith("**Subcategory**:"):
                        current_eval["subcategory"] = line.replace("**Subcategory**:", "").strip()
                    elif line.startswith("**Quote**:"):
                        current_eval["quote"] = line.replace("**Quote**:", "").strip()
                    elif line.startswith("**Summary**:"):
                        current_eval["summary"] = line.replace("**Summary**:", "").strip()
                    elif line.startswith("**Reference**:"):
                        current_eval["reference"] = line.replace("**Reference**:", "").strip()
                        # end of a complete block
                        all_evals.append(current_eval)
                        current_eval = {}

                for ev in all_evals:
                    if ev["category"] == selected_category and ev["subcategory"] in selected_subcategories:
                        summary_text = (
                            f"**Quote**: \"{ev['quote']}\"\n\n"
                            f"**Summary**: {ev['summary']}\n\n"
                            f"**Reference**: {ev['reference']}"
                        )
                        evaluations.append({
                            "subcategory": ev["subcategory"],
                            "title": video["title"],
                            "summary": summary_text
                        })

        if evaluations:
            st.markdown(f"### 🏅 {selected_category}")
            for eval_entry in evaluations:
                st.markdown(f"**Subcategory**: {eval_entry['subcategory']}")
                st.markdown(f"**Video Title**: {eval_entry['title']}")
                st.markdown(eval_entry['summary'])
                st.markdown("---")
        else:
            st.info("No evaluations match the selected subcategories.")
    elif summary_officer_name and (not selected_category or not selected_subcategories):
        st.warning("Please select both a category and at least one subcategory to view evaluations.")



with tabs[2]:
    st.subheader("Add a New Officer Video")
    st.caption("This tab lets you add a new body cam video by entering the officer’s name, video title, and YouTube URL, making it easy to expand the video database for review and analysis.")


    new_officer = st.text_input("Officer Name")
    new_video_title = st.text_input("Video Title")
    new_video_url = st.text_input("YouTube Video URL")

    if "video_added" not in st.session_state:
        st.session_state.video_added = False

    if st.button("Add Video"):
        if new_officer and new_video_url and new_video_title:
            new_entry = {
                "title": new_video_title,
                "url": new_video_url
            }
            officer_data = load_data()  # Reload in case of updates from other tab
            if new_officer in officer_data:
                officer_data[new_officer].append(new_entry)
            else:
                officer_data[new_officer] = [new_entry]
            save_data(officer_data)
            st.session_state.video_added = True
            st.rerun()
        else:
            st.error("Please fill out all fields before submitting.")

    # Show success message after rerun
    if st.session_state.get("video_added", False):
        st.success(f"Video added for Officer '{new_officer}'!")
        st.session_state.video_added = False  # Reset for next time
