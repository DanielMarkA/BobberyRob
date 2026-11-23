# Bobbery Rob

Bobbery Rob is a conversational social-deception game built with Python and Streamlit. Play as a fictional visitor trying to recover an artifact from a museum's restricted collection. Invent a cover story, talk to AI-controlled guards in your own words, and remember what you've already told them.

**Status: In development.** The museum mission and mechanics below describe the MVP target, not a claim that every feature is implemented.

## Run locally

From the repository root, with Python and pip installed:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit.

## Museum MVP

- **Free-form dialogue:** Create a fictional identity through conversation and interact with at least two distinct guard personalities.
- **Hidden identity memory:** The game keeps the conversation history and a structured record of your claims. You can revisit the dialogue, but you won't see an automatic identity summary. Corrections preserve the original claim, and accusations cite earlier statements.
- **Suspicion and interrogation:** Contradictions and failed checks can draw scrutiny. New or missing details aren't contradictions on their own. During interrogation, an explanation can be convincing, partially convincing, or unconvincing.
- **Inventory:** The fictional passport, bribe money, and invitation letter offer alternate approaches. Each item has usage conditions, and the game tracks quantities.
- **Mission progression:** Meet the requirements for each location, reach the restricted collection, and attempt the artifact objective. The MVP targets at least three endings based on how the mission plays out.

## Architecture

**The AI interprets the conversation; the game engine controls the game.**

| Component | Responsibility |
| --- | --- |
| Streamlit UI | Display dialogue, the current location, objectives, suspicion, and inventory. |
| Python game engine | Validate actions and own suspicion, inventory, location, objective progress, and endings. |
| LLM service | Roleplay characters, extract claims, and evaluate possible contradictions and explanations. The engine validates model output before applying any game effects. |
| Memory and persistence | Retain conversation history, claim revisions and evidence, guard reports, and mission state. SQLite is the planned store. |
| Scenario configuration | Define routes, characters, objectives, item rules, interrogation triggers, and endings. JSON is the planned format for scenario and item definitions. |

The first release focuses on one complete museum mission. Additional scenarios, procedural generation, voice, and multiplayer are outside the MVP.
