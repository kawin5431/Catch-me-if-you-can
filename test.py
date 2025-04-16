import pygame
import sys
import math

pygame.init()
pygame.mixer.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 1500, 850
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Catch me if you can")

SCALE = 1

background_image = pygame.image.load("img/map_area.png")
orig_w, orig_h = background_image.get_size()
background_image = pygame.transform.scale(background_image, (orig_w * SCALE, orig_h * SCALE))
MAP_WIDTH, MAP_HEIGHT = background_image.get_size()

car_image = pygame.image.load("img/lamborghini.png")
CAR_W, CAR_H = 37, 67
car_image = pygame.transform.scale(car_image, (CAR_W, CAR_H))

car_x = 6000.0
car_y = 1000.0
car_angle = 0

car_speed = 0.0
max_speed = 75
max_backward_speed = 10
acceleration = 2
friction = 1.3
base_turn_speed = 2
max_turn_speed = 10

previous_up = False

speed_modifier = 1.0
modifier_fade_rate = 0.1

try:
    background_sound = pygame.mixer.Sound("sound/background.mp3")
    background_channel = background_sound.play(-1)
    background_channel.set_volume(0.5)

    reverse_sound = pygame.mixer.Sound("sound/reverselambo.mp3")
    reverse_channel = reverse_sound.play(-1)
    reverse_channel.set_volume(0.25)
except:
    print("Warning: Some sound files not found.")

current_sound = None

reverse_vol = 0.25
fade_rate = 0.0025

car_hp = 500  
font = pygame.font.SysFont(None, 48)

HITBOX_COLOR_NORMAL = (57, 255, 20)
HITBOX_COLOR_COLLIDE = (255, 0, 0)
hitbox_color = HITBOX_COLOR_NORMAL

collision_time = -9999
collision_duration = 1000

def check_boundaries(x, y):
    if x < 0:
        x = 0
    if x > MAP_WIDTH:
        x = MAP_WIDTH
    if y < 0:
        y = 0
    if y > MAP_HEIGHT:
        y = MAP_HEIGHT
    return x, y

def get_rotated_box(cx, cy, width, height, angle_deg, shift_x=0, shift_y=0, angle_offset=0):
    hw = width / 2.0
    hh = height / 2.0
    corners = [
        (-hw, -hh),
        ( hw, -hh),
        ( hw,  hh),
        (-hw,  hh)
    ]
    shifted_corners = [(x + shift_x, y + shift_y) for (x, y) in corners]
    angle_total = angle_offset - angle_deg
    rad = math.radians(angle_total)
    cosA, sinA = math.cos(rad), math.sin(rad)
    rotated_points = []
    for (x, y) in shifted_corners:
        rx = x * cosA - y * sinA
        ry = x * sinA + y * cosA
        rotated_points.append((cx + rx, cy + ry))
    return rotated_points

tire_marks = []
mark_fade_speed = 20

running = True
clock = pygame.time.Clock()

while running:
    dt = clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    current_up = keys[pygame.K_UP]
    just_released_up = (previous_up and not current_up)

    if keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
        if speed_modifier > 0.6:
            speed_modifier -= modifier_fade_rate
            if speed_modifier < 0.6:
                speed_modifier = 0.6
    else:
        if speed_modifier < 1.0:
            speed_modifier += modifier_fade_rate
            if speed_modifier > 1.0:
                speed_modifier = 1.0

    turn_speed = base_turn_speed + (abs(car_speed) / max_speed) * (max_turn_speed - base_turn_speed)
    if abs(car_speed) >= 1:
        if keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
            lbx, lby = -CAR_W/4, CAR_H/8
            rbx, rby = CAR_W/4, CAR_H/8

            rad_angle = math.radians(car_angle)
            cosA = math.cos(rad_angle)
            sinA = math.sin(rad_angle)
            lx = lbx * cosA - lby * sinA
            ly = lbx * sinA + lby * cosA
            rx = rbx * cosA - rby * sinA
            ry = rbx * sinA + rby * cosA

            left_tire = (car_x + lx, car_y + ly)
            right_tire = (car_x + rx, car_y + ry)

            for _ in range(10):
                tire_marks.append([left_tire[0], left_tire[1], 255])
                tire_marks.append([right_tire[0], right_tire[1], 255])

        if keys[pygame.K_LEFT]:
            car_angle += turn_speed
        if keys[pygame.K_RIGHT]:
            car_angle -= turn_speed

    if current_up:
        car_speed += acceleration
        if car_speed > max_speed:
            car_speed = max_speed
        if current_sound != "lambo":
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.load("sound/lamboreal02.mp3")
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(1.0)
            except:
                pass
            current_sound = "lambo"
    elif keys[pygame.K_DOWN]:
        car_speed -= acceleration
        if car_speed < -max_backward_speed:
            car_speed = -max_backward_speed
    else:
        if car_speed > 0:
            car_speed -= friction
            if car_speed < 0:
                car_speed = 0
        elif car_speed < 0:
            car_speed += friction
            if car_speed > 0:
                car_speed = 0

    if just_released_up:
        pygame.mixer.music.stop()
        try:
            pygame.mixer.music.load("sound/slow03.mp3")
            pygame.mixer.music.play(0)
            pygame.mixer.music.set_volume(1.0)
        except:
            pass
        current_sound = "slow"
    if current_sound == "slow":
        if not pygame.mixer.music.get_busy():
            current_sound = None

    effective_speed = car_speed * speed_modifier
    rad = math.radians(car_angle)
    intended_x = car_x + effective_speed * -math.sin(rad)
    intended_y = car_y + effective_speed * -math.cos(rad)
    new_x, new_y = check_boundaries(intended_x, intended_y)
    car_x, car_y = new_x, new_y
    if (new_x != intended_x or new_y != intended_y):
        now = pygame.time.get_ticks()
        if now > collision_time + collision_duration:
            car_hp -= 10
            if car_hp < 0:
                car_hp = 0
            collision_time = now
            hitbox_color = HITBOX_COLOR_COLLIDE
    if pygame.time.get_ticks() > collision_time + collision_duration:
        hitbox_color = HITBOX_COLOR_NORMAL

    camera_x = car_x - (SCREEN_WIDTH / 2)
    camera_y = car_y - (SCREEN_HEIGHT / 2)
    max_camera_x = max(MAP_WIDTH - SCREEN_WIDTH, 0)
    max_camera_y = max(MAP_HEIGHT - SCREEN_HEIGHT, 0)
    if camera_x < 0:
        camera_x = 0
    if camera_y < 0:
        camera_y = 0
    if camera_x > max_camera_x:
        camera_x = max_camera_x
    if camera_y > max_camera_y:
        camera_y = max_camera_y

    screen.blit(background_image, (-camera_x, -camera_y))
    for mark in tire_marks:
        mark[2] -= mark_fade_speed
    tire_marks = [m for m in tire_marks if m[2] > 0]
    for mark in tire_marks:
        draw_x = mark[0] - camera_x
        draw_y = mark[1] - camera_y
        pygame.draw.circle(screen, (100, 100, 100), (int(draw_x), int(draw_y)), 3)

    rotated_car = pygame.transform.rotate(car_image, car_angle)
    car_rect = rotated_car.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(rotated_car, car_rect)

    hit_box_points = get_rotated_box(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, CAR_W, CAR_H,
                                     car_angle, shift_x=0, shift_y=0, angle_offset=0)
    pygame.draw.polygon(screen, hitbox_color, hit_box_points, 2)

    hp_text = font.render(f"HP: {car_hp}", True, (255, 255, 255))
    screen.blit(hp_text, (20, 20))

    speed_text = font.render(f"Speed: {int(effective_speed)}", True, (255, 255, 255))
    screen.blit(speed_text, (20, SCREEN_HEIGHT - speed_text.get_height() - 20))
    
    pygame.display.update()
    pygame.time.delay(30)
    previous_up = current_up

    if current_sound == "lambo":
        reverse_vol = 0.0003
    elif current_sound == "slow":
        if reverse_vol < 0.25:
            reverse_vol += fade_rate
            if reverse_vol > 0.25:
                reverse_vol = 0.25
    else:
        reverse_vol = 0.25
    reverse_channel.set_volume(reverse_vol)

pygame.quit()
sys.exit()
