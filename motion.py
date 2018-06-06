#!/usr/bin/env python3
# Designed to run on a Raspberry Pi 3

import logging
logging.basicConfig(format='%(message)s', level=logging.INFO)
log = logging.getLogger('')
import datetime
import argparse
import time
import os
import select
import sys
import fcntl
import selectors
import json
from picamera.array import PiRGBArray
from picamera import PiCamera
import cv2


class ConfigData:
    
    def __init__(self):
        self.x = 317
        self.y = 367
        
        self.updateROI = True
        self.reloadView = False
        
        self.liveView_path = '/{}/{}/{}'.format('media','config', 'viewLive.jpg')
        self.roiView_path = '/{}/{}/{}'.format('media','config', 'roi.jpg')
        self.img_path = '/{}/{}'.format('media','motion')
       
        self.w = 948
        self.h = 351
        
        self.startTime =datetime.datetime.now()
        
        self.update()
        
    def update(self):
        self.x1 = self.x
        self.y1 = self.y
        self.x2 = self.x + self.w 
        self.y2 = self.y + self.h
    
    def log(self):
        log.info('Data: x {} y {} w {} h {}'.format(self.x,self.y,self.w,self.h))
        

myData = ConfigData()

def annotate_frame(frame, area, contour,offsetX,offsetY):
    timestamp = datetime.datetime.now()
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    (x, y, w, h) = cv2.boundingRect(contour)
    # show ROI
    cv2.rectangle(frame, ( myData.x, myData.y), (myData.x + myData.w, myData.y + myData.h), (255, 0, 0), 2)
    
    # show motion
    cv2.rectangle(frame, ( offsetX + x, offsetY + y), (offsetX + x + w, offsetY + y + h), (255, 255, 255), 1)
    
    cv2.putText(frame, str(area), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    return frame


def start(args):
    
    
    
    with open('config.json', 'r') as f:
        config = json.load(f)

        myData.x = config['CAM1']['x']
        myData.y = config['CAM1']['y']
        myData.w = config['CAM1']['w']
        myData.h = config['CAM1']['h']
        myData.update()
        

    camera = PiCamera()
    camera.resolution = args.resolution
    camera.framerate = args.fps
    log.info("Warming up camera")
    time.sleep(5)
    loop(args, camera)

def loop(args, camera):
    avg = None
    raw_capture = PiRGBArray(camera, size=args.resolution)
    log.info("Starting capture")
    global myData
    myData.log()
    timestampLast =  time.perf_counter()
    
    for f in camera.capture_continuous(raw_capture, format="bgr", use_video_port=True):
        frame = f.array
        
        if myData.reloadView == True:
            log.info("Reload view")
            cv2.rectangle(frame, ( myData.x, myData.y), (myData.x + myData.w, myData.y + myData.h), (255, 0, 0), 2)
            cv2.imwrite(myData.liveView_path, frame)
            myData.reloadView = False
            
        if myData.updateROI == True:
            log.info("Update ROI")
            frameRoiView = frame[myData.y1:myData.y2,myData.x1:myData.x2]
            cv2.imwrite(myData.roiView_path, frameRoiView)
            avg = None
            myData.updateROI = False
        # resize, grayscale & blur out noise
        # numpy syntax expects [y:y+h, x:x+w]
        frameRoi = frame[myData.y1:myData.y2,myData.x1:myData.x2]
        gray = cv2.cvtColor(frameRoi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        for k, mask in m_selector.select(timeout=0):
            callback = k.data
            callback(k.fileobj,mask)
        
        # if the average frame is None, initialize it
        if avg is None:
            log.info("Initialising average frame")
            avg = gray.copy().astype("float")
            raw_capture.truncate(0)
            continue

        # accumulate the weighted average between the current frame and
        # previous frames, then compute the difference between the current
        # frame and running average
        cv2.accumulateWeighted(gray, avg, 0.5)
        frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

        # threshold the delta image, dilate the thresholded image to fill
        # in holes, then find contours on thresholded image
        thresh = cv2.threshold(frame_delta, args.delta_threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        (img,contours, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
       
        
        motion = False
        for c in contours:
            # if the contour is too small, ignore it
            area =  cv2.contourArea(c)
            if area < args.min_area:
                continue

            motion = True
            
            log.info("Motion detected  Area={}".format(area))
            
            # draw the text and timestamp on the frame
            #if args.enable_annotate:
            frame = annotate_frame( frame, area, c, myData.x, myData.y)

        if motion:
            timestampNow =  time.perf_counter() 
            timediff = timestampNow - timestampLast
            log.info("Motion time {} ".format(timediff))
            if timediff >= 1:
                timestampLast = timestampNow
                img_name = datetime.datetime.today().strftime('%Y-%m-%d_%H_%M_%S.%f') + '.jpg'
                myFolder = myData.img_path +"/" + myData.startTime.strftime('%Y-%m-%d')
                if not os.path.isdir(myFolder):
                    os.makedirs(myFolder)
                img_path = '{}/{}'.format(myFolder, img_name)
                log.info("Save picture {}".format(img_name))
                cv2.imwrite(img_path, frame)
            

        raw_capture.truncate(0)
        motion = False
      

# function to be called when enter is pressed
def got_keyboard_data(stdin,mask):
   
    strCommmand = stdin.readline().rstrip()
    
    log.info('Keyboard input: {}'.format(strCommmand))
    if strCommmand == 'reload':
        # load new picture
        myData.reloadView = True
    elif strCommmand.startswith('roi'):
        command,x,y,w,h = strCommmand.split(',')
        myData.x = int(x) 
        myData.y = int(y) 
        myData.w = int(w) 
        myData.h = int(h)
        myData.updateROI = True
        myData.update()
        myData.log()
        with open('config.json', 'r') as f:
            config = json.load(f)
            config['CAM1']['x'] = myData.x
            config['CAM1']['y'] = myData.y
            config['CAM1']['w'] = myData.w
            config['CAM1']['h'] = myData.h
            with open('config.json', 'w') as f2:
                json.dump(config, f2,indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
        

# register event
m_selector = selectors.DefaultSelector()
m_selector.register(sys.stdin, selectors.EVENT_READ, got_keyboard_data)


def parse_res(v):
    x, y = v.lower().split('x')
    return int(x), int(y)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Motion detect')
    parser.add_argument('--resolution', help='e.g 640x480', default=parse_res('1280x720'))
    parser.add_argument('--fps', help='Framerate e.g: 18', default=int('18'))
    parser.add_argument('--delta-threshold', default=int(5))
    parser.add_argument('--enable-annotate', help='Draw detected regions to image', action='store_true', default=True)
    parser.add_argument('--min-area', default=int(5000))
    
    args = parser.parse_args()
    log.debug(args)  
    start(args)
