# NiRIce/Combined

This branch includes all extra features that I find useful.

## BRANCH: keyboard_named_binds
Allows to setup custom keybinds
E.g.
```
    bind_group "overview" {
        binds {
            Left { focus-column-left; }
            Right { focus-column-right; }
            Up { focus-window-or-workspace-up; }
            Down { focus-window-or-workspace-down; }
        }
    }
    bind_group "column-width" {
        binds{
            ///
            "9" { set-column-width "90%"; }
            "0" { set-column-width "100%"; }
        }
    }

binds {
    Mod+BracketLeft  { set-keybinding-group "column-width"; }
```


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
# BRANCH: force-lid-open
(removed)
# keycode-queue
(almost removed; only cmds remained)
