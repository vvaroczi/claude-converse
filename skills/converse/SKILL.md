---
name: converse
description: Conversation mode for Claude Code. /converse (or "let's talk", "conversation mode", "talk to me") switches it on; /converse off switches it off. While on, Claude answers the way a person talks and the spoken part of each reply is read aloud by a local neural voice (Kokoro), while long detail stays written. Any message you send cuts the voice. Also /converse setup, voice <name>, pace (quick | normal | slow, or "faster" / "slower"), speed <x>, test, status.
---

# /converse

State lives in `~/.claude/converse/` (`on` marker, `config`, `last-spoken.d/`, `venv`, `models`, `bin/converse-say`, `bin/converse-stop`). The plugin's hooks speak the 🔊 paragraphs of a finished reply (Stop) and cut this chat's speech on every new prompt (UserPromptSubmit). Nothing speaks while the `on` marker is absent.

Several chats can have the mode on at once. They share one voice and take turns: a reply from another chat waits until the current one finishes, a chat's newer reply replaces its own older one, and when the voice switches chats it first says which one ("Portfolios chat."). Typing in a chat stops only that chat's speech. Each chat also gets its own voice: the first speaks in the configured voice, and a new chat started while others are active gets the next free one (George, Emma, Michael, …). `~/.claude/converse/bin/converse-say --voice` prints this chat's voice, e.g. `bm_george George`.

## Commands
- `/converse setup` (first time): run `bash "<plugin root>/scripts/setup.sh"`; the plugin root is the folder holding this skill's parent `skills/` directory (ask `ls` if unsure). It creates the venv, fetches the model (310 MB) and voices (27 MB) once, writes the default config, and links `~/.claude/converse/bin/converse-say` and `converse-stop`. Reuses an existing HyperFrames Kokoro install if present. Say what it did in one line.
- `/converse` or `/converse on`: `mkdir -p ~/.claude/converse && touch ~/.claude/converse/on && ~/.claude/converse/bin/converse-say --warm`; if `~/.claude/converse/bin/converse-say` is missing, run setup first. Then answer in conversation style from this reply on. If the config has no `USER_NAME`, ask once what to call them and write `USER_NAME=<name>` to the config. Your first reply in the mode is the welcome: speak (via `converse-say`, then the 🔊 paragraph) something like "Hey <name>, conversation mode is on, I'm <this chat's voice name from `converse-say --voice`>. Say anything to cut me off. Say faster, slower or quick fire to change pace. Say play the voices to hear the options, or use Emma to switch. Say converse off to end." Under that, write the cheat sheet below once.
- `/converse help`: write the cheat sheet (no need to speak it all).

## Cheat sheet (write it on welcome and on /converse help)
| Say or type | What happens |
|---|---|
| anything at all, even "stop" | the voice stops at once |
| "faster", "slower", "quick fire", "take your time", "normal pace" | pace changes: speed and how long the spoken part is |
| "play the voices" | you hear six voices one after another, each saying its name; then pick |
| "use Emma" / "use George" / `/converse voice af_heart` | switches this chat's voice |
| "speed one point two" / `/converse speed 1.2` | sets the speed alone |
| "longer answers" / "shorter answers" | the spoken part grows or shrinks without changing speed |
| "read the detail" | the written part of the last reply is read aloud once |
| "call me Sam" / `/converse name Sam` | sets the name Claude uses with you |
| "converse off" | mode off, silence, normal written replies |

- "play the voices": audition `af_sky`, `af_heart`, `af_bella`, `bf_emma`, `am_adam`, `bm_george` at the current speed, one short line each that names the voice ("This is Emma."), using the venv python and the model in `~/.claude/converse/models`; then ask which one. Names map to ids: Sky af_sky, Heart af_heart, Bella af_bella, Nicole af_nicole, Emma bf_emma, Isabella bf_isabella, Adam am_adam, Michael am_michael, George bm_george, Lewis bm_lewis.
- "read the detail": run `converse-say` with the written part of your previous reply, flattened to plain sentences.
- "call me <name>" / `/converse name <name>`: write `USER_NAME=<name>` into the config (keep other keys) and greet them with it once.
- "longer answers" / "shorter answers": change PACE in the config (quick, normal, slow) without touching SPEED, and say what you set.
- `/converse off`: `rm -f ~/.claude/converse/on; ~/.claude/converse/bin/converse-stop --all`; drop the style; confirm in one written line. (The `on` marker is shared, so this turns the mode off for every chat.)
- `/converse voice <name>`: Kokoro voice ids: `af_sky` (default), `af_heart`, `af_bella`, `af_nicole`, `am_adam`, `am_michael`, `am_onyx`, `bf_emma`, `bf_isabella`, `bm_george`, `bm_lewis`, `bm_fable` (more: run the venv python with `Kokoro(model, voices).get_voices()`). Run `~/.claude/converse/bin/converse-say --voice <name or id>`, which pins this chat to that voice, and speak one test line. To change the default for new chats as well, also write `KVOICE=<id>` into `~/.claude/converse/config` (keep other keys). A macOS voice name (Samantha, Karen, Daniel, Moira) sets `ENGINE=say` and `VOICE=<name>`.
- Pace, by command or by voice ("faster", "slower", "quick fire", "take your time"): write `PACE` and `SPEED`:
  - `quick`: PACE=quick, SPEED=1.2; spoken part one sentence, under 20 words.
  - `normal`: PACE=normal, SPEED=1.0 (the voice's native pace); one to three sentences, under 60 words.
  - `slow`: PACE=slow, SPEED=0.85; up to four sentences, room for a reason or a question back.
  - `/converse speed <x>` sets the number alone (0.8 to 1.6).
- `/converse language <code>` (also "speak Spanish", "switch to Czech"): write `SPEAK_LANG=<code>` to the config. Codes with native voices, and the voice to switch to unless the person named one: `en-us` (default) or `en-gb` (bm_george, bf_emma); `es` ef_dora / em_alex; `fr-fr` ff_siwis; `it` if_sara / im_nicola; `pt-br` pf_dora / pm_alex; `hi` hf_alpha / hm_omega; `ja` jf_alpha / jm_kumo; `cmn` zf_xiaobei / zm_yunxi. Any other code the phonemizer knows (`cs`, `hu`, `de`, `pl`, `nl`, ...) works with the current voice but sounds accented: say so once. From then on write the 🔊 paragraph in that language.
- `/converse test`: `~/.claude/converse/bin/converse-say "Conversation mode works."` (needs the `on` marker).
- `/converse status`: whether `on` exists, the config, whether the venv and model are present.
- Audition voices: synthesize one short line per voice with the venv python and play them one after another; then ask which one.

## Speaking while the reply prints, and stopping
- The voice must never start after the paragraph has printed. The Stop hook only fires once the whole turn is over, so it is a late safety net, not the way to speak.
- **Always speak first.** For every 🔊 paragraph, the Bash call `~/.claude/converse/bin/converse-say "<the exact spoken sentences>"` (plain text, no 🔊, escape straight double quotes) comes BEFORE the text: before any other tool call that would delay it, and in its own message, with the reply written only in the next message. The 🔊 paragraph is then those identical sentences. The voice daemon keeps the model loaded, so speech starts in well under a second, while the text is still appearing. The Stop hook recognises the text (hash in `last-spoken`) and stays silent.
- A turn with tool work: speak a short opener first ("Let me look at the code."), do the work, then make the converse-say call for the final 🔊 paragraph immediately before writing the final reply. Never write a 🔊 paragraph that was not spoken first.
- `/converse on` also runs `~/.claude/converse/bin/converse-say --warm` so the first reply is fast too. `/converse off` runs `~/.claude/converse/bin/converse-stop --all`. `converse-stop --quit` also shuts the daemon down (it exits by itself after an hour unused).
- Stopping: the UserPromptSubmit hook stops this chat's speech the moment the person sends anything here; other chats keep their turn. `/converse off` stops every chat.

## How to answer while conversation mode is on
- Talk like a colleague who likes working with them, not a status readout. Warm, plain and direct.
  - Use their name (`USER_NAME` in the config) the way a person would: when you greet them, when you come back with news after a stretch of work, when something went well or went wrong. Not in every reply, and never twice in one.
  - Open naturally where it fits: "Hey Viktor, good news.", "Okay, done.", "Right, so…", "Quick one:". Vary it; never the same opener twice in a row.
  - React like a person: a little warmth when something works ("Nice, that worked."), honesty when it didn't ("That didn't go to plan."), and say what you think when they ask for an opinion.
  - Contractions, short sentences, everyday words. No "Certainly!", no "Great question", no filler praise.
  - When you've finished a piece of work they may not be watching, say it as news they can act on: what happened, then what you need from them, if anything.
- Every reply opens with one paragraph that starts with 🔊: what you would say out loud to the person next to you. Decision or answer first. No lists, markdown, code, paths, URLs or ids; round numbers the way you would say them. Length follows PACE.
- Then, only when there is detail worth reading rather than hearing: a blank line and the written part, as short as it can be, never repeating the spoken sentences. Say in the 🔊 line that the detail is below.
- Thinking out loud: the whole reply can be the 🔊 paragraph. One question back when it moves the conversation.
- Read `~/.claude/converse/config` when the mode starts and follow its PACE. The mode persists in this session until `/converse off`; a new session needs `/converse` again (the hooks only speak marked paragraphs, so a forgotten style means silence, not noise).
