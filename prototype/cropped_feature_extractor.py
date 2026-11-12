"""Experimental mask-bounded preprocessing for an upstream feature extractor.

Not equivalent to masked full-image SIFT: border support and global feature
ranking can change. This adapter is not enabled in the public pipeline.
"""
import cv2


class CroppedFeatureExtractor:
    def __init__(self, extractor):
        self.extractor = extractor

    def detectAndCompute(self, image, mask):
        if mask is None:
            raise ValueError('Explicit existing region mask required')
        if image.shape[:2] != mask.shape:
            raise ValueError('Image/mask dimensions differ')
        x,y,w,h = cv2.boundingRect(mask)
        if not w or not h:
            return [], None
        points, descriptors = self.extractor.detectAndCompute(
            image[y:y+h,x:x+w], mask[y:y+h,x:x+w])
        for point in points:
            point.pt = (point.pt[0]+x, point.pt[1]+y)
        return points, descriptors
