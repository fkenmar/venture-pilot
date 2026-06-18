# venture-pilot — demo GIF, recorded from the REAL `vp` CLI (mock mode).
# The app and this GIF are the same thing: `python -m vp validate|synthesize`.
# Build:  vhs docs/assets/demo.tape

Output "/Users/kenmarfrancisco/Projects/venture-pilot/docs/assets/demo.gif"

Set Shell "bash"
Set FontFamily "Menlo"
Set FontSize 18
Set Width 1100
Set Height 880
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
Type `vp() { /opt/homebrew/Caskroom/miniconda/base/bin/python -m vp "$@"; }`
Enter
Type "clear"
Enter
Show
Sleep 700ms

Type `vp validate "Slack bot that summarizes long threads for managers"`
Sleep 400ms
Enter
Sleep 2600ms
Type "y"
Sleep 300ms
Enter
Sleep 5s

Type "vp synthesize ./interviews/*.md"
Sleep 400ms
Enter
Sleep 6s
Sleep 1500ms
