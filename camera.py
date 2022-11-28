from __future__ import annotations

import urllib.request
import cv2
import numpy as np

from typing import Optional, NewType
from robot import *


Image = NewType('Image', any)


class NumberToLarge(Exception):
    pass


class BankException(Exception):
    pass


class NoResultException(Exception):
    pass


class Camera:
    """
    Camera object to interface with each robot's camera.
    """
    switch_counter = 0
    witch_object = 0
    object_located = 0

    def __init__(self,
                 ip: str,
                 offsets: Vec2,
                 offset_scale: Vec2,
                 invert: Vec2,
                 camera_cut: tuple[Vec2, Vec2],
                 camera_threshold: int,
                 objects: list[Object]):
        self.ip = ip
        self.offset = offsets
        self.offset_scale = offset_scale
        self.invert = invert
        self.camera_cut = camera_cut
        self.objects = objects

        if camera_threshold not in range(0, 257):
            raise NumberToLarge(f'camera_threshold needs to be in range 0..256, current value is {camera_threshold}')

        self.camera_threshold = camera_threshold

        # TODO: Actually ping the camera to see if it responds.

    @staticmethod
    def show_image(image: Image | list[Image], wait=True) -> Image:
        if type(image) is list:
            for img in image:
                cv2.imshow('image', img)
        else:
            cv2.imshow('image', image)

        if wait:
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    def get_image(self) -> Image:
        req = urllib.request.urlopen(f'http://{self.ip}/LiveImage.jpg')
        arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
        img = cv2.imdecode(arr, -1)

        x, y = self.camera_cut[0].to_tuple()
        h, w = self.camera_cut[1].to_tuple()

        img = img[x:w, y:h]

        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        return img

    def image_to_threshold(self, image: Image) -> Image:
        return cv2.threshold(image, self.camera_threshold, 255, cv2.THRESH_BINARY)[1]

    def image_coords_to_robot_coords(self, x: int | float, y: int | float) -> tuple[float, float]:
        x = ((x + self.offset.x) * self.invert.x) * self.offset_scale.x
        y = ((y + self.offset.y) * self.invert.y) * self.offset_scale.y

        return x, y

    def get_cubes(self) -> list[Vec2]:
        img = self.get_image()

        threshold = self.image_to_threshold(img)

        contours, hierarchy = cv2.findContours(threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        cubes = []

        for cnt in contours:
            x1, y1 = cnt[0][0]
            approx = cv2.approxPolyDP(cnt, 0.04 * cv2.arcLength(cnt, True), True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(cnt)

                if w < 25 or h < 25:
                    continue

                x, y = self.image_coords_to_robot_coords(x, y)

                cube = Vec2((y + (h / 2)) / 1000, (x + (w / 2)) / 1000)

                cubes.append(cube)

        return cubes if len(cubes) > 0 else []

    def get_cylinders(self) -> list[Vec2]:
        img = self.get_image()
        img = cv2.blur(img, (3, 3))
        circles = cv2.HoughCircles(img, cv2.HOUGH_GRADIENT, 1, 20,
                                   param1=50,
                                   param2=30,
                                   minRadius=1,
                                   maxRadius=40
                                   )

        cylinders = []

        if circles is not None:
            circles = np.uint16(np.around(circles))

            for pt in circles[0, :]:
                a, b, r = pt[0], pt[1], pt[2]

                a, b = self.image_coords_to_robot_coords(a, b)

                cylinders.append(Vec2(b / 1000, a / 1000))

        return cylinders if len(cylinders) > 0 else []

    def get_shapes(self) -> tuple[Optional[list[Vec2]], Optional[list[Vec2]]]:
        return self.get_cubes(), self.get_cylinders()

    def switch_object(self, bank: int):
        """
        Switch what object the camera detects.

        In theory, it changes what locator it uses. So `INT_1_0` is the first object locator in the camera. That means
        that `INT_1_1` is the second object locator.

        TODO: Change function to take channel as parameter to change to a specific object locator.
        TODO: Make `switch_counter` be of type `Object` insteadof `int`.
        """
        res = urllib.request.urlopen(f'http://10.1.1.8/CmdChannel?sINT_1_{bank}')

        if 'Ref bank index is not used.' in res.read().decode():
            raise BankException('Change to empty bank. There are not that many object locators created, try a lower '
                                'number. bang = {bank}')

        time.sleep(3)

        self.witch_object = self.objects[bank]

        print(f"Camera {self.ip}: object switched to {self.witch_object}")


""" Code graveyard
        # list for storing names of shapes
        for contour in contours:

            # here we are ignoring first counter because
            # findcontour function detects whole image as shape
            if i == 0:
                i = 1
                continue

            # cv2.approxPloyDP() function to approximate the shape
            approx = cv2.approxPolyDP(
                contour, 0.01 * cv2.arcLength(contour, True), True)

            # using drawContours() function
            cv2.drawContours(img, [contour], 0, (0, 0, 255), 5)

            # finding center point of shape
            M = cv2.moments(contour)
            if M['m00'] != 0.0:
                x = int(M['m10'] / M['m00'])
                y = int(M['m01'] / M['m00'])

            # putting shape name at center of each shape
            if len(approx) == 3:
                cv2.putText(img, 'Triangle', (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            elif len(approx) == 4:
                cv2.putText(img, 'Quadrilateral', (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            elif len(approx) == 5:
                cv2.putText(img, 'Pentagon', (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            elif len(approx) == 6:
                cv2.putText(img, 'Hexagon', (x, y),cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            else:
                cv2.putText(img, 'circle', (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
"""
