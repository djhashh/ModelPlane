#! /usr/bin/env python
""" Provides a virtual trackball for 3D scene viewing

Example usage:
 
   trackball = Trackball(45,45)

   @window.event
   def on_mouse_drag(x, y, dx, dy, button, modifiers):
       x  = (x*2.0 - window.width)/float(window.width)
       dx = 2*dx/float(window.width)
       y  = (y*2.0 - window.height)/float(window.height)
       dy = 2*dy/float(window.height)
       trackball.drag(x,y,dx,dy)

   @window.event
   def on_resize(width,height):
       glViewport(0, 0, window.width, window.height)
       glMatrixMode(GL_PROJECTION)
       glLoadIdentity()
       gluPerspective(45, window.width / float(window.height), .1, 1000)
       glMatrixMode (GL_MODELVIEW)
       glLoadIdentity ()
       glTranslatef (0, 0, -3)
       glMultMatrixf(trackball.matrix)

You can also set trackball orientation directly by setting theta and phi value
expressed in degrees. Theta relates to the rotation angle around X axis while
phi relates to the rotation angle around Z axis.

"""
__docformat__ = 'restructuredtext'
__version__ = '1.0'

import math
import OpenGL.GL as gl
from OpenGL.GL import GLfloat


# Some useful functions on vectors
# -----------------------------------------------------------------------------
def _v_add(v1, v2):
    return [v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2]]


def _v_sub(v1, v2):
    return [v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]]


def _v_mul(v, s):
    return [v[0] * s, v[1] * s, v[2] * s]


def _v_dot(v1, v2):
    return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]


def _v_cross(v1, v2):
    return [(v1[1] * v2[2]) - (v1[2] * v2[1]),
            (v1[2] * v2[0]) - (v1[0] * v2[2]),
            (v1[0] * v2[1]) - (v1[1] * v2[0])]


def _v_length(v):
    return math.sqrt(_v_dot(v, v))


def _v_normalize(v):
    try:
        return _v_mul(v, 1.0 / _v_length(v))
    except ZeroDivisionError:
        return v


# Some useful functions on quaternions
# -----------------------------------------------------------------------------
def _q_add(q1, q2):
    t1 = _v_mul(q1, q2[3])
    t2 = _v_mul(q2, q1[3])
    t3 = _v_cross(q2, q1)
    tf = _v_add(t1, t2)
    tf = _v_add(t3, tf)
    tf.append(q1[3] * q2[3] - _v_dot(q1, q2))
    return tf


def _q_mul(q, s):
    return [q[0] * s, q[1] * s, q[2] * s, q[3] * s]


def _q_dot(q1, q2):
    return q1[0] * q2[0] + q1[1] * q2[1] + q1[2] * q2[2] + q1[3] * q2[3]


def _q_length(q):
    return math.sqrt(_q_dot(q, q))


def _q_normalize(q):
    try:
        return _q_mul(q, 1.0 / _q_length(q))
    except ZeroDivisionError:
        return q


def _q_from_axis_angle(v, phi):
    q = _v_mul(_v_normalize(v), math.sin(phi / 2.0))
    q.append(math.cos(phi / 2.0))
    return q


def _q_rotmatrix(q):
    m = [0.0] * 16
    m[0*4+0] = 1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
    m[0*4+1] = 2.0 * (q[0] * q[1] - q[2] * q[3])
    m[0*4+2] = 2.0 * (q[2] * q[0] + q[1] * q[3])
    m[0*4+3] = 0.0
    m[1*4+0] = 2.0 * (q[0] * q[1] + q[2] * q[3])
    m[1*4+1] = 1.0 - 2.0 * (q[2] * q[2] + q[0] * q[0])
    m[1*4+2] = 2.0 * (q[1] * q[2] - q[0] * q[3])
    m[1*4+3] = 0.0
    m[2*4+0] = 2.0 * (q[2] * q[0] - q[1] * q[3])
    m[2*4+1] = 2.0 * (q[1] * q[2] + q[0] * q[3])
    m[2*4+2] = 1.0 - 2.0 * (q[1] * q[1] + q[0] * q[0])
    m[3*4+3] = 1.0
    return m


class Trackball:
    """ Virtual trackball for 3D scene viewing. """

    def __init__(self, theta=0, phi=0, zoom=1, distance=3):
        """ Build a new trackball with specified view """

        self._rotation = [0, 0, 0, 1]
        self._zoom = zoom
        self._distance = distance
        self._count = 0
        self._matrix = None
        self._RENORMCOUNT = 97
        self._TRACKBALLSIZE = 0.8
        self._theta = theta
        self._phi = phi
        self._set_orientation(theta, phi)
        self._x = 0.0
        self._y = 0.0

    def drag_to(self, x, y, dx, dy):
        """ Move trackball view from x,y to x+dx,y+dy. """
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        width, height = float(viewport[2]), float(viewport[3])
        x = (x * 2.0 - width) / width
        dx = (2.0 * dx) / width
        y = (y * 2.0 - height) / height
        dy = (2.0 * dy) / height
        q = self._rotate(x, y, dx, dy)
        self._rotation = _q_add(q, self._rotation)
        self._rotation[2] = 0.0
        self._count += 1
        if self._count > self._RENORMCOUNT:
            self._rotation = _q_normalize(self._rotation)
            self._count = 0
        m = _q_rotmatrix(self._rotation)
        self._matrix = (GLfloat * len(m))(*m)

    def zoom_to(self, x, y, dx, dy):
        """ Zoom trackball by a factor dy """
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        height = float(viewport[3])
        self.zoom = self.zoom - 5 * dy / height

    def pan_to(self, x, y, dx, dy):
        """ Pan trackball by a factor dx,dy """
        self._x += dx * 0.1
        self._y += dy * 0.1

    def push(self):
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        aspect = viewport[2] / float(viewport[3])
        aperture = 35.0
        near = 0.1
        far = 100.0
        top = math.tan(aperture * math.pi / 360.0) * near * self._zoom
        bottom = -top
        left = aspect * bottom
        right = aspect * top
        gl.glFrustum(left, right, bottom, top, near, far)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        # gl.glTranslate (0.0, 0, -self._distance)
        gl.glTranslate(self._x, self._y, -self._distance)
        gl.glMultMatrixf(self._matrix)

    @staticmethod
    def pop():
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPopMatrix()

    @property
    def matrix(self):
        return self._matrix

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, zoom):
        self._zoom = zoom
        if self._zoom < .25:
            self._zoom = .25
        if self._zoom > 10.0:
            self._zoom = 10.0

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, distance):
        self._distance = distance
        if self._distance < 1:
            self._distance = 1

    @property
    def theta(self):
        self._theta, self._phi = self._get_orientation()
        return self._theta

    @theta.setter
    def theta(self, theta):
        self._set_orientation(math.fmod(theta, 360.0), math.fmod(self._phi, 360.0))

    @property
    def phi(self):
        self._theta, self._phi = self._get_orientation()
        return self._phi

    @phi.setter
    def phi(self, phi):
        self._set_orientation(math.fmod(self._theta, 360.0), math.fmod(phi, 360.0))

    def _get_orientation(self):
        """ Return current computed orientation (theta,phi). """ 

        q0, q1, q2, q3 = self._rotation
        ax = math.atan(2 * (q0 * q1 + q2 * q3) / (1 - 2 * (q1 * q1 + q2 * q2))) * 180.0 / math.pi
        az = math.atan(2 * (q0 * q3 + q1 * q2) / (1 - 2 * (q2 * q2 + q3 * q3))) * 180.0 / math.pi
        return -az, ax

    def _set_orientation(self, theta, phi):
        """ Computes rotation corresponding to theta and phi. """ 

        self._theta = theta
        self._phi = phi
        angle = self._theta*(math.pi/180.0)
        sine = math.sin(0.5*angle)
        xrot = [1 * sine, 0, 0, math.cos(0.5 * angle)]
        angle = self._phi * (math.pi / 180.0)
        sine = math.sin(0.5 * angle)
        zrot = [0, 0, sine, math.cos(0.5 * angle)]
        self._rotation = _q_add(xrot, zrot)
        m = _q_rotmatrix(self._rotation)
        self._matrix = (GLfloat * len(m))(*m)

    @staticmethod
    def _project(r, x, y):
        """ Project an x,y pair onto a sphere of radius r OR a hyperbolic sheet
            if we are away from the center of the sphere.
        """

        d = math.sqrt(x * x + y * y)
        if d < r * 0.70710678118654752440:    # Inside sphere
            z = math.sqrt(r * r - d * d)
        else:                                   # On hyperbola
            t = r / 1.41421356237309504880
            z = t * t / d
        return z

    def _rotate(self, x, y, dx, dy): 
        """ Simulate a track-ball.

            Project the points onto the virtual trackball, then figure out the
            axis of rotation, which is the cross product of x,y and x+dx,y+dy.

            Note: This is a deformed trackball-- this is a trackball in the
            center, but is deformed into a hyperbolic sheet of rotation away
            from the center.  This particular function was chosen after trying
            out several variations.
        """

        if not dx and not dy:
            return [0.0, 0.0, 0.0, 1.0]
        last = [x, y, self._project(self._TRACKBALLSIZE, x, y)]
        new = [x + dx, y + dy, self._project(self._TRACKBALLSIZE, x + dx, y + dy)]
        a = _v_cross(new, last)
        d = _v_sub(last, new)
        t = _v_length(d) / (2.0 * self._TRACKBALLSIZE)
        if t > 1.0:
            t = 1.0
        if t < -1.0:
            t = -1.0
        phi = 2.0 * math.asin(t)
        return _q_from_axis_angle(a, phi)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        phi = str(self.phi)
        theta = str(self.theta)
        zoom = str(self.zoom)
        return f'Trackball(phi={phi},theta={theta},zoom={zoom})'
