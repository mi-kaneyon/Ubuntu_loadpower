import pygame
from pygame.locals import *
import sys
from OpenGL.GL import *
from OpenGL.GLU import *
import threading
import time
import numpy as np
import torch

# ライティングの初期化
def initialize_lighting():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    light_position = [10.0, 10.0, 10.0, 1.0]  # 光源位置
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
    glEnable(GL_COLOR_MATERIAL)

# テクスチャの読み込み
def load_texture():
    try:
        print("Loading texture...")  # デバッグ: テクスチャの読み込み開始
        texture_surface = pygame.image.load('texture.jpg')
        print("Texture loaded successfully.")  # デバッグ: テクスチャが正常に読み込まれた場合

        texture_data = pygame.image.tostring(texture_surface, 'RGB', 1)
        width = texture_surface.get_width()
        height = texture_surface.get_height()

        glEnable(GL_TEXTURE_2D)
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        print(f"Texture ID generated: {texture_id}")  # デバッグ: 生成されたテクスチャIDを通知
        return texture_id
    except pygame.error as e:
        print(f"Error loading texture: {e}")
        return None

# 回転する立体を描画
def draw_rotating_shapes(texture_id, rotation_angle):
    if texture_id:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        print(f"[DEBUG] Texture bound with ID: {texture_id}")
    else:
        print("[DEBUG] No texture found. Drawing without texture.")
        glDisable(GL_TEXTURE_2D)

    # 描画する立体（キューブ、球体、円錐）
    shapes = ["cube", "sphere", "cone"]
    np.random.shuffle(shapes)

    for shape in shapes:
        glPushMatrix()
        glTranslatef(np.random.uniform(-3, 3), np.random.uniform(-3, 3), np.random.uniform(-3, 3))
        glRotatef(rotation_angle, 1, 1, 1)
        if shape == "cube":
            draw_cube()
        elif shape == "sphere":
            draw_sphere(0.5, 20, 20)
        elif shape == "cone":
            draw_cone(0.5, 1.0, 20, 20)
        glPopMatrix()

    error = glGetError()
    if error != GL_NO_ERROR:
        print(f"OpenGL Error during shape drawing: {gluErrorString(error)}")

# キューブを描画
def draw_cube():
    vertices = [
        (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)
    ]

    faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 4, 7, 3),
        (1, 5, 6, 2),
        (3, 2, 6, 7),
        (0, 1, 5, 4)
    ]

    tex_coords = [
        (0, 0), (1, 0), (1, 1), (0, 1)  # UV座標
    ]

    glBegin(GL_QUADS)
    for face in faces:
        for i, vertex in enumerate(face):
            glTexCoord2fv(tex_coords[i % len(tex_coords)])  # UV座標を指定
            glVertex3fv(vertices[vertex])
    glEnd()

    error = glGetError()
    if error != GL_NO_ERROR:
        print(f"OpenGL Error during cube drawing: {gluErrorString(error)}")

# 球体を描画
def draw_sphere(radius, slices, stacks):
    quadric = gluNewQuadric()
    gluQuadricTexture(quadric, GL_TRUE)
    glColor3f(0.0, 0.0, 1.0)  # 青色で描画
    gluSphere(quadric, radius, slices, stacks)
    gluDeleteQuadric(quadric)

    error = glGetError()
    if error != GL_NO_ERROR:
        print(f"OpenGL Error during sphere drawing: {gluErrorString(error)}")

# 円錐を描画
def draw_cone(base, height, slices, stacks):
    quadric = gluNewQuadric()
    gluQuadricTexture(quadric, GL_TRUE)
    glColor3f(1.0, 0.0, 0.0)  # 赤色で描画
    gluCylinder(quadric, base, 0.0, height, slices, stacks)
    gluDeleteQuadric(quadric)

    error = glGetError()
    if error != GL_NO_ERROR:
        print(f"OpenGL Error during cone drawing: {gluErrorString(error)}")

# GPU負荷をかける関数
def apply_gpu_load(load_percentage, stop_event, gpu_id):
    pygame.init()
    screen = pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)
    pygame.display.set_caption(f"GPU Load Test (GPU {gpu_id})")

    # 視野の設定
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (800/600), 0.1, 50.0)  # 視野角、アスペクト比、ニアクリップ、ファークリップ
    glMatrixMode(GL_MODELVIEW)

    # OpenGL設定
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    initialize_lighting()
    texture_id = load_texture()
    rotation_angle = 0

    if texture_id is None:
        print("[DEBUG] Texture loading failed, proceeding without texture.")

    # カリングを無効にして、全ての面が描画されるようにする
    glDisable(GL_CULL_FACE)

    # 背景色の設定（黒以外にすることでオブジェクトが見やすくなる）
    glClearColor(0.3, 0.3, 0.3, 1.0)  # 背景色を少し明るくする

    while not stop_event.is_set():
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        # バッファのクリア
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # カメラの設定
        gluLookAt(0.0, 0.0, 15.0,  # カメラの位置を調整
                  0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0)

        # 回転する立体を描画
        draw_rotating_shapes(texture_id, rotation_angle)

        rotation_angle += load_percentage / 10.0  # 負荷に応じて回転速度を調整

        pygame.display.flip()
        glFlush()
        time.sleep(0.01)

        # OpenGLエラーチェック
        error = glGetError()
        if error != GL_NO_ERROR:
            print(f"OpenGL Error during main loop: {gluErrorString(error)}")



# Tensorを使ってGPU負荷をかける関数
def tensor_calculation(load_percentage, stop_event, gpu_id):
    torch.cuda.set_device(gpu_id)
    while not stop_event.is_set():
        a = torch.rand((8000, 8000), device='cuda')
        b = torch.rand((8000, 8000), device='cuda')
        c = torch.matmul(a, b)
        torch.cuda.synchronize()
        time.sleep(1 / (load_percentage + 1))  # 負荷の割合に応じて待機時間を調整

# GPU Tensor負荷をかける関数
def apply_gpu_tensor_load(load_percentage, stop_event, gpu_ids):
    print(f"Starting GPU Tensor Load with {load_percentage}% on GPUs: {gpu_ids}")
    for gpu_id in gpu_ids:
        threading.Thread(target=tensor_calculation, args=(load_percentage, stop_event, gpu_id), daemon=True).start()

# GPU負荷を組み合わせてかける関数
def apply_combined_load(load_percentage, stop_event, gpu_ids):
    for gpu_id in gpu_ids:
        threading.Thread(target=tensor_calculation, args=(load_percentage, stop_event, gpu_id), daemon=True).start()
        threading.Thread(target=apply_gpu_load, args=(load_percentage, stop_event, gpu_id), daemon=True).start()

# VRAMに負荷をかける関数
def apply_gpu_vram_load(vram_percentage, stop_event, gpu_ids):
    for gpu_id in gpu_ids:
        threading.Thread(target=allocate_vram, args=(vram_percentage, stop_event, gpu_id), daemon=True).start()

# VRAMを確保することで負荷をかける
def allocate_vram(vram_percentage, stop_event, gpu_id):
    device = torch.device(f'cuda:{gpu_id}')
    total_memory = torch.cuda.get_device_properties(device).total_memory
    target_memory = total_memory * (vram_percentage / 100)
    allocated_memory = 0

    tensors = []

    while not stop_event.is_set():
        try:
            chunk_size = int(total_memory * 0.01 / 4)
            tensor = torch.zeros(chunk_size, dtype=torch.float32, device=device)
            tensors.append(tensor)
            allocated_memory += chunk_size * 4
            if allocated_memory >= target_memory:
                break
        except RuntimeError as e:
            print(f"[ERROR] VRAM Allocation Error: {e}")
            break
        time.sleep(0.1)

    print("Stopping VRAM load.")
    del tensors
    torch.cuda.empty_cache()
