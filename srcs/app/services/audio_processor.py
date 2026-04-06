"""Audio processing service."""
import io
import wave


class AudioProcessor:
    """Handles audio file processing and feature extraction."""

    @staticmethod
    def extract_audio_features(audio_data: bytes) -> tuple[float | None, int | None, int | None]:
        """Extract basic audio features from audio data.
        
        Args:
            audio_data: Raw audio bytes (expects WAV format).
            
        Returns:
            Tuple of (duration_seconds, sample_rate, channels).
            Returns (None, None, None) if extraction fails.
        """
        try:
            with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
                frame_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                frame_count = wav_file.getnframes()
                duration = frame_count / float(frame_rate)
                return duration, frame_rate, channels
        except Exception:
            return None, None, None

    @staticmethod
    def validate_audio_data(audio_data: bytes) -> bool:
        """Validate if audio data is valid WAV format.
        
        Args:
            audio_data: Raw audio bytes.
            
        Returns:
            True if valid, False otherwise.
        """
        try:
            with wave.open(io.BytesIO(audio_data), "rb") as wav_file:
                # If we can open it, try to read frame count
                wav_file.getnframes()
            return True
        except Exception:
            return False
