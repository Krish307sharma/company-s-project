"""Property video engine with scene-timed AI narration and optional background music."""
from pathlib import Path
import asyncio
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageEnhance

class PropertyVideoGenerator:
    def __init__(self, property_data, image_paths, output_path="output_property_tour.mp4",
                 width=1920, height=1080, fps=24, seconds_per_image=3.5,
                 animation="Ken Burns", enhance=True, music_path=None,
                 music_volume=0.14, narration=True, voice="en-IN-NeerjaNeural"):
        self.data = property_data
        self.image_paths = [str(p) for p in image_paths]
        self.output_path = str(output_path)
        self.width, self.height, self.fps = int(width), int(height), int(fps)
        self.seconds = float(seconds_per_image)
        self.animation = animation
        self.enhance = bool(enhance)
        self.music_path = str(music_path) if music_path else None
        self.music_volume = float(music_volume)
        self.narration = bool(narration)
        self.voice = voice
        self.title_seconds = 3.0

    def _prepare_image(self, path):
        im = Image.open(path).convert("RGB")
        target = self.width / self.height
        ratio = im.width / im.height
        if ratio > target:
            nw = int(im.height * target)
            left = (im.width - nw) // 2
            im = im.crop((left, 0, left + nw, im.height))
        else:
            nh = int(im.width / target)
            top = (im.height - nh) // 2
            im = im.crop((0, top, im.width, top + nh))
        im = im.resize((self.width, self.height), Image.Resampling.LANCZOS)
        if self.enhance:
            im = ImageEnhance.Color(im).enhance(1.07)
            im = ImageEnhance.Contrast(im).enhance(1.05)
            im = ImageEnhance.Sharpness(im).enhance(1.18)
        return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)

    def _animated(self, base, t, idx):
        if self.animation == "Static":
            return base.copy()
        h, w = base.shape[:2]
        zoom = 1.0 + 0.065 * t
        cw, ch = max(2, int(w / zoom)), max(2, int(h / zoom))
        max_x, max_y = w - cw, h - ch
        x = int(max_x * (t if idx % 2 == 0 else 1.0 - t))
        y = int(max_y * (0.5 + 0.25 * np.sin(t * np.pi)))
        crop = base[y:y+ch, x:x+cw]
        return cv2.resize(crop, (w, h), interpolation=cv2.INTER_LANCZOS4)

    @staticmethod
    def _draw_text(frame, text, position, scale=0.85, color=(255,255,255)):
        text = str(text).encode("ascii", "replace").decode("ascii")[:100]
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, text, position, font, scale, (0,0,0), 5, cv2.LINE_AA)
        cv2.putText(frame, text, position, font, scale, color, 2, cv2.LINE_AA)

    def _narration_segments(self):
        d = self.data
        title = d.get("title", "this beautiful property")
        location = d.get("location", "")
        price = d.get("price", "")
        ptype = d.get("type", "residential property")
        intro = f"Welcome to {title}, a {ptype} in {location}. {price}."
        # One short line per image; each line is scheduled only over its matching scene.
        return [intro] + [f"Explore the {caption}." for caption in d.get("features", [])]

    def _create_tts_segments(self, folder):
        if not self.narration:
            return []
        try:
            import edge_tts
            async def create_all():
                paths = []
                for i, text in enumerate(self._narration_segments()):
                    p = folder / f"narration_scene_{i:02d}.mp3"
                    await edge_tts.Communicate(text, self.voice).save(str(p))
                    paths.append(p)
                return paths
            return asyncio.run(create_all())
        except Exception as exc:
            print(f"Could not create scene narration: {exc}")
            return []

    @staticmethod
    def _audio_duration(path):
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            check=True, capture_output=True, text=True
        )
        return float(probe.stdout.strip())

    def _mux_audio(self, silent_path, voice_paths, video_duration):
        music_ok = bool(self.music_path and Path(self.music_path).exists())
        voice_paths = [Path(p) for p in voice_paths if Path(p).exists()]
        if not music_ok and not voice_paths:
            Path(silent_path).replace(self.output_path)
            return self.output_path

        cmd = ["ffmpeg", "-y", "-i", str(silent_path)]
        input_index = 1
        music_index = None
        if music_ok:
            cmd += ["-stream_loop", "-1", "-i", self.music_path]
            music_index = input_index
            input_index += 1

        voice_specs = []
        for j, path in enumerate(voice_paths):
            cmd += ["-i", str(path)]
            slot_start = 0.0 if j == 0 else self.title_seconds + (j - 1) * self.seconds
            slot_length = self.title_seconds if j == 0 else self.seconds
            clip_duration = self._audio_duration(path)
            # Speed up a long spoken line just enough to fit its own scene.
            # This prevents narration from spilling into the following image.
            speed = max(1.0, clip_duration / max(0.5, slot_length - 0.15))
            speed = min(speed, 2.0)
            voice_specs.append((input_index, slot_start, slot_length, speed))
            input_index += 1

        filters = []
        mix_labels = []
        if music_index is not None:
            filters.append(
                f"[{music_index}:a]volume={self.music_volume},"
                f"atrim=0:{video_duration},asetpts=PTS-STARTPTS[music]"
            )
            mix_labels.append("[music]")

        for j, (idx, slot_start, slot_length, speed) in enumerate(voice_specs):
            label = f"voice{j}"
            filters.append(
                f"[{idx}:a]atempo={speed:.4f},"
                f"atrim=0:{max(0.5, slot_length - 0.08)},"
                f"asetpts=PTS-STARTPTS,adelay={int(slot_start*1000)}|{int(slot_start*1000)}"
                f"[{label}]"
            )
            mix_labels.append(f"[{label}]")

        if len(mix_labels) == 1:
            filters.append(f"{mix_labels[0]}anull[aout]")
        else:
            filters.append(
                f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:"
                f"duration=longest:dropout_transition=0,alimiter=limit=0.95[aout]"
            )

        cmd += [
            "-filter_complex", ";".join(filters),
            "-map", "0:v:0", "-map", "[aout]",
            "-t", str(video_duration), "-c:v", "copy", "-c:a", "aac",
            "-movflags", "+faststart", self.output_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        Path(silent_path).unlink(missing_ok=True)
        return self.output_path

    def build_video(self):
        if not self.image_paths:
            raise ValueError("Upload at least one property image.")
        for p in self.image_paths:
            if not Path(p).exists():
                raise FileNotFoundError(f"Image not found: {p}")
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        silent_path = str(Path(self.output_path).with_name(Path(self.output_path).stem + "_silent.mp4"))
        writer = cv2.VideoWriter(silent_path, cv2.VideoWriter_fourcc(*"mp4v"),
                                 self.fps, (self.width, self.height))
        if not writer.isOpened():
            raise RuntimeError("Could not start video writer.")
        frames_per_scene = max(1, int(self.seconds * self.fps))
        title = self.data.get("title", "Luxury Residence")
        location = self.data.get("location", "")
        price = self.data.get("price", "")
        ptype = self.data.get("type", "Property")
        contact = self.data.get("contact", "")
        try:
            for f in range(int(self.title_seconds * self.fps)):
                frame = np.zeros((self.height, self.width, 3), np.uint8)
                frame[:] = (31, 24, 20)
                cv2.rectangle(frame, (60,60), (self.width-60,self.height-60), (170,150,130), 2)
                alpha = min(1.0, (f + 1) / max(1, self.fps))
                self._draw_text(frame, title, (90, int(self.height*.39)), 1.45, tuple(int(c*alpha) for c in (255,255,255)))
                self._draw_text(frame, f"{ptype} | {location}", (90, int(self.height*.51)), .85, (210,195,180))
                self._draw_text(frame, f"Offered at: {price}", (90, int(self.height*.63)), 1.0, (100,220,150))
                self._draw_text(frame, contact, (90, int(self.height*.78)), .72, (230,230,230))
                writer.write(frame)

            previous_last = None
            features = self.data.get("features", [])
            for idx, path in enumerate(self.image_paths):
                base = self._prepare_image(path)
                caption = features[idx] if idx < len(features) and features[idx] else f"{ptype} view {idx+1}"
                for f in range(frames_per_scene):
                    t = f / max(1, frames_per_scene - 1)
                    frame = self._animated(base, t, idx)
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (0,self.height-155), (self.width,self.height), (12,17,22), -1)
                    frame = cv2.addWeighted(overlay, .50, frame, .50, 0)
                    self._draw_text(frame, caption, (70,self.height-75), .9)
                    progress = (idx + t + 1) / len(self.image_paths)
                    cv2.rectangle(frame, (70,self.height-25), (self.width-70,self.height-17), (75,75,75), -1)
                    cv2.rectangle(frame, (70,self.height-25),
                                  (70+int((self.width-140)*progress),self.height-17), (80,190,130), -1)
                    if f < int(self.fps*.45) and previous_last is not None:
                        a = (f+1) / max(1,int(self.fps*.45))
                        frame = cv2.addWeighted(previous_last, 1-a, frame, a, 0)
                    writer.write(frame)
                previous_last = frame.copy()
        finally:
            writer.release()

        total_duration = self.title_seconds + len(self.image_paths) * frames_per_scene / self.fps
        voice_paths = self._create_tts_segments(Path(self.output_path).parent)
        return self._mux_audio(silent_path, voice_paths, total_duration)
