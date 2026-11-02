# AI Property Video Generator

An automated tool to generate professional property marketing videos from property details and photos. Supports both a **Streamlit Web UI** and a **Command Line Interface (CLI)**.

## Features
- **Clean Real-Estate Styling**: Professional title slide, smooth Ken Burns / zoom/pan photo transitions, feature callouts, price tags, and contact/CTA cards.
- **Dual Interface**: Use the interactive Streamlit web dashboard or run directly from the command line.
- **Template-Based Reliability**: Fact-based automated script generation ensuring zero hallucination.
- **Optional Narration & Background Music**: Built-in offline text-to-speech (gTTS) and customizable background audio.
- **Robust Error Handling**: Gracefully catches missing images, invalid pricing, or unconfigured parameters.

## Installation
1. Clone or download this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Streamlit Web App
```bash
streamlit run app.py
```

### 2. Command Line Interface (CLI)
```bash
python cli.py --title "Luxury Villa" --location "Sector 48, Chandigarh" --price "₹4.5 Cr" --type "4 BHK Villa" --images img1.jpg img2.jpg img3.jpg --output property_tour.mp4
```
