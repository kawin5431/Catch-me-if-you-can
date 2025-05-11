import csv, math, random, sys, pygame, matplotlib.pyplot as plt, pandas as pd

pygame.init()
pygame.mixer.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 1500, 850
SAND_COLOR = (238, 217, 182)
DOT_COLOR = (222, 196, 142)
DOT_SPACING, DOT_RADIUS = 25, 2
CAR_W, CAR_H = 37, 67
POLICE_W, POLICE_H = 43, 81

class SoundManager:
    def __init__(self):
        self.channels = {}
        try:
            self.sounds = {
                "bg": pygame.mixer.Sound("sound/background.mp3"),
                "reverse": pygame.mixer.Sound("sound/reverselambo.mp3"),
                "crash": pygame.mixer.Sound("sound/Hitsound.mp3"),
                "lambo": "sound/lamboreal02.mp3",
                "slow": "sound/slow03.mp3"
            }
        except:
            self.sounds = {}
        self.current_music = None
    def play_loop(self, name, volume):
        if name in self.sounds:
            ch = self.sounds[name].play(-1)
            ch.set_volume(volume)
            self.channels[name] = ch
    def play_once(self, name):
        if name in self.sounds:
            self.sounds[name].play()
    def music(self, name, volume):
        if self.current_music == name:
            return
        pygame.mixer.music.stop()
        if name in self.sounds:
            try:
                pygame.mixer.music.load(self.sounds[name])
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(volume)
                self.current_music = name
            except:
                self.current_music = None
        else:
            self.current_music = None

class Background:
    def draw(self, screen, cx, cy):
        screen.fill(SAND_COLOR)
        for x in range(0, SCREEN_WIDTH, DOT_SPACING):
            for y in range(0, SCREEN_HEIGHT, DOT_SPACING):
                wx, wy = x + cx, y + cy
                seed = (wx // DOT_SPACING, wy // DOT_SPACING)
                r = (hash(seed) % 100) / 100
                if r < 0.3:
                    pygame.draw.circle(screen, DOT_COLOR, (x, y), DOT_RADIUS)

def rotated_box(cx, cy, w, h, angle):
    hw, hh = w / 2, h / 2
    rad = math.radians(-angle)
    ca, sa = math.cos(rad), math.sin(rad)
    pts = []
    for ox, oy in [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]:
        pts.append((cx + ox * ca - oy * sa, cy + ox * sa + oy * ca))
    return pts

def polys_intersect(p1, p2):
    def proj(poly, ax):
        dots = [x * ax[0] + y * ax[1] for x, y in poly]
        return min(dots), max(dots)
    for poly in [p1, p2]:
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            edge = (poly[j][0] - poly[i][0], poly[j][1] - poly[i][1])
            ax = (-edge[1], edge[0])
            p1min, p1max = proj(p1, ax)
            p2min, p2max = proj(p2, ax)
            if p1max < p2min or p2max < p1min:
                return False
    return True

class TireMarkManager:
    def __init__(self):
        self.marks = []
    def add(self, x, y):
        self.marks.append([x, y, 255])
    def update(self):
        for m in self.marks:
            m[2] -= 20
        self.marks = [m for m in self.marks if m[2] > 0]
    def draw(self, screen, cx, cy):
        for x, y, a in self.marks:
            pygame.draw.circle(screen, (0, 0, 0), (int(x - cx), int(y - cy)), 3)

class NitroFlame:
    def __init__(self):
        self.active = False
        self.end = 0
        self.fade = False
        self.fade_rate = 0.5
    def start(self):
        self.active = True
        self.end = pygame.time.get_ticks() + 2000
    def update(self, max_speed, base_max):
        if self.active and pygame.time.get_ticks() > self.end:
            self.active = False
            self.fade = True
        if self.fade:
            max_speed -= self.fade_rate
            if max_speed <= base_max:
                max_speed = base_max
                self.fade = False
        return max_speed
    def draw(self, screen, angle):
        for i in range(5):
            ratio = i / 5
            radius = int(12 * (1 - ratio)) + 4
            col = (min(300, int(255 - 100 * ratio)), int(100 + 100 * (1 - ratio)), 0)
            alpha = int(180 * (1 - ratio))
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*col, alpha), (radius, radius), radius)
            offx = math.sin(math.radians(angle)) * (CAR_H / 2 + i * 6)
            offy = math.cos(math.radians(angle)) * (CAR_H / 2 + i * 6)
            screen.blit(surf, (SCREEN_WIDTH // 2 + offx - radius, SCREEN_HEIGHT // 2 + offy - radius))

class CarBase:
    def __init__(self, x, y, img, w, h):
        self.x = x
        self.y = y
        self.angle = 0
        self.vx = 0.0
        self.vy = 0.0
        self.rotation_speed = 0.0
        self.speed = 0.0
        self.image = pygame.transform.scale(pygame.image.load(img), (w, h))
        self.w = w
        self.h = h
    def move(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.9
        self.vy *= 0.9
        self.angle += self.rotation_speed
        self.rotation_speed *= 0.8
    def draw(self, screen, cx, cy):
        rot = pygame.transform.rotate(self.image, self.angle)
        rect = rot.get_rect(center=(int(self.x - cx), int(self.y - cy)))
        screen.blit(rot, rect)
        hit = rotated_box(self.x - cx, self.y - cy, self.w, self.h, self.angle)
        return hit

class PlayerCar(CarBase):
    def __init__(self, x, y):
        super().__init__(x, y, "img/lamborghini.png", CAR_W, CAR_H)
        self.max_speed = 38
        self.max_back = 10
        self.accel = 4
        self.friction = 1.3
        self.base_turn = 2
        self.max_turn = 10
        self.hp = 10000
        self.total_distance = 0.0
        self.speed_modifier = 1.0
        self.mod_fade = 0.1
    def control(self, keys, max_speed_current, tiremarks):
        current_up = keys[pygame.K_UP]
        if keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
            self.speed_modifier = max(0.8, self.speed_modifier - self.mod_fade)
        else:
            self.speed_modifier = min(1.0, self.speed_modifier + self.mod_fade)
        turn = self.base_turn + (abs(self.speed) / self.max_speed) * (self.max_turn - self.base_turn)
        if abs(self.speed) >= 1 and (keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]):
            if keys[pygame.K_LEFT]:
                self.angle += turn
            if keys[pygame.K_RIGHT]:
                self.angle -= turn
            rad = math.radians(self.angle)
            cosA = math.cos(rad)
            sinA = math.sin(rad)
            for ox in [(-self.w / 4, self.h / 8), (self.w / 4, self.h / 8)]:
                px = self.x + ox[0] * cosA - ox[1] * sinA
                py = self.y + ox[0] * sinA + ox[1] * cosA
                tiremarks.add(px, py)
        if current_up:
            self.speed = min(max_speed_current, self.speed + self.accel)
        elif keys[pygame.K_DOWN]:
            self.speed = max(-self.max_back, self.speed - self.accel)
        else:
            if self.speed > 0:
                self.speed = max(0, self.speed - self.friction)
            elif self.speed < 0:
                self.speed = min(0, self.speed + self.friction)
        eff_speed = self.speed * self.speed_modifier
        rad = math.radians(self.angle)
        self.x += eff_speed * -math.sin(rad)
        self.y += eff_speed * -math.cos(rad)
        return eff_speed
    def hitbox(self):
        return rotated_box(self.x, self.y, self.w, self.h, self.angle)

class PoliceCar(CarBase):
    def __init__(self, x, y):
        super().__init__(x, y, "img/Screenshot_2568-05-11_at_02.04.16-removebg-preview.png", POLICE_W, POLICE_H)
        self.max_speed = 47
        self.accel = 3
        self.friction = 0.1
        self.base_turn = 4
        self.max_turn = 8
        self.hp = 20
    def update(self, tx, ty):
        if self.hp <= 0:
            return
        dx = tx - self.x
        dy = ty - self.y
        ang = math.degrees(math.atan2(-dx, -dy))
        diff = (ang - self.angle + 180) % 360 - 180
        turn = self.base_turn + (abs(self.speed) / self.max_speed) * (self.max_turn - self.base_turn)
        if diff > 1:
            self.angle += min(turn, diff)
        elif diff < -1:
            self.angle += max(-turn, diff)
        self.speed = min(self.max_speed, self.speed + self.accel)
        if abs(diff) > 5:
            self.speed *= 0.8
        rad = math.radians(self.angle)
        self.x += self.speed * -math.sin(rad)
        self.y += self.speed * -math.cos(rad)
        self.move()
    def hitbox(self):
        return rotated_box(self.x, self.y, self.w, self.h, self.angle)

class StatsManager:
    def save(self, dist, t, avg, nitro, police):
        fn = "game_stats.csv"
        exists = False
        try:
            with open(fn, "r"):
                exists = True
        except:
            pass
        with open(fn, "a", newline="") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["Distance", "Time", "AvgSpeed", "Nitros", "Police"])
            w.writerow([dist, t, avg, nitro, police])
    def plot(self):
        try:
            df = pd.read_csv("game_stats.csv")
            plt.figure(figsize=(10, 5))
            plt.plot(df["Distance"], label="Distance")
            plt.plot(df["Time"], label="Time")
            plt.plot(df["AvgSpeed"], label="Avg Speed")
            plt.xlabel("Session")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plt.savefig("game_stats_plot.png")
            plt.close()
        except:
            pass

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Catch me if you can")
        self.clock = pygame.time.Clock()
        self.player = PlayerCar(200.0, 200.0)
        self.tiremarks = TireMarkManager()
        self.nitro = NitroFlame()
        self.bg = Background()
        self.snd = SoundManager()
        self.snd.play_loop("bg", 0.5)
        self.snd.play_loop("reverse", 0.25)
        self.police = [PoliceCar(self.player.x + 3000, self.player.y + 3000)]
        self.last_spawn = pygame.time.get_ticks()
        self.font = pygame.font.SysFont(None, 48)
        self.start_time = pygame.time.get_ticks()
        self.camera_shake = 0
        self.shake_mag = 8
        self.total_distance = 0.0
        self.last_milestone = 0
        self.nitro_count = 0
        self.stats = StatsManager()
    def start_screen(self):
        f_big = pygame.font.SysFont(None, 96)
        f = pygame.font.SysFont(None, 48)
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                    return
            self.screen.fill((0, 0, 0))
            t1 = f_big.render("Catch me if you can", True, (255, 255, 255))
            t2 = f.render("Press ENTER to Start", True, (200, 200, 200))
            self.screen.blit(t1, t1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100)))
            self.screen.blit(t2, t2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)))
            pygame.display.flip()
    def game_over(self):
        f_big = pygame.font.SysFont(None, 96)
        f = pygame.font.SysFont(None, 48)
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
            self.screen.fill((0, 0, 0))
            t1 = f_big.render("GAME OVER", True, (255, 0, 0))
            t2 = f.render("Press ESC or close window", True, (200, 200, 200))
            self.screen.blit(t1, t1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100)))
            self.screen.blit(t2, t2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)))
            pygame.display.flip()
    def spawn_police(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        if elapsed <= 20000:
            target = 2
        elif elapsed <= 40000:
            target = 5
        else:
            target = 20
        alive = [p for p in self.police if p.hp > 0]
        if len(alive) < target and pygame.time.get_ticks() - self.last_spawn >= 1000:
            ox = random.choice([-1, 1]) * random.randint(2500, 6000)
            oy = random.choice([-1, 1]) * random.randint(2500, 6000)
            self.police.append(PoliceCar(self.player.x + ox, self.player.y + oy))
            self.last_spawn = pygame.time.get_ticks()
    def collision_response(self, a, b, w1, h1, w2, h2, sa, sb, va, vb):
        box1 = rotated_box(a.x, a.y, w1, h1, sa)
        box2 = rotated_box(b.x, b.y, w2, h2, sb)
        if polys_intersect(box1, box2):
            dx = a.x - b.x
            dy = a.y - b.y
            dist = math.hypot(dx, dy)
            if dist == 0:
                dx, dy = 1, 0
                dist = 1
            dirx, diry = dx / dist, dy / dist
            rel = abs(va - vb)
            force = min(30, 5 + rel * 0.8) * 0.3
            torque = rel * 0.4 * 0.3
            a.vx += dirx * force
            a.vy += diry * force
            b.vx -= dirx * force
            b.vy -= diry * force
            a.rotation_speed += torque * (-1 if dirx > 0 else 1)
            b.rotation_speed += torque * (1 if dirx > 0 else -1)
            a.x += dirx * 5
            a.y += diry * 5
            b.x -= dirx * 5
            b.y -= diry * 5
    def run(self):
        self.start_screen()
        prev_up = False
        while True:
            dt = self.clock.tick(60)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_q and self.nitro_count > 0 and not self.nitro.active:
                    self.nitro.start()
                    self.nitro_count -= 1
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP] and not prev_up:
                self.snd.music("lambo", 1.0)
            if prev_up and not keys[pygame.K_UP]:
                self.snd.music("slow", 1.0)
            prev_up = keys[pygame.K_UP]
            base_max = 40
            max_speed_current = 67 if self.nitro.active else base_max
            max_speed_current = self.nitro.update(max_speed_current, base_max)
            eff_speed = self.player.control(keys, max_speed_current, self.tiremarks)
            self.spawn_police()
            player_box = self.player.hitbox()
            for p in self.police:
                self.collision_response(self.player, p, CAR_W, CAR_H, POLICE_W, POLICE_H, self.player.angle, p.angle, eff_speed, p.speed)
            for i in range(len(self.police)):
                for j in range(i + 1, len(self.police)):
                    self.collision_response(self.police[i], self.police[j], POLICE_W, POLICE_H, POLICE_W, POLICE_H, self.police[i].angle, self.police[j].angle, self.police[i].speed, self.police[j].speed)
            hit_player = False
            for p in self.police:
                p.update(self.player.x, self.player.y)
                if p.hp > 0 and polys_intersect(player_box, p.hitbox()):
                    hit_player = True
                    p.hp = max(0, p.hp - 10)
                    dx = self.player.x - p.x
                    dy = self.player.y - p.y
                    d = math.hypot(dx, dy)
                    if d == 0:
                        d = 1
                    self.player.vx += (dx / d) * 1.5
                    self.player.vy += (dy / d) * 1.5
            if hit_player:
                self.player.hp = max(0, self.player.hp - 10)
                self.camera_shake = 10
                self.snd.play_once("crash")
            self.player.move()
            self.tiremarks.update()
            self.total_distance += abs(eff_speed)
            dist_m = int(self.total_distance / 6)
            if dist_m - self.last_milestone >= 2200:
                self.nitro_count += 1
                self.last_milestone = dist_m
            camx = self.player.x - SCREEN_WIDTH // 2
            camy = self.player.y - SCREEN_HEIGHT // 2
            if self.camera_shake > 0:
                camx += math.sin(pygame.time.get_ticks()) * self.shake_mag
                camy += math.cos(pygame.time.get_ticks()) * self.shake_mag
                self.camera_shake -= 1
            self.bg.draw(self.screen, camx, camy)
            for p in self.police:
                p.draw(self.screen, camx, camy)
            self.tiremarks.draw(self.screen, camx, camy)
            if self.nitro.active:
                self.nitro.draw(self.screen, self.player.angle)
            hit = self.player.draw(self.screen, camx, camy)
            pygame.draw.polygon(self.screen, (57, 255, 20), [(x - camx, y - camy) for x, y in hit], 2)
            hp_txt = self.font.render(f"HP: {self.player.hp}", True, (0, 0, 0))
            sp_txt = self.font.render(f"Speed: {int(eff_speed)}", True, (0, 0, 0))
            dist_txt = self.font.render(f"Distance: {dist_m} m", True, (0, 0, 0))
            elapsed = pygame.time.get_ticks() - self.start_time
            mins = elapsed // 60000
            secs = (elapsed // 1000) % 60
            time_txt = self.font.render(f"Time: {mins:02}:{secs:02}", True, (0, 0, 0))
            status_txt = self.font.render(f"Nitro: {self.nitro_count} | Police: {len([p for p in self.police if p.hp > 0])}", True, (0, 0, 255))
            self.screen.blit(hp_txt, (20, 20))
            self.screen.blit(sp_txt, (20, SCREEN_HEIGHT - sp_txt.get_height() - 20))
            self.screen.blit(dist_txt, (20, SCREEN_HEIGHT - sp_txt.get_height() - 80))
            self.screen.blit(time_txt, time_txt.get_rect(center=(SCREEN_WIDTH // 2, 20)))
            self.screen.blit(status_txt, (SCREEN_WIDTH - status_txt.get_width() - 20, SCREEN_HEIGHT - status_txt.get_height() - 20))
            pygame.display.update()
            if self.player.hp <= 0:
                t = elapsed // 1000
                avg = dist_m / t if t > 0 else 0
                self.stats.save(dist_m, t, avg, 3 - self.nitro_count, len(self.police))
                self.stats.plot()
                self.game_over()

if __name__ == "__main__":
    Game().run()
