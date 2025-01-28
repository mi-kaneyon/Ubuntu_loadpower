import pygame
from pygame.locals import *
import sys
from OpenGL.GL import *
from OpenGL.GLU import *
import threading
import time
import numpy as np
import torch


######################################
#  OpenGL 用のライティング初期化
######################################
def initialize_lighting():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    light_position = [10.0, 10.0, 10.0, 1.0]
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
    glEnable(GL_COLOR_MATERIAL)

######################################
#  テクスチャ読み込み
######################################
def load_texture():
    try:
        print("Loading texture...")
        texture_surface = pygame.image.load('texture.jpg')
        print("Texture loaded successfully.")

        texture_data = pygame.image.tostring(texture_surface, 'RGB', 1)
        width = texture_surface.get_width()
        height = texture_surface.get_height()

        glEnable(GL_TEXTURE_2D)
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0,
                     GL_RGB, GL_UNSIGNED_BYTE, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        print(f"Texture ID generated: {texture_id}")
        return texture_id
    except pygame.error as e:
        print(f"Error loading texture: {e}")
        return None

######################################
#  回転する立体をまとめて描画する
######################################
def draw_rotating_shapes(texture_id, rotation_angle):
    if texture_id:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)
    else:
        glDisable(GL_TEXTURE_2D)

    shapes = ["cube", "sphere", "cone"]
    np.random.shuffle(shapes)

    for shape in shapes:
        glPushMatrix()
        glTranslatef(np.random.uniform(-3, 3),
                     np.random.uniform(-3, 3),
                     np.random.uniform(-3, 3))
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
        print(f"OpenGL Error (draw_shapes): {gluErrorString(error)}")

######################################
#  キューブ描画
######################################
def draw_cube():
    vertices = [
        (-1, -1, -1),
        ( 1, -1, -1),
        ( 1,  1, -1),
        (-1,  1, -1),
        (-1, -1,  1),
        ( 1, -1,  1),
        ( 1,  1,  1),
        (-1,  1,  1)
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
        (0, 0),
        (1, 0),
        (1, 1),
        (0, 1)
    ]

    glBegin(GL_QUADS)
    for face in faces:
        for i, vertex in enumerate(face):
            glTexCoord2fv(tex_coords[i % len(tex_coords)])
            glVertex3fv(vertices[vertex])
    glEnd()

    error = glGetError()
    if error != GL_NO_ERROR:
        print(f"OpenGL Error (draw_cube): {gluErrorString(error)}")

######################################
#  球体描画
######################################
def draw_sphere(radius, slices, stacks):
    quadric = gluNewQuadric()
    gluQuadricTexture(quadric, GL_TRUE)
    glColor3f(0.0, 0.0, 1.0)
    gluSphere(quadric, radius, slices, stacks)
    gluDeleteQuadric(quadric)

    error = glGetError()
    if error != GL_NO_ERROR:
        print(f"OpenGL Error (draw_sphere): {gluErrorString(error)}")

######################################
#  円錐描画
######################################
def draw_cone(base, height, slices, stacks):
    quadric = gluNewQuadric()
    gluQuadricTexture(quadric, GL_TRUE)
    glColor3f(1.0, 0.0, 0.0)
    gluCylinder(quadric, base, 0.0, height, slices, stacks)
    gluDeleteQuadric(quadric)

    error = glGetError()
    if error != GL_NO_ERROR:
        print(f"OpenGL Error (draw_cone): {gluErrorString(error)}")

#########################################################
# (1) GPU 負荷 (OpenGL レンダリング) - 修正版
#########################################################
def apply_gpu_load(load_percentage, stop_event, gpu_id):
    """
    OpenGL を使って 3D 描画負荷をかける (修正版)。
    - sys.exit() を使わず、stop_event またはウィンドウを閉じると終了。
    - 再度テストしてもセグフォが起きにくいようにする。
    """
    pygame.init()
    screen = pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)
    pygame.display.set_caption(f"GPU Load Test (GPU {gpu_id})")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (800 / 600), 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    initialize_lighting()
    texture_id = load_texture()
    rotation_angle = 0

    if texture_id is None:
        print("[DEBUG] Texture loading failed; proceeding without texture.")

    glClearColor(0.3, 0.3, 0.3, 1.0)

    while not stop_event.is_set():
        # イベント処理
        for event in pygame.event.get():
            if event.type == QUIT:
                # ウィンドウ閉じる操作が来たら stop_event を立ててループを抜ける
                print("[DEBUG] Window close event -> stopping GPU load.")
                stop_event.set()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        gluLookAt(
            0.0, 0.0, 15.0,
            0.0, 0.0, 0.0,
            0.0, 1.0, 0.0
        )

        draw_rotating_shapes(texture_id, rotation_angle)
        rotation_angle += load_percentage / 10.0

        pygame.display.flip()
        glFlush()
        time.sleep(0.01)

        error = glGetError()
        if error != GL_NO_ERROR:
            print(f"OpenGL Error (main loop): {gluErrorString(error)}")

    # ループ終了時にウィンドウを閉じる
    print("[DEBUG] Exiting GPU load loop. Doing pygame.quit() ...")
    pygame.quit()
    print("[DEBUG] Pygame quit. Thread returning now.")

######################################
#  (2) Tensor 計算で GPU に負荷
######################################
def tensor_calculation(load_percentage, stop_event, gpu_id):
    torch.cuda.set_device(gpu_id)
    while not stop_event.is_set():
        a = torch.rand((8000, 8000), device='cuda')
        b = torch.rand((8000, 8000), device='cuda')
        _ = torch.matmul(a, b)
        torch.cuda.synchronize()
        time.sleep(1 / (load_percentage + 1))

def apply_gpu_tensor_load(load_percentage, stop_event, gpu_ids):
    """
    PyTorch の Tensor 演算を使って負荷をかける。
    停止時は stop_event をセットしてループを抜ける。
    """
    print(f"Starting GPU Tensor Load with {load_percentage}% on GPUs: {gpu_ids}")
    for gpu_id in gpu_ids:
        threading.Thread(
            target=tensor_calculation,
            args=(load_percentage, stop_event, gpu_id),
            daemon=True
        ).start()

######################################
#  (3) 3D 描画 + Tensor 計算の複合負荷
######################################
def apply_combined_load(load_percentage, stop_event, gpu_ids):
    """
    GPU 上で Tensor 計算 + OpenGL レンダリングを同時に行う。
    OpenGL スレッドでは sys.exit() せず、stop_event で終了管理。
    """
    for gpu_id in gpu_ids:
        # Tensor
        threading.Thread(
            target=tensor_calculation,
            args=(load_percentage, stop_event, gpu_id),
            daemon=True
        ).start()

        # OpenGL (修正版)
        threading.Thread(
            target=apply_gpu_load,
            args=(load_percentage, stop_event, gpu_id),
            daemon=True
        ).start()


######################################
#  (4) VRAM 負荷 (単純版: 電力しきい値なし)
######################################
def apply_gpu_vram_load(vram_percentage, stop_event, gpu_ids):
    """
    ユーザーがスライダーで指定した vram_percentage (%) を元に、
    停止されるまで VRAM を確保し続けるテスト。
    GPU 消費電力に依存せず単純に割り当てる。
    """
    for gpu_id in gpu_ids:
        threading.Thread(
            target=allocate_vram_dynamic,
            args=(vram_percentage, stop_event, gpu_id),
            daemon=True
        ).start()

def allocate_vram_dynamic(vram_percentage, stop_event, gpu_id):
    """
    (vram_percentage)% の VRAM をなるべく使うようにし、
    超えたら解放、足りなければ追加確保。
    停止指令でループを抜ける。
    """
    device = torch.device(f'cuda:{gpu_id}')
    print(f"[INFO] Starting VRAM load on GPU {gpu_id} => target={vram_percentage}% of total memory.")

    allocated_tensors = []

    while not stop_event.is_set():
        free_mem, total_mem = torch.cuda.mem_get_info(device=device)
        used_mem = total_mem - free_mem
        used_percent = (used_mem / total_mem) * 100.0

        target_bytes = int(total_mem * (vram_percentage / 100.0))
        current_alloc = used_mem  # 現在の使用量 (他プロセス含む)

        if current_alloc < target_bytes:
            to_allocate = target_bytes - current_alloc
            chunk_size = to_allocate // 10
            if chunk_size < 1:
                chunk_size = 1
            chunk_size_float = chunk_size // 4

            if chunk_size_float > 0:
                try:
                    tensor = torch.zeros(chunk_size_float, dtype=torch.float32, device=device)
                    allocated_tensors.append(tensor)
                except RuntimeError as e:
                    print(f"[WARN] OOM on GPU {gpu_id}: {e}")
                    time.sleep(1.0)
            time.sleep(0.1)

        elif current_alloc > target_bytes:
            to_free = current_alloc - target_bytes
            freed = 0
            while freed < to_free and allocated_tensors:
                pop_t = allocated_tensors.pop()
                freed += pop_t.numel() * 4
                del pop_t
            torch.cuda.empty_cache()
            time.sleep(0.1)

        else:
            # ほぼ目標付近
            time.sleep(0.2)

    # 停止ボタン押下または終了
    print(f"[INFO] Stopping VRAM load on GPU {gpu_id}. Freed all allocated tensors.")
    del allocated_tensors
    torch.cuda.empty_cache()
    print(f"[INFO] GPU {gpu_id} memory freed.")
