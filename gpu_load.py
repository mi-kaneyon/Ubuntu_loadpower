import pygame
from pygame.locals import *
import sys
from OpenGL.GL import *
from OpenGL.GLU import *
import threading
import time
import numpy as np
import torch

def load_texture():
    try:
        texture_surface = pygame.image.load('texture.jpg')
        texture_data = pygame.image.tostring(texture_surface, 'RGB', 1)
        width = texture_surface.get_width()
        height = texture_surface.get_height()

        glEnable(GL_TEXTURE_2D)
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return texture_id
    except pygame.error as e:
        print(f"Error loading texture: {e}")
        return None

def draw_background_gradient():
    glBegin(GL_QUADS)
    glColor3f(0.0, 0.0, 0.0)  # Black color
    glVertex2f(-1.0, -1.0)
    glColor3f(1.0, 1.0, 1.0)  # White color
    glVertex2f(1.0, -1.0)
    glColor3f(0.0, 0.0, 0.0)  # Black color
    glVertex2f(1.0, 1.0)
    glColor3f(1.0, 1.0, 1.0)  # White color
    glVertex2f(-1.0, 1.0)
    glEnd()

def draw_sphere(radius, slices, stacks):
    quadric = gluNewQuadric()
    gluQuadricTexture(quadric, GL_TRUE)
    gluSphere(quadric, radius, slices, stacks)
    gluDeleteQuadric(quadric)

def apply_gpu_load(load_percentage, stop_event):
    pygame.init()
    screen = pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("GPU Load Test")

    glEnable(GL_DEPTH_TEST)
    texture_id = load_texture()
    rotation_angle = 0

    while not stop_event.is_set():
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        draw_background_gradient()  # Draw background gradient

        glTranslatef(0.0, 0.0, -5)
        glRotatef(rotation_angle, 1, 1, 1)

        # Draw multiple spheres
        if texture_id:
            glBindTexture(GL_TEXTURE_2D, texture_id)
        glColor3f(1.0, 0.0, 0.0)  # 球体の色を赤に設定

        for i in range(10):  # 複数の球体を描画
            glPushMatrix()
            glTranslatef(np.random.uniform(-2, 2), np.random.uniform(-2, 2), np.random.uniform(-2, 2))
            draw_sphere(0.5, 50, 50)
            glPopMatrix()
        
        rotation_angle += 1

        pygame.display.flip()
        time.sleep(0.01)  # 少しの待機時間を入れる

def tensor_calculation(load_percentage, stop_event):
    while not stop_event.is_set():
        a = torch.rand((10000, 10000), device='cuda')  # 計算量を増やす
        b = torch.rand((10000, 10000), device='cuda')  # 計算量を増やす
        c = torch.matmul(a, b)
        torch.cuda.synchronize()
        time.sleep(1 / load_percentage)

def apply_gpu_tensor_load(load_percentage, stop_event):
    threading.Thread(target=tensor_calculation, args=(load_percentage, stop_event), daemon=True).start()

def apply_combined_load(load_percentage, stop_event):
    threading.Thread(target=tensor_calculation, args=(load_percentage, stop_event), daemon=True).start()
    apply_gpu_load(load_percentage, stop_event)
