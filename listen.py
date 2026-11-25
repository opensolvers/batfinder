#!/usr/bin/env python3
"""Keep scoring the Vleermic with BattyBirdNET.

The microphone records 384 kHz mono S16. The EU classifier is trained at
256 kHz, so each block is resampled before a 144000-sample window is scored.
A hit is five windows in a row, about 2.3 seconds, of the same species at 0.50 or higher.
Every window is also written to overview.json for the local web page.
"""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np
import onnxruntime as ort
import soxr

DIR = os.environ.get("BATFINDER_DIR", os.path.dirname(os.path.abspath(__file__)))
BACKBONE = f"{DIR}/birdnet_backbone.onnx"
HEAD = f"{DIR}/BattyBirdNET-EU-256kHz_fp32.onnx"
LABELS_PATH = f"{DIR}/BattyBirdNET-EU-256kHz_Labels.txt"
HITS = f"{DIR}/hits.log"
OVERVIEW = f"{DIR}/overview.json"

IN_RATE = 384_000
OUT_RATE = 256_000
WINDOW = 144_000
OVERLAP = 36_000
HOP = WINDOW - OVERLAP
THRESH = 0.50
CONFIRM = 5
READ_FRAMES = 48_000
DEVICE = "hw:VleermicUSB384k,0"

arecord = None


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def say(msg, hit=False):
    line = f"{utc()} {msg}"
    print(line, flush=True)
    if hit:
        with open(HITS, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def stop(signum, _frame):
    if arecord is not None and arecord.poll() is None:
        arecord.terminate()
    raise SystemExit(0)


def load_labels():
    with open(LABELS_PATH, encoding="utf-8") as handle:
        labels = [line.strip() for line in handle if line.strip()]
    if not labels:
        raise SystemExit("label file is empty")
    return labels


def open_sessions():
    if hasattr(ort, "set_default_logger_severity"):
        ort.set_default_logger_severity(3)
    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    opts.intra_op_num_threads = 2
    opts.inter_op_num_threads = 1
    backbone = ort.InferenceSession(
        BACKBONE, opts, providers=["CPUExecutionProvider"]
    )
    head = ort.InferenceSession(HEAD, opts, providers=["CPUExecutionProvider"])
    return backbone, head


def score(backbone, head, labels, frame):
    embedding = backbone.run(None, {"input": frame.reshape(1, WINDOW)})[0]
    logits = head.run(None, {"input": embedding.reshape(1, 1024)})[0].reshape(-1)
    probs = 1.0 / (1.0 + np.exp(-logits))
    index = int(np.argmax(probs))
    name = labels[index] if index < len(labels) else f"class {index}"
    return name, float(probs[index])


def load_history():
    history = {"started": utc(), "minutes": [], "hits": []}
    try:
        with open(OVERVIEW, encoding="utf-8") as handle:
            old = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return history
    if isinstance(old.get("started"), str):
        history["started"] = old["started"]
    if isinstance(old.get("minutes"), list):
        history["minutes"] = old["minutes"][-360:]
    if isinstance(old.get("hits"), list):
        history["hits"] = old["hits"][-200:]
    return history


def publish(history, windows, latest, recent):
    payload = {
        "updated": utc(),
        "started": history["started"],
        "device": DEVICE,
        "threshold": THRESH,
        "windows": windows,
        "latest": latest,
        "recent": recent,
        "minutes": history["minutes"],
        "hits": history["hits"],
    }
    temporary = OVERVIEW + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    os.replace(temporary, OVERVIEW)


def remember(history, windows, recent, name, conf, rms, hit):
    stamp = utc()
    item = {
        "t": stamp,
        "species": name,
        "score": round(conf, 4),
        "rms": round(rms, 5),
        "hit": bool(hit),
    }
    recent.append(item)
    del recent[:-40]
    minute = stamp[:16]
    if history["minutes"] and history["minutes"][-1].get("t") == minute:
        bucket = history["minutes"][-1]
    else:
        bucket = {
            "t": minute,
            "species": name,
            "score": 0.0,
            "rms": 0.0,
            "windows": 0,
            "hits": 0,
        }
        history["minutes"].append(bucket)
        del history["minutes"][:-360]
    bucket["windows"] += 1
    bucket["rms"] = round(max(bucket["rms"], rms), 5)
    if conf >= bucket["score"]:
        bucket["score"] = round(conf, 4)
        bucket["species"] = name
    if hit:
        bucket["hits"] += 1
        history["hits"].append(
            {
                "t": stamp,
                "species": name,
                "score": round(conf, 4),
                "rms": round(rms, 5),
            }
        )
        del history["hits"][:-200]
    publish(history, windows, item, recent)
    return item


def main():
    global arecord
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    labels = load_labels()
    backbone, head = open_sessions()
    resampler = soxr.ResampleStream(
        IN_RATE, OUT_RATE, 1, dtype="float32", quality="HQ"
    )
    arecord = subprocess.Popen(
        [
            "arecord",
            "-q",
            "-D",
            DEVICE,
            "-f",
            "S16_LE",
            "-r",
            str(IN_RATE),
            "-c",
            "1",
            "-t",
            "raw",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    say(
        f"listening {DEVICE} {IN_RATE} Hz -> {OUT_RATE} Hz "
        f"window {WINDOW / OUT_RATE:.4f}s hop {HOP / OUT_RATE:.4f}s "
        f"threshold {THRESH:.2f} confirm {CONFIRM} labels {len(labels)}"
    )

    history = load_history()
    pending = np.empty(0, np.float32)
    raw_need = READ_FRAMES * 2
    windows = 0
    streak_name = None
    streak = 0
    opened = 0
    recent = []
    period_max = 0.0
    period_rms = 0.0
    period_start = time.monotonic()

    try:
        while True:
            if arecord.poll() is not None:
                say(f"arecord exited {arecord.returncode}")
                raise SystemExit(1)
            blob = arecord.stdout.read(raw_need)
            if not blob:
                say("arecord pipe closed")
                raise SystemExit(1)
            if len(blob) % 2:
                blob = blob[:-1]
            pcm = np.frombuffer(blob, dtype="<i2").astype(np.float32) / 32768.0
            converted = np.asarray(
                resampler.resample_chunk(pcm), dtype=np.float32
            ).reshape(-1)
            pending = np.concatenate((pending, converted))
            while pending.size >= WINDOW:
                frame = np.ascontiguousarray(pending[:WINDOW])
                pending = pending[HOP:]
                rms = float(np.sqrt(np.mean(np.square(frame))))
                name, conf = score(backbone, head, labels, frame)
                windows += 1
                period_max = max(period_max, conf)
                period_rms = max(period_rms, rms)
                if conf >= THRESH and name == streak_name:
                    streak += 1
                elif conf >= THRESH:
                    streak_name = name
                    streak = 1
                else:
                    streak_name = None
                    streak = 0
                is_hit = streak >= CONFIRM
                remember(history, windows, recent, name, conf, rms, is_hit)
                if is_hit:
                    say(
                        f"HIT {name} {conf:.3f} rms={rms:.4f} window={windows}",
                        hit=True,
                    )
                elif opened < 4:
                    say(f"window={windows} rms={rms:.4f} top={name} {conf:.3f}")
                    opened += 1
                now = time.monotonic()
                if now - period_start >= 60.0:
                    say(
                        f"status windows={windows} max={period_max:.3f} "
                        f"rms={period_rms:.4f}"
                    )
                    period_max = 0.0
                    period_rms = 0.0
                    period_start = now
    finally:
        if arecord is not None and arecord.poll() is None:
            arecord.terminate()
            try:
                arecord.wait(timeout=2)
            except subprocess.TimeoutExpired:
                arecord.kill()


if __name__ == "__main__":
    main()
