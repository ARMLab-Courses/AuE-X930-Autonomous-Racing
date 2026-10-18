# NeoRacer 101

**Authors:** [Chinmay Samak](https://www.linkedin.com/in/samakchinmay) and [Tanmay Samak](https://www.linkedin.com/in/samaktanmay)

This guide introduces the NeoRacer vehicle architecture and covers the handover, unboxing, setup, installation, and testing instructions (with troubleshooting tips). It assumes working knowledge of Linux, Python, and ROS 2.

> [!NOTE]
> **Course context:** NeoRacer serves as a 1:12 scale reference platform for this course. It integrates onboard compute, sensing (encoder, IMU, camera, and LIDAR), actuation (drive-by-wire and steer-by-wire), and vehicle interfaces into a compact Ackermann-steered 4WD chassis, providing the hardware foundation for autonomous vehicle development.

## Learning goals

By the end of this guide, you should be able to:

- acknowledge the NeoRacer handover;
- unbox and verify the package contents;
- setup the vehicle hardware and interfaces;
- install NeoRacer dependencies and ROS 2 driver;
- test core units and interfaces of the vehicle.

## Core mental model

```mermaid
flowchart TB

    %% =========================
    %% POWER
    %% =========================

    Battery["LiPo Battery<br/><small>11.1 V 5200 mAh</small>"]
    Power["Power Module"]
    Switch["Power Switch"]

    %% =========================
    %% SENSORS
    %% =========================

    Camera["Camera<br/><small>130° FOV RGB Camera</small>"]
    LIDAR["LIDAR<br/><small>LakiBeam1</small>"]
    Encoder["Encoder<br/><small>Hall Effect</small>"]

    %% =========================
    %% COMPUTE
    %% =========================

    Jetson["Jetson<br/><small>Orin Nano</small>"]

    subgraph OSCORE["OSCORE"]
        IMU["IMU<br/><small>QMI8658A + QMC6309</small>"]
        ESP["ESP32-S3<br/><small>WROOM-1U-N16R8</small>"]
        ETH["Ethernet<br/><small>HR641680E</small>"]
        USB["USB Hub<br/><small>CH339F</small>"]
        DC["9-26 V DC Regulator<br/><small>TPS54540</small>"]
    end

    %% =========================
    %% COMMS
    %% =========================

    Router["WiFi Router<br/><small>Cudy TR1200</small>"]
    RC["RC Receiver<br/><small>FS-iA6B</small>"]

    %% =========================
    %% ACTUATORS & INDICATORS
    %% =========================

    Servo["Servo"]
    ESC["ESC"]
    LED["LED Dot Matrix<br/><small>MAX7219 8×8</small>"]
    Motor["DC Motor"]

    %% =========================
    %% DATA FLOW
    %% =========================

    Router <-->|"USB-C"| USB
    Router <-->|"RJ45"| ETH
    Camera -->|"USB-A 5P"| Jetson
    LIDAR -->|"USB-C 4P"| USB
    USB -->|"MX1.25 4P"| LED
    Jetson <-->|"USB-A 4P"| USB
    Encoder -->|"MX1.25 4P"| ESP
    Encoder -.- Motor

    RC -->|"SH1.0 3P"| ESP
    ESP -->|"2.54 3P"| Servo
    ESP -->|"2.54 3P"| ESC
    ESC -->|"2P"| Motor

    %% =========================
    %% POWER FLOW
    %% =========================

    Battery -->|"XT60"| Power
    Power -->|"2P"| Switch
    Switch -->|"DC5525"| Jetson
    Switch -->|"XT30"| DC

    %% =========================
    %% FORCE ACTUATOR ORDER
    %% =========================
    %% Invisible links force horizontal ordering:
    %% Servo -> ESC -> LED

    Servo ~~~ ESC
    ESC ~~~ LED

    %% Keep Motor below ESC
    ESC ~~~ Motor

    %% =========================
    %% STYLING
    %% =========================

    classDef power fill:#FFE8E8,stroke:#C94C4C,stroke-width:2px,color:#1B2036;
    classDef sensor fill:#E8F4FF,stroke:#2B78C5,stroke-width:2px,color:#1B2036;
    classDef compute fill:#EDE7F6,stroke:#6A4C93,stroke-width:2px,color:#1B2036;
    classDef comms fill:#E5F7EC,stroke:#299B5F,stroke-width:2px,color:#1B2036;
    classDef actuator fill:#FFF4D6,stroke:#D99A00,stroke-width:2px,color:#1B2036;

    class Battery,Power,Switch,DC power;
    class Camera,LIDAR,Encoder,IMU sensor;
    class Jetson,ESP compute;
    class Router,RC,ETH,USB comms;
    class ESC,Motor,Servo,LED actuator;
```

- All **power** modules are highlighted in $\color{red}{\text{red}}$ color.
- All **sensor** modules are highlighted in $\color{cornflowerblue}{\text{blue}}$ color.
- All **compute** modules are highlighted in $\color{plum}{\text{violet}}$ color.
- All **network** modules are highlighted in $\color{green}{\text{green}}$ color.
- All **actuator** modules are highlighted in $\color{gold}{\text{yellow}}$ color.

## 1. Handover procedure

Each team will be provided with a course equipment package, which includes:
- 1 × NeoRacer vehicle (with 1 × LiPo battery)
- 1 × LiPo battery charger
- 1 × WiFi router
- 1 × tools pouch
- ⁠1 × accessories pouch
- ⁠1 × remote controller (with 4 × AA alkaline batteries)
- 1 × vehicle stand

Each team will return the NeoRacer hardware and associated components to the designated course staff at the end of the semester in substantially the same condition in which they were received. Ordinary wear and tear is expected and will undergo an acceptance review.

Teams may be responsible for any damage, loss, or misuse of the NeoRacer hardware and associated components during the checkout period, subject to applicable course policies.

Each team will sign the [Equipment Acknowledgment](Acknowledgment.pdf) to complete the handover.

## 2. Unbox the course equipment package

Verify the contents of your course equipment package:
- [x] 1 × NeoRacer vehicle (with 1 × LiPo battery)
- [x] 1 × LiPo battery charger
- [x] 1 × WiFi router
- [x] 1 × tools pouch
- [x] ⁠1 × accessories pouch
- [x] ⁠1 × remote controller (with 4 × AA alkaline batteries)
- [x] 1 × vehicle stand

Following is a box-by-box layout of the course equipment package contents:

```mermaid
block
    columns 1
    block:SHIPMENT
        columns 1
        block:NEO
            columns 2
            VEHICLE["🏎️<br/><b>NeoRacer Vehicle</b><br/><font color='#64748B'>🔧 Semi-Assembled<br/>🔋 LiPo Battery Included</font>"]
            block:ACC
                columns 2

                CHARGER["🔌<br/><b>LiPo Battery Charger</b><br/><font color='#64748B'>ToolkitRC M4AC</font>"]

                ROUTER["🛜<br/><b>WiFi Router</b><br/><font color='#64748B'>Cudy TR1200</font>"]

                ACCESSORIES["⚙️<br/><b>Accessories Pouch</b><br/><font color='#64748B'>NeoRacer Accessories</font>"]

                TOOLS["🧰<br/><b>Tools Pouch</b><br/><font color='#64748B'>NeoRacer Tools</font>"]
            end
        end

        CONTROLLER["🎮<br/><b>Remote Controller</b><br/><font color='#64748B'>FlySky FSi6S 2.4 GHz Transmitter<br/>🔋 4 x AA Alkaline Batteries Included</font>"]
    end
    block
        columns 2
        STAND["🛞<br/><b>VEHICLE STAND</b><br/><font color='#64748B'>Duratrax Pit Tech Deluxe Truck Stand<br/>⚫ DTXC2379 (Black)</font>"]
        HANDOFF["📝<br/><b>HANDOFF ACKNOWLEDGMENT</b><br/><font color='#64748B'>Equipment Acknowledgment Form<br/>✍️ Fill & Sign</font>"]
    end

    %% =====================================================
    %% STYLING
    %% =====================================================

    %% Shipment — warm cardboard brown
    style SHIPMENT fill:#F5E6D3,stroke:#8B5E34,stroke-width:3px,color:#4A2C17

    %% NeoRacer box — red
    style NEO fill:#FFEDED,stroke:#EF4444,stroke-width:2.5px,color:#7F1D1D
    style ACC fill:#FFEDED,stroke:#EF4444,stroke-width:2.5px,color:#7F1D1D

    %% NeoRacer contents
    style VEHICLE fill:#FFEDED,stroke:#EF4444,stroke-width:1.5px,color:#0F172A
    style CHARGER fill:#FFEDED,stroke:#EF4444,stroke-width:1.5px,color:#0F172A
    style ROUTER fill:#FFEDED,stroke:#EF4444,stroke-width:1.5px,color:#0F172A
    style ACCESSORIES fill:#FFEDED,stroke:#EF4444,stroke-width:1.5px,color:#0F172A
    style TOOLS fill:#FFEDED,stroke:#EF4444,stroke-width:1.5px,color:#0F172A

    %% FlySky — white / gray
    style CONTROLLER fill:#F8FAFC,stroke:#64748B,stroke-width:2px,color:#1E293B

    %% Outside items
    style STAND fill:#ECFDF5,stroke:#10B981,stroke-width:2px,color:#065F46
    style HANDOFF fill:#F8FAFC,stroke:#94A3B8,stroke-width:2px,color:#334155

```

> [!TIP]
> Refer to the [NeoRacer unboxing guide](https://neobotics.org/docs/getting-started/unbox) to learn more about the contents of the NeoRacer shipment package.

## 3. Setup the vehicle

The very first step to getting started with the vehicle setup is most likely to charge the LiPo battery, since it would have been in "storage" mode with ~3.85 V/cell (about 11.55 V total).

> [!TIP]
> Refer to the [NeoRacer battery charging guide](https://neobotics.org/docs/getting-started/charge-and-power) to learn more about charging the battery.

Once the battery is charged, you can begin the hardware setup:
- Setup the WiFi router (Cudy TR1200)
- Attach antennas to Jetson's Wi-Fi card
- Connect Jetson to power and OSCORE
- Connect the camera and LIDAR cables
- Plug in monitor and keyboard/mouse
- Connect to the internet (WiFi/Ethernet)

> [!TIP]
> Refer to the [NeoRacer vehicle setup guide](https://neobotics.org/docs/getting-started/prepare-the-car) to learn more about setting up the vehicle.

## 4. Install the drivers

Once the hardware is setup, you can install the [`neoracer_ros2_driver`](https://github.com/Neobotics-Foundation-Inc/neoracer_ros2_driver).

- Change directory to `$HOME`:
    ```bash
    cd ~
    ```
- Clone the [`neoracer-installer`](https://github.com/Neobotics-Foundation-Inc/neoracer-installer) repository:
    ```bash
    git clone https://github.com/Neobotics-Foundation-Inc/neoracer-installer.git
    ```    
> [!IMPORTANT]
> Unmask the NVIDIA camera service before installing the `neoracer_ros2_driver`:
> ```bash
> sudo systemctl unmask nvargus-daemon
> ```
- Run the `install.sh` shell script (single-command installation):
    ```bash
    bash neoracer-installer/scripts/install.sh
    ```
- Reboot (`group membership`, `udev symlinks`, `racecar services`, etc. only take effect on next boot):
    ```bash
    sudo reboot
    ```

> [!TIP]
> Refer to the [NeoRacer driver installation guide](https://neobotics.org/docs/getting-started/install-driver) to learn more about installing the ROS 2 driver.

## 5. Test the system

Run the `Async Core Test` notebook to check every sensor and control surface on the car and print a pass/fail summary:

- Launch a browser session and go to http://192.168.10.100:8888 to access JupyterLab.

- In the JupyterLab file browser (left pane), go to `neoracer-os` → `labs` → `tests`.

- Open the `test_async_core_real.ipynb` by double-clicking on it.

- Run the notebook by clicking the ▶ button from the toolbar at the top.

- Each test follows a common structure: a title, a short explanation of what is being tested, the code, and the output it prints below. Watch the outputs as they appear.

> [!TIP]
> Refer to the [NeoRacer driver installation guide](https://neobotics.org/docs/getting-started/test-the-system) to learn more about testing the system.

## Tips:

- Smaller screws can be difficult to install, try magnetizing the hex key for ease.

- Once the top platform is disassembled, Jetson WiFi card is accessible from the bottom. You do NOT need to unmount the Jetson carrier board.

- Attach the WiFi antennas to the chassis using zip ties before connecting them to the Jetson Wi-Fi card. This helps them stay in place as you work on connecting them.

- At least for the very first time you boot the vehicle, you will need a monitor with HDMI cable, and a USB keyboard/mouse to work with the vehicle. You can then choose to set up [remote desktop](https://neobotics.org/docs/software/remote-desktop) via the [Cudy router hotspot](https://neobotics.org/docs/getting-started/connect-to-router) or the [Jetson access point](https://neobotics.org/docs/software/networking) for later use.

- Ensure all toggle switches are in TOP position before turning the RC transmitter ON (by long-pressing both the power buttons). Set the position of the speed-mode (left-most) toggle switch as desired: TOP (low-speed), BOTTOM (high-speed). Set the position of the driving-mode (second from left) toggle switch as desired: TOP (autonomous), BOTTOM (manual).

> [!TIP]
> Refer to the [NeoRacer troubleshooting tips](https://neobotics.org/docs/reference/troubleshooting) for more details.

## Safety:

- Operate the vehicle ONLY in open/uncrowded spaces, with at least one dedicated person operating the remote controller for manual override.

- The vehicle speed in autonomous mode is regulated to 6 m/s for safety.

- NEVER leave the vehicle powered unattended.

- Do NOT let your vehicle's LiPo battery reach a state of deep discharge (when its voltage drops below the safe minimum threshold of 3.0 volts per cell). Stop and charge your battery when the vehicle starts making a beeping sound!

- Configure the charger before plugging the battery in for charging.

- ⁠The battery charger is ill-designed, make sure to insert the `balance terminal` (4-pin) correctly (since it can go in either way). Ensure that the negative (black) wire of the `balance terminal` connects to the (-) pin of the charger.

- Adjust the charger voltage to 4.20 V and current to 2.5 A.

- NEVER leave batteries on charging unattended.

- While charging the batteries, make sure to keep the equipment in relatively open/uncrowded spaces and nowhere near any flammable  substances.

- Do NOT charge batteries if you observe any abnormality (puffing, heating, odor, smoke, etc.).

- Do NOT charge the batteries while the discharge terminal is plugged in.

> [!TIP]
> Refer to the [NeoRacer safety procedures](https://neobotics.org/docs/reference/safety) for more details.

## Further reading

- [NeoRacer official website](https://neobotics.org/kits)
- [NeoRacer official documentation](https://neobotics.org/docs)
- [NeoRacer hardware overview](https://neobotics.org/docs/hardware/overview)
- [NeoRacer networking guide](https://neobotics.org/docs/software/networking)
- [NeoRacer remote desktop guide](https://neobotics.org/docs/software/remote-desktop)
- [NeoRacer maintenance schedule](https://neobotics.org/docs/reference/maintenance)
- [NeoRacer frequently asked questions](https://neobotics.org/docs/reference/faq)
