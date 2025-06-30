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

## TODO: readme other branches:
### forced_alpha
### keyboard_named_binds
### keycode-queue


