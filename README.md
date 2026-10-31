# Blueprint Agent and Space Fractions

Task 1 submission: a Windows desktop code agent using the official DeepSeek API, plus a generated desktop maths game.

## Demonstration

YouTube video: ADD YOUR VIDEO LINK HERE.

The video uses synthetic English narration and Chinese subtitles. It shows a saved generation log and the locally repaired game.

## Repository layout

- agent/: code agent source, offline tests, architecture input examples, build script and reference research.
- game/: generated game source with documented local repairs, tests and design artifacts.
- evidence/STATUS.md: generation outcome, recorded usage and remaining limitations.

## Run the agent

Use Windows with Python 3.12 and Tkinter. In a terminal:

```powershell
cd agent
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python app.py
```

Enter your own official DeepSeek API key privately in the app. Generation incurs API charges. The cost guard is an estimate, not a provider-enforced billing cap. Running the offline tests does not generate a project or require an API key.

## Run the existing game

From the repository root:

```powershell
cd game
python -m pip install -r requirements-dev.txt
python -m pytest -q
python desktop.py
```

Running the existing game does not require an API key or another generation request. Build scripts inside agent/ and game/ can produce Windows executables.

## Result and limitations

The DeepSeek run stopped at its budget guard. Its output was then repaired locally; the repaired game passed 25 tests. The default UI stores data in memory, and PostgreSQL integration and production requirements remain unverified. See game/LOCAL-REVIEW.md and evidence/STATUS.md. This is a demonstration, not a claim of complete requirement compliance.

The displayed run estimate was US$0.670112; actual billing still needs verification.

## Provenance and references

The code agent was developed with AI coding assistance. The game originated from the recorded DeepSeek run and received subsequent AI-assisted local repairs. The repair record distinguishes those changes from the original generated output.

Reference repositories and design notes are credited in agent/docs/RESEARCH.md. The two assignment input documents are in agent/examples/. Review sharing permission before making the repository public. No license is granted for third-party assignment materials by this repository.
