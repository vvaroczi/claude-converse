# converse: Claude talks back

Conversation mode for Claude Code. You already dictate to Claude; this makes Claude answer out loud, with a local neural voice, without reading you every line.

- `/converse` on, `/converse off`. Nothing speaks unless the mode is on.
- Each reply opens with a short spoken part. Long breakdowns, tables and paths stay written for you to read.
- Speech starts while the text is still appearing.
- Send anything, even one letter, and the voice stops at once.
- Pick a voice by talking ("use Emma", "try George") and set the pace ("faster", "quick fire", "take your time").
- Runs fully on your Mac: Kokoro-82M through kokoro-onnx. No API key, no audio leaves the machine. Falls back to the macOS voice if the model is missing.

## Install

```bash
claude plugin marketplace add vvaroczi/claude-converse
claude plugin install converse@converse-marketplace
```

Then in any Claude Code session:

```
/converse setup     # once: venv, model (310 MB) and voices (27 MB)
/converse           # talk
```

From a local checkout instead: `claude plugin marketplace add /path/to/claude-converse` then the same `install` line.

## Demo

[72-second demo video](demo/converse-demo.mp4): conversation mode on, a reply spoken while it prints, an interrupt, pace and voice changes, Spanish, off.

## Talking to it (cheat sheet)
Once the mode is on, these work by voice or typed:

| Say or type | What happens |
|---|---|
| anything at all, even "stop" | the voice stops at once |
| "faster", "slower", "quick fire", "take your time", "normal pace" | pace: speed and how long the spoken part is |
| "play the voices" | six voices, each says its name; then pick |
| "use Emma", "use George", or `/converse voice af_heart` | switch voice |
| "speed one point two" or `/converse speed 1.2` | speed alone |
| "longer answers" / "shorter answers" | spoken part grows or shrinks |
| "read the detail" | the written part of the last reply, read once |
| "converse off" | mode off, silent written replies |

`/converse help` prints this list; `/converse status` shows the current voice and pace.

## Languages
English is the default and the best. Native voices also exist for Spanish, French, Italian, Portuguese (Brazil), Hindi, Japanese and Mandarin: `/converse language es` (or "speak Spanish") switches both the pronunciation and the voice. Other languages, Czech, Hungarian, German, Polish, Dutch among them, are pronounced by rule through a non-native voice, so they come out with an accent: fine for a quick read, not for comfort.

## Requirements
- macOS (audio through `afplay`; Linux works with `ffplay` or `aplay`, Windows is not wired yet)
- Python 3.10 or newer
- Claude Code 2.1 or newer (hooks: Stop, UserPromptSubmit)

## How it works
- `hooks/hooks.json` wires two hooks: Stop reads the 🔊 paragraphs of the finished reply; UserPromptSubmit kills any playback.
- The `converse` skill tells Claude how to answer in the mode: spoken part first, written detail second, and how to trigger speech before the text lands (`~/.claude/converse/bin/converse-say`), with a hash so the end-of-turn hook does not repeat it.
- `scripts/speak-kokoro.py` synthesizes sentence groups ahead of playback, so there are no gaps.
- State and models live in `~/.claude/converse/`, never inside the plugin, so updates keep your voice and pace.

## Voices
Kokoro ships 50 voices. English ones worth trying: `af_sky` (default), `af_heart`, `af_bella`, `af_nicole`, `am_adam`, `am_michael`, `bf_emma`, `bf_isabella`, `bm_george`, `bm_lewis`. Ask Claude to "play a few voices" and pick.

## Licences
Plugin code: MIT. Kokoro-82M weights: Apache-2.0 (hexgrad). kokoro-onnx runtime: MIT (thewh1teagle). Models are downloaded from the kokoro-onnx GitHub release at setup time, not bundled.

## About

Working from home, deep in Claude Code, talking to it all day through dictation, and it never talks back. You read, and read, and read. Conversation mode fixes that. Switch it on with /converse and Claude answers out loud with a natural local voice; the spoken part is short, the detail stays written for you to read. It starts speaking while the text is still printing. Say anything and it stops instantly. Change the voice ("use George") or the pace ("faster", "quick fire") just by saying so. Runs entirely on the Mac, no keys, no cloud. A personal side project, shared in case it helps.
