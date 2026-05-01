# Kid Safe Launcher v3

A simple Python/Tkinter kid-safe dashboard for Windows.

## Run

```bash
python kid_launcher.py
```

Default parent PIN: `1234`

## What changed in v3

- Approved websites/apps are opened maximized/fullscreen where possible.
- The dashboard is no longer lowered behind the Windows desktop.
- When an approved app/site is open, the fullscreen dashboard stays behind it as a safe background.
- A small always-on-top **← Dashboard** button remains in the bottom-left corner.
- Websites opened with Microsoft Edge use app mode plus fullscreen startup flags.

## Important lockdown note

This is a guided launcher, not a complete Windows security boundary. For stronger kid-safety, use:

1. A separate standard Windows child account, not an administrator account.
2. Microsoft Family Safety web/app restrictions.
3. Optional Windows kiosk/assigned access mode.
4. Remove taskbar shortcuts and disable unnecessary startup apps.

This launcher is designed to make the experience simple and contained, but Windows keyboard shortcuts like Alt+Tab, Ctrl+Alt+Del, and system dialogs cannot be fully blocked by normal Python apps.
