# Prompt — audio_track.mp3 (o .wav)
# Traccia audio per il video promo LibreFolio (40 secondi)
#
# File output:  audio_track.mp3   (questa stessa cartella)
# Durata:       40 secondi esatti (1200 frame @ 30fps)
# Tool:         Gemini (MusicFX) / Suno / Udio / ElevenLabs Sound Effects
# ─────────────────────────────────────────────────────────────────

## STRUTTURA NARRATIVA DEL VIDEO (per riferimento)

  0–5s   → Scena 1: Hook (caos, problema)
  5–12s  → Scena 2: Hero (soluzione, dashboard)
 12–20s  → Scena 3: Multi-Asset (features, grafici)
 20–28s  → Scena 4: Mobile (ovunque, accessibilità)
 28–35s  → Scena 5: Open Source (valori)
 35–40s  → Scena 6: CTA (chiusura con logo)

## PROMPT PRINCIPALE (Gemini MusicFX / MusicLM)

Modern technology background music, 40 seconds, no lyrics.
Structure:
- 0-5s: slightly tense, fragmented electronic pulses (problem setup)
- 5-12s: clean cinematic swell, strings + synth rise (resolution moment)
- 12-20s: confident upbeat electronic, subtle drum groove (features showcase)
- 20-28s: lighter, mobile-feel, playful synth arp (accessibility)
- 28-35s: open and hopeful, community feel, warm pads (open source values)
- 35-40s: triumphant brief resolution, logo sting feel (CTA closer)
Style: cinematic tech promo, similar to Apple/Stripe product videos.
Tempo: 105 BPM. Key: D minor resolving to D major at second half.
No vocals, no drums in first 5 seconds, builds gradually.

## PROMPT ALTERNATIVO (Suno / Udio — stile più preciso)

Instrumental corporate tech promo music, 40 seconds.
Genre: modern cinematic electronic.
BPM: 105.
Instruments: synthesizer pads, subtle piano, electronic drums (from 8s),
light strings, bass, arpeggiator.
Arc: starts sparse and slightly uneasy (0-5s) → brightens and swells (5-12s)
→ confident groove (12-28s) → warm and open (28-35s) → punchy logo sting close (35-40s).
Mix: wide stereo, -14 LUFS for video use, no vocals, no lyrics.
Reference vibe: Stripe product video, Vercel launch trailer, Linear app promo.

## PROPOSTA TESTO PER SOUND EFFECT (ElevenLabs / Freesound)

Se non riesci a generare 40s interi, puoi comporre con:
- 0-5s:   sfx/whoosh digitale + glitch elettronico (tensione)
- 5s:     impact/whoosh di transizione (momento soluzione)
- 6-34s:  loop ~28s di tech-corporate-upbeat (dal sito Pixabay/Bensound)
- 35-40s: logo sting breve (3 note ascendenti, stile Apple "ta-da" moderno)

## NOTE TECNICHE

| Parametro | Valore |
|-----------|--------|
| Durata    | 40.0s esatti (oppure 42s con tail fade) |
| Formato   | MP3 320kbps o WAV 44.1kHz/16bit |
| Livello   | -14 LUFS (standard YouTube/social) |
| Canali    | Stereo |
| Nome file | `audio_track.mp3` (questa cartella) |

## COME USARLO NEL CODICE REMOTION

Una volta generato e messo qui, aggiungere in `src/MainVideo.tsx`:

```tsx
import { Audio, staticFile } from "remotion";

// Dentro LibreFolioPromo, prima della <Series>:
<Audio src={staticFile("ai/audio_track.mp3")} />
```

Remotion sincronizza automaticamente l'audio con i frame.
