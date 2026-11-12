"""Maintained upstream person segmentation for camera-image registration.

Masks exclude foreground people from SIFT descriptor selection. They do not
alter stone detections, label rink features, or supply geometry/identity truth.
The checkpoint, operating point, runtime and local CPU execution are recorded.
"""
from pathlib import Path
import time
import cv2
import numpy as np
from prototype.detection_cache import digest


class CameraForeground:
    def __init__(self,checkpoint,expected_sha256,*,threads=4):
        import torch
        import ultralytics
        from ultralytics import YOLO
        checkpoint=Path(checkpoint)
        if digest(checkpoint)!=expected_sha256:raise ValueError('Camera foreground checkpoint changed')
        self.model=YOLO(str(checkpoint));self.threads=threads
        if self.model.names.get(0)!='person':raise ValueError('Camera foreground model must use the COCO person class')
        self.model.add_callback('on_predict_start',lambda _:torch.set_num_threads(threads))
        self.provenance={'backend':'ultralytics.YOLO.predict/segment','ultralytics':ultralytics.__version__,
            'torch':str(torch.__version__),'checkpoint_sha256':expected_sha256,'device':'cpu',
            'threads':threads,'classes':[0],'confidence':.25,'imgsz':640,
            'purpose':'Learned person masks excluded from static image feature selection; no rink/stone annotation or physical truth.'}
        self.seconds=0.;self.frames=0

    def mask(self,image):
        import torch
        started=time.perf_counter();previous=torch.get_num_threads()
        try:
            result=self.model.predict(image,classes=[0],conf=.25,imgsz=640,device='cpu',verbose=False)[0]
        finally:torch.set_num_threads(previous)
        mask=np.zeros(image.shape[:2],np.uint8)
        if result.masks is not None:
            for polygon in result.masks.xy:
                cv2.fillPoly(mask,[np.rint(polygon).astype(np.int32)],255)
        self.seconds+=time.perf_counter()-started;self.frames+=1
        return mask
