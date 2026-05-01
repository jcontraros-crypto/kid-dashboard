# Kid Safe Launcher - Manual Lockdown Edition

Run manually:

```bash
python kid_launcher.py
```

Default parent PIN: `1234`

## What this version adds

- Still **does not launch on startup**. You manually start it when you want kid mode.
- Fullscreen dashboard stays as the safe background.
- Parent PIN required for Parent Mode or Exit.
- Approved websites open in Microsoft Edge kiosk fullscreen mode when Edge is installed.
- Approved apps are launched and then maximized where Windows allows it.
- Small always-on-top **← Dashboard** button appears while an approved app/site is open.
- Blocks right-click/context menus where Python/Windows permits.
- Blocks common escape shortcuts while running:
  - Alt+Tab
  - Alt+Esc
  - Alt+F4
  - Ctrl+Esc
  - Left/Right Windows key

## Important Windows limitation

A normal Python app cannot fully block **Ctrl+Alt+Del**, Task Manager launched from the secure Windows screen, power buttons, or OS-level accessibility/security dialogs. Windows intentionally protects those shortcuts.

For the strongest practical kid-safe setup, use this launcher with:

1. A separate **standard** Windows child account, not an administrator account.
2. Microsoft Family Safety or browser family settings.
3. No desktop shortcuts except this launcher.
4. A PIN/password your kids do not know.

## Parent controls

Inside the launcher:

- Click **Parent** or press `F12` / `Ctrl+P`.
- Enter the parent PIN.
- Add/edit/remove approved apps and websites.
- Change the PIN and lockdown options.

## Notes for Netflix and other sites

Websites work best with Microsoft Edge installed. The launcher uses Edge kiosk fullscreen mode so kids do not see a normal address bar or normal browser controls. Some streaming services may still show their own internal links or account screens.
