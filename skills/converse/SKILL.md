---
name: converse
description: Conversation mode for Claude Code. /converse (or "let's talk", "conversation mode", "talk to me") switches it on; /converse off switches it off. While on, Claude answers the way a person talks and the spoken part of each reply is read aloud by a local neural voice (Kokoro), while long detail stays written. Any message you send cuts the voice. Also /converse setup, voice <name>, pace (quick | normal | slow, or "faster" / "slower"), speed <x>, test, status.
---

# /converse

State lives in `~/.claude/converse/` (`on` marker, `config`, `last-spoken`, `venv`, `models`, `bin/converse-say`, `bin/converse-stop`). The plugin's hooks speak the 🔊 paragraphs of a finished reply (Stop) and cut speech on every new prompt (UserPromptSubmit). Nothing speaks while the `on` marker is absent.

## Commands
- `/converse setup` (first time): run `bash "<plugin root>/scripts/setup.sh"`; the plugin root is the folder holding this skill's parent `skills/` directory (ask `ls` if unsure). It creates the venv, fetches the model (310 MB) and voices (27 MB) once, writes the default config, and links `~/.claude/converse/bin/converse-say` and `converse-stop`. Reuses an existing HyperFrames Kokoro install if present. Say what it did in one line.
- `/converse` or `/converse on`: `mkdir -p ~/.claude/converse && touch ~/.claude/converse/on`; if `~/.claude/converse/bin/converse-say` is missing, run setup first. Then answer in conversation style from this reply on. Your first spoken line says you are in conversation mode and that any message cuts you off.
- `/converse off`: `rm -f ~/.claude/converse/on; ~/.claude/converse/bin/converse-stop`; drop the style; confirm in one written line.
- `/converse voice <name>`: Kokoro voice ids: `af_sky` (default), `af_heart`, `af_bella`, `af_nicole`, `am_adam`, `am_michael`, `am_onyx`, `bf_emma`, `bf_isabella`, `bm_george`, `bm_lewis`, `bm_fable` (more: run the venv python with `Kokoro(model, voices).get_voices()`). Write `KVOICE=<id>` into `~/.claude/converse/config` (keep other keys) and speak one test line. A macOS voice name (Samantha, Karen, Daniel, Moira) sets `ENGINE=say` and `VOICE=<name>`.
- Pace, by command or by voice ("faster", "slower", "quick fire", "take your time"): write `PACE` and `SPEED`:
  - `quick`: PACE=quick, SPEED=1.45; spoken part one sentence, under 20 words.
  - `normal`: PACE=normal, SPEED=1.3; one to three sentences, under 60 words.
  - `slow`: PACE=slow, SPEED=1.0; up to four sentences, room for a reason or a question back.
  - `/converse speed <x>` sets the number alone (0.8 to 1.6).
- `/converse test`: `~/.claude/converse/bin/converse-say "Conversation mode works."` (needs the `on` marker).
- `/converse status`: whether `on` exists, the config, whether the venv and model are present.
- Audition voices: synthesize one short line per voice with the venv python and play them one after another; then ask which one.

## Speaking while the reply prints, and stopping
- Hooks fire only at the end of a turn. To speak at the same time as the text appears, first make a Bash call `~/.claude/converse/bin/converse-say "<the exact spoken sentences>"` (plain text, no 🔊, escape straight double quotes), then in the next message write the reply whose 🔊 paragraph is those identical sentences. Speech starts about two seconds later while the person reads; the Stop hook recognises the text (hash in `last-spoken`) and stays silent. Do the same for a mid-turn progress line worth hearing.
- Stopping: the UserPromptSubmit hook kills playback the moment the person sends anything. `/converse off` also stops it.

## How to answer while conversation mode is on
- Every reply opens with one paragraph that starts with 🔊: what you would say out loud to the person next to you. Decision or answer first. No lists, markdown, code, paths, URLs or ids; round numbers the way you would say them. Length follows PACE.
- Then, only when there is detail worth reading rather than hearing: a blank line and the written part, as short as it can be, never repeating the spoken sentences. Say in the 🔊 line that the detail is below.
- Thinking out loud: the whole reply can be the 🔊 paragraph. One question back when it moves the conversation.
- Read `~/.claude/converse/config` when the mode starts and follow its PACE. The mode persists in this session until `/converse off`; a new session needs `/converse` again (the hooks only speak marked paragraphs, so a forgotten style means silence, not noise).
