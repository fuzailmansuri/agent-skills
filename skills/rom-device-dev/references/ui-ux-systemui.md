# UI/UX, SystemUI & Launcher architecture

## 1. Quick Settings & media
- Sliders (brightness/volume) must resize in both orientations with smooth corner-radius
  scaling and live feedback; keep the render path in the standard framework primitives so
  90/120Hz stays smooth and skip custom animation dependencies where the base already
  provides them.
- Media player: consistent padding across QS and shade; popup/compact states must scale with
  the tile grid.

## 2. SystemUI modules (live activities pill, etc.)
- Compact pill → expanded overlay → dual-activity split: each state independently testable,
  settings toggle applies without restart.
- **Cutout & curvature safety:** verify alignment against the actual panel cutout and status
  bar margins on every device you ship this on; prevent left/right clipping on corner radii
  (measure, don't assume).

## 3. Launcher (AOSP/Launcher3 forks)
- Glanceable-hub-style surfaces: widget picker dimensions must match the hub layout exactly
  or resize glitches appear; resize handles share styling with the system picker.
- Dark-shaded opaque styling for feeds/search surfaces.
- 120Hz discipline: eliminate frame deadline misses in launcher touch/swipe handlers first —
  isolate jitter using static wallpapers before blaming launcher code (live-wallpaper FPS
  throttlers throttle independently).
- Commits: describe the mechanism, not the inspiration. Bad: "Add iOS-style pill animation";
  good: "SystemUI: Stage pill animation on surface control resize".
