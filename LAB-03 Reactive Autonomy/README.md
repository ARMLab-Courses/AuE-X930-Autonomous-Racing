# Reactive Autonomy

**Authors:** [Chinmay Samak](https://www.linkedin.com/in/samakchinmay) and [Tanmay Samak](https://www.linkedin.com/in/samaktanmay)

```bash
ros2 pkg create --build-type ament_python reactive_autonomy --dependencies rclpy std_msgs geometry_msgs sensor_msgs nav_msgs ackermann_msgs
```

```bash
docker run --name autodrive_neoracer_api --rm -it --network=host --ipc=host -v /tmp/.X11-unix:/tmp/.X11-unix:rw -v "$PWD/aueX930_ws":/root/aueX930_ws --env DISPLAY --privileged --gpus all autodriveecosystem/autodrive_neoracer_api:2026-fall-practice
```

```bash
cd ~/aueX930_ws
colcon build --symlink-install
source install/setup.bash
```

```bash
ros2 run reactive_autonomy emergency_braking
ros2 run reactive_autonomy wall_following
```

```bash
ros2 launch reactive_autonomy emergency_braking.launch.py
ros2 launch reactive_autonomy wall_following.launch.py
```

```bash
docker run --name autodrive_neoracer_sim --rm -it --network=host --ipc=host -v /tmp/.X11-unix:/tmp/.X11-unix:rw --env DISPLAY --privileged --gpus all autodriveecosystem/autodrive_neoracer_sim:2026-fall-practice
```

## Parameters:

Name    |    Description    |    Default Value    |    Minimum Value    |    Maximum Value    |


```bash
ros2 param set emergency_braking <param_name> <param_value>
```