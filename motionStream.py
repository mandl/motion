#!/usr/bin/env python3
# 

import logging
logging.basicConfig(filename='/home/mandl/motion/motion.log',format='%(process)s    %(asctime)s %(message)s', level=logging.INFO)
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
import pyinotify

# load darknet
mycfg = "cfg/yolov3.cfg".encode('utf8')
myweights = "cfg/yolov3.weights".encode('utf8')
myCocoData = "cfg/coco.data"
net = darknet.load_net(mycfg, myweights, 0)
meta = darknet.load_meta(myCocoData.encode('utf8'))


class EventProcessor(pyinotify.ProcessEvent):
    _methods = ["IN_CREATE",
                "IN_OPEN",
                "IN_ACCESS",
                "IN_ATTRIB",
                "IN_CLOSE_NOWRITE",
                "IN_CLOSE_WRITE",
                "IN_DELETE",
                "IN_DELETE_SELF",
                "IN_IGNORED",
                "IN_MODIFY",
                "IN_MOVE_SELF",
                "IN_MOVED_FROM",
                "IN_MOVED_TO",
                "IN_Q_OVERFLOW",
                "IN_UNMOUNT",
                "default"]

def process_generator(cls, method):
    def _method_name(self, event):
        log.info("File name: {} Event Name: {}".format(event.pathname, event.maskname))
        time.sleep(3)
        doJob(event.pathname)
    _method_name.__name__ = "process_{}".format(method)
    setattr(cls, _method_name.__name__, _method_name)



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
        self.imgBw_path = self.rootPath2 / "picture" / "bwmotion"
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
        log.info('Motion path:    {}'.format(self.img_path))
        log.info('MotionBw path:  {}'.format(self.imgBw_path))
        log.info('ROI path:       {}'.format(self.roiView_path))
        log.info('Live path:      {}'.format(self.liveView_path))
        log.info('Root path:      {}'.format(self.rootPath))
        log.info('Cam name:       {}'.format(self.camName))
        log.info('Annotate:       {}'.format(self.enable_annotate))
        log.info('Delta threshold {}'.format(myData.delta_threshold))
        log.info('Min area        {}'.format(myData.min_area))
        log.info('Dark score      {}'.format(myData.darkScore))

myData = ConfigData()


def annotate_frame(frame, area, contour,offsetX,offsetY):
    #timestamp = datetime.datetime.now()
    #ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
    (x, y, w, h) = cv2.boundingRect(contour)
    # show ROI
    #cv2.rectangle(frame, ( myData.x, myData.y), (myData.x + myData.w, myData.y + myData.h), (255, 0, 0), 2)
    # show motion
    cv2.rectangle(frame, ( offsetX + x, offsetY + y), (offsetX + x + w, offsetY + y + h), (255, 255, 255), 1)
    #cv2.putText(frame, str(area), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    return frame

def isbw(img):
    #img is a numpy.ndarray, loaded using cv2.imread
    if len(img.shape) > 2:
        looks_like_rgbbw = not False in ((img[:,:,0:1] == img[:,:,1:2]) == (img[:,:,1:2] ==  img[:,:,2:3]))
        looks_like_hsvbw = not (True in (img[:,:,0:1] > 0) or True in (img[:,:,1:2] > 0))
        return looks_like_rgbbw or looks_like_hsvbw
    else:
        return True

def start(args):

    global myData
    with open('config.json', 'r') as f:
        config = json.load(f)

        myData.x = config[args.cam]['x']
        myData.y = config[args.cam]['y']
        myData.w = config[args.cam]['w']
        myData.h = config[args.cam]['h']
        myData.camName = args.cam
        myData.enable_annotate = args.enable_annotate
        myData.delta_threshold = args.delta_threshold
        myData.min_area = args.min_area
        myData.darkScore = args.score
        myData.update()
    myData.log()


def watchFolder(args):
    global myData
    for method in EventProcessor._methods:
        process_generator(EventProcessor, method)

    watch_manager = pyinotify.WatchManager()
    event_notifier = pyinotify.Notifier(watch_manager, EventProcessor())
    watch_this = os.path.abspath( str(myData.rootPath) +"/"+ args.cam)
    log.info("Watch this folder: {}".format(watch_this))
    watch_manager.add_watch(watch_this, pyinotify.IN_CLOSE_WRITE)
    event_notifier.loop()



def loopOverFiles(args):
    myMp4 = myData.rootPath / args.cam / '*.mp4'
    log.info("Loop over this folder {}".format(myMp4))
    files = glob.glob(str(myMp4))
    files.sort(key=os.path.getmtime)
    for name in files:
        doJob(name)

def doJob(name):
    #draknet
    global net
    global meta

    global myData
    doJobStart = time.perf_counter()
    log.info("Open file   "+ name)
    foundSomeThing = False
    avg = None
    vcap = cv2.VideoCapture(name)
    log.debug("Video width:  {}".format(vcap.get(cv2.CAP_PROP_FRAME_WIDTH)))
    log.debug("Video height: {}".format(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    log.debug("Video fps:    {}".format(round(vcap.get(cv2.CAP_PROP_FPS))))
    myData.reloadView = True
    myData.updateROI = True
    timestampLast = time.perf_counter()
    while True:
        ret, frame = vcap.read()
        if ret==False:
            log.debug("End of file ")
            break
        if myData.reloadView == True:
            log.debug("Reload view " +  myData.camName)
            cv2.rectangle(frame, ( myData.x, myData.y), (myData.x + myData.w, myData.y + myData.h), (255, 0, 0), 2)
            cv2.imwrite(str(myData.liveView_path), frame)
            myData.reloadView = False
        if myData.updateROI == True:
            log.debug("Update ROI " +  myData.camName)
            frameRoiView = frame[myData.y1:myData.y2,myData.x1:myData.x2]
            #cv2.imwrite(myData.roiView_path, frameRoiView)
            avg = None
            myData.updateROI = False
        currFramePos =  vcap.get(cv2.CAP_PROP_POS_FRAMES)
        # resize, grayscale & blur out noise
        # numpy syntax expects [y:y+h, x:x+w]
        frameRoi = frame[myData.y1:myData.y2,myData.x1:myData.x2]
        gray = cv2.cvtColor(frameRoi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        # if the average frame is None, initialize it
        if avg is None:
            log.debug("Initialising average frame " +  myData.camName)
            avg = gray.copy().astype("float")
            continue
        # accumulate the weighted average between the current frame and
        # previous frames, then compute the difference between the current
        # frame and running average
        cv2.accumulateWeighted(gray, avg, 0.5)
        frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
        # threshold the delta image, dilate the thresholded image to fill
        # in holes, then find contours on thresholded image
        thresh = cv2.threshold(frame_delta, myData.delta_threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        (contours, hierarchy) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion = False
        for c in contours:
            # if the contour is too small, ignore it
            area =  cv2.contourArea(c)
            if area < myData.min_area:
                continue
            motion = True
            log.debug("Motion detected  Area={} from {}".format(area, myData.camName))
            # draw the text and timestamp on the frame
            if myData.enable_annotate:
                frame = annotate_frame( frame, area, c, myData.x, myData.y)

        if (motion == True) and (isbw(frame)== False):
            darknetFound = False
            bwImageFound = False
            darkTimeStart = time.perf_counter()
            results = darknet.detect(net, meta, frame)
            darkTimeStop = time.perf_counter()
            #log.info(results)
            for foundThing, score, bounds in results:
                myThing = foundThing.decode("utf-8")
                if (myThing == "person" ) or (myThing== "car") or (myThing == "truck") or (myThing == "cat") or (myThing == "dog"):
                    if score > myData.darkScore:
                        #if isbw(frame):
                        #    log.info("bw image")
                        #    bwImageFound = True
                        x, y, w, h = bounds
                        cv2.rectangle(frame, (int(x - w / 2), int(y - h / 2)), (int(x + w / 2), int(y + h / 2)), (255, 0, 0), thickness=2)
                        cv2.putText(frame,str(foundThing.decode("utf-8")),(int(x),int(y)),cv2.FONT_HERSHEY_COMPLEX,1,(255,255,0))
                        log.info("{} found {} with {:3.1f} % time {:3.4f}".format(args.cam,myThing,score * 100,darkTimeStop-darkTimeStart))
                        darknetFound = True
            if darknetFound == True:
                foundSomeThing = True
                timestampNow =  time.perf_counter()
                timediff = timestampNow - timestampLast
                log.debug("Motion time {} ".format(timediff))
                if timediff >= 1:
                    timestampLast = timestampNow
                    img_name = datetime.datetime.today().strftime('%Y-%m-%d_%H_%M_%S.%f') + '.jpg'
                    if bwImageFound == True:
                        myFolder = str(myData.imgBw_path) +"/" + datetime.datetime.now().strftime('%Y-%m-%d')
                    else:
                        myFolder = str(myData.img_path) +"/" + datetime.datetime.now().strftime('%Y-%m-%d')
                    if not os.path.isdir(myFolder):
                        log.info('create folder {}'.format(myFolder))
                        os.makedirs(myFolder)
                    img_path = '{}/{}'.format(myFolder, img_name)
                    log.info("Save picture {} from cam {}".format(img_name,myData.camName))
                    if cv2.imwrite(img_path, frame) == False:
                        log.error('Image write fail !!!!!!!!')
        motion = False
    vcap.release()
    if foundSomeThing == True:
        #backup file
        backupFile = '/home/mandl/disk/video/backup/' + args.cam + "_" + os.path.basename(name)
        log.info("Backup file to {}".format(backupFile))
        os.rename(name,backupFile)
    else:
        #remove file
        log.info("Remove file {}".format(name))
        os.remove(name)
    doJobStop = time.perf_counter()
    log.info("File {} Runtime {:.2f} min for {}".format(name, (doJobStop - doJobStart)/ 60, myData.camName))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Motion detect')
    parser.add_argument('--cam', help='Foldername  with mp4 recordings', default='cam1')
    parser.add_argument('--delta-threshold', default=int(10))
    parser.add_argument('--enable-annotate', help='Draw detected regions to image', action='store_true', default=True)
    parser.add_argument('--enable-watch', help='Watch folder', action='store_true', default=False)
    parser.add_argument('--min-area', default=int(5000))
    parser.add_argument('--score', default=float(0.65))

    log.info("*************** start new run ***********************")
    args = parser.parse_args()
    log.debug(args)
    start(args)
    if args.enable_watch == True:
        watchFolder(args)
    else:
        loopOverFiles(args)
    log.info("*************** ready *******************************")
