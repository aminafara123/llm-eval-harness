# Renders docs/demo.gif with charmbracelet/vhs (needs vhs, ttyd and ffmpeg on PATH).
# Run from the repo root, with the deps installed in .venv:  vhs docs/demo.tape
# Follows DEMO.md: offline tests -> a YAML suite -> scorecard against local Ollama -> regression diff.
Output docs/demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 700
Set Padding 24
Set Theme "Catppuccin Mocha"
Set WindowBar Colorful
Set TypingSpeed 40ms

Hide
Type "VIRTUAL_ENV_DISABLE_PROMPT=1 source .venv/bin/activate"
Enter
Wait@120s
Type `curl -s localhost:11434/api/generate -d '{"model":"qwen3:30b-a3b-instruct-2507-q4_K_M","keep_alive":"10m"}' >/dev/null`
Enter
Wait@120s
Type "clear"
Enter
Wait@120s
Show
Sleep 500ms

Type "make test"
Sleep 400ms
Enter
Wait@120s
Sleep 2s

Type "sed -n '1,20p' suites/json_extraction.yaml"
Sleep 400ms
Enter
Wait@120s
Sleep 3s

Hide
Type "clear"
Enter
Sleep 200ms
Show
Type "python -m eval_harness run suites/qa.yaml"
Sleep 400ms
Enter
Wait@120s
Sleep 4s

Hide
Type "clear"
Enter
Sleep 200ms
Show
Type "make diff"
Sleep 400ms
Enter
Wait@120s
Sleep 4s

Sleep 1s
