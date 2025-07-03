# BRANCH: force-lid-open

This branch adds `force-lid-open` workaround action. Example of addition to `config.kdl`:

```
    Mod+Ctrl+KP_Enter  { force-lid-open; }
```


When action is called, the niri runs the code equivalent to the code received from lid openness switch.
For some reason in many cases the event is not received by niri(at least when I use two monitors). 
Sometimes it does receive the event, if I press random keys beforehand,
but often doesn't. I'm too lazy to debug too deep in the closest eternity, so workaround is sufficient:
once the second monitor turns on, I can press Mod+Ctrl+Keypad enter and the monitor on the laptop turns on.
