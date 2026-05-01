# Kid Safe Launcher

A fullscreen Python launcher for kids. It only displays the apps and websites you approve.

## How to run

1. Install Python 3 on Windows.
2. Unzip this folder.
3. Double-click `kid_launcher.py`, or open PowerShell in the folder and run:

```powershell
python kid_launcher.py
```

## Default parent PIN

`1234`

Change it immediately from **Parent Mode**.

## Parent controls

Open Parent Mode with:

- The **Parent** button
- `Ctrl + P`
- `F12`

From there you can:

- Add allowed websites
- Add allowed apps
- Remove items
- Change the PIN
- Turn fullscreen/topmost behavior on or off

## Website behavior

If Microsoft Edge is installed, websites open in Edge `--app` mode, which hides the normal address bar and makes casual browsing away from the approved site harder.

## Important safety note

This is a guided launcher, not a perfect security sandbox. A determined older child may still be able to escape using Windows shortcuts, Task Manager, Ctrl+Alt+Del, another user account, or system access.

For best results:

1. Create a separate standard Windows account for your child.
2. Do not give that account admin rights.
3. Use Microsoft Family Safety or Windows assigned access/kiosk settings if you need stronger lockdown.
4. Put this launcher in the child's Startup folder.
5. Use browser parental controls/DNS filtering for web-level protection.

## Put launcher in Windows Startup

Press `Win + R`, type:

```text
shell:startup
```

Then create a shortcut to `kid_launcher.py` in that folder.
