# Batfinder

Listener for the [Vleermic](https://www.veldshop.nl/en/vleermic-384khz-ultrasonic-microphone.html) on the Banana Pi SM10. BattyBirdNET scores the microphone, and a small page shows what was heard.

`listen.py` records with ALSA at 384 kHz, resamples to 256 kHz with soxr, and scores windows of 144,000 samples (0.56 s) with the BirdNET v2.4 backbone and the EU head. ONNX Runtime uses `CPUExecutionProvider`. `web.py` reads `overview.json` and serves the page on port 8090.

A species name is shown from 10% upward. A confirmation is five windows in a row of the same species at 50% or higher, about 2.3 seconds. The microphone is a [Vleermic 384 kHz](https://www.veldshop.nl/en/vleermic-384khz-ultrasonic-microphone.html) ([Nederlands](https://www.veldshop.nl/nl/vleermic-384khz-ultrasone-microfoon.html), [manual](https://cdn.webshopapp.com/shops/39297/files/493997606/vleermic-nl-en-v03.pdf)). ALSA sees it as `hw:VleermicUSB384k,0`. It accepts only 384 kHz, 16-bit, mono.

## Models

The weights are not in this repo. They are CC BY-NC-SA 4.0. Credit BirdNET wherever the models are used.

```bash
cd /home/eessi/battybirdnet
curl -L -o birdnet_backbone.onnx \
  https://huggingface.co/biodiversica/BirdNET-onnx-backbone/resolve/main/birdnet_backbone.onnx
curl -L -o BattyBirdNET-EU-256kHz_fp32.onnx \
  https://huggingface.co/tphakala/BattyBirdNET-onnx/resolve/main/fp32/BattyBirdNET-EU-256kHz_fp32.onnx
curl -L -o BattyBirdNET-EU-256kHz_Labels.txt \
  https://huggingface.co/tphakala/BattyBirdNET-onnx/resolve/main/labels/BattyBirdNET-EU-256kHz_Labels.txt
```

## Install

On Bianbu, next to the models:

```bash
sudo apt install python3-onnxruntime python3-soxr python3-numpy alsa-utils
install -m 755 listen.py web.py /home/eessi/battybirdnet/
sudo install -m 644 systemd/battybirdnet.service systemd/battybirdnet-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now battybirdnet.service battybirdnet-web.service
```

The service runs as `eessi` and receives the `audio` group through `SupplementaryGroups`, because the ALSA device is `root:audio`. Set `BATFINDER_DIR` when the scripts do not sit next to the models.

The page is on port 8090 and opens in English. NL in the header switches to Dutch, and the browser remembers that choice. `journalctl -u battybirdnet -f` follows the listener. Confirmations are also appended to `hits.log`.
