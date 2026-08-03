from __future__ import annotations

# === ADACOR PATCH: Voice/Narrator ausgeblendet ===
# Transcribe/TTS/Narrator sind im Upstream hartkodiert gegen api.mistral.ai
# (Mistral-SDK-Realtime-Protokoll bzw. Mistral-Chat-Modell). Adacor hat einen
# eigenen Whisper-Endpoint, aber (noch) kein TTS — bis der Adacor-Voice-Pfad
# steht, werden Voice-Mode und Narrator vollstaendig deaktiviert und aus der UI
# ausgeblendet, damit keine Audio-/Turn-Daten an Mistral gehen.
#
# Reaktivieren: diesen Schalter auf True setzen — setzt aber voraus, dass die
# Adacor-Transcribe-/TTS-Clients existieren, sonst zeigen die Features wieder
# auf Mistral.
VOICE_FEATURES_ENABLED = False


def voice_features_enabled() -> bool:
    # Bewusst als Funktion (nicht direkter Konstanten-Import), damit der Schalter
    # zur Laufzeit gelesen und in Tests via monkeypatch umgeschaltet werden kann.
    return VOICE_FEATURES_ENABLED
