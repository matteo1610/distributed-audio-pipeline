import io
import json
import types
import wave
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import worker


class _FakeObj:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data

    def close(self):
        return None

    def release_conn(self):
        return None


class _FakeMinio:
    def __init__(self, data):
        self._data = data

    def get_object(self, _bucket, _object_key):
        return _FakeObj(self._data)


class _AckChannel:
    def __init__(self):
        self.tags = []

    def basic_ack(self, delivery_tag):
        self.tags.append(delivery_tag)


def _wav_bytes(frame_rate=8000, channels=1, seconds=1):
    frame_width = 2 * channels
    frames = b"\x00" * frame_width * frame_rate * seconds
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(frame_rate)
            wav_file.writeframes(frames)
        return buffer.getvalue()


def test_extract_basic_audio_features_for_valid_wav():
    data = _wav_bytes(frame_rate=16000, channels=2, seconds=1)

    duration, sample_rate, channels = worker.extract_basic_audio_features(data)

    assert duration == 1.0
    assert sample_rate == 16000
    assert channels == 2


def test_extract_basic_audio_features_for_invalid_data():
    duration, sample_rate, channels = worker.extract_basic_audio_features(b"not-a-wav")

    assert duration is None
    assert sample_rate is None
    assert channels is None


def test_process_message_success_acknowledges(monkeypatch):
    calls = []

    def fake_set_job_status(job_id, status, error_message=None):
        calls.append((job_id, status, error_message))

    monkeypatch.setattr(worker, "set_job_status", fake_set_job_status)
    monkeypatch.setattr(worker, "save_result", lambda *_args: None)
    monkeypatch.setattr(worker, "minio_client", lambda: _FakeMinio(_wav_bytes()))

    channel = _AckChannel()
    method = types.SimpleNamespace(delivery_tag="t-1")
    payload = {"job_id": "job-1", "object_key": "obj-1"}

    worker.process_message(channel, method, None, json.dumps(payload).encode("utf-8"))

    assert channel.tags == ["t-1"]
    assert calls[0][1] == "PROCESSING"
    assert calls[-1][1] == "DONE"


def test_process_message_failure_marks_failed(monkeypatch):
    calls = []

    def fake_set_job_status(job_id, status, error_message=None):
        calls.append((job_id, status, error_message))

    monkeypatch.setattr(worker, "set_job_status", fake_set_job_status)
    monkeypatch.setattr(worker, "minio_client", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    channel = _AckChannel()
    method = types.SimpleNamespace(delivery_tag="t-2")
    payload = {"job_id": "job-2", "object_key": "obj-2"}

    worker.process_message(channel, method, None, json.dumps(payload).encode("utf-8"))

    assert channel.tags == ["t-2"]
    assert calls[0][1] == "PROCESSING"
    assert calls[-1][1] == "FAILED"
    assert "boom" in calls[-1][2]
