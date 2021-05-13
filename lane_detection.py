import numpy as np
import cv2
from PIL import Image
import scipy
# from scipy.misc import imresize       # no use after scipy==1.13.0
from moviepy.editor import VideoFileClip
#from IPython.display import HTML
from keras.models import load_model

# Load Keras model
model = load_model('full_CNN_model.h5')

# Class to average lanes with
class Lanes():
    def __init__(self):
        self.recent_fit = []
        self.avg_fit = []

def road_lines(image,lanes,model):
    """ Takes in a road image, re-sizes for the model,
    predicts the lane to be drawn from the model in G color,
    recreates an RGB image of a lane and merges with the
    original road image.
    """
    # Get image ready for feeding into model
    # small_img = imresize(image, (80, 160, 3))
    # print(type(image))
    # print(image.shape)
    small_img = np.array(Image.fromarray(image).resize(((160, 80))))
    small_img = np.array(small_img)
    small_img = small_img[None,:,:,:]

    # Make prediction with neural network (un-normalize value by multiplying by 255)
    prediction = model.predict(small_img)[0] * 255

    # Add lane prediction to list for averaging
    lanes.recent_fit.append(prediction)
    # Only using last five for average
    if len(lanes.recent_fit) > 5:
        lanes.recent_fit = lanes.recent_fit[1:]

    # Calculate average detection
    lanes.avg_fit = np.mean(np.array([i for i in lanes.recent_fit]), axis = 0)

    # Generate fake R & B color dimensions, stack with G
    blanks = np.zeros_like(lanes.avg_fit).astype(np.uint8)  
    lane_drawn = np.dstack((blanks, lanes.avg_fit, blanks))

    # Re-size to match the original image
    # lane_image = imresize(lane_drawn, (720,1280, 3))
    # print('='*30,'\n')
    # print(type(lane_drawn))
    # print(lane_drawn.shape)
    lane_image=cv2.resize(lane_drawn,dsize=(256,144),interpolation=cv2.INTER_LINEAR)
    return lane_image
    # return lane_image
    # lane_image = np.array(Image.fromarray((lane_drawn * 255).astype(np.uint8)).resize(((720,1280))))
    # Merge the lane drawing onto the original image
    print(image.shape)
    print(lane_image.shape)
    result = cv2.addWeighted(image, 0.1, lane_image, 0.5, 0, dtype=cv2.CV_32F)
    return result

# 运行车道线检测程序
# lanes = Lanes()

# Location of the input video
# clip1 = VideoFileClip("video_3.mp4")

# Where to save the output video
# vid_output = 'output_video_3.mp4'

# vid_clip = clip1.fl_image(road_lines)
# vid_clip.write_videofile(vid_output, audio=False)
