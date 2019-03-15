#!/usr/bin/env python3
# 
import logging
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
log = logging.getLogger('')
import datetime
import argparse
import time
import os
import darknet
import select
import sys
import fcntl
import selectors
import json
import glob
from pathlib import Path
import cv2


class ConfigData:
    
    def __init__(self):
        self.x = 317
        self.y = 367
        self.updateROI = True
        self.reloadView = True
        self.camName=""
        #self.liveView_path = '/{}/{}/{}'.format('media','config', 'view'+ camName +'.jpg')
        #self.roiView_path = '/{}/{}/{}'.format('media','config', 'roi'+ camName +'.jpg')
        
        self.rootPath = Path("/home/mandl/disk/video")
        self.rootPath2 = Path("/home/mandl/motion")
        self.img_path = self.rootPath2 / "picture" / "motion"
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
        self.liveView_path = self.rootPath2 / "picture" / "config" / "view" / (self.camName +'.png')
        self.roiView_path = self.rootPath2 / "picture" / "config" / "roi" / (self.camName +'.png')
        #self.img_path = '/{}/{}'.format('media','motion')

    def log(self):
        log.info('Data: x {} y {} w {} h {}'.format(self.x,self.y,self.w,self.h))
        log.info('Cam stream:  {}'.format(self.stream))
        log.info('Motion path: {}'.format(self.img_path))
        log.info('ROI path:    {}'.format(self.roiView_path))
        log.info('Live path:   {}'.format(self.liveView_path))
        log.info('Root path: {}'.format(self.rootPath))
        log.info('CamName: {}'.format(self.camName))

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
        myData.camName = args.cam
        myData.update() 
    loop(args)

def loop(args):
    avg = None
    log.info("Starting capture " + args.cam)
    global myData
    myData.log()
    myMp4 = myData.rootPath / args.cam / '*.mp4'
    mycfg = "cfg/yolov3.cfg".encode('utf8')
    myweights = "cfg/yolov3.weights".encode('utf8')
    myCocoData = "cfg/coco.data"
    net = darknet.load_net(mycfg, myweights, 0)
    meta = darknet.load_meta(myCocoData.encode('utf8'))

    #r = detect(net, meta, "data/dog.jpg")
    for name in glob.glob(str(myMp4)):
        log.info("Open file:"+ name)
        vcap = cv2.VideoCapture(name)
        log.info("Video width: {}".format(vcap.get(cv2.CAP_PROP_FRAME_WIDTH)))
        log.info("Video height: {}".format(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        log.info("Video fps: {}".format(round(vcap.get(cv2.CAP_PROP_FPS))))
        while True:
            ret, frame = vcap.read()
            if ret==False:
                log.info("End of file ")
                break
            if myData.reloadView == True:
                log.info("Reload view " + camName)
                cv2.rectangle(frame, ( myData.x, myData.y), (myData.x + myData.w, myData.y + myData.h), (255, 0, 0), 2)
                cv2.imwrite(str(myData.liveView_path), frame)
                myData.reloadView = False
            #if myData.updateROI == True:
            #    log.info("Update ROI " + camName)
            #    frameRoiView = frame[myData.y1:myData.y2,myData.x1:myData.x2]
            #    cv2.imwrite(myData.roiView_path, frameRoiView)
            #    avg = None
            #    myData.updateROI = False
            # resize, grayscale & blur out noise
            # numpy syntax expects [y:y+h, x:x+w]
            frameRoi = frame[myData.y1:myData.y2,myData.x1:myData.x2]
            gray = cv2.cvtColor(frameRoi, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
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
            (contours, hierarchy) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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
                r = detect(net, meta, frame)
                log.info(r)
                #timestampNow =  time.perf_counter() 
                #timediff = timestampNow - timestampLast
                #log.debug("Motion time ") #.format(timediff))
                #if timediff >= 1:
                #timestampLast = timestampNow
                img_name = datetime.datetime.today().strftime('%Y-%m-%d_%H_%M_%S.%f') + '.jpg'
                myFolder = str(myData.img_path) +"/" + datetime.datetime.now().strftime('%Y-%m-%d')
                if not os.path.isdir(myFolder):
                    log.info('create folder {}'.format(myFolder))
                    os.makedirs(myFolder)
                img_path = '{}/{}'.format(myFolder, img_name)
                log.debug("Save picture {} from cam {}".format(img_name,camName))
                cv2.imwrite(img_path, frame)
            motion = False
        vcap.release()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Motion detect')
    parser.add_argument('--cam', help='cam1', default='cam1')
    parser.add_argument('--delta-threshold', default=int(10))
    parser.add_argument('--enable-annotate', help='Draw detected regions to image', action='store_true', default=True)
    parser.add_argument('--min-area', default=int(5000))
    args = parser.parse_args()
    camName = args.cam
    log.debug(args)
    start(args)
