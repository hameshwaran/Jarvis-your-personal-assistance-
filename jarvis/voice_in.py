"""
===========================================================
J.A.R.V.I.S. — Voice Input Module
===========================================================
Two-stage voice pipeline:
  1. Wake Word Detection: openWakeWord listening for "Hey Jarvis"
  2. Speech-to-Text: faster-whisper (offline, base.en model)

Runs in background threads. Non-blocking.
VAD (Voice Activity Detection) stops recording after 1.5s silence.
===========================================================
"""

import io
import time
import wave
import logging
import threading
import numpy as np
from pathlib import Path
from typing import Callable, Optional

from jarvis.config import (
    WAKE_WORD_MODEL, WAKE_WORD_THRESHOLD,
    WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE,
    AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
    AUDIO_SILENCE_THRESHOLD, AUDIO_SILENCE_DURATION,
    AUDIO_MAX_DURATION, SOUNDS_DIR
)

logger = logging.getLogger("jarvis.voice_in")


class WakeWordDetector:
    """
    Continuously listens for the wake word "Hey Jarvis" using openWakeWord.
    Runs in a background thread. Calls a callback when the wake word is detected.
    """

    def __init__(self, on_wake: Callable = None):
        """
        Args:
            on_wake: Callback function to invoke when wake word is detected.
        """
        self.on_wake = on_wake
        self._running = False
        self._thread = None
        self._model = None
        self._stream = None

        self._init_model()

    def _init_model(self):
        """Load the openWakeWord model."""
        try:
            import openwakeword
            from openwakeword.model import Model

            # Download pre-trained models if needed
            openwakeword.utils.download_models()

            self._model = Model(
                wakeword_models=[WAKE_WORD_MODEL],
                inference_framework="onnx"
            )
            logger.info(f"Wake word model '{WAKE_WORD_MODEL}' loaded")
        except Exception as e:
            logger.error(f"Wake word model init failed: {e}")
            self._model = None

    def start(self):
        """Start listening for the wake word in a background thread."""
        if self._model is None:
            logger.warning("Cannot start wake word detection — model not loaded")
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Wake word detection started")

    def stop(self):
        """Stop the wake word listener."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("Wake word detection stopped")

    def _listen_loop(self):
        """Main listening loop — runs in background thread."""
        try:
            import sounddevice as sd

            chunk_size = 1280  # ~80ms at 16kHz
            stream = sd.InputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype="int16",
                blocksize=chunk_size
            )
            stream.start()

            logger.info("Microphone stream opened for wake word detection")

            while self._running:
                try:
                    audio_data, overflowed = stream.read(chunk_size)
                    if overflowed:
                        continue

                    # Feed audio to the wake word model
                    audio_flat = audio_data.flatten().astype(np.int16)
                    prediction = self._model.predict(audio_flat)

                    # Check all wake word scores
                    for model_name, score in prediction.items():
                        if score > WAKE_WORD_THRESHOLD:
                            logger.info(f"Wake word detected! Score: {score:.3f}")
                            self._play_activation_sound()
                            if self.on_wake:
                                self.on_wake()
                            # Reset model to avoid double triggers
                            self._model.reset()
                            time.sleep(0.5)
                            break

                except Exception as e:
                    logger.error(f"Wake word listen error: {e}")
                    time.sleep(0.1)

            stream.stop()
            stream.close()

        except Exception as e:
            logger.error(f"Wake word listener crashed: {e}")

    def _play_activation_sound(self):
        """Play a short activation sound when wake word is detected."""
        try:
            sound_file = SOUNDS_DIR / "activate.wav"
            if sound_file.exists():
                import sounddevice as sd
                import scipy.io.wavfile as wavfile
                rate, data = wavfile.read(str(sound_file))
                sd.play(data, rate)
            else:
                # Generate a simple beep tone if no sound file exists
                self._play_beep()
        except Exception as e:
            logger.debug(f"Activation sound failed: {e}")

    @staticmethod
    def _play_beep():
        """Generate and play a simple activation beep."""
        try:
            import sounddevice as sd
            duration = 0.15
            freq = 880  # Hz — A5 note
            t = np.linspace(0, duration, int(AUDIO_SAMPLE_RATE * duration), False)
            # Smooth beep with envelope
            envelope = np.sin(np.pi * t / duration)
            tone = envelope * 0.3 * np.sin(2 * np.pi * freq * t)
            sd.play(tone.astype(np.float32), AUDIO_SAMPLE_RATE)
        except Exception:
            pass


class SpeechToText:
    """
    Offline speech-to-text using faster-whisper.
    Records audio with VAD and returns transcribed text.
    """

    def __init__(self):
        self._model = None
        self._init_model()

    def _init_model(self):
        """Load the faster-whisper model."""
        try:
            from faster_whisper import WhisperModel

            # Auto-detect CUDA
            device = WHISPER_DEVICE
            compute_type = WHISPER_COMPUTE_TYPE
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    compute_type = "float16"
                    logger.info("CUDA detected — using GPU for Whisper")
            except ImportError:
                pass

            self._model = WhisperModel(
                WHISPER_MODEL,
                device=device,
                compute_type=compute_type
            )
            logger.info(f"Whisper model '{WHISPER_MODEL}' loaded on {device}")

        except Exception as e:
            logger.error(f"Whisper model init failed: {e}")
            self._model = None

    def listen_and_transcribe(self, timeout: float = None) -> Optional[str]:
        """
        Record audio from microphone with VAD, then transcribe.
        
        Args:
            timeout: Max recording duration in seconds (default from config)
            
        Returns:
            Transcribed text string, or None if nothing detected
        """
        timeout = timeout or AUDIO_MAX_DURATION
        audio_data = self._record_with_vad(timeout)

        if audio_data is None or len(audio_data) < AUDIO_SAMPLE_RATE * 0.5:
            return None

        return self._transcribe(audio_data)

    def transcribe_file(self, audio_path: str) -> Optional[str]:
        """Transcribe an audio file."""
        if self._model is None:
            return None
        try:
            segments, info = self._model.transcribe(audio_path)
            text = " ".join([seg.text for seg in segments]).strip()
            return text if text else None
        except Exception as e:
            logger.error(f"File transcription failed: {e}")
            return None

    def _record_with_vad(self, max_duration: float) -> Optional[np.ndarray]:
        """
        Record audio from microphone with Voice Activity Detection.
        Stops when silence exceeds AUDIO_SILENCE_DURATION.
        
        Returns:
            numpy array of audio samples, or None
        """
        try:
            import sounddevice as sd

            logger.info("Listening... (speak now)")
            chunk_duration = 0.1  # 100ms chunks
            chunk_samples = int(AUDIO_SAMPLE_RATE * chunk_duration)
            max_chunks = int(max_duration / chunk_duration)
            silence_chunks = int(AUDIO_SILENCE_DURATION / chunk_duration)

            recorded_chunks = []
            silent_count = 0
            has_speech = False

            stream = sd.InputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype="float32",
                blocksize=chunk_samples
            )
            stream.start()

            for _ in range(max_chunks):
                audio_chunk, _ = stream.read(chunk_samples)
                audio_flat = audio_chunk.flatten()
                recorded_chunks.append(audio_flat)

                # Check audio level for VAD
                rms = np.sqrt(np.mean(audio_flat ** 2))

                if rms > AUDIO_SILENCE_THRESHOLD:
                    silent_count = 0
                    has_speech = True
                else:
                    silent_count += 1

                # Stop if we've had speech and then silence
                if has_speech and silent_count >= silence_chunks:
                    logger.info("Silence detected — stopping recording")
                    break

            stream.stop()
            stream.close()

            if not has_speech:
                logger.info("No speech detected")
                return None

            audio_data = np.concatenate(recorded_chunks)
            logger.info(f"Recorded {len(audio_data) / AUDIO_SAMPLE_RATE:.1f}s of audio")
            return audio_data

        except Exception as e:
            logger.error(f"Audio recording failed: {e}")
            return None

    def _transcribe(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe a numpy audio array using faster-whisper.
        
        Args:
            audio_data: Float32 audio samples at 16kHz
            
        Returns:
            Transcribed text string
        """
        if self._model is None:
            logger.error("Whisper model not loaded — cannot transcribe")
            return None

        try:
            segments, info = self._model.transcribe(
                audio_data,
                language="en",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                )
            )

            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            text = " ".join(text_parts).strip()

            if text:
                logger.info(f"Transcribed: \"{text}\"")
                return text
            else:
                logger.info("Transcription returned empty text")
                return None

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    def get_status(self) -> dict:
        """Return STT module status."""
        return {
            "model_loaded": self._model is not None,
            "model_name": WHISPER_MODEL,
            "device": WHISPER_DEVICE,
        }


class VoiceInput:
    """
    Combined voice input handler — wake word + STT.
    Provides a unified interface for the orchestrator.
    """

    def __init__(self, on_command: Callable[[str], None] = None):
        """
        Args:
            on_command: Callback invoked with transcribed text when user speaks
        """
        self.on_command = on_command
        self._active = False
        self._listening_for_command = False

        # Initialize sub-modules
        self.wake_detector = WakeWordDetector(on_wake=self._on_wake_detected)
        self.stt = SpeechToText()

        logger.info("Voice input system initialized")

    def _on_wake_detected(self):
        """Called when wake word is detected — start recording command."""
        if self._listening_for_command:
            return  # Already listening

        self._listening_for_command = True
        logger.info("Wake word activated — listening for command...")

        # Record and transcribe in a thread to not block wake word
        thread = threading.Thread(target=self._process_command, daemon=True)
        thread.start()

    def _process_command(self):
        """Record user speech, transcribe, and invoke callback."""
        try:
            text = self.stt.listen_and_transcribe()
            if text and self.on_command:
                self.on_command(text)
        except Exception as e:
            logger.error(f"Command processing error: {e}")
        finally:
            self._listening_for_command = False

    def start(self):
        """Start the full voice input pipeline."""
        self._active = True
        self.wake_detector.start()
        logger.info("Voice input pipeline active — say 'Hey Jarvis'")

    def stop(self):
        """Stop all voice input."""
        self._active = False
        self.wake_detector.stop()
        logger.info("Voice input pipeline stopped")

    def listen_once(self) -> Optional[str]:
        """
        Listen for a single command without wake word (for manual trigger).
        Blocks until speech is detected and transcribed.
        """
        return self.stt.listen_and_transcribe()

    def get_status(self) -> dict:
        """Return voice input status."""
        return {
            "active": self._active,
            "listening_for_command": self._listening_for_command,
            "wake_word_model": WAKE_WORD_MODEL,
            "stt": self.stt.get_status(),
        }
