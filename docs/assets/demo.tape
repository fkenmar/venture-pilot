# venture-pilot — demo GIF.
# This replays REAL output captured from `vp ... --sdk` running live on a Claude
# subscription (docs/assets/demo_validate.ansi / demo_synth.ansi — genuine web-search
# sources + a real grounded verdict), paced for the camera so there's no dead air.
# Build:  vhs docs/assets/demo.tape

Output "/Users/kenmarfrancisco/Projects/venture-pilot/docs/assets/demo.gif"

Set Shell "bash"
Set FontFamily "Menlo"
Set FontSize 18
Set Width 1100
Set Height 920
Set Padding 30
Set Margin 26
Set MarginFill "#05070C"
Set BorderRadius 12
Set WindowBar Colorful
Set WindowBarSize 40
Set Framerate 24
Set TypingSpeed 30ms
Set Theme { "name": "venture-pilot", "background": "#0A0E14", "foreground": "#E6EDF3", "cursor": "#20E3A2", "selection": "#15342C", "black": "#0A0E14", "red": "#F2545B", "green": "#20E3A2", "yellow": "#F5A524", "blue": "#5B8DEF", "magenta": "#B794F6", "cyan": "#34D399", "white": "#E6EDF3", "brightBlack": "#5B6675", "brightRed": "#F2545B", "brightGreen": "#20E3A2", "brightYellow": "#F5A524", "brightBlue": "#5B8DEF", "brightMagenta": "#B794F6", "brightCyan": "#34D399", "brightWhite": "#FFFFFF" }

Hide
Type "export PS1='~ $ '"
Enter
Type "cd /Users/kenmarfrancisco/Projects/venture-pilot"
Enter
Type `vp() { f=docs/assets/demo_validate.ansi; [ "$1" = synthesize ] && f=docs/assets/demo_synth.ansi; while IFS= read -r l; do printf "%s\n" "$l"; sleep 0.03; done < "$f"; }`
Enter
Type "clear"
Enter
Show
Sleep 700ms

Type `vp validate "Slack bot that summarizes long threads for managers"`
Sleep 400ms
Enter
Sleep 4s

Type "vp synthesize ./interviews/*.md"
Sleep 400ms
Enter
Sleep 4s
Sleep 1500ms
