# Batfinder

Luisteraar voor de Vleermic op de Banana Pi SM10. BattyBirdNET scoort de microfoon, een kleine pagina toont wat er gehoord is.

`listen.py` neemt op via ALSA op 384 kHz, zet dat met soxr om naar 256 kHz en scoort vensters van 144.000 samples (0,56 s) met de BirdNET v2.4-backbone en de EU-kop. ONNX Runtime gebruikt `CPUExecutionProvider`. `web.py` leest `overview.json` en serveert de pagina op poort 8090.

Een soortnaam verschijnt vanaf 10%. Een bevestiging is vijf vensters achter elkaar van dezelfde soort op 50% of hoger, ongeveer 2,3 seconde. De microfoon heet `hw:VleermicUSB384k,0` en levert alleen 384 kHz, 16-bit, mono.

## Modellen

De gewichten staan niet in deze repo. Ze vallen onder CC BY-NC-SA 4.0. BirdNET moet genoemd worden waar de modellen gebruikt worden.

```bash
cd /home/eessi/battybirdnet
curl -L -o birdnet_backbone.onnx \
  https://huggingface.co/biodiversica/BirdNET-onnx-backbone/resolve/main/birdnet_backbone.onnx
curl -L -o BattyBirdNET-EU-256kHz_fp32.onnx \
  https://huggingface.co/tphakala/BattyBirdNET-onnx/resolve/main/fp32/BattyBirdNET-EU-256kHz_fp32.onnx
curl -L -o BattyBirdNET-EU-256kHz_Labels.txt \
  https://huggingface.co/tphakala/BattyBirdNET-onnx/resolve/main/labels/BattyBirdNET-EU-256kHz_Labels.txt
```

## Installatie

Op Bianbu, naast de modellen:

```bash
sudo apt install python3-onnxruntime python3-soxr python3-numpy alsa-utils
install -m 755 listen.py web.py /home/eessi/battybirdnet/
sudo install -m 644 systemd/battybirdnet.service systemd/battybirdnet-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now battybirdnet.service battybirdnet-web.service
```

De service draait als `eessi` en krijgt de groep `audio` via `SupplementaryGroups`, omdat het ALSA-apparaat `root:audio` is. `BATFINDER_DIR` wijst naar een andere map als de scripts niet naast de modellen staan.

De pagina staat op poort 8090. `journalctl -u battybirdnet -f` toont de luisteraar. Bevestigingen komen ook in `hits.log`.
