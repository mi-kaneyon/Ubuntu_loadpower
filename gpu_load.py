import pygame
from pygame.locals import *
import sys
from OpenGL.GL import *
from OpenGL.GLU import *
import threading
import time
import numpy as np
import torch
import tkinter as tk
from tkinter import messagebox

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

def apply_gpu_load(load_percentage, stop_event, gpu_id):
    pygame.init()
    screen = pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)
    pygame.display.set_caption(f"GPU Load Test (GPU {gpu_id})")

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
        glColor3f(1.0, 0.0, 0.0)  # Set sphere color to red

        for i in range(10):  # Draw multiple spheres
            glPushMatrix()
            glTranslatef(np.random.uniform(-2, 2), np.random.uniform(-2, 2), np.random.uniform(-2, 2))
            draw_sphere(0.5, 50, 50)
            glPopMatrix()
        
        rotation_angle += 1

        pygame.display.flip()
        time.sleep(0.01)  # Add a slight delay

def tensor_calculation(load_percentage, stop_event, gpu_id):
    torch.cuda.set_device(gpu_id)
    while not stop_event.is_set():
        a = torch.rand((10000, 10000), device='cuda')  # Increase calculation load
        b = torch.rand((10000, 10000), device='cuda')  # Increase calculation load
        c = torch.matmul(a, b)
        torch.cuda.synchronize()
        time.sleep(1 / load_percentage)

def apply_gpu_tensor_load(load_percentage, stop_event, gpu_ids):
    for gpu_id in gpu_ids:
        threading.Thread(target=tensor_calculation, args=(load_percentage, stop_event, gpu_id), daemon=True).start()

def apply_combined_load(load_percentage, stop_event, gpu_ids):
    for gpu_id in gpu_ids:
        threading.Thread(target=tensor_calculation, args=(load_percentage, stop_event, gpu_id), daemon=True).start()
        threading.Thread(target=apply_gpu_load, args=(load_percentage, stop_event, gpu_id), daemon=True).start()

def apply_gpu_vram_load(vram_percentage, stop_event, gpu_ids):
    for gpu_id in gpu_ids:
        threading.Thread(target=allocate_vram, args=(vram_percentage, stop_event, gpu_id), daemon=True).start()

def allocate_vram(vram_percentage, stop_event, gpu_id):
    device = torch.device(f'cuda:{gpu_id}')
    total_memory = torch.cuda.get_device_properties(device).total_memory
    target_memory = total_memory * (vram_percentage / 100)
    allocated_memory = 0

    tensors = []

    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    while not stop_event.is_set():
        try:
            # 小さなチャンクでメモリを割り当てる
            chunk_size = int(total_memory * 0.01 / 4)  # 1% of total memory
            tensor = torch.zeros(chunk_size, dtype=torch.float32, device=device)
            tensors.append(tensor)
            allocated_memory += chunk_size * 4
            print(f"Allocated memory: {allocated_memory / (1024**3):.2f} GB")
            if allocated_memory >= target_memory:
                break
        except RuntimeError as e:
            messagebox.showerror("メモリ割り当てエラー", f"メモリの割り当てに失敗しました: {e}")
            break
        time.sleep(0.1)  # Add a slight delay to manage allocation pace
    
    print("Stopping VRAM load.")
    del tensors  # Free the tensors
    torch.cuda.empty_cache()  # Clear the cache
