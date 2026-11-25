"""Persistent browser audio controller for BGM, UI hover/click SFX, and AI guard speech.

Uses Streamlit's `st.html(..., unsafe_allow_javascript=True)` to maintain a single
`window.__bobberyAudio` controller across reruns, fragments, and screen changes so
background music never restarts or stutters on chat turns.

Custom asset override:
Drop your own `.mp3`, `.ogg`, or `.wav` files into `static/audio/bgm/` or
`static/audio/sfx/` with the matching stem name (`menu`, `stealth`, `tension`,
`victory`, `captured`, `hover`, `click`, `send`, `item_success`, `item_fail`,
`suspicion_up`, `move`) and they will automatically be preferred over generated `.wav`s.
"""

import json
from pathlib import Path
from typing import Any, Optional

import streamlit as st

from ui.tts import resolve_guard_id, synthesize_guard_speech_uri

_AUDIO_ROOT = Path(__file__).resolve().parent.parent / "static" / "audio"
_EXTENSIONS = (".mp3", ".ogg", ".wav")

BGM_NAMES = ("menu", "stealth", "tension", "victory", "captured")
SFX_NAMES = ("hover", "click", "send", "item_success", "item_fail", "suspicion_up", "move")


def _asset_url(subdir: str, stem: str) -> Optional[str]:
    folder = _AUDIO_ROOT / subdir
    for ext in _EXTENSIONS:
        candidate = folder / f"{stem}{ext}"
        if candidate.is_file():
            return f"/app/static/audio/{subdir}/{stem}{ext}"
    return None


def _asset_manifest() -> dict[str, dict[str, str]]:
    bgm = {name: url for name in BGM_NAMES if (url := _asset_url("bgm", name))}
    sfx = {name: url for name in SFX_NAMES if (url := _asset_url("sfx", name))}
    return {"bgm": bgm, "sfx": sfx}


def queue_sfx(name: str) -> None:
    """Queue a one-shot gameplay sound effect to play on the next audio sync."""
    if name not in SFX_NAMES:
        return
    seq = int(st.session_state.get("_audio_sfx_seq", 0)) + 1
    st.session_state["_audio_sfx_seq"] = seq
    st.session_state["_audio_pending_sfx"] = {"id": seq, "name": name}


def queue_speech(speaker: str, text: str, guard_id: Optional[str] = None) -> None:
    """Queue a guard line for neural TTS playback (deduplicated per utterance)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return
    resolved_guard = resolve_guard_id(guard_id=guard_id, speaker=speaker)
    sig = f"{resolved_guard}|{cleaned}"
    if st.session_state.get("_audio_last_speech_sig") == sig:
        return
    st.session_state["_audio_last_speech_sig"] = sig
    seq = int(st.session_state.get("_audio_speech_seq", 0)) + 1
    st.session_state["_audio_speech_seq"] = seq
    st.session_state["_audio_pending_speech"] = {
        "id": seq,
        "guard_id": resolved_guard,
        "speaker": speaker,
        "text": cleaned,
    }


def reset_speech_dedup() -> None:
    """Clear speech deduplication when starting a fresh mission."""
    st.session_state.pop("_audio_last_speech_sig", None)
    st.session_state.pop("_audio_pending_speech", None)


def track_for_gameplay(game: dict[str, Any]) -> str:
    """Select the gameplay BGM track based on suspicion and interrogation state."""
    interrogation = game.get("interrogation") or {}
    suspicion_val = int((game.get("suspicion") or {}).get("value", 0))
    if interrogation.get("active") or suspicion_val >= 60:
        return "tension"
    return "stealth"


def track_for_result(result: dict[str, Any]) -> str:
    """Select the debrief BGM track based on mission outcome tone."""
    return "captured" if result.get("tone") == "failure" else "victory"


def render_audio_controller(
    *,
    track: str,
    speak_current: Optional[tuple[str, str, Optional[str]]] = None,
) -> None:
    """Mount/update the persistent browser audio engine, BGM, SFX, and guard TTS."""
    if speak_current is not None:
        speaker, text, guard_id = speak_current
        queue_speech(speaker=speaker, text=text, guard_id=guard_id)

    pending_sfx = st.session_state.pop("_audio_pending_sfx", None)
    pending_speech = st.session_state.pop("_audio_pending_speech", None)

    speech_payload = None
    if pending_speech is not None:
        audio_uri = synthesize_guard_speech_uri(
            pending_speech["text"], pending_speech["guard_id"]
        )
        speech_payload = {
            "id": pending_speech["id"],
            "guard_id": pending_speech["guard_id"],
            "text": pending_speech["text"],
            "audio_uri": audio_uri,
        }

    payload = {
        "manifest": _asset_manifest(),
        "track": track,
        "sfx": pending_sfx,
        "speech": speech_payload,
    }
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    st.html(
        f"""
        <script>
        (function() {{
          const PAYLOAD = {payload_json};
          const STORAGE_KEY = "bobbery_audio_prefs_v1";

          function loadPrefs() {{
            try {{
              const raw = localStorage.getItem(STORAGE_KEY);
              if (raw) return Object.assign({{ bgm: true, sfx: true, voice: true }}, JSON.parse(raw));
            }} catch (e) {{}}
            return {{ bgm: true, sfx: true, voice: true }};
          }}

          function savePrefs(prefs) {{
            try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); }} catch (e) {{}}
          }}

          if (!window.__bobberyAudio) {{
            const prefs = loadPrefs();
            const bgmEl = new Audio();
            bgmEl.loop = true;
            bgmEl.preload = "auto";
            bgmEl.volume = 0;

            const voiceEl = new Audio();
            voiceEl.preload = "auto";
            voiceEl.volume = 0.92;

            const state = {{
              prefs,
              manifest: PAYLOAD.manifest,
              unlocked: false,
              currentTrack: null,
              desiredTrack: null,
              baseVolume: 0.24,
              ducked: false,
              fadeTimer: null,
              lastSfxId: 0,
              lastSpeechId: 0,
              lastHoverAt: 0,
              sfxCache: {{}},
              bgmEl,
              voiceEl,
            }};

            function targetBgmVolume() {{
              if (!state.prefs.bgm) return 0;
              return state.ducked ? state.baseVolume * 0.28 : state.baseVolume;
            }}

            function fadeBgmTo(targetVol, durationMs, onDone) {{
              if (state.fadeTimer) clearInterval(state.fadeTimer);
              const startVol = bgmEl.volume;
              const steps = Math.max(1, Math.round(durationMs / 30));
              let step = 0;
              state.fadeTimer = setInterval(() => {{
                step++;
                const t = Math.min(1, step / steps);
                bgmEl.volume = Math.max(0, Math.min(1, startVol + (targetVol - startVol) * t));
                if (t >= 1) {{
                  clearInterval(state.fadeTimer);
                  state.fadeTimer = null;
                  if (onDone) onDone();
                }}
              }}, 30);
            }}

            function ensureBgmPlaying() {{
              const track = state.desiredTrack;
              const url = track && state.manifest.bgm[track];
              if (!url) return;

              if (!state.prefs.bgm) {{
                fadeBgmTo(0, 220, () => bgmEl.pause());
                return;
              }}

              if (state.currentTrack === track && !bgmEl.paused) {{
                fadeBgmTo(targetBgmVolume(), 260);
                return;
              }}

              const startNew = () => {{
                state.currentTrack = track;
                if (bgmEl.getAttribute("data-src") !== url) {{
                  bgmEl.src = url;
                  bgmEl.setAttribute("data-src", url);
                }}
                bgmEl.volume = 0;
                const p = bgmEl.play();
                if (p && p.then) {{
                  p.then(() => fadeBgmTo(targetBgmVolume(), 650)).catch(() => {{}});
                }}
              }};

              if (!bgmEl.paused && bgmEl.volume > 0.01) {{
                fadeBgmTo(0, 380, startNew);
              }} else {{
                startNew();
              }}
            }}

            function playSfx(name, volume) {{
              if (!state.prefs.sfx || !state.unlocked) return;
              const url = state.manifest.sfx[name];
              if (!url) return;
              try {{
                let template = state.sfxCache[name];
                if (!template) {{
                  template = new Audio(url);
                  template.preload = "auto";
                  state.sfxCache[name] = template;
                }}
                const node = template.cloneNode(true);
                node.volume = volume != null ? volume : (name === "hover" ? 0.22 : 0.48);
                const p = node.play();
                if (p && p.catch) p.catch(() => {{}});
              }} catch (e) {{}}
            }}

            function stopVoice() {{
              try {{
                voiceEl.pause();
                voiceEl.currentTime = 0;
              }} catch (e) {{}}
              try {{
                if (window.speechSynthesis) window.speechSynthesis.cancel();
              }} catch (e) {{}}
              state.ducked = false;
              if (state.prefs.bgm && !bgmEl.paused) fadeBgmTo(targetBgmVolume(), 350);
            }}

            function speakFallbackWeb(text, guardId) {{
              if (!window.speechSynthesis || !state.prefs.voice) return;
              try {{
                window.speechSynthesis.cancel();
                const u = new SpeechSynthesisUtterance(text);
                const profiles = {{
                  guard_casual: {{ rate: 1.0, pitch: 1.0 }},
                  guard_strict: {{ rate: 0.94, pitch: 0.85 }},
                  guard_observant: {{ rate: 1.02, pitch: 1.15 }},
                  guard_experienced: {{ rate: 0.90, pitch: 0.80 }},
                  guard_impatient: {{ rate: 1.16, pitch: 1.04 }},
                  guard_interrogator: {{ rate: 1.04, pitch: 0.82 }},
                }};
                const prof = profiles[guardId] || {{ rate: 1.0, pitch: 1.0 }};
                u.rate = prof.rate;
                u.pitch = prof.pitch;
                u.onstart = () => {{ state.ducked = true; fadeBgmTo(targetBgmVolume(), 220); }};
                u.onend = u.onerror = () => {{ state.ducked = false; fadeBgmTo(targetBgmVolume(), 420); }};
                window.speechSynthesis.speak(u);
              }} catch (e) {{}}
            }}

            function playSpeech(speech) {{
              if (!speech || speech.id <= state.lastSpeechId) return;
              state.lastSpeechId = speech.id;
              if (!state.prefs.voice) return;

              stopVoice();
              if (speech.audio_uri) {{
                voiceEl.src = speech.audio_uri;
                state.ducked = true;
                fadeBgmTo(targetBgmVolume(), 220);
                const p = voiceEl.play();
                if (p && p.catch) {{
                  p.catch(() => {{
                    state.ducked = false;
                    fadeBgmTo(targetBgmVolume(), 300);
                  }});
                }}
              }} else {{
                speakFallbackWeb(speech.text, speech.guard_id);
              }}
            }}

            voiceEl.addEventListener("ended", () => {{
              state.ducked = false;
              fadeBgmTo(targetBgmVolume(), 420);
            }});
            voiceEl.addEventListener("error", () => {{
              state.ducked = false;
              fadeBgmTo(targetBgmVolume(), 420);
            }});

            function unlockAudio() {{
              if (state.unlocked) return;
              state.unlocked = true;
              ensureBgmPlaying();
            }}

            document.addEventListener("pointerdown", unlockAudio, {{ passive: true }});
            document.addEventListener("keydown", unlockAudio, {{ passive: true }});

            // Zero-rerun delegated hover & click SFX for all interactive UI controls
            document.addEventListener("pointerover", (ev) => {{
              const target = ev.target && ev.target.closest
                ? ev.target.closest("button:not(:disabled), [role='button'], summary")
                : null;
              if (!target || target.id?.startsWith("bobbery-audio-")) return;
              const now = performance.now();
              if (now - state.lastHoverAt < 90) return;
              if (ev.relatedTarget && target.contains(ev.relatedTarget)) return;
              state.lastHoverAt = now;
              playSfx("hover", 0.22);
            }}, {{ passive: true }});

            document.addEventListener("pointerdown", (ev) => {{
              const target = ev.target && ev.target.closest
                ? ev.target.closest("button:not(:disabled), [role='button'], summary")
                : null;
              if (!target) return;
              const label = (target.textContent || "").trim().toLowerCase();
              if (label === "send") {{
                playSfx("send", 0.45);
              }} else {{
                playSfx("click", 0.42);
              }}
            }}, {{ passive: true }});

            // Mount compact floating audio dock matching Bobbery Rob noir theme
            function ensureDock() {{
              if (document.getElementById("bobbery-audio-dock")) return;
              const style = document.createElement("style");
              style.id = "bobbery-audio-dock-css";
              style.textContent = `
                #bobbery-audio-dock {{
                  position: fixed;
                  top: 0.72rem;
                  left: 50%;
                  transform: translateX(-50%);
                  z-index: 999999;
                  display: inline-flex;
                  align-items: center;
                  gap: 0.32rem;
                  padding: 0.22rem 0.34rem;
                  border-radius: 6px;
                  border: 1px solid rgba(224, 159, 62, 0.28);
                  background: rgba(18, 21, 18, 0.88);
                  backdrop-filter: blur(8px);
                  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
                  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                }}
                #bobbery-audio-dock button {{
                  appearance: none;
                  border: 1px solid rgba(236, 232, 222, 0.14);
                  border-radius: 4px;
                  background: rgba(255, 255, 255, 0.04);
                  color: #9a9f93;
                  font-size: 0.68rem;
                  font-weight: 600;
                  letter-spacing: 0.06em;
                  padding: 0.24rem 0.48rem;
                  cursor: pointer;
                  transition: border-color 140ms ease, color 140ms ease, background 140ms ease;
                }}
                #bobbery-audio-dock button.is-on {{
                  border-color: rgba(224, 159, 62, 0.55);
                  background: rgba(224, 159, 62, 0.16);
                  color: #f3c46b;
                }}
                #bobbery-audio-dock button:hover {{
                  border-color: rgba(224, 159, 62, 0.85);
                  color: #ece8de;
                }}
              `;
              document.head.appendChild(style);

              const dock = document.createElement("div");
              dock.id = "bobbery-audio-dock";
              dock.setAttribute("aria-label", "Audio controls");

              const items = [
                ["bgm", "BGM"],
                ["voice", "VOICE"],
                ["sfx", "SFX"],
              ];

              items.forEach(([key, label]) => {{
                const btn = document.createElement("button");
                btn.id = "bobbery-audio-" + key;
                btn.type = "button";
                const syncBtn = () => {{
                  const on = !!state.prefs[key];
                  btn.className = on ? "is-on" : "";
                  btn.textContent = label + (on ? " ON" : " OFF");
                  btn.setAttribute("aria-pressed", String(on));
                }};
                syncBtn();
                btn.addEventListener("click", () => {{
                  state.unlocked = true;
                  state.prefs[key] = !state.prefs[key];
                  savePrefs(state.prefs);
                  syncBtn();
                  if (key === "bgm") ensureBgmPlaying();
                  if (key === "voice" && !state.prefs.voice) stopVoice();
                }});
                dock.appendChild(btn);
              }});

              document.body.appendChild(dock);
            }}

            ensureDock();

            window.__bobberyAudio = {{
              sync(p) {{
                state.manifest = p.manifest || state.manifest;
                ensureDock();
                if (p.track && p.track !== state.desiredTrack) {{
                  state.desiredTrack = p.track;
                  if (state.unlocked) ensureBgmPlaying();
                }} else if (state.unlocked && state.prefs.bgm && bgmEl.paused && state.desiredTrack) {{
                  ensureBgmPlaying();
                }}
                if (p.sfx && p.sfx.id > state.lastSfxId) {{
                  state.lastSfxId = p.sfx.id;
                  playSfx(p.sfx.name);
                }}
                if (p.speech) {{
                  playSpeech(p.speech);
                }}
              }},
            }};
          }}

          window.__bobberyAudio.sync(PAYLOAD);
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )
