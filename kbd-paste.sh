NIRI=./target/debug/niri
$NIRI msg action reset-keyboard-recording
$NIRI msg action extend-keyboard-recording "+50 +43 -43 -50 +26 -26 +46 -46 +46 -46 +32 -32 +65 -65 +50 +25 -25 -50 +50 +32 -32 -50 +50 +27 -27 -50 +46 -46 +40 -40"
sleep 2s
$NIRI msg action playback-keyboard-recording
