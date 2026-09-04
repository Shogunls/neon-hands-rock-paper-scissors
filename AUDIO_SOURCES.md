# Audio sources and usage rights

Every sound in Neon Hands was created specifically for this project through mathematical synthesis:

- `assets/audio/soft_loop.wav` — calm 24-second looping menu track.
- `assets/audio/battle_loop.wav` — rhythmic 104 BPM battle loop.
- `assets/audio/soft_click.wav` — soft interface click.
- `assets/audio/hand_whoosh.wav` — short movement whoosh.
- `assets/audio/reveal_swish.wav` — final hand-reveal effect.
- `assets/audio/victory_fanfare.wav` — three-second brass, snare, and bell victory cue.
- `assets/audio/defeat_sting.wav` — descending muted-brass defeat cue.

No third-party recording, sample, melody, or trademark is used. The sounds may be included in this project and its published application.

The menu and battle tracks crossfade when screens change. During a match-result cue, the battle music is temporarily ducked and then restored to the user's configured level.

The deterministic source generator is `tools/generate_audio_assets.py`:

```powershell
.\.venv\Scripts\python.exe .\tools\generate_audio_assets.py
```
