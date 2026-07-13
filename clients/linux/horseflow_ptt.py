#!/usr/bin/env python3
"""Hold Ctrl+Space to dictate; the hotkey is swallowed before applications see it."""

import argparse
import json
import os
import selectors
import signal
import subprocess
import time
import urllib.request
import uuid
from contextlib import suppress
from pathlib import Path

from evdev import InputDevice, UInput, ecodes, list_devices

CTRL_KEYS = {ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL}
SPACE = ecodes.KEY_SPACE
EXCLUDED_DEVICE_NAMES = ("ydotool", "horseflow")
RECORDING_DIR = Path("/tmp/horseflow")


def required_environment(name: str) -> str:
    return os.environ[name]


def keyboards() -> list[InputDevice]:
    devices = []
    for path in list_devices():
        device = InputDevice(path)
        keys = device.capabilities().get(ecodes.EV_KEY, [])
        if (
            SPACE in keys
            and ecodes.KEY_LEFTCTRL in keys
            and not any(name in device.name.lower() for name in EXCLUDED_DEVICE_NAMES)
        ):
            devices.append(device)
        else:
            device.close()
    return devices


class Recorder:
    def __init__(self, microphone: str) -> None:
        self.microphone = microphone
        self.process: subprocess.Popen[bytes] | None = None
        self.path: Path | None = None

    def start(self) -> None:
        if self.process is not None:
            return
        self.path = RECORDING_DIR / f"recording-{time.time_ns()}.wav"
        self.process = subprocess.Popen(
            [
                "pw-record",
                "--target",
                self.microphone,
                "--rate",
                "16000",
                "--channels",
                "1",
                str(self.path),
            ]
        )

    def abort(self) -> None:
        if self.process is None or self.path is None:
            return
        self.process.kill()
        self.process.wait()
        self.path.unlink(missing_ok=True)
        self.process = None
        self.path = None

    def finish(self) -> None:
        if self.process is None or self.path is None:
            return
        subprocess.Popen(
            [
                str(Path(__file__).resolve()),
                "--finish",
                str(self.process.pid),
                str(self.path),
            ],
            env=os.environ,
            start_new_session=True,
        )
        self.process = None
        self.path = None


def finish_recording(pid: int, recording: Path) -> None:
    time.sleep(0.3)
    with suppress(ProcessLookupError):
        os.kill(pid, signal.SIGINT)
    time.sleep(0.2)

    try:
        text = upload(recording, required_environment("HORSEFLOW_API_URL"))
    finally:
        recording.unlink(missing_ok=True)

    if text:
        subprocess.run(["wl-copy", "--", text], check=True)
        subprocess.run(
            ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
            check=True,
        )
        subprocess.run(
            ["notify-send", "-a", "Horseflow", "-t", "3000", "Horseflow", text],
            check=True,
        )
    else:
        subprocess.run(
            [
                "notify-send",
                "-a",
                "Horseflow",
                "-t",
                "2000",
                "Horseflow",
                "(nothing heard)",
            ],
            check=True,
        )


def upload(recording: Path, api_url: str) -> str:
    boundary = f"Horseflow-{uuid.uuid4()}"
    audio = recording.read_bytes()
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="audio"; filename="recording.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n"
    ).encode()
    body += audio
    body += f"\r\n--{boundary}--\r\n".encode()

    request = urllib.request.Request(
        api_url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    return payload["text"].strip()


def run_daemon() -> None:
    microphone = required_environment("HORSEFLOW_MIC")
    required_environment("HORSEFLOW_API_URL")
    RECORDING_DIR.mkdir(parents=True, exist_ok=True)

    devices = keyboards()
    if not devices:
        raise SystemExit("no physical keyboard with Ctrl+Space found")

    clone = UInput.from_device(*devices, name="horseflow-keyboard")
    selector = selectors.DefaultSelector()
    for device in devices:
        device.grab()
        selector.register(device, selectors.EVENT_READ)
        print(f"grabbed {device.path} ({device.name})", flush=True)

    recorder = Recorder(microphone)
    ctrl_down: set[int] = set()
    speculative = False
    push_to_talk = False
    swallowing_space = False

    try:
        while True:
            for key, _ in selector.select():
                for event in key.fileobj.read():
                    if event.type == ecodes.EV_KEY:
                        if event.code in CTRL_KEYS:
                            if event.value == 1:
                                if not ctrl_down:
                                    speculative = True
                                    recorder.start()
                                ctrl_down.add(event.code)
                            elif event.value == 0:
                                ctrl_down.discard(event.code)
                                if not ctrl_down:
                                    if push_to_talk:
                                        push_to_talk = False
                                        recorder.finish()
                                    elif speculative:
                                        recorder.abort()
                                    speculative = False
                        elif event.code == SPACE:
                            if event.value == 1 and ctrl_down and not swallowing_space:
                                swallowing_space = True
                                if not (speculative or push_to_talk):
                                    recorder.start()
                                speculative = False
                                push_to_talk = True
                                continue
                            if swallowing_space:
                                if event.value == 0:
                                    swallowing_space = False
                                    if push_to_talk:
                                        push_to_talk = False
                                        recorder.finish()
                                continue
                        elif event.value == 1 and speculative and not push_to_talk:
                            speculative = False
                            recorder.abort()
                    clone.write_event(event)
    finally:
        recorder.abort()
        clone.close()
        for device in devices:
            device.ungrab()
            device.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--finish", nargs=2, metavar=("PID", "WAV"))
    arguments = parser.parse_args()
    if arguments.finish:
        finish_recording(int(arguments.finish[0]), Path(arguments.finish[1]))
    else:
        run_daemon()


if __name__ == "__main__":
    main()
