# Bobbery Rob

Talk your way through a museum after hours, take the gold urn, and get it past exit security. Bobbery Rob is a single-player social-deception game built with Python and Streamlit. You invent the cover story; the guards remember it. **There’s no conversation log to look back at.**

## Quick start

Use **Python 3.12** (tested). From the repository root, create a virtual environment:

```sh
python -m venv .venv
```

Activate it with `.\.venv\Scripts\Activate.ps1` in Windows PowerShell, or `source .venv/bin/activate` on macOS/Linux. Then run:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed in the terminal, enter a codename, and start the mission. **No API key is needed to try the interface.** Without one, the app uses a limited mock guard: useful for testing screens and item actions, but not representative of free-form questioning. Use live dialogue for a playthrough or demo.

### Enable live dialogue

Create `.streamlit/secrets.toml` locally and add your provider settings. This file is ignored by Git. The app also accepts the same names as environment variables.

```toml
OPENAI_API_KEY = "your-api-key"
# Optional: select a model your account can access (default: gpt-6-luna).
# BOBBERY_LLM_MODEL = "your-model-id"
# Optional: point the client at an OpenAI-compatible endpoint.
# OPENAI_BASE_URL = "https://your-provider.example/v1"
```

Live mode sends player messages and relevant game evidence to the configured provider. If analysis times out, the guard can ask you to repeat an answer without a suspicion penalty.

## How to play

1. **Establish your cover.** Give the receptionist a name and a reason for visiting. Later guards ask their own questions and may check what was reported to them. An explicit correction is different from silently changing your story.
2. **Watch suspicion and objectives separately.** Low suspicion alone doesn’t unlock a door. A guard who finds a contradiction can quote the earlier statement and ask for an explanation.
3. **Inspect your inventory.** A passport, bribe, or invitation can help or hurt depending on the guard. At the restricted checkpoint, you can present the invitation or request a curator escort that adds 25 seconds to your score.
4. **Finish the escape.** Clear vault security, take the urn, and answer the exit guard. Taking it isn’t the win condition. The mission has five possible endings, including capture and an alternative exit.

**Scoring:** The leaderboard shows the ten fastest codenames in each ranked category, using each player’s best adjusted time: elapsed time plus penalties. Captured runs aren’t ranked. Codenames and completed-run statistics are stored in `database/bobbery_rob.db`; dialogue and claims stay in the running session and aren’t saved to the leaderboard database.

## Deploy on Streamlit Community Cloud

1. Push the project to GitHub. In Community Cloud, create an app from that repository and select the branch you pushed, `app.py` as the entrypoint, and Python **3.12**.
2. For live play, paste the TOML settings above into the app’s **Secrets**. Community Cloud installs [requirements.txt](requirements.txt). The checked-in [Streamlit config](.streamlit/config.toml) enables serving the bundled artwork and fonts.
3. After deployment, enter a codename and send a reply to the first guard to verify the app and its provider settings.

**Leaderboard persistence:** Refreshing a browser does not erase saved scores. Community Cloud’s local filesystem, however, is not durable: a reboot or redeploy can replace the SQLite file. For a multi-day competition where scores must survive, use persistent database storage.

## Development

The **model interprets what the player says; the Python engine decides what happens**. A guard’s generated reply cannot grant an item, clear a checkpoint, or change the score on its own.

| Location | What lives there |
| --- | --- |
| [app.py](app.py), [screens/](screens/), [ui/](ui/) | Streamlit entrypoint, screens, and player actions |
| [game/](game/), [scenario/museum.json](scenario/museum.json) | Game rules and the museum’s guards, routes, items, and endings |
| [llm/](llm/), [memory/](memory/) | Live and mock clients, dialogue evidence, claim corrections, and guard reports |
| [database/](database/) | SQLite player registration, completed runs, and leaderboard queries |

Run both offline test suites from the repository root:

```sh
python -m unittest discover
python -m tests.run_conversations
```

To exercise the model interface separately, run `python -m llm.try_it "I'm here for the gala." --mock`. For UI testing, set the environment variable `BOBBERY_LLM_MOCK=1` to force offline mode even with a key configured, or `BOBBERY_DEV_SHORTCUTS=1` to preview endings from gameplay.

For a presentation, use the [demo walkthrough](docs/demo_script.md). For balance testing, use the [playtest guide](docs/playtest.md). The playable build uses no audio files; the optional [audio generator](scripts/generate_audio.py) documents how to recreate the original WAV assets.
