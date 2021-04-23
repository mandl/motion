#!/usr/bin/env python3
#

"""
    Copyright (C) 2018-2021 Mandl

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

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
import subprocess
import shutil

# load darknet yolov4

mycfg = "cfg/yolov4.cfg".encode('utf8')
myweights = "cfg/yolov4.weights".encode('utf8')
myCocoData = "cfg/coco.data"
net = darknet.load_net(mycfg, myweights, 0)
metadata = darknet.load_meta(myCocoData.encode('utf8'))
class_names = [metadata.names[i].decode("ascii") for i in range(metadata.classes)]

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
        log.debug("File name: {} Event Name: {}".format(event.pathname, event.maskname))
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
        self.videoTestPath = ""
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
        log.debug('Data: x {} y {} w {} h {}'.format(self.x,self.y,self.w,self.h))
        log.debug('Motion path:    {}'.format(self.img_path))
        log.debug('MotionBw path:  {}'.format(self.imgBw_path))
        log.debug('ROI path:       {}'.format(self.roiView_path))
        log.debug('Live path:      {}'.format(self.liveView_path))
        log.debug('Root path:      {}'.format(self.rootPath))
        log.debug('Cam name:       {}'.format(self.camName))
        log.debug('Annotate:       {}'.format(self.enable_annotate))
        log.debug('Delta threshold {}'.format(myData.delta_threshold))
        log.debug('Min area        {}'.format(myData.min_area))
        log.debug('Dark score      {}'.format(myData.darkScore))

myData = ConfigData()

def annotate_frame(frame, area, contour,offsetX,offsetY,cX,cY):
    (x, y, w, h) = cv2.boundingRect(contour)
    # show ROI
    #cv2.rectangle(frame, ( myData.x, myData.y), (myData.x + myData.w, myData.y + myData.h), (255, 0, 0), 2)
    # show motion
    cv2.rectangle(frame, ( offsetX + x, offsetY + y), (offsetX + x + w, offsetY + y + h), (255, 255, 255), 1)
    # draw point
    cv2.circle(frame, (offsetX + cX, offsetY + cY), 7, (255, 255, 255), -1)
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
        log.info("config:: {}".format(config))
        myData.x = config[args.cam]['x']
        myData.y = config[args.cam]['y']
        myData.w = config[args.cam]['w']
        myData.h = config[args.cam]['h']
        myData.camName = args.cam
        myData.enable_annotate = args.enable_annotate
        myData.delta_threshold = args.delta_threshold
        myData.min_area = args.min_area
        myData.darkScore = args.score
        myData.enable_test = args.enable_test
        myData.videoTestPath = Path(config['videoTestPath'])
        myData.update()
    myData.log()


def readconfig():
    with open('config.json', 'r') as f:
        config = json.load(f)
        cam = myData.camName
        myData.x = config[cam]['x']
        myData.y = config[cam]['y']
        myData.w = config[cam]['w']
        myData.h = config[cam]['h']
        #myData.videoTestPath = config[rootPath]
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
    global myData
    readconfig()
    if myData.enable_test == True:
        myMp4 = myData.videoTestPath / '*.webm'
    else:
        myMp4 = myData.rootPath / args.cam / '*.mp4'
    log.info("Loop over this folder {}".format(myMp4))
    files = glob.glob(str(myMp4))
    files.sort(key=os.path.getmtime)
    for name in files:
        doJob(name)

def rectOverlap(A, B):
    (Ax1,Ay1,Ax2,Ay2) = A
    (Bx1,By1,Bx2,By2) = B
    overlap = (Ax1 < Bx2) and (Ax2 > Bx1) and (Ay1 < By2) and (Ay2 > By1)
    log.debug("r1: {} r2: {}  overlap {}".format(A,B,overlap))
    return  overlap

def doJob(name):
    #draknet
    global net
    global class_names

    global myData
    doJobStart = time.perf_counter()
    log.debug("Open file   "+ name)
    foundSomeThing = False
    readconfig()
    avg = None
    vcap = cv2.VideoCapture(name)
    log.debug("Video width:  {}".format(vcap.get(cv2.CAP_PROP_FRAME_WIDTH)))
    log.debug("Video height: {}".format(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    log.debug("Video fps:    {}".format(round(vcap.get(cv2.CAP_PROP_FPS))))
    myData.reloadView = True
    myData.updateROI = True
    timestampLast = time.perf_counter()
    timestampLastAction = 0
    foundTimestamp=""
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
        # save motion points
        motionPoints = ()
        motionRects = ()
        for c in contours:
            # if the contour is too small, ignore it
            area =  cv2.contourArea(c)
            if area < myData.min_area:
                continue
            motion = True
            log.debug("Motion detected  Area={} from {}".format(area, myData.camName))
            # compute the center of the contour
            M = cv2.moments(c)
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            motionPoints += (cX,cY),
            (x, y, w, h) = cv2.boundingRect(c)
            motionRects += (myData.x + x, myData.y + y, myData.x+ x+ w, myData.y + y + h),
            # draw the text and timestamp on the frame
            if myData.enable_annotate:
                frame = annotate_frame( frame, area, c, myData.x, myData.y,cX,cY)

        if (motion == True) and (isbw(frame)== False):
            darknetFound = False
            bwImageFound = False
            darkTimeStart = time.perf_counter()
            results = darknet.detect(net, class_names, frame)
            darkTimeStop = time.perf_counter()
            #log.info(results)
            for foundThing, score, bounds in results:
                myThing = foundThing
                if (myThing == "person" ) or (myThing== "car") or (myThing == "truck"):
                    if score > myData.darkScore:
                        #if isbw(frame):
                        #    log.info("bw image")
                        #    bwImageFound = True
                        (x, y, w, h) = bounds
                        (cx1,cy1,cx2,cy2) = darknet.convertBack(x, y, w, h)
                        #darknetFound = True
                        for motionRect in motionRects:
                            if rectOverlap(motionRect, (cx1,cy1,cx2,cy2)) == True:
                                darknetFound = True
                                cv2.putText(frame,foundThing,(int(x),int(y)),cv2.FONT_HERSHEY_COMPLEX,1,(255,255,0))
                                cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (255, 0, 0), thickness=2) 

            if darknetFound == True:
                foundSomeThing = True
                timestampNow =  time.perf_counter()
                timediff = timestampNow - timestampLast
                timediffAction = vcap.get(cv2.CAP_PROP_POS_MSEC)
                if timediffAction-timestampLastAction  > (45* 1000):
                    myMark = timediffAction/1000/60
                    log.info("Time mark {}".format(myMark))
                    myMarkMinute = round((((myMark*0.25) % 1) * 60) * 100) 
                    foundTimestamp= foundTimestamp + " " + str(int(myMark *0.25))+"." + str(myMarkMinute)
                    timestampLastAction = timediffAction

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
        backupFile = backupFile.replace('.mp4','.webm')
        log.info("Backup file to {}".format(backupFile))
        drawtext="setpts=0.25*PTS,drawtext=fontfile=/usr/share/fonts/truetype/freefont/FreeSans.ttf::fontcolor=white:fontsize=20:text=" + foundTimestamp 
        process = subprocess.run(['/usr/bin/ffmpeg','-hide_banner','-loglevel','quiet','-i',name,'-codec:v','libvpx-vp9','-deadline','good','-cpu-used','2','-r','16','-vf',drawtext,backupFile], check=True,stdout=subprocess.PIPE,universal_newlines=True)
        log.info(process.stdout)
        os.remove(name)
    else:
        #move file
        log.debug("Move file {} to archive".format(name))
        shutil.move(name,'/home/mandl/disk/video/videoArchive/' + args.cam + "_" + os.path.basename(name))
    doJobStop = time.perf_counter()
    log.debug("File {} Runtime {:.2f} min for {}".format(name, (doJobStop - doJobStart)/ 60, myData.camName))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Motion detect')
    parser.add_argument('--cam', help='Foldername  with mp4 recordings', default='cam1')
    parser.add_argument('--delta-threshold', default=int(10))
    parser.add_argument('--enable-annotate', help='Draw detected regions to image', action='store_true', default=False)
    parser.add_argument('--enable-watch', help='Watch folder', action='store_true', default=False)
    parser.add_argument('--enable-test', help='Use the test folder', action='store_true', default=False)
    parser.add_argument('--min-area', default=int(5000))
    parser.add_argument('--score', default=float(0.80))

    log.info("*************** start new run ***********************")
    args = parser.parse_args()
    log.debug(args)
    start(args)
    if args.enable_watch == True:
        watchFolder(args)
    else:
        loopOverFiles(args)
    log.info("*************** ready *******************************")
