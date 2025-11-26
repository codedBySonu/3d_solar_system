import math
import sys
import random

import glfw
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image

# ---------- Window settings ----------
WIN_WIDTH = 1280
WIN_HEIGHT = 720

# ---------- Camera settings ----------
cam_distance = 40.0
cam_y = 12.0
cam_angle = 0.0  # will slowly rotate around the sun

# ---------- Planet data ----------
class Planet:
    def __init__(self, orbit_radius, size, orbit_speed, color, phase=0.0):
        self.orbit_radius = orbit_radius
        self.size = size
        self.orbit_speed = orbit_speed  # radians per second
        self.color = color
        self.phase = phase  # starting angle
        self.texture_id = 0  # OpenGL texture ID


# Sun + planets
sun = Planet(0.0, 3.0, 0.0, (1.0, 0.95, 0.4))
planets = [
    Planet(5.0, 0.5, 1.8, (0.8, 0.8, 0.7), 0.0),   # Mercury
    Planet(7.5, 0.8, 1.4, (1.0, 0.8, 0.4), 1.0),   # Venus
    Planet(10.0, 0.9, 1.0, (0.2, 0.4, 1.0), 2.0),  # Earth
    Planet(12.5, 0.7, 0.8, (0.9, 0.3, 0.1), 3.0),  # Mars
    Planet(16.0, 1.8, 0.5, (0.9, 0.7, 0.5), 0.5),  # Jupiter
    Planet(20.0, 1.4, 0.4, (0.9, 0.85, 0.6), 1.5), # Saturn
    Planet(24.0, 1.2, 0.3, (0.5, 0.9, 0.9), 2.5),  # Uranus
    Planet(28.0, 1.1, 0.25,(0.3, 0.5, 1.0), 3.5),  # Neptune
]

quadric = None  # will be created after GL context

# Extra global stuff
skybox_tex_id = 0
saturn_ring_tex_id = 0
asteroids = []  # list of (radius, base_angle, height, size, speed)


# ---------- Texture loading ----------
def load_texture(path):
    try:
        img = Image.open(path)
    except Exception as e:
        print(f"Failed to load texture '{path}':", e)
        return 0

    # OpenGL expects (0,0) at bottom-left
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img = img.convert("RGBA")
    img_data = img.tobytes()
    width, height = img.size

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    glGenerateMipmap(GL_TEXTURE_2D)

    glBindTexture(GL_TEXTURE_2D, 0)
    print(f"Loaded texture '{path}' as ID {tex_id}")
    return tex_id


# ---------- Callbacks ----------
def framebuffer_size_callback(window, width, height):
    global WIN_WIDTH, WIN_HEIGHT
    WIN_WIDTH = max(width, 1)
    WIN_HEIGHT = max(height, 1)
    glViewport(0, 0, WIN_WIDTH, WIN_HEIGHT)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, WIN_WIDTH / float(WIN_HEIGHT), 0.1, 400.0)
    glMatrixMode(GL_MODELVIEW)


def process_input(window):
    global cam_distance, cam_y

    # Close on ESC
    if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
        glfw.set_window_should_close(window, True)

    # Zoom in/out
    if glfw.get_key(window, glfw.KEY_W) == glfw.PRESS:
        cam_distance -= 0.5
    if glfw.get_key(window, glfw.KEY_S) == glfw.PRESS:
        cam_distance += 0.5

    # Move camera up/down
    if glfw.get_key(window, glfw.KEY_UP) == glfw.PRESS:
        cam_y += 0.3
    if glfw.get_key(window, glfw.KEY_DOWN) == glfw.PRESS:
        cam_y -= 0.3

    # Clamp values a bit
    cam_distance = max(10.0, min(120.0, cam_distance))
    cam_y = max(-5.0, min(40.0, cam_y))


# ---------- OpenGL setup ----------
def init_opengl():
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)

    # Background space-like color
    glClearColor(0.0, 0.0, 0.03, 1.0)

    # Lighting
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)

    # Light properties
    light_ambient = [0.1, 0.1, 0.1, 1.0]
    light_diffuse = [1.0, 1.0, 1.0, 1.0]
    light_specular = [1.0, 1.0, 1.0, 1.0]
    glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)
    glLightfv(GL_LIGHT0, GL_SPECULAR, light_specular)

    # Material
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 32.0)

    # Texturing
    glEnable(GL_TEXTURE_2D)


def draw_sphere(radius, slices=32, stacks=16):
    global quadric
    if quadric is None:
        return
    gluSphere(quadric, radius, slices, stacks)


def draw_orbit(radius):
    glDisable(GL_LIGHTING)
    glDisable(GL_TEXTURE_2D)
    glColor3f(0.3, 0.3, 0.5)
    glBegin(GL_LINE_LOOP)
    for i in range(0, 128):
        angle = 2.0 * math.pi * i / 128.0
        x = math.cos(angle) * radius
        z = math.sin(angle) * radius
        glVertex3f(x, 0.0, z)
    glEnd()
    glEnable(GL_LIGHTING)
    glEnable(GL_TEXTURE_2D)


def draw_skybox():
    global skybox_tex_id
    if not skybox_tex_id:
        return

    # Draw a huge textured sphere around everything
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)

    glPushMatrix()
    glBindTexture(GL_TEXTURE_2D, skybox_tex_id)
    glColor3f(1.0, 1.0, 1.0)
    draw_sphere(150.0, 40, 20)
    glBindTexture(GL_TEXTURE_2D, 0)
    glPopMatrix()

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)


def draw_saturn_rings(inner_radius, outer_radius):
    global saturn_ring_tex_id
    if not saturn_ring_tex_id:
        return

    glBindTexture(GL_TEXTURE_2D, saturn_ring_tex_id)
    glNormal3f(0.0, 1.0, 0.0)  # flat disk facing up

    segments = 128
    glBegin(GL_TRIANGLE_STRIP)
    for i in range(segments + 1):
        angle = 2.0 * math.pi * i / segments
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # texture coord along ring
        t = i / float(segments)

        # inner edge
        x_inner = cos_a * inner_radius
        z_inner = sin_a * inner_radius
        glTexCoord2f(t, 0.0)
        glVertex3f(x_inner, 0.0, z_inner)

        # outer edge
        x_outer = cos_a * outer_radius
        z_outer = sin_a * outer_radius
        glTexCoord2f(t, 1.0)
        glVertex3f(x_outer, 0.0, z_outer)
    glEnd()

    glBindTexture(GL_TEXTURE_2D, 0)


def init_asteroid_belt():
    global asteroids
    random.seed(42)  # stable pattern
    asteroids = []
    # belt between Mars (12.5) and Jupiter (16.0)
    for _ in range(220):
        radius = random.uniform(13.0, 15.5)
        base_angle = random.uniform(0.0, 2.0 * math.pi)
        height = random.uniform(-0.4, 0.4)
        size = random.uniform(0.07, 0.18)
        speed = random.uniform(0.1, 0.35)  # slow orbit
        asteroids.append((radius, base_angle, height, size, speed))


def draw_asteroid_belt(time_sec):
    global asteroids
    glDisable(GL_TEXTURE_2D)  # plain rocks
    glColor3f(0.6, 0.6, 0.6)

    for (radius, base_angle, height, size, speed) in asteroids:
        angle = base_angle + speed * time_sec
        x = math.cos(angle) * radius
        z = math.sin(angle) * radius

        glPushMatrix()
        glTranslatef(x, height, z)
        draw_sphere(size, 12, 8)
        glPopMatrix()

    glEnable(GL_TEXTURE_2D)


def render_scene(time_sec):
    global cam_angle

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # Camera rotation around the sun
    cam_angle = time_sec * 0.1  # slow spin
    eye_x = math.cos(cam_angle) * cam_distance
    eye_z = math.sin(cam_angle) * cam_distance

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(eye_x, cam_y, eye_z,  # eye
              0.0, 0.0, 0.0,        # center (sun)
              0.0, 1.0, 0.0)        # up

    # Draw skybox first (behind everything)
    draw_skybox()

    # Light at the sun (center)
    light_pos = [0.0, 0.0, 0.0, 1.0]
    glLightfv(GL_LIGHT0, GL_POSITION, light_pos)

    # ----- Draw Sun -----
    glPushMatrix()
    glColor3f(*sun.color)
    if sun.texture_id:
        glBindTexture(GL_TEXTURE_2D, sun.texture_id)
    draw_sphere(sun.size, 40, 20)
    glBindTexture(GL_TEXTURE_2D, 0)
    glPopMatrix()

    # ----- Draw Planets + orbits -----
    for idx, p in enumerate(planets):
        # orbit line
        draw_orbit(p.orbit_radius)

        # planet position
        angle = p.orbit_speed * time_sec + p.phase
        x = math.cos(angle) * p.orbit_radius
        z = math.sin(angle) * p.orbit_radius

        glPushMatrix()
        glTranslatef(x, 0.0, z)

        # Saturn rings (planet index 5 in our list)
        if idx == 5:
            inner_r = p.size * 2.0
            outer_r = p.size * 3.5
            draw_saturn_rings(inner_r, outer_r)

        glColor3f(*p.color)
        if p.texture_id:
            glBindTexture(GL_TEXTURE_2D, p.texture_id)
        draw_sphere(p.size, 24, 12)
        glBindTexture(GL_TEXTURE_2D, 0)

        glPopMatrix()

    # ----- Asteroid belt -----
    draw_asteroid_belt(time_sec)


def main():
    global quadric, sun, planets
    global skybox_tex_id, saturn_ring_tex_id

    # ---------- Init GLFW ----------
    if not glfw.init():
        print("Failed to initialize GLFW")
        sys.exit(1)

    glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)

    window = glfw.create_window(
        WIN_WIDTH, WIN_HEIGHT,
        "3D Realistic Solar System (Python + PyOpenGL)", None, None
    )
    if not window:
        print("Failed to create GLFW window")
        glfw.terminate()
        sys.exit(1)

    glfw.make_context_current(window)
    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)

    # ---------- Init OpenGL state ----------
    init_opengl()
    quadric = gluNewQuadric()
    gluQuadricNormals(quadric, GL_SMOOTH)
    gluQuadricTexture(quadric, GL_TRUE)  # enable texture coords on spheres

    # Set initial projection
    framebuffer_size_callback(window, WIN_WIDTH, WIN_HEIGHT)

    # ---------- Load textures ----------
    sun.texture_id        = load_texture("sun.jpg")
    planets[0].texture_id = load_texture("mercury.jpg")
    planets[1].texture_id = load_texture("venus.jpg")
    planets[2].texture_id = load_texture("earth.jpg")
    planets[3].texture_id = load_texture("mars.jpg")
    planets[4].texture_id = load_texture("jupiter.jpg")
    planets[5].texture_id = load_texture("saturn.jpg")
    planets[6].texture_id = load_texture("uranus.jpg")
    planets[7].texture_id = load_texture("neptune.jpg")

    saturn_ring_tex_id = load_texture("saturn_ring.png")
    # use space.jpeg as deep space background
    skybox_tex_id = load_texture("space.jpeg")

    # ---------- Init asteroid belt ----------
    init_asteroid_belt()

    # ---------- Render loop ----------
    while not glfw.window_should_close(window):
        process_input(window)

        t = glfw.get_time()
        render_scene(t)

        glfw.swap_buffers(window)
        glfw.poll_events()

    # ---------- Cleanup ----------
    if quadric is not None:
        gluDeleteQuadric(quadric)
    glfw.destroy_window(window)
    glfw.terminate()


if __name__ == "__main__":
    main()
