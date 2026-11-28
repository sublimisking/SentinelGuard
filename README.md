# SentinelGuard

A Windows laptop security application for libraries, cafés, and shared workspaces. Arm it before you step away: if someone unplugs your charger, connects a USB device, or touches your mouse or keyboard, a loud alarm sounds until the correct PIN is entered.

## Features
- USB connection and disconnection monitoring
- Power adapter disconnection detection
- Mouse and keyboard activity monitoring
- PIN-protected alarm deactivation
- Customizable alarm audio output
- Alarm photo: one camera photo is taken when the alarm starts
- Local security event history (last 10 events) and a Photos tab
- Automatic updates from GitHub with SHA256 verification

## Privacy
SentinelGuard works entirely on your computer. It has no accounts, no analytics, and no cloud service.

- **Alarm photos** are taken only when an alarm starts, and only if the camera option is on (Settings > Alarm Photo; on by default). The camera is not used at any other time.
- Photos are saved locally in `%LOCALAPPDATA%\SentinelGuard\captures`. They are never uploaded or sent anywhere.
- At most **5 photos** are kept. When a sixth is taken, the oldest is deleted automatically.
- You can view and delete photos at any time in the **Photos** tab.
- The **event history** is stored locally in `%LOCALAPPDATA%\SentinelGuard\events.db`. It records only the event type, a short description, and the time. It never stores your PIN, typed keys, or USB device identifiers.
- Your PIN is stored only as a hash on this computer.
- The only network access is the update feature, which asks GitHub for the latest release and downloads the installer when you choose to update. It sends none of your data.

If the camera cannot be opened, check Windows Settings > Privacy & security > Camera and allow desktop apps to use it. Alarm photos may capture people near your laptop, so make sure you comply with the privacy rules that apply where you use it.

## Installation
Download the latest `SentinelGuard-vX.Y.Z-Setup.exe` from the [Releases](https://github.com/sublimisking/SentinelGuard/releases) page, run it, then configure your alarm speaker and security PIN.

## Important
SentinelGuard is a deterrent. It does not replace Windows device security, disk encryption, or physical theft protection. The application can be terminated, and alarm delivery cannot be guaranteed.
