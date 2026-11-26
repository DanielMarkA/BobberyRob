"""Procedural noir-heist BGM loop and UI SFX generator for Bobbery Rob.

Generates seamless looping background music tracks in `static/audio/bgm/`
and tactile UI/event sound effects in `static/audio/sfx/`.

Run once from repository root:
    python -m pip install -r scripts/requirements-audio.txt
    python scripts/generate_audio.py
"""

from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, filtfilt

SR = 44100
ROOT = Path(__file__).resolve().parent.parent
BGM_DIR = ROOT / "static" / "audio" / "bgm"
SFX_DIR = ROOT / "static" / "audio" / "sfx"


def midi_to_hz(note: float) -> float:
    return 440.0 * (2.0 ** ((note - 69.0) / 12.0))


def lowpass(sig: np.ndarray, cutoff_hz: float, order: int = 3) -> np.ndarray:
    b, a = butter(order, min(cutoff_hz / (SR * 0.5), 0.95), btype="low")
    if sig.ndim == 2:
        return np.column_stack([filtfilt(b, a, sig[:, 0]), filtfilt(b, a, sig[:, 1])])
    return filtfilt(b, a, sig)


def bandpass(sig: np.ndarray, low_hz: float, high_hz: float, order: int = 2) -> np.ndarray:
    nyq = SR * 0.5
    b, a = butter(order, [max(low_hz / nyq, 0.001), min(high_hz / nyq, 0.95)], btype="band")
    return filtfilt(b, a, sig)


def add_stereo_delay(
    stereo: np.ndarray, delay_ms: float = 185.0, decay: float = 0.28
) -> np.ndarray:
    """Wrap-around ping-pong echo for seamless looping ambience."""
    d = int(SR * delay_ms / 1000.0)
    out = stereo.copy()
    wet_l = np.roll(stereo[:, 1], d) * decay
    wet_r = np.roll(stereo[:, 0], int(d * 1.35)) * (decay * 0.85)
    out[:, 0] += wet_l
    out[:, 1] += wet_r
    out[:, 0] += np.roll(wet_r, d) * (decay * 0.45)
    out[:, 1] += np.roll(wet_l, int(d * 1.25)) * (decay * 0.4)
    return out


def mix_wrap(
    buf: np.ndarray, start_idx: int, sound: np.ndarray, pan: float = 0.0, gain: float = 1.0
) -> None:
    """Add mono sound into stereo loop buffer with seamless modulo wrap-around."""
    n = buf.shape[0]
    length = len(sound)
    l_gain = gain * np.cos((pan + 1.0) * np.pi / 4.0)
    r_gain = gain * np.sin((pan + 1.0) * np.pi / 4.0)
    indices = (np.arange(length) + start_idx) % n
    np.add.at(buf[:, 0], indices, sound * l_gain)
    np.add.at(buf[:, 1], indices, sound * r_gain)


def synth_rhodes(midi_note: float, dur: float, velocity: float = 0.6) -> np.ndarray:
    """Warm electric piano tone with gentle bell tine and soft decay."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = midi_to_hz(midi_note)
    attack = np.minimum(1.0, t / 0.012)
    body_env = attack * np.exp(-t * 1.55)
    tine_env = attack * np.exp(-t * 9.5)
    tremolo = 1.0 - 0.08 * np.sin(2.0 * np.pi * 4.2 * t)
    sig = (
        1.00 * np.sin(2.0 * np.pi * f * t) * body_env
        + 0.28 * np.sin(2.0 * np.pi * 2.0 * f * t) * np.exp(-t * 2.8) * attack
        + 0.14 * np.sin(2.0 * np.pi * 3.0 * f * t) * tine_env
        + 0.08 * np.sin(2.0 * np.pi * 7.0 * f * t) * tine_env
    )
    return sig * tremolo * velocity


def synth_upright_bass(midi_note: float, dur: float, velocity: float = 0.85) -> np.ndarray:
    """Plucked noir upright bass with subtle finger thump."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = midi_to_hz(midi_note)
    pitch_bend = 1.0 + 0.015 * np.exp(-t * 45.0)
    phase = 2.0 * np.pi * np.cumsum(f * pitch_bend) / SR
    env = np.minimum(1.0, t / 0.008) * np.exp(-t * 2.6)
    sig = (
        1.0 * np.sin(phase)
        + 0.42 * np.sin(2.0 * phase) * np.exp(-t * 5.0)
        + 0.14 * np.sin(3.0 * phase) * np.exp(-t * 9.0)
    ) * env
    return lowpass(sig, 520.0, order=2) * velocity


def synth_pad(midi_notes: list[float], dur: float, velocity: float = 0.22) -> np.ndarray:
    """Slow warm atmospheric pad chord."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    fade_in = np.minimum(1.0, t / 0.9)
    fade_out = np.minimum(1.0, np.maximum(0.0, (dur - t) / 0.9))
    env = fade_in * fade_out
    sig = np.zeros(n, dtype=np.float64)
    for note in midi_notes:
        f = midi_to_hz(note)
        sig += (
            0.55 * np.sin(2.0 * np.pi * f * t)
            + 0.25 * np.sin(2.0 * np.pi * (f * 1.003) * t)
            + 0.20 * np.sin(2.0 * np.pi * (f * 0.997) * t)
            + 0.12 * np.sin(2.0 * np.pi * (2.0 * f) * t)
        )
    sig /= max(1, len(midi_notes))
    return lowpass(sig * env, 950.0, order=2) * velocity


def synth_brush(
    dur: float = 0.075, velocity: float = 0.12, rng: np.random.Generator = None
) -> np.ndarray:
    """Soft brushed jazz hi-hat / clockwork tick."""
    rng = rng or np.random.default_rng(42)
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    filtered = bandpass(noise, 4500.0, 9500.0, order=2)
    env = np.minimum(1.0, t / 0.004) * np.exp(-t * 48.0)
    return filtered * env * velocity


def synth_pulse_kick(dur: float = 0.22, velocity: float = 0.55) -> np.ndarray:
    """Deep heartbeat sub-pulse for interrogation tension."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = 48.0 + 62.0 * np.exp(-t * 28.0)
    phase = 2.0 * np.pi * np.cumsum(freq) / SR
    env = np.minimum(1.0, t / 0.006) * np.exp(-t * 14.0)
    return np.sin(phase) * env * velocity


def save_wav(path: Path, audio: np.ndarray, target_peak: float = 0.72) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = float(np.max(np.abs(audio)))
    if peak > 1e-6:
        audio = audio * (target_peak / peak)
    clipped = np.clip(audio, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype(np.int16)
    wavfile.write(str(path), SR, pcm)


# -----------------------------------------------------------------------------
# BGM Tracks
# -----------------------------------------------------------------------------


def build_bgm_menu() -> np.ndarray:
    """Smoky noir jazz dossier groove (Dm9 -> Gm9 -> Bbmaj7 -> A7b9, 88 BPM, 8 bars)."""
    bpm = 88.0
    beat = 60.0 / bpm
    total_beats = 16  # 4 bars (4/4) ~10.9s smooth loop
    n = int(SR * total_beats * beat)
    buf = np.zeros((n, 2), dtype=np.float64)
    rng = np.random.default_rng(101)

    chords = [
        (0.0, [50, 57, 60, 64, 65]),  # Dm9
        (4.0, [55, 62, 65, 69, 70]),  # Gm9
        (8.0, [46, 53, 57, 60, 62]),  # Bbmaj9
        (12.0, [45, 52, 55, 58, 61]),  # A7b9
    ]
    for start_b, notes in chords:
        mix_wrap(buf, int(start_b * beat * SR), synth_pad(notes[:4], 4.2 * beat, 0.16), pan=0.0)
        for i, note in enumerate(notes):
            # Subtle strummed Rhodes feel
            offset = int((start_b * beat + i * 0.025) * SR)
            mix_wrap(buf, offset, synth_rhodes(note, 3.4 * beat, 0.24), pan=-0.25 + 0.12 * i)
        # Syncopated response chord on beat + 2.5
        for i, note in enumerate(notes[1:]):
            offset = int(((start_b + 2.5) * beat + i * 0.02) * SR)
            mix_wrap(buf, offset, synth_rhodes(note, 1.4 * beat, 0.14), pan=0.2)

    bass_line = [
        (0.0, 38),
        (1.5, 45),
        (2.0, 41),
        (3.0, 43),
        (4.0, 43),
        (5.5, 46),
        (6.0, 50),
        (7.0, 48),
        (8.0, 46),
        (9.5, 50),
        (10.0, 45),
        (11.0, 46),
        (12.0, 45),
        (13.5, 43),
        (14.0, 40),
        (15.0, 39),
    ]
    for b, note in bass_line:
        mix_wrap(buf, int(b * beat * SR), synth_upright_bass(note, 1.2 * beat, 0.52), pan=-0.05)

    for b in range(total_beats * 2):
        vel = 0.09 if b % 2 == 0 else 0.045
        swing = 0.06 * beat if b % 2 == 1 else 0.0
        mix_wrap(buf, int((b * 0.5 * beat + swing) * SR), synth_brush(0.065, vel, rng), pan=0.22)

    buf = add_stereo_delay(buf, delay_ms=beat * 375.0, decay=0.22)
    return lowpass(buf, 7500.0, order=2)


def build_bgm_stealth() -> np.ndarray:
    """Museum infiltration stealth loop (Em -> Cmaj7 -> Am9 -> B7, 94 BPM, 16 beats)."""
    bpm = 94.0
    beat = 60.0 / bpm
    total_beats = 16
    n = int(SR * total_beats * beat)
    buf = np.zeros((n, 2), dtype=np.float64)
    rng = np.random.default_rng(202)

    pads = [
        (0.0, [52, 59, 62, 66]),  # Em9
        (4.0, [48, 55, 59, 64]),  # Cmaj7
        (8.0, [45, 52, 55, 59]),  # Am9
        (12.0, [47, 54, 57, 63]),  # B7
    ]
    for b, notes in pads:
        mix_wrap(buf, int(b * beat * SR), synth_pad(notes, 4.3 * beat, 0.22), pan=0.0)

    # Sneaky plucked bass ostinato
    bass = [
        (0.0, 40),
        (1.0, 40),
        (1.5, 43),
        (2.5, 47),
        (3.5, 45),
        (4.0, 36),
        (5.0, 36),
        (5.5, 40),
        (6.5, 43),
        (7.5, 42),
        (8.0, 33),
        (9.0, 33),
        (9.5, 36),
        (10.5, 40),
        (11.5, 38),
        (12.0, 35),
        (13.0, 35),
        (13.5, 38),
        (14.5, 42),
        (15.5, 41),
    ]
    for b, note in bass:
        mix_wrap(buf, int(b * beat * SR), synth_upright_bass(note, 0.75 * beat, 0.56), pan=-0.06)

    # Sparse glass/museum marimba-like Rhodes motif
    motif = [
        (0.5, 71),
        (2.0, 74),
        (3.0, 71),
        (4.5, 67),
        (6.0, 71),
        (7.0, 67),
        (8.5, 69),
        (10.0, 72),
        (11.0, 69),
        (12.5, 66),
        (14.0, 71),
        (15.0, 69),
    ]
    for b, note in motif:
        mix_wrap(buf, int(b * beat * SR), synth_rhodes(note, 1.3 * beat, 0.19), pan=0.3)

    # Subtle clockwork security tick
    for b in range(total_beats * 2):
        vel = 0.085 if b % 4 == 0 else 0.04
        mix_wrap(
            buf,
            int(b * 0.5 * beat * SR),
            synth_brush(0.045, vel, rng),
            pan=-0.25 if b % 2 == 0 else 0.25,
        )

    buf = add_stereo_delay(buf, delay_ms=beat * 500.0, decay=0.26)
    return lowpass(buf, 6800.0, order=2)


def build_bgm_tension() -> np.ndarray:
    """High-scrutiny / interrogation tension pulse (Cm -> Db -> Cm -> G7, 108 BPM)."""
    bpm = 108.0
    beat = 60.0 / bpm
    total_beats = 16
    n = int(SR * total_beats * beat)
    buf = np.zeros((n, 2), dtype=np.float64)
    rng = np.random.default_rng(303)

    pads = [
        (0.0, [48, 55, 58, 63]),  # Cm7
        (4.0, [49, 55, 58, 61]),  # Db dim tension
        (8.0, [48, 55, 58, 62]),  # Cm9
        (12.0, [43, 50, 53, 59]),  # G7
    ]
    for b, notes in pads:
        mix_wrap(buf, int(b * beat * SR), synth_pad(notes, 4.2 * beat, 0.26), pan=0.0)

    # Heartbeat double-pulse kick + urgent bass ostinato
    for bar in range(4):
        base = bar * 4.0
        mix_wrap(buf, int(base * beat * SR), synth_pulse_kick(0.24, 0.52), pan=0.0)
        mix_wrap(buf, int((base + 0.75) * beat * SR), synth_pulse_kick(0.18, 0.34), pan=0.0)
        mix_wrap(buf, int((base + 2.0) * beat * SR), synth_pulse_kick(0.24, 0.45), pan=0.0)

    bass_roots = [36, 37, 36, 31]
    for bar, root in enumerate(bass_roots):
        for step in range(8):
            b = bar * 4.0 + step * 0.5
            note = root + (7 if step % 4 == 2 else 0)
            vel = 0.44 if step % 2 == 0 else 0.28
            mix_wrap(buf, int(b * beat * SR), synth_upright_bass(note, 0.45 * beat, vel), pan=-0.05)

    # High tense shimmer ticks
    for step in range(total_beats * 2):
        vel = 0.09 if step % 2 == 0 else 0.045
        mix_wrap(
            buf,
            int(step * 0.5 * beat * SR),
            synth_brush(0.04, vel, rng),
            pan=0.28 if step % 2 else -0.28,
        )

    buf = add_stereo_delay(buf, delay_ms=beat * 375.0, decay=0.25)
    return lowpass(buf, 6200.0, order=2)


def build_bgm_victory() -> np.ndarray:
    """Warm resolving heist-complete outro loop (Fmaj9 -> G13 -> Em9 -> Am9, 84 BPM)."""
    bpm = 84.0
    beat = 60.0 / bpm
    total_beats = 16
    n = int(SR * total_beats * beat)
    buf = np.zeros((n, 2), dtype=np.float64)
    rng = np.random.default_rng(404)

    chords = [
        (0.0, [53, 57, 60, 64, 67]),  # Fmaj9
        (4.0, [55, 59, 62, 65, 69]),  # G13
        (8.0, [52, 55, 59, 62, 66]),  # Em9
        (12.0, [45, 52, 55, 59, 64]),  # Am9
    ]
    for b, notes in chords:
        mix_wrap(buf, int(b * beat * SR), synth_pad(notes[:4], 4.2 * beat, 0.22), pan=0.0)
        for i, note in enumerate(notes):
            mix_wrap(
                buf,
                int((b * beat + i * 0.03) * SR),
                synth_rhodes(note, 3.8 * beat, 0.26),
                pan=-0.2 + 0.1 * i,
            )
        mix_wrap(
            buf, int(b * beat * SR), synth_upright_bass(notes[0] - 12, 3.2 * beat, 0.48), pan=0.0
        )

    for b in range(total_beats):
        mix_wrap(buf, int(b * beat * SR), synth_brush(0.06, 0.06, rng), pan=0.18)

    buf = add_stereo_delay(buf, delay_ms=beat * 500.0, decay=0.28)
    return lowpass(buf, 7800.0, order=2)


def build_bgm_captured() -> np.ndarray:
    """Somber low interrogation-room failure loop (Am -> Fmaj7 -> Dm -> E7, 72 BPM)."""
    bpm = 72.0
    beat = 60.0 / bpm
    total_beats = 16
    n = int(SR * total_beats * beat)
    buf = np.zeros((n, 2), dtype=np.float64)

    chords = [
        (0.0, [45, 52, 57, 60]),
        (4.0, [41, 48, 53, 57]),
        (8.0, [38, 45, 50, 53]),
        (12.0, [40, 47, 50, 56]),
    ]
    for b, notes in chords:
        mix_wrap(buf, int(b * beat * SR), synth_pad(notes, 4.4 * beat, 0.28), pan=0.0)
        mix_wrap(buf, int(b * beat * SR), synth_rhodes(notes[-1] + 12, 3.6 * beat, 0.18), pan=0.15)
        mix_wrap(
            buf, int(b * beat * SR), synth_upright_bass(notes[0] - 12, 3.5 * beat, 0.5), pan=0.0
        )

    buf = add_stereo_delay(buf, delay_ms=beat * 500.0, decay=0.3)
    return lowpass(buf, 4800.0, order=2)


# -----------------------------------------------------------------------------
# UI & Event SFX
# -----------------------------------------------------------------------------


def build_sfx_hover() -> np.ndarray:
    """Ultra-subtle tactile hover tick (38 ms)."""
    dur = 0.038
    t = np.arange(int(SR * dur)) / SR
    sig = np.sin(2.0 * np.pi * 1450.0 * t) * np.exp(-t * 140.0) * 0.45
    sig += np.sin(2.0 * np.pi * 2900.0 * t) * np.exp(-t * 210.0) * 0.18
    return np.column_stack([sig, sig])


def build_sfx_click() -> np.ndarray:
    """Crisp damped mechanical switch click (65 ms)."""
    dur = 0.065
    t = np.arange(int(SR * dur)) / SR
    rng = np.random.default_rng(7)
    freq = 620.0 + 480.0 * np.exp(-t * 180.0)
    tone = np.sin(2.0 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 85.0)
    snap = bandpass(rng.standard_normal(len(t)), 2000.0, 7000.0) * np.exp(-t * 190.0) * 0.35
    sig = tone * 0.7 + snap
    return np.column_stack([sig, sig])


def build_sfx_send() -> np.ndarray:
    """Soft ascending comms transmit blip (115 ms)."""
    dur = 0.115
    t = np.arange(int(SR * dur)) / SR
    f = 540.0 + 360.0 * (t / dur)
    phase = 2.0 * np.pi * np.cumsum(f) / SR
    env = np.minimum(1.0, t / 0.008) * np.exp(-t * 28.0)
    sig = np.sin(phase) * env
    return np.column_stack([sig, sig])


def build_sfx_item_success() -> np.ndarray:
    """Clean two-note warm brass/badge clearance chime (300 ms)."""
    dur = 0.32
    n = int(SR * dur)
    buf = np.zeros((n, 2), dtype=np.float64)
    mix_wrap(buf, 0, synth_rhodes(74, 0.22, 0.7), pan=-0.1)
    mix_wrap(buf, int(0.085 * SR), synth_rhodes(81, 0.23, 0.8), pan=0.1)
    return buf


def build_sfx_item_fail() -> np.ndarray:
    """Low muted security rejection buzz (240 ms)."""
    dur = 0.24
    t = np.arange(int(SR * dur)) / SR
    env = np.minimum(1.0, t / 0.01) * np.exp(-t * 11.0)
    sig = (np.sin(2.0 * np.pi * 195.0 * t) + 0.55 * np.sin(2.0 * np.pi * 207.0 * t)) * env
    sig = lowpass(sig, 900.0, order=2)
    return np.column_stack([sig, sig])


def build_sfx_suspicion_up() -> np.ndarray:
    """Tense muted two-pulse warning sting (340 ms)."""
    dur = 0.34
    t = np.arange(int(SR * dur)) / SR
    p1 = np.sin(2.0 * np.pi * 311.0 * t) * np.exp(-t * 18.0)
    t2 = np.maximum(0.0, t - 0.12)
    p2 = (t >= 0.12) * np.sin(2.0 * np.pi * 330.0 * t2) * np.exp(-t2 * 14.0)
    sig = lowpass((p1 * 0.7 + p2 * 0.9), 1400.0, order=2)
    return np.column_stack([sig, sig])


def build_sfx_move() -> np.ndarray:
    """Soft turnstile latch + two footsteps (280 ms)."""
    dur = 0.28
    n = int(SR * dur)
    buf = np.zeros((n, 2), dtype=np.float64)
    rng = np.random.default_rng(19)
    step1 = lowpass(rng.standard_normal(int(SR * 0.09)), 420.0, order=2) * np.exp(
        -np.arange(int(SR * 0.09)) / SR * 35.0
    )
    step2 = lowpass(rng.standard_normal(int(SR * 0.09)), 380.0, order=2) * np.exp(
        -np.arange(int(SR * 0.09)) / SR * 35.0
    )
    mix_wrap(buf, 0, step1 * 0.9, pan=-0.15)
    mix_wrap(buf, int(0.13 * SR), step2 * 0.8, pan=0.15)
    return buf


def main() -> None:
    print("Generating BGM tracks...")
    save_wav(BGM_DIR / "menu.wav", build_bgm_menu(), target_peak=0.65)
    save_wav(BGM_DIR / "stealth.wav", build_bgm_stealth(), target_peak=0.62)
    save_wav(BGM_DIR / "tension.wav", build_bgm_tension(), target_peak=0.65)
    save_wav(BGM_DIR / "victory.wav", build_bgm_victory(), target_peak=0.65)
    save_wav(BGM_DIR / "captured.wav", build_bgm_captured(), target_peak=0.65)

    print("Generating UI & gameplay SFX...")
    save_wav(SFX_DIR / "hover.wav", build_sfx_hover(), target_peak=0.40)
    save_wav(SFX_DIR / "click.wav", build_sfx_click(), target_peak=0.65)
    save_wav(SFX_DIR / "send.wav", build_sfx_send(), target_peak=0.60)
    save_wav(SFX_DIR / "item_success.wav", build_sfx_item_success(), target_peak=0.72)
    save_wav(SFX_DIR / "item_fail.wav", build_sfx_item_fail(), target_peak=0.70)
    save_wav(SFX_DIR / "suspicion_up.wav", build_sfx_suspicion_up(), target_peak=0.72)
    save_wav(SFX_DIR / "move.wav", build_sfx_move(), target_peak=0.65)
    print("Done! All audio files written to static/audio/.")


if __name__ == "__main__":
    main()
