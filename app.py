"""Streamlit UI: property photos, explicit per-photo captions, AI narration and music."""
from pathlib import Path
import streamlit as st
from engine import PropertyVideoGenerator

st.set_page_config(page_title="AI Property Video Generator", page_icon="🏡", layout="wide")
st.title("🏡 AI Property Video Generator")
st.caption("Create a cinematic property tour. Match every caption to its photo before rendering.")

a, b = st.columns(2)
with a:
    title = st.text_input("Property title", "Luxury 4 BHK Penthouse")
    location = st.text_input("Location", "Chandigarh")
    price = st.text_input("Price", "₹3.85 Cr")
with b:
    prop_type = st.text_input("Property type", "Penthouse")
    contact = st.text_input("Contact / call to action", "Contact us today")

uploads = st.file_uploader("Upload property photos", type=["jpg","jpeg","png"], accept_multiple_files=True)
features = []
if uploads:
    st.subheader("Match each photo with its correct description")
    st.info("Captions are NOT guessed from upload order. Check each thumbnail and enter what that exact photo shows.")
    for i, up in enumerate(uploads):
        with st.container(border=True):
            c1, c2 = st.columns([1,2])
            with c1:
                st.image(up, caption=up.name, use_container_width=True)
            with c2:
                default = ""
                name = Path(up.name).stem.replace("_", " ").replace("-", " ")
                if any(word in name.lower() for word in ["kitchen", "bedroom", "living", "balcony", "bath", "exterior"]):
                    default = name.title()
                caption = st.text_input(f"Description for photo {i+1}", value=default,
                                         placeholder="e.g. Modular kitchen with island counter",
                                         key=f"caption_{i}")
                features.append(caption.strip())

st.subheader("Video settings")
c1, c2, c3 = st.columns(3)
with c1:
    resolution = st.selectbox("Resolution", ["1080p Full HD", "720p HD"])
    animation = st.selectbox("Animation", ["Ken Burns", "Static"])
with c2:
    seconds = st.slider("Seconds per photo", 2.0, 6.0, 3.5, 0.5)
    enhance = st.checkbox("Enhance image colour and sharpness", True)
with c3:
    narration = st.checkbox("Generate AI English voice narration", True)
    music_enabled = st.checkbox("Add background music", False)
music_file = st.file_uploader("Background music (MP3/WAV)", type=["mp3","wav","m4a"]) if music_enabled else None
music_volume = st.slider("Background music volume", 0.05, 0.5, 0.16, 0.01) if music_enabled else 0.16
voice = st.selectbox("AI voice", ["en-IN-NeerjaNeural", "en-IN-PrabhatNeural", "en-US-AriaNeural", "en-GB-SoniaNeural"])

if st.button("🎬 Generate cinematic property video", type="primary", use_container_width=True):
    if not uploads:
        st.error("Please upload at least one property photo.")
        st.stop()
    if any(not x for x in features):
        st.error("Please enter a correct description for every photo. This prevents kitchen/exterior caption mismatches.")
        st.stop()
    work = Path("temp_uploads")
    work.mkdir(exist_ok=True)
    image_paths = []
    for i, up in enumerate(uploads):
        p = work / f"photo_{i:03d}_{Path(up.name).name}"
        p.write_bytes(up.getbuffer())
        image_paths.append(str(p))
    music_path = None
    if music_enabled and music_file:
        media = Path("temp_media")
        media.mkdir(exist_ok=True)
        music_path = media / Path(music_file.name).name
        music_path.write_bytes(music_file.getbuffer())
    elif music_enabled and not music_file:
        st.warning("Music is enabled but no music file was uploaded. The video will use narration only.")
    data = {"title":title, "location":location, "price":price, "type":prop_type,
            "contact":contact, "features":features}
    width, height = (1920,1080) if resolution.startswith("1080") else (1280,720)
    generator = PropertyVideoGenerator(data, image_paths, width=width, height=height,
        seconds_per_image=seconds, animation=animation, enhance=enhance,
        music_path=music_path, music_volume=music_volume, narration=narration, voice=voice)
    with st.spinner("Generating video and AI narration. Please keep this window open..."):
        try:
            output = generator.build_video()
            st.success("Video rendered!")
            if narration:
                st.caption("If narration could not be generated, check the terminal for Edge-TTS/network errors.")
            st.video(output)
            st.download_button("⬇️ Download MP4", data=Path(output).read_bytes(),
                               file_name="property_tour.mp4", mime="video/mp4")
        except Exception as exc:
            st.error(f"Video generation failed: {exc}")
            st.exception(exc)

st.caption("AI narration uses Edge TTS and requires internet access. Audio muxing requires FFmpeg installed and available on PATH.")
