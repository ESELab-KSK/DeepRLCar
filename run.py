from airsim_client import *
from rl_model import RlModel
import numpy as np
import time
import sys
import json
import PIL
import PIL.ImageFilter
import datetime
import cv2

MODEL_FILENAME = 'data/bestpoint/deep+handle+speed+far_reward_penalty_1;9/132341.json'
random_respawn = False

print('If you want to use handle, Enter "y", otherwise "n"')
handle_choose = True
# if input() == 'y': pass
# else: handle_choose = False
print('If you want to use lane detection, Enter "y", otherwise "n"')
lane_choose = False
# if input() == 'n': pass
# else: lane_choose = True
print('If you want to do speed handling, Enter "y", otherwise "n"')
speed_choose = True
# if input() == 'y': pass
# else: speed_choose = False

model = RlModel(None, False, handle_choose, lane_choose, speed_choose)
with open(MODEL_FILENAME, 'r') as f:
    checkpoint_data = json.loads(f.read())
    model.from_packet(checkpoint_data['model'])



print('Connecting to AirSim...')
car_client = CarClient()
car_client.confirmConnection()
car_client.enableApiControl(True)
car_controls = CarControls()
print('Connected!')

def get_image(car_client):
    image_response = car_client.simGetImages([ImageRequest(0, AirSimImageType.Scene, False, False)])[0]
    image1d = np.frombuffer(image_response.image_data_uint8, dtype=np.uint8)
    image_rgba = image1d.reshape(image_response.height, image_response.width, 4)
    image_rgba = image_rgba[76:135,0:255,0:3].astype(float)
    image_rgba = image_rgba.reshape(59, 255, 3)
    return image_rgba

#added by wb -> change starting point
#---------------------------------------
def get_next_starting_point(car_client):

    # Get the current state of the vehicle
    car_state = car_client.getCarState()

    # Pick a random road.
    random_line_index = np.random.randint(0, high=len(road_points))
    
    # Pick a random position on the road. 
    # Do not start too close to either end, as the car may crash during the initial run.
    
    # added return to origin by Kang 21-03-10
    if not random_respawn:
        random_interp = 0.1    # changed by GY 21-03-10

        # Pick a random direction to face
        random_direction_interp = 0.4 # changed by GY 21-03-10
    else:
        random_interp = (np.random.random_sample() * 0.4) + 0.3 
        random_direction_interp = np.random.random_sample()

    # Compute the starting point of the car
    random_line = road_points[random_line_index]
    random_start_point = list(random_line[0])
    random_start_point[0] += (random_line[1][0] - random_line[0][0])*random_interp
    random_start_point[1] += (random_line[1][1] - random_line[0][1])*random_interp

    # Compute the direction that the vehicle will face
    # Vertical line
    if (np.isclose(random_line[0][1], random_line[1][1])):
        if (random_direction_interp > 0.5):
            random_direction = (0,0,0)
        else:
            random_direction = (0, 0, math.pi)
    # Horizontal line
    elif (np.isclose(random_line[0][0], random_line[1][0])):
        if (random_direction_interp > 0.5):
            random_direction = (0,0,math.pi/2)
        else:
            random_direction = (0,0,-1.0 * math.pi/2)

    # The z coordinate is always zero
    random_start_point[2] = -0
    return (random_start_point, random_direction)

def init_road_points():
    road_points = []
    car_start_coords = [12961.722656, 6660.329102, 0]
    road = ''
    if not random_respawn:
        road = 'road_lines.txt'
    else:
        road = 'origin_road_lines.txt'
    with open(os.path.join(os.path.join('data', 'data'), road), 'r') as f:
        for line in f:
            points = line.split('\t')
            first_point = np.array([float(p) for p in points[0].split(',')] + [0])
            second_point = np.array([float(p) for p in points[1].split(',')] + [0])
            road_points.append(tuple((first_point, second_point)))

    # Points in road_points.txt are in unreal coordinates
    # But car start coordinates are not the same as unreal coordinates
    for point_pair in road_points:
        for point in point_pair:
            point[0] -= car_start_coords[0]
            point[1] -= car_start_coords[1]
            point[0] /= 100
            point[1] /= 100
    return road_points

road_points = init_road_points() 
starting_points, starting_direction = get_next_starting_point(car_client)
car_client.simSetPose(Pose(Vector3r(starting_points[0], starting_points[1], starting_points[2]), AirSimClientBase.toQuaternion(starting_direction[0], starting_direction[1], starting_direction[2])), True)
#---------------------------------------
state_buffer = []
print('Running car for a few seconds...')
car_controls.steering = 0
car_controls.throttle = 1
car_controls.brake = 0
car_client.setCarControls(car_controls)
prev_steering = 0
handle_dir = 'data/handle_image/'
handles = {0 : cv2.cvtColor(cv2.imread(handle_dir+'0.png'), cv2.COLOR_BGR2GRAY),
            20 : cv2.cvtColor(cv2.imread(handle_dir+'right20.png'), cv2.COLOR_BGR2GRAY),
            40 : cv2.cvtColor(cv2.imread(handle_dir+'right40.png'), cv2.COLOR_BGR2GRAY),
            60 : cv2.cvtColor(cv2.imread(handle_dir+'right60.png'), cv2.COLOR_BGR2GRAY),
            80 : cv2.cvtColor(cv2.imread(handle_dir+'right80.png'), cv2.COLOR_BGR2GRAY),
            -20 : cv2.cvtColor(cv2.imread(handle_dir+'left20.png'), cv2.COLOR_BGR2GRAY),
            -40 : cv2.cvtColor(cv2.imread(handle_dir+'left40.png'), cv2.COLOR_BGR2GRAY),
            -60 : cv2.cvtColor(cv2.imread(handle_dir+'left60.png'), cv2.COLOR_BGR2GRAY),
            -80 : cv2.cvtColor(cv2.imread(handle_dir+'left80.png'), cv2.COLOR_BGR2GRAY)}
print('Running model')
while(True):
    state_buffer = get_image(car_client)
    #with handle
    if handle_choose:
        angle = -int(prev_steering/0.05*4)
        pre_handle = handles[angle].reshape(59,255,1)
        state_buffer = np.concatenate([state_buffer, pre_handle], axis=2)

    if speed_choose:
        speed = max(0, car_client.getCarState().speed)
        state_speed = np.ones((59,255,1))
        state_speed.fill(speed)
        # uint_img = np.array(state_speed*3315).astype('uint8')
        # grayImage = cv2.cvtColor(uint_img, cv2.COLOR_GRAY2BGR)
        # cv2.imshow('test',grayImage)
        state_buffer = np.concatenate([state_buffer, state_speed], axis=2)
    
        
    next_state, next_throttle, dummy = model.predict_state(state_buffer, use_speed = speed_choose)
    if speed_choose:
        next_control_signal = model.state_to_control_signals(next_state, car_throttle=next_throttle, use_speed=speed_choose)
    else:
        next_control_signal = model.state_to_control_signals(next_state, car_client.getCarState())

    car_controls.steering = next_control_signal[0]
    # prev_steering = car_controls.steering
    car_controls.throttle = next_control_signal[1]
    car_controls.brake = next_control_signal[2]
    
    print('State = {0}, steering = {1}, throttle = {2}, brake = {3}'.format(next_state, car_controls.steering, car_controls.throttle, car_controls.brake))

    car_client.setCarControls(car_controls)
    
    time.sleep(0.1)