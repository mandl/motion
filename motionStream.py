#!/usr/bin/env python3
# 
import logging
logging.basicConfig(format='%(message)s', level=logging.DEBUG)
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

import cv2

camName = ""
class ConfigData:
    
    def __init__(self):
        self.x = 317
        self.y = 367
        
        self.updateROI = True
        self.reloadView = True
        
        self.liveView_path = '/{}/{}/{}'.format('media','config', 'view'+ camName +'.jpg')
        self.roiView_path = '/{}/{}/{}'.format('media','config', 'roi'+ camName +'.jpg')
        self.img_path = '/{}/{}'.format('media','motion')
       
        self.w = 948
        self.h = 351
        
        self.startTime =datetime.datetime.now()
        self.stream = ""
        self.update()
        
    def update(self):
        self.x1 = self.x
        self.y1 = self.y
        self.x2 = self.x + self.w 
        self.y2 = self.y + self.h
        self.liveView_path = '/{}/{}/{}'.format('media','config', 'view'+ camName +'.jpg')
        self.roiView_path = '/{}/{}/{}'.format('media','config', 'roi'+ camName +'.jpg')
        self.img_path = '/{}/{}'.format('media','motion')
       
    
    def log(self):
        log.info('Data: x {} y {} w {} h {}'.format(self.x,self.y,self.w,self.h))
        log.info('Cam stream:  {}'.format(self.stream))
        log.info('Motion path: {}'.format(self.img_path))
        log.info('ROI path:    {}'.format(self.roiView_path))
        log.info('Live path:   {}'.format(self.liveView_path))
        

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

        myData.x = config[camName]['x']
        myData.y = config[camName]['y']
        myData.w = config[camName]['w']
        myData.h = config[camName]['h']
        myData.stream = config['STREAM'+camName]
        myData.update() 
    loop(args)

def loop(args):
    avg = None
    log.info("Starting capture " + camName)
    global myData
    myData.log()
    timestampLast =  time.perf_counter()
    
    while True:
        vcap = cv2.VideoCapture(myData.stream)
        while True: 
            ret, frame = vcap.read()
            if ret==False:
                log.info("Stream broken " + camName)
                break
            if myData.reloadView == True:
                log.info("Reload view " + camName)
                cv2.rectangle(frame, ( myData.x, myData.y), (myData.x + myData.w, myData.y + myData.h), (255, 0, 0), 2)
                cv2.imwrite(myData.liveView_path, frame)
                myData.reloadView = False
                
            if myData.updateROI == True:
                log.info("Update ROI " + camName)
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
                log.info("Initialising average frame " + camName)
                avg = gray.copy().astype("float")
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
                
                log.debug("Motion detected  Area={} from cam {}".format(area,camName))
                
                # draw the text and timestamp on the frame
                #if args.enable_annotate:
                frame = annotate_frame( frame, area, c, myData.x, myData.y)
    
            if motion:
                timestampNow =  time.perf_counter() 
                timediff = timestampNow - timestampLast
                log.debug("Motion time {} ".format(timediff))
                if timediff >= 1:
                    timestampLast = timestampNow
                    img_name = datetime.datetime.today().strftime('%Y-%m-%d_%H_%M_%S.%f') + '.jpg'
                    myFolder = myData.img_path +"/" + datetime.datetime.now().strftime('%Y-%m-%d')
                    if not os.path.isdir(myFolder):
                        log.info('create folder {}'.format(myFolder))
                        os.makedirs(myFolder)
                    img_path = '{}/{}'.format(myFolder, img_name)
                    log.debug("Save picture {} from cam {}".format(img_name,camName))
                    cv2.imwrite(img_path, frame)
                
    
            
            motion = False
        vcap.release()

# function to be called when enter is pressed
def got_keyboard_data(stdin,mask):
   
    strCommmand = stdin.readline().rstrip()
    
    log.info('Command: {}'.format(strCommmand))
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
        myData.reloadView = True
        myData.update()
        myData.log()
        with open('config.json', 'r') as f:
            config = json.load(f)
            config[camName]['x'] = myData.x
            config[camName]['y'] = myData.y
            config[camName]['w'] = myData.w
            config[camName]['h'] = myData.h
            with open('config.json', 'w') as f2:
                json.dump(config, f2,indent=4, sort_keys=True, separators=(',', ': '), ensure_ascii=False)
        

# register event
m_selector = selectors.DefaultSelector()
m_selector.register(sys.stdin, selectors.EVENT_READ, got_keyboard_data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Motion detect')
    parser.add_argument('--cam', help='CAM1', default='CAM1')
    parser.add_argument('--delta-threshold', default=int(10))
    parser.add_argument('--enable-annotate', help='Draw detected regions to image', action='store_true', default=True)
    parser.add_argument('--min-area', default=int(5000))
    
    args = parser.parse_args()
    camName = args.cam
    log.debug(args)  
    start(args)
