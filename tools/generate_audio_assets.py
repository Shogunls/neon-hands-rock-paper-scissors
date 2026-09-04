"""Generate the game's original, royalty-free WAV audio assets."""

import math
import random
import struct
import wave
from pathlib import Path

RATE = 22050
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "audio"
OUTPUT.mkdir(parents=True, exist_ok=True)


def write_wav(name, samples):
    peak = max(1.0, max(abs(value) for value in samples))
    scale = 0.92 / peak
    data = b"".join(
        struct.pack("<h", int(max(-1, min(1, value * scale)) * 32767))
        for value in samples
    )
    with wave.open(str(OUTPUT / name), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(RATE)
        target.writeframes(data)


def soft_music():
    duration = 24.0
    total = int(duration * RATE)
    chords = (
        (261.63, 329.63, 392.00, 493.88),
        (220.00, 261.63, 329.63, 392.00),
        (174.61, 220.00, 261.63, 329.63),
        (196.00, 246.94, 293.66, 392.00),
        (261.63, 329.63, 392.00, 493.88),
        (220.00, 261.63, 329.63, 392.00),
        (174.61, 220.00, 261.63, 349.23),
        (196.00, 246.94, 293.66, 392.00),
    )
    samples = []
    for index in range(total):
        time = index / RATE
        chord = chords[min(7, int(time // 3))]
        local = time % 3
        pad_envelope = min(1, local / 0.55, (3 - local) / 0.7)
        pad = (
            sum(
                math.sin(math.tau * frequency * time + voice * 0.7)
                + 0.22 * math.sin(math.tau * frequency * 0.5 * time)
                for voice, frequency in enumerate(chord)
            )
            / 5
        )
        bell_phase = time % 1.5
        bell_frequency = chord[(int(time / 1.5) + 2) % len(chord)] * 2
        bell = (
            math.sin(math.tau * bell_frequency * time)
            * math.exp(-4.2 * bell_phase)
            * 0.12
        )
        global_fade = min(1, time / 0.35, (duration - time) / 0.35)
        samples.append((pad * pad_envelope * 0.18 + bell) * global_fade)
    write_wav("soft_loop.wav", samples)


def battle_music():
    """A focused 104 BPM loop: energetic, but still soft enough for menus."""
    bpm = 104
    beat = 60 / bpm
    duration = beat * 32
    total = int(duration * RATE)
    chords = (
        (146.83, 174.61, 220.00),  # D minor
        (116.54, 146.83, 174.61),  # B-flat
        (130.81, 164.81, 196.00),  # C major
        (110.00, 138.59, 164.81),  # A minor
    )
    rng = random.Random(16384)
    previous_noise = 0.0
    samples = []
    for index in range(total):
        time = index / RATE
        beat_position = time / beat
        beat_index = int(beat_position)
        local_beat = time % beat
        half_beat = beat / 2
        local_half = time % half_beat
        bar_index = int(beat_position // 4)
        chord = chords[bar_index % len(chords)]

        bass_envelope = math.exp(-3.6 * local_beat)
        bass_frequency = chord[0] / 2
        bass = (
            (
                math.sin(math.tau * bass_frequency * time)
                + 0.24 * math.sin(math.tau * bass_frequency * 2 * time)
            )
            * 0.20
            * bass_envelope
        )

        arp_index = int(time / half_beat)
        arp_frequency = chord[(arp_index + bar_index) % 3] * 2
        arp_envelope = math.exp(-7.0 * local_half)
        arpeggio = (
            (
                math.sin(math.tau * arp_frequency * time)
                + 0.22 * math.sin(math.tau * arp_frequency * 2 * time)
            )
            * 0.105
            * arp_envelope
        )

        kick_phase = local_beat
        kick_frequency = 47 + 54 * math.exp(-24 * kick_phase)
        kick = (
            math.sin(math.tau * kick_frequency * kick_phase)
            * math.exp(-18 * kick_phase)
            * 0.42
        )

        raw_noise = rng.uniform(-1, 1)
        high_noise = raw_noise - previous_noise
        previous_noise = raw_noise
        hat = high_noise * math.exp(-48 * local_half) * 0.052

        snare = 0.0
        if beat_index % 4 in (1, 3):
            snare = high_noise * math.exp(-20 * local_beat) * 0.105

        pad = (
            sum(
                math.sin(math.tau * frequency * time + voice * 0.9)
                for voice, frequency in enumerate(chord)
            )
            * 0.018
        )
        global_fade = min(1, time / 0.06, (duration - time) / 0.06)
        samples.append((bass + arpeggio + kick + hat + snare + pad) * global_fade)
    write_wav("battle_loop.wav", samples)


def victory_fanfare():
    """Bright brass call with a short marching-snare roll."""
    duration = 3.0
    notes = (
        (0.00, 0.26, 392.00, 0.34),
        (0.34, 0.18, 392.00, 0.31),
        (0.55, 0.18, 440.00, 0.31),
        (0.78, 0.28, 493.88, 0.35),
        (1.10, 1.48, 523.25, 0.40),
        (1.10, 1.48, 659.25, 0.23),
        (1.10, 1.48, 783.99, 0.19),
    )
    drum_hits = tuple(index * 0.105 for index in range(10)) + (
        1.08,
        1.30,
        1.52,
        1.74,
    )
    rng = random.Random(32768)
    samples = []
    smooth_noise = 0.0
    for index in range(int(duration * RATE)):
        time = index / RATE
        brass = 0.0
        for start, note_duration, frequency, amplitude in notes:
            local = time - start
            if 0 <= local <= note_duration:
                attack = min(1, local / 0.035)
                release = min(1, (note_duration - local) / 0.16)
                envelope = attack * release
                vibrato = 1 + 0.0035 * math.sin(math.tau * 5.2 * local)
                phase = math.tau * frequency * vibrato * local
                horn = (
                    math.sin(phase)
                    + 0.43 * math.sin(2 * phase)
                    + 0.18 * math.sin(3 * phase)
                )
                brass += horn * amplitude * envelope

        noise = rng.uniform(-1, 1)
        smooth_noise = smooth_noise * 0.32 + noise * 0.68
        snare = 0.0
        for hit in drum_hits:
            local = time - hit
            if 0 <= local < 0.13:
                snare += smooth_noise * math.exp(-34 * local) * 0.16

        cymbal_local = time - 1.10
        cymbal = 0.0
        if cymbal_local >= 0:
            cymbal = (noise - smooth_noise) * math.exp(-2.8 * cymbal_local) * 0.055
        global_fade = min(1, time / 0.02, (duration - time) / 0.20)
        samples.append((brass + snare + cymbal) * global_fade)
    write_wav("victory_fanfare.wav", samples)


def defeat_sting():
    """Three descending muted-horn calls for a clear loss cue."""
    duration = 2.3
    notes = (
        (0.00, 0.54, 220.00, 0.34),
        (0.67, 0.56, 174.61, 0.36),
        (1.37, 0.78, 146.83, 0.40),
    )
    samples = []
    for index in range(int(duration * RATE)):
        time = index / RATE
        value = 0.0
        for start, note_duration, frequency, amplitude in notes:
            local = time - start
            if 0 <= local <= note_duration:
                attack = min(1, local / 0.055)
                release = min(1, (note_duration - local) / 0.22)
                envelope = attack * release
                droop = 1 - 0.055 * (local / note_duration)
                phase = math.tau * frequency * droop * local
                muted_horn = (
                    math.sin(phase)
                    + 0.34 * math.sin(2 * phase)
                    + 0.10 * math.sin(3 * phase)
                )
                value += muted_horn * amplitude * envelope
        global_fade = min(1, time / 0.025, (duration - time) / 0.14)
        samples.append(value * global_fade)
    write_wav("defeat_sting.wav", samples)


def soft_click():
    duration = 0.095
    rng = random.Random(2048)
    samples = []
    previous = 0.0
    for index in range(int(duration * RATE)):
        time = index / RATE
        noise = rng.uniform(-1, 1)
        previous = previous * 0.72 + noise * 0.28
        envelope = math.exp(-42 * time)
        tone = math.sin(math.tau * (720 - time * 1800) * time)
        samples.append((tone * 0.38 + previous * 0.16) * envelope)
    write_wav("soft_click.wav", samples)


def hand_whoosh():
    duration = 0.24
    rng = random.Random(4096)
    samples = []
    smooth = 0.0
    for index in range(int(duration * RATE)):
        time = index / RATE
        phase = time / duration
        smooth = smooth * 0.86 + rng.uniform(-1, 1) * 0.14
        envelope = math.sin(math.pi * phase) ** 1.8
        whistle = math.sin(math.tau * (780 - 370 * phase) * time) * 0.12
        samples.append((smooth * 0.48 + whistle) * envelope)
    write_wav("hand_whoosh.wav", samples)


def reveal_swish():
    duration = 0.58
    rng = random.Random(8192)
    samples = []
    smooth = 0.0
    for index in range(int(duration * RATE)):
        time = index / RATE
        phase = time / duration
        smooth = smooth * 0.9 + rng.uniform(-1, 1) * 0.1
        whoosh = smooth * math.sin(math.pi * phase) * 0.52
        chime_envelope = math.exp(-5.2 * max(0, time - 0.16))
        chime = 0.0
        if time > 0.16:
            chime = (
                (
                    math.sin(math.tau * 659.25 * time)
                    + 0.55 * math.sin(math.tau * 987.77 * time)
                )
                * 0.16
                * chime_envelope
            )
        samples.append(whoosh + chime)
    write_wav("reveal_swish.wav", samples)


if __name__ == "__main__":
    soft_music()
    battle_music()
    victory_fanfare()
    defeat_sting()
    soft_click()
    hand_whoosh()
    reveal_swish()
    for path in sorted(OUTPUT.glob("*.wav")):
        print(path.name, path.stat().st_size)
