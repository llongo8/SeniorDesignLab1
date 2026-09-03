# Setup

About 20 minutes per machine. Do this on all three laptops in week 1 — a teammate who cannot build
is a teammate who cannot help.

## 0. Prerequisites

| Tool | Check | Get it |
|---|---|---|
| Git | `git --version` | <https://git-scm.com/downloads> |
| Python 3.11+ | `python --version` | See the warning below |
| VS Code | | <https://code.visualstudio.com/> |

> **Windows: avoid the Microsoft Store build of Python.** It ships a read-only `pip.ini` that forces
> `pip install --user`, which collides with PlatformIO installing packages into its own directory.
> The failure looks like `ERROR: Can not combine '--user' and '--target'`, followed by a corrupted
> package and `MissingPackageManifestError`. Install Python from
> [python.org](https://www.python.org/downloads/windows/) instead, ticking "Add Python to PATH".
> If you are stuck with the Store build, see [the workaround](#platformio-fails-with---user-and---target).

## 1. Clone

```bash
git clone <your-repo-url> SeniorDesignLab1
```

## 2. VS Code extensions

Open the folder in VS Code. It will offer the extensions listed in `.vscode/extensions.json` —
accept. The important ones are **PlatformIO IDE** (firmware) and **Python** + **Pylance** (PC app).

PlatformIO IDE bundles its own Python and is the most reliable way to install it on Windows. It
takes a few minutes on first launch; let it finish before opening a terminal.

## 3. PC application

```bash
cd pc-app
python -m venv .venv
```

Activate it — PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Git Bash or macOS/Linux:

```bash
source .venv/Scripts/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create your local config:

```bash
cp .env.example .env
```

Leave `BOX_HOST` pointing at the simulator for now (`127.0.0.1`, port `8080`).

### Run it

Two terminals. First the simulated box:

```bash
cd pc-app
python tools/fake_box.py
```

Then the app:

```bash
cd pc-app
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000>. You should see two live readouts and a scrolling chart within a few
seconds. **No hardware needed** — this is how two of us work while the third has the box.

### Check it

```bash
cd pc-app
python tools/smoke_test.py
```

Expect `18 passed, 0 failed`. Run this before every push.

## 4. Firmware

```bash
copy firmware\include\secrets.example.h firmware\include\secrets.h
```

Edit `include/secrets.h` with your WiFi name and password. It is gitignored — **do not commit it**,
and do not paste credentials into any other file.

Build:

```bash
python -m platformio run -d firmware
```

The first build downloads the ESP32 toolchain — around 300 MB and several minutes. A successful
build ends with a memory summary; ours currently sits at RAM 14.8%, Flash 62.5%.

Flash the board and watch it boot:

```bash
python -m platformio run -d firmware --target upload
```

Then open the serial monitor:

```bash
python -m platformio device monitor -d firmware
```

It prints the IP address once WiFi connects. Put that address in `pc-app/.env` as `BOX_HOST`, set
`BOX_PORT=80`, and restart the PC app to talk to real hardware. The LCD does not show the IP —
both its rows are taken by the two sensors.

If `pio` is not on your PATH, use `python -m platformio` in place of `pio`, or open a
**PlatformIO Core CLI** terminal from the VS Code PlatformIO sidebar.

---

## Troubleshooting

### PlatformIO fails with `--user` and `--target`

Your pip is configured to always install with `--user`. Override it for the build:

```bash
PIP_USER=0 python -m platformio run
```

In PowerShell:

```bash
$env:PIP_USER=0; python -m platformio run
```

If a package was already half-installed, delete it and let PlatformIO fetch it again — for example
`rm -rf ~/.platformio/packages/tool-esptoolpy`. The real fix is to install python.org Python.

### Upload fails or the port is not found

- Install the USB-serial driver your board needs: **CP210x** for most ESP32 DevKits, **CH340** for
  cheaper clones.
- Use a data USB cable. Plenty of cables are charge-only and give no port at all.
- Some boards need `BOOT` held down as the upload starts.

### The LCD is blank

Work through it in this order — it is almost always contrast, not wiring.

- **Blank and unlit**: the backlight. Our blue module needs **5 V** on pin 15 through 220 ohm; at
  3.3 V a blue LED has no headroom and stays dark.
- **Lit but blank**: contrast. `VDD` must also be on **5 V** — a 5 V HD44780 cannot reach usable
  contrast from a 3.3 V supply at any pot setting. Then set `V0` (pin 3) to about 0.5 V.
- **Solid blocks**: too much contrast, or the controller is not being initialised. Back the
  contrast off first; if blocks persist, check pin 5 `RW` is grounded and that `D4`-`D7` reach
  GPIO 21, 17, 16, 15 **in that order**.
- **Text appeared once then vanished**: the display is initialised only at boot, so a power glitch
  leaves it garbled. Press the ESP32 reset button.

See [the wiring guide](docs/06-breadboard-wiring.md) for the full reasoning.

### Temperature reads `-127` or the probe is never found

`-127` is the DS18B20 "no device" sentinel. Check the **4.7 kΩ pull-up between DATA and 3V3** —
one per bus. Without it the bus never reads anything. Check the probe wiring too: red 3V3, black
GND, yellow or white DATA.

### Alerts fail with `535 5.7.8 Username and Password not accepted`

Google rejected the login. Check the shape of the password first: an app password is **16 lowercase
letters**, no digits or symbols. Google shows it as four groups of four, but the spaces are
presentational and the app strips them for you.

If the shape is right, the credential itself is being refused. In order of likelihood:

1. **The app password belongs to a different Google account.** `myaccount.google.com/apppasswords`
   generates for whichever account is active, which is easy to get wrong when signed into several.
   Sign in as only that account in an incognito window and confirm the password is listed.
2. **The account is too new.** Google blocks SMTP and app passwords on freshly created accounts
   until they look established, often for a day or more. No configuration change fixes this.
3. **2-Step Verification was turned off**, which silently revokes every app password.

To tell them apart, try an established personal Gmail with its own freshly generated app password.
If that sends, the problem is the new account rather than anything in the repository.

If Gmail keeps refusing, any SMTP provider works — only the four `SMTP_*` values change. Brevo and
SendGrid both have free tiers intended for exactly this and issue credentials that work
immediately. Do not bother with a `uiowa.edu` address: Iowa runs Microsoft 365, which has basic
SMTP authentication disabled.

### The PC app says "no data available"

- Can you reach the box directly? Open `http://<box-ip>/api/state` in a browser.
- Are the PC and the box on the **same** network? Many campus and guest networks isolate clients
  from each other, which blocks this completely. Use your own hotspot.
- Is `BOX_HOST` in `pc-app/.env` the address the box actually printed at boot? DHCP leases change.
