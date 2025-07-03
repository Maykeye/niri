# NiRIce/Combined

This branch includes all extra features that I find useful.

## BRANCH: niri-ipc-stdin

This branch adds very special option to the niri `--stdin`.

When `niri --stdin` is called, instead of parsing `argv`,
niri reads lines  from stdin and assumes each line is passed as argument.
eg
```fish

fish> echo "
niri msg version
niri msg keyboard-layouts
" | niri --stdin
```

will print version and known keyboard layouts.
Empty lines are ignored.
First error will abort the execution.

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

## TODO: readme other branches:
### forced_alpha
### keyboard_named_binds
### keycode-queue
