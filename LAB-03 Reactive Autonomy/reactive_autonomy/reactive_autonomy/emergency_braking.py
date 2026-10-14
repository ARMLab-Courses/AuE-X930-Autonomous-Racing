#!/usr/bin/env python3

################################################################################

# Copyright (c) 2026, Tinker Twins, AutoDRIVE Ecosystem
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

################################################################################

# ROS 2 module imports
import rclpy # ROS 2 client library (rcl) for Python (built on rcl C API)
from rclpy.node import Node # Node class for Python nodes
from sensor_msgs.msg import LaserScan # LaserScan (LIDAR range measurements) message class
from ackermann_msgs.msg import AckermannDriveStamped # Actuation (speed and steering commands) message class
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy # Quality of Service (tune communication between nodes)

# Python module imports
import numpy as np # Numerical computations

################################################################################

MAX_SPEED_MPS = 6.0 # DBW speed limit for the drive motor (m/s)
SAFE_SPEED_MPS = 1.5 # Safe speed limit for the vehicle (m/s)
LIDAR_ANG_RES = 0.25 # LIDAR angular resolution (degrees)
LIDAR_FRONT_IDX = 720 # LIDAR scan front index

################################################################################

class Emergency_Braking(Node):
    def __init__(self):
        # Node information
        info = '\nDetect imminent frontal collisions and trigger emergency braking when necessary.\n'
        print(info)

        # Node infrastructure
        super().__init__('emergency_braking') # Create a node with name 'emergency_braking'
        qos_profile = QoSProfile( # Ouality of Service profile
            reliability=ReliabilityPolicy.RELIABLE, # Reliable (not best effort) communication
            history=HistoryPolicy.KEEP_LAST, # Keep/store only up to last N samples
            depth=10 # Queue size/depth of 10 (only honored if the “history” policy was set to “keep last”)
        )
        
        # Node parameters
        self.declare_parameter('control_rate', 10.0) # Control loop execution rate (Hz)
        self.declare_parameter('speed_setpoint', 1.0) # Desired vehicle speed (m/s)
        self.declare_parameter('dtc_offset', 0.265) # LIDAR to bumper offset (m)
        self.declare_parameter('dtc_threshold', 0.855) # Threshold for emergency braking (m)
        self.declare_parameter('front_scan_sector', 0.0) # Front laserscan sector (degrees)
        self.declare_parameter('perception_verbose', True) # Verbose perception output
        self.declare_parameter('control_verbose', True) # Verbose control output
        self.control_rate = self.get_parameter('control_rate').value
        self.speed_setpoint = self.get_parameter('speed_setpoint').value
        self.dtc_offset = self.get_parameter('dtc_offset').value
        self.dtc_threshold = self.get_parameter('dtc_threshold').value
        self.front_scan_sector = self.get_parameter('front_scan_sector').value
        self.perception_verbose = self.get_parameter('perception_verbose').value
        self.control_verbose = self.get_parameter('control_verbose').value

        # Publishers and subscribers
        self.vehicle_scan_sub = self.create_subscription(LaserScan, '/scan', self.perception_callback, qos_profile) # Subscriber which will subscribe to LaserScan message on the topic '/scan' adhering to 'qos_profile' QoS profile
        self.vehicle_scan_sub # Prevent unused variable warning
        self.vehicle_ctrl_pub = self.create_publisher(AckermannDriveStamped, '/drive', qos_profile) # Publisher which will publish AckermannDriveStamped message to the topic '/drive' adhering to 'qos_profile' QoS profile
        timer_period = 1/self.control_rate # Node execution time period (seconds)
        self.create_timer(timer_period, self.parameter_callback) # Define timer to execute 'parameter_callback()' every 'timer_period' seconds
        self.create_timer(timer_period, self.control_callback) # Define timer to execute 'control_callback()' every 'timer_period' seconds

        # Member variables
        self.front_scan = np.inf # Initialize variable to capture the front laserscan
        self.ctrl_msg = AckermannDriveStamped() # Vehicle control commands

    def parameter_callback(self):
        names = (
            'control_rate',
            'speed_setpoint',
            'dtc_offset',
            'dtc_threshold',
            'front_scan_sector',
            'perception_verbose',
            'control_verbose'
        )
        for parameter in self.get_parameters(names):
            setattr(self, parameter.name, parameter.value)

    def perception_callback(self, msg):
        if self.front_scan_sector == 0:
            self.front_scan = msg.ranges[LIDAR_FRONT_IDX] # Single front scan measurement
        else:
            # Average measurement over the front scan sector
            start_index = int((LIDAR_FRONT_IDX - (self.front_scan_sector/LIDAR_ANG_RES)/2))
            end_index = int((LIDAR_FRONT_IDX + (self.front_scan_sector/LIDAR_ANG_RES)/2))
            self.front_scan = np.mean(msg.ranges[start_index:end_index])
        if self.perception_verbose:
            print('Front scan: {:.3f} m'.format(self.front_scan))

    def control_callback(self):
        # Nominal behavior: let vehicle continue its motion
        if self.front_scan - self.dtc_offset > self.dtc_threshold:
            if self.speed_setpoint > SAFE_SPEED_MPS:
                self.speed_setpoint = SAFE_SPEED_MPS # Limit the speed setpoint to the safe speed
                if self.control_verbose:
                    print('Speed setpoint limited to {} m/s'.format(self.speed_setpoint))
            self.ctrl_msg.drive.speed = self.speed_setpoint/MAX_SPEED_MPS # Set linear velocity (normalized)
            self.ctrl_msg.drive.steering_angle = 0.0 # Set steering angle (normalized)
            self.vehicle_ctrl_pub.publish(self.ctrl_msg) # Publish vehicle control message
            if self.control_verbose:
                print('Speed setpoint: {} m/s'.format(self.speed_setpoint))
        # Collision imminent: execute emergency braking maneuver
        else:
            self.ctrl_msg.drive.speed = 0.0 # Set linear velocity (normalized)
            self.ctrl_msg.drive.steering_angle = 0.0 # Set steering angle (normalized)
            self.vehicle_ctrl_pub.publish(self.ctrl_msg) # Publish vehicle control message
            if self.control_verbose:
                print('AEB triggered!')

################################################################################

def main(args=None):
    rclpy.init(args=args) # Start ROS 2 communications
    node = Emergency_Braking() # Create node
    rclpy.spin(node) # Execute node
    node.destroy_node() # Destroy node explicitly (optional - otherwise it will be done automatically when garbage collector destroys the node object)
    rclpy.shutdown() # Shutdown ROS 2 communications

################################################################################

if __name__ == "__main__":
    main()
