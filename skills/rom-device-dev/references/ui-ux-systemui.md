# SystemUI and Launcher integration

Identify the actual branch implementation first: Views, Compose, Shell, SurfaceControl,
Launcher3 and vendor extensions vary by release. Trace the component's state owner,
lifecycle, settings source and resource overlays before adding another path.

Preserve the user's requested design. Do not impose a pill, feed style, corner radius,
refresh rate or another platform's appearance because a previous task used it.

For layout changes, check relevant orientations, density/font scales, cutouts, insets,
RTL, accessibility, navigation modes and collapsed/expanded states. For gesture or
animation changes, check interruption, cancellation and state synchronization using
the primitives already supported by the branch.

Measure frame timing on the target before claiming a performance improvement. Separate
app, compositor, wallpaper, thermal and input-path causes. A high refresh-rate setting
or smooth-looking emulator recording is not proof of meeting device frame deadlines.
If runtime inspection is unavailable, explain the static reasoning and remaining tests.
