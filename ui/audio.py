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
SFX_NAMES = (
    "hover",
    "click",
    "send",
    "item_success",
    "item_fail",
    "suspicion_up",
    "move",
    "jumpscare",
)


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
    if game.get("prompt_injection_detected"):
        return "captured"
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
    scene_key: Optional[str] = None,
    item_tooltips: Optional[dict[str, dict[str, str]]] = None,
) -> None:
    """Mount/update the persistent browser audio engine, BGM, SFX, guard TTS, and UX keys."""
    # Audio & TTS temporarily disabled (BGM, SFX, and guard TTS are muted/skipped below),
    # while keeping scene fades and inventory hover tooltips active.
    pending_sfx = None
    speech_payload = None
    track = ""

    # if speak_current is not None:
    #     speaker, text, guard_id = speak_current
    #     queue_speech(speaker=speaker, text=text, guard_id=guard_id)
    #
    # pending_sfx = st.session_state.pop("_audio_pending_sfx", None)
    # pending_speech = st.session_state.pop("_audio_pending_speech", None)
    #
    # speech_payload = None
    # if pending_speech is not None:
    #     audio_uri = synthesize_guard_speech_uri(
    #         pending_speech["text"], pending_speech["guard_id"]
    #     )
    #     speech_payload = {
    #         "id": pending_speech["id"],
    #         "guard_id": pending_speech["guard_id"],
    #         "text": pending_speech["text"],
    #         "audio_uri": audio_uri,
    #     }

    payload = {
        "manifest": _asset_manifest(),
        "track": track,
        "sfx": pending_sfx,
        "speech": speech_payload,
        "scene_key": scene_key,
        "item_tooltips": item_tooltips or {},
    }
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    st.html(
        f"""
        <script>
        (function() {{
          const PAYLOAD = {payload_json};
          const STORAGE_KEY = "bobbery_audio_prefs_v1";

          function loadPrefs() {{
            return {{ bgm: false, sfx: false, voice: false }};
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
              queuedSpeech: null,
              lastSceneKey: null,
              itemTooltips: {{}},
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

            function playJumpscareSting() {{
              stopVoice();
              if (!state.prefs.sfx) return;
              try {{
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (!AudioCtx) return;
                const ctx = new AudioCtx();
                const now = ctx.currentTime;
                const master = ctx.createGain();
                master.gain.setValueAtTime(0.001, now);
                master.gain.exponentialRampToValueAtTime(0.62, now + 0.015);
                master.gain.exponentialRampToValueAtTime(0.0008, now + 0.95);
                master.connect(ctx.destination);

                // Sudden sub-bass impact drop
                const sub = ctx.createOscillator();
                const subGain = ctx.createGain();
                sub.type = "sawtooth";
                sub.frequency.setValueAtTime(110, now);
                sub.frequency.exponentialRampToValueAtTime(34, now + 0.55);
                subGain.gain.setValueAtTime(0.65, now);
                subGain.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
                sub.connect(subGain);
                subGain.connect(master);
                sub.start(now);
                sub.stop(now + 0.65);

                // Dissonant metallic screech chord (tritone + minor second)
                [587.3, 622.3, 830.6, 1174.7].forEach((freq) => {{
                  const osc = ctx.createOscillator();
                  const g = ctx.createGain();
                  osc.type = "sawtooth";
                  osc.frequency.setValueAtTime(freq, now);
                  osc.frequency.linearRampToValueAtTime(freq * 0.92, now + 0.85);
                  g.gain.setValueAtTime(0.16, now);
                  g.gain.exponentialRampToValueAtTime(0.001, now + 0.85);
                  osc.connect(g);
                  g.connect(master);
                  osc.start(now);
                  osc.stop(now + 0.9);
                }});

                // Sharp filtered noise burst
                const len = Math.floor(ctx.sampleRate * 0.45);
                const buf = ctx.createBuffer(1, len, ctx.sampleRate);
                const ch = buf.getChannelData(0);
                for (let i = 0; i < len; i++) {{
                  ch[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.14));
                }}
                const noise = ctx.createBufferSource();
                noise.buffer = buf;
                const filt = ctx.createBiquadFilter();
                filt.type = "bandpass";
                filt.frequency.setValueAtTime(1400, now);
                filt.Q.setValueAtTime(1.2, now);
                const nGain = ctx.createGain();
                nGain.gain.setValueAtTime(0.55, now);
                nGain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
                noise.connect(filt);
                filt.connect(nGain);
                nGain.connect(master);
                noise.start(now);
                setTimeout(() => {{ try {{ ctx.close(); }} catch (e) {{}} }}, 1200);
              }} catch (e) {{}}
            }}

            function playSfx(name, volume) {{
              if (name === "jumpscare") {{
                playJumpscareSting();
                return;
              }}
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
              if (!state.unlocked) {{
                // Defer until first browser gesture unlocks audio autoplay
                state.queuedSpeech = speech;
                return;
              }}
              state.lastSpeechId = speech.id;
              state.queuedSpeech = null;
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
              if (state.queuedSpeech) {{
                playSpeech(state.queuedSpeech);
              }}
            }}

            document.addEventListener("pointerdown", unlockAudio, {{ passive: true }});
            document.addEventListener("keydown", unlockAudio, {{ passive: true }});

            // UX: Enter sends chat response, Shift+Enter inserts a newline
            document.addEventListener("keydown", (ev) => {{
              if (ev.key !== "Enter" || ev.shiftKey || ev.ctrlKey || ev.altKey || ev.metaKey || ev.isComposing) {{
                return;
              }}
              const target = ev.target;
              if (!target || target.tagName !== "TEXTAREA") return;
              const bar = target.closest(".st-key-response_bar");
              if (!bar) return;
              ev.preventDefault();
              if (!target.value || !target.value.trim()) return;
              const submitBtn = bar.querySelector("button:not(:disabled)");
              if (submitBtn) {{
                // Let Streamlit sync textarea value before submitting the form
                target.dispatchEvent(new Event("input", {{ bubbles: true }}));
                setTimeout(() => submitBtn.click(), 10);
              }}
            }}, true);

            // Short cinematic scene fade overlay when advancing between locations
            function triggerSceneFade() {{
              let veil = document.getElementById("bobbery-scene-veil");
              if (!veil) {{
                veil = document.createElement("div");
                veil.id = "bobbery-scene-veil";
                veil.style.cssText =
                  "position:fixed;inset:0;z-index:999990;pointer-events:none;" +
                  "background:#0c0f0c;opacity:0;transition:opacity 360ms ease;";
                document.body.appendChild(veil);
              }}
              veil.style.transition = "none";
              veil.style.opacity = "0.78";
              requestAnimationFrame(() => {{
                requestAnimationFrame(() => {{
                  veil.style.transition = "opacity 460ms ease-out";
                  veil.style.opacity = "0";
                }});
              }});
            }}

            // Custom noir hover tooltip for Inventory items (keeps st.button DOM 100% untouched)
            let hoveredPickEl = null;
            function ensureItemTooltip() {{
              let tip = document.getElementById("bobbery-item-tooltip");
              if (!tip) {{
                tip = document.createElement("div");
                tip.id = "bobbery-item-tooltip";
                tip.style.cssText =
                  "position:fixed;z-index:999998;pointer-events:none;opacity:0;" +
                  "max-width:270px;padding:0.65rem 0.78rem;border-radius:6px;" +
                  "border:1px solid rgba(224,159,62,0.55);background:rgba(16,20,16,0.96);" +
                  "box-shadow:0 12px 30px rgba(0,0,0,0.7);color:#ece8de;" +
                  "font-family:system-ui,-apple-system,sans-serif;font-size:0.8rem;line-height:1.4;" +
                  "transition:opacity 120ms ease;backdrop-filter:blur(8px);";
                document.body.appendChild(tip);
              }}
              return tip;
            }}

            function hideItemTooltip() {{
              hoveredPickEl = null;
              const tip = document.getElementById("bobbery-item-tooltip");
              if (tip) tip.style.opacity = "0";
            }}

            function showItemTooltip(pickEl, itemId) {{
              const info = state.itemTooltips && state.itemTooltips[itemId];
              if (!info) return;
              const tip = ensureItemTooltip();
              tip.innerHTML = "";
              const head = document.createElement("div");
              head.textContent = info.header || itemId;
              head.style.cssText =
                "color:#f3c46b;font-family:ui-monospace,monospace;font-size:0.7rem;" +
                "font-weight:700;letter-spacing:0.07em;text-transform:uppercase;" +
                "margin-bottom:0.35rem;padding-bottom:0.25rem;" +
                "border-bottom:1px solid rgba(224,159,62,0.22);";
              tip.appendChild(head);

              const lines = String(info.lines || "").split("\\n").filter(Boolean);
              lines.forEach((line) => {{
                const p = document.createElement("div");
                p.textContent = line;
                p.style.cssText = "color:#d5d2c7;margin-top:0.18rem;";
                tip.appendChild(p);
              }});

              const rect = pickEl.getBoundingClientRect();
              const tipW = tip.offsetWidth || 260;
              const tipH = tip.offsetHeight || 120;
              let left = rect.left - tipW - 12;
              if (left < 12) left = Math.min(window.innerWidth - tipW - 12, rect.right + 12);
              let top = rect.top + (rect.height - tipH) / 2;
              top = Math.max(12, Math.min(window.innerHeight - tipH - 12, top));
              tip.style.left = left + "px";
              tip.style.top = top + "px";
              tip.style.opacity = "1";
            }}

            document.addEventListener("pointerover", (ev) => {{
              const pickEl = ev.target && ev.target.closest
                ? ev.target.closest('[class*="st-key-pick_"]')
                : null;
              if (!pickEl) return;
              if (hoveredPickEl === pickEl) return;
              const btn = pickEl.querySelector("button");
              if (btn && btn.matches('[data-testid^="stBaseButton-primary"]')) {{
                hideItemTooltip();
                return;
              }}
              const match = pickEl.className.match(/st-key-pick_([A-Za-z0-9_-]+)/);
              if (!match) return;
              hoveredPickEl = pickEl;
              showItemTooltip(pickEl, match[1]);
            }}, {{ passive: true }});

            document.addEventListener("pointerout", (ev) => {{
              if (!hoveredPickEl) return;
              if (ev.relatedTarget && hoveredPickEl.contains(ev.relatedTarget)) return;
              hideItemTooltip();
            }}, {{ passive: true }});

            document.addEventListener("pointerdown", hideItemTooltip, {{ passive: true }});
            window.addEventListener("scroll", hideItemTooltip, {{ passive: true, capture: true }});

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
                @media (max-width: 900px) {{
                  #bobbery-audio-dock {{
                    top: auto;
                    bottom: 0.65rem;
                    left: auto;
                    right: 0.75rem;
                    transform: none;
                  }}
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

            // Audio dock hidden while audio/TTS is disabled.
            // ensureDock();

            window.__bobberyAudio = {{
              sync(p) {{
                state.manifest = p.manifest || state.manifest;
                if (p.item_tooltips) {{
                  state.itemTooltips = p.item_tooltips;
                }}
                // ensureDock();
                if (p.scene_key && state.lastSceneKey && p.scene_key !== state.lastSceneKey) {{
                  triggerSceneFade();
                }}
                if (p.scene_key) {{
                  state.lastSceneKey = p.scene_key;
                }}
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
