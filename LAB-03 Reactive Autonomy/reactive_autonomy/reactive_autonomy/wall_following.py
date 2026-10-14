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
import queue # FIFO queue
import time # Tracking time

################################################################################

MAX_SPEED_MPS = 6.0 # DBW speed limit for the drive motor (m/s)
SAFE_SPEED_MPS = 1.5 # Safe speed limit for the vehicle (m/s)
MAX_STEER_RAD = 0.5236 # Maximum steering angle (rad)
LIDAR_ANG_RES = 0.25 # LIDAR angular resolution (degrees)
LIDAR_LEFT_IDX = 1080 # LIDAR scan left index
LIDAR_RIGHT_IDX = 360 # LIDAR scan right index

################################################################################

class PID_Controller:
    '''
    Generates control action taking into account instantaneous error (proportional action),
    accumulated error (integral action) and rate of change of error (derivative action).
    '''
    def __init__(self, kP, kI, kD, kS):
        self.kP       = kP # Proportional gain
        self.kI       = kI # Integral gain
        self.kD       = kD # Derivative gain
        self.kS       = kS # Saturation constant (error history buffer size)
        self.err_int  = 0 # Error integral
        self.err_dif  = 0 # Error difference
        self.err_prev = 0 # Previous error
        self.err_hist = queue.Queue(self.kS) # Limited buffer of error history
        self.t_prev   = 0 # Previous time

    def control(self, err, t, kP=None, kI=None, kD=None):
        '''
        Generate PID controller output.
        :param err: Instantaneous error in control variable w.r.t. setpoint
        :param t  : Current timestamp
        :return u : PID controller output
        '''
        kP = self.kP if kP is None else kP
        kI = self.kI if kI is None else kI
        kD = self.kD if kD is None else kD
        # Timestep
        if self.t_prev == 0:
            dt = 1
        else:
            dt = t - self.t_prev
        if dt > 0.0:
            self.err_hist.put(err) # Update error history
            self.err_int += err # Integrate error
            if self.err_hist.full(): # Jacketing logic to prevent integral windup
                self.err_int -= self.err_hist.get() # Rolling FIFO buffer
            self.err_dif = (err - self.err_prev) # Error difference
            u = (kP * err) + (kI * self.err_int * dt) + (kD * self.err_dif / dt) # PID control law
            self.err_prev = err # Update previous error term
            self.t_prev = t # Update timestamp
            return u # Control signal

################################################################################

class Wall_Following(Node):
    def __init__(self):
        # Node information
        info = '\nMaintain a safe distance from track boundaries and navigate the racetrack without collisions.\n'
        print(info)

        # Node infrastructure
        super().__init__('wall_following') # Create a node with name 'wall_following'
        qos_profile = QoSProfile( # Ouality of Service profile
            reliability=ReliabilityPolicy.RELIABLE, # Reliable (not best effort) communication
            history=HistoryPolicy.KEEP_LAST, # Keep/store only up to last N samples
            depth=10 # Queue size/depth of 10 (only honored if the “history” policy was set to “keep last”)
        )

        # Node parameters
        self.declare_parameter('control_rate', 10.0) # Control loop execution rate (Hz)
        self.declare_parameter('speed_setpoint', 1.0) # Desired vehicle speed (m/s)
        self.declare_parameter('left_scan_sector', 15.0) # Left laserscan sector (degrees)
        self.declare_parameter('left_scan_offset', 15.0) # Left laserscan offset (degrees)
        self.declare_parameter('right_scan_sector', 15.0) # Right laserscan sector (degrees)
        self.declare_parameter('right_scan_offset', 15.0) # Right laserscan offset (degrees)
        self.declare_parameter('pid_controller_kp', 0.5) # Wall-following PID controller proportional gain
        self.declare_parameter('pid_controller_ki', 0.01) # Wall-following PID controller integral gain
        self.declare_parameter('pid_controller_kd', 0.02) # Wall-following PID controller derivative gain
        self.declare_parameter('perception_verbose', True) # Verbose perception output
        self.declare_parameter('control_verbose', True) # Verbose control output
        self.control_rate = self.get_parameter('control_rate').value
        self.speed_setpoint = self.get_parameter('speed_setpoint').value
        self.left_scan_sector = self.get_parameter('left_scan_sector').value
        self.left_scan_offset = self.get_parameter('left_scan_offset').value
        self.right_scan_sector = self.get_parameter('right_scan_sector').value
        self.right_scan_offset = self.get_parameter('right_scan_offset').value
        self.pid_controller_kp = self.get_parameter('pid_controller_kp').value
        self.pid_controller_ki = self.get_parameter('pid_controller_ki').value
        self.pid_controller_kd = self.get_parameter('pid_controller_kd').value
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
        self.left_scan = 0.0 # Initialize variable to capture the left laserscan
        self.right_scan = 0.0 # Initialize variable to capture the right laserscan
        self.ctrl_msg = AckermannDriveStamped() # Vehicle control commands
        self.pid_controller = PID_Controller(self.pid_controller_kp,
                                             self.pid_controller_ki,
                                             self.pid_controller_kd,
                                             10) # Lateral PID controller object initialized with kP, kI, kD, kS

    def parameter_callback(self):
        names = (
            'control_rate',
            'speed_setpoint',
            'left_scan_sector',
            'left_scan_offset',
            'right_scan_sector',
            'right_scan_offset',
            'pid_controller_kp',
            'pid_controller_ki',
            'pid_controller_kd',
            'perception_verbose',
            'control_verbose'
        )
        for parameter in self.get_parameters(names):
            setattr(self, parameter.name, parameter.value)

    def perception_callback(self, msg):
        if self.left_scan_sector == 0:
            self.left_scan = msg.ranges[LIDAR_LEFT_IDX] # Single left scan measurement
        else:
            # Average measurement over the left scan sector
            start_index = int((LIDAR_LEFT_IDX - self.left_scan_offset/LIDAR_ANG_RES) - (self.left_scan_sector/LIDAR_ANG_RES)/2)
            end_index = int((LIDAR_LEFT_IDX - self.left_scan_offset/LIDAR_ANG_RES) + (self.left_scan_sector/LIDAR_ANG_RES)/2)
            self.left_scan = np.mean(msg.ranges[start_index:end_index])
        if self.right_scan_sector == 0:
            self.right_scan = msg.ranges[LIDAR_RIGHT_IDX] # Single right scan measurement
        else:
            # Average measurement over the right scan sector
            start_index = int((LIDAR_RIGHT_IDX + self.right_scan_offset/LIDAR_ANG_RES) - (self.right_scan_sector/LIDAR_ANG_RES)/2)
            end_index = int((LIDAR_RIGHT_IDX + self.right_scan_offset/LIDAR_ANG_RES) + (self.right_scan_sector/LIDAR_ANG_RES)/2)
            self.right_scan = np.mean(msg.ranges[start_index:end_index])
        if self.perception_verbose:
            print('Left scan: {:.3f} m | Right scan: {:.3f} m'.format(self.left_scan, self.right_scan))

    def control_callback(self):
        # Longitudinal control
        if self.speed_setpoint > SAFE_SPEED_MPS:
            self.speed_setpoint = SAFE_SPEED_MPS # Limit the speed setpoint to the safe speed
            if self.control_verbose:
                print('Speed setpoint limited to {} m/s'.format(self.speed_setpoint))
        self.ctrl_msg.drive.speed = self.speed_setpoint/MAX_SPEED_MPS # Set linear velocity (normalized)
        # Lateral control
        cte = self.left_scan - self.right_scan # Compute error (distance from either walls)
        t_stamp = time.time() # Current timestamp (s)
        if cte == np.inf: # Large gap on the left side (no wall detected)
            self.ctrl_msg.drive.steering_angle = 1.0 # Steer left (normalized)
        elif cte == -np.inf: # Large gap on the right side (no wall detected)
            self.ctrl_msg.drive.steering_angle = -1.0 # Steer right (normalized)
        else:
            self.ctrl_msg.drive.steering_angle = max(-1.0, min(1.0,
                                                 self.pid_controller.control(cte,
                                                                             t_stamp,
                                                                             self.pid_controller_kp,
                                                                             self.pid_controller_ki,
                                                                             self.pid_controller_kd))) # Set steering angle (normalized)
        self.vehicle_ctrl_pub.publish(self.ctrl_msg) # Publish vehicle control message
        if self.control_verbose:
            print('Speed: {:.3f} m/s | Steer: {:.3f} rad | Error: {:.3f} m'.format(self.ctrl_msg.drive.speed*MAX_SPEED_MPS,
                                                                                   self.ctrl_msg.drive.steering_angle*MAX_STEER_RAD,
                                                                                   cte))

################################################################################

def main(args=None):
    rclpy.init(args=args) # Start ROS 2 communications
    node = Wall_Following() # Create node
    rclpy.spin(node) # Execute node
    node.destroy_node() # Destroy node explicitly (optional - otherwise it will be done automatically when garbage collector destroys the node object)
    rclpy.shutdown() # Shutdown ROS 2 communications

################################################################################

if __name__ == "__main__":
    main()
