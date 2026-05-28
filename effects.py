import math
import random
import pygame

moonDust = (200, 200, 215)
portalJumpColor = (120, 220, 120)
portalGravityColor = (180, 120, 240)
portalJetpackColor = (250, 180, 70)


class ParticleSystem:
    def __init__(self):
        self.parts = []

    # update all particles and also remove all that thier lives have expired
    def update(self, dt):
        for i in range(len(self.parts) - 1, -1, -1):
            p = self.parts[i]
            p["vy"] += p["gravity"] * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
            if p["life"] <= 0:
                self.parts.pop(i)

    # draw the actual particles using their attributes, size is base on remaining life
    def draw(self, surf, camX):
        for p in self.parts:
            t = max(0.0, p["life"] / p["maxLife"])
            radius = max(1, int(p["radius"] * t))
            sx, sy = int(p["x"] - camX), int(p["y"])
            pygame.draw.circle(surf, p["color"], (sx, sy), radius)

    # initialize a new partical with the given attributes and adds it to the lsit
    def spawn(self, x, y, vx, vy, life, color, radius=5, gravity=0.0):
        self.parts.append({
            "x": x, "y": y, "vx": vx, "vy": vy,
            "life": life, "maxLife": life,
            "color": color, "radius": radius, "gravity": gravity,
        })

    # trail effect
    def trail(self, x, y, color=moonDust):
        self.spawn(
            x + random.uniform(-3, 3), y + random.uniform(-3, 3),
            random.uniform(-0.4, 0.4), random.uniform(-0.3, 0.3),
            18, color, radius=4,
        )

    # ladning effect
    def landDust(self, x, y):
        for _ in range(8):
            ang = random.uniform(math.pi, 2 * math.pi)
            spd = random.uniform(1.5, 3.5)
            self.spawn(
                x, y,
                math.cos(ang) * spd, math.sin(ang) * spd * 0.5,
                25, moonDust, radius=5, gravity=0.15,
            )

    # jetpack effect
    def jetpackFlame(self, x, y, dirY=1):
        for _ in range(2):
            color = random.choice([(255, 180, 60), (255, 120, 30), (255, 220, 80)])
            self.spawn(
                x + random.uniform(-4, 4), y,
                random.uniform(-0.6, 0.6),
                dirY * random.uniform(3.0, 5.0),
                14, color, radius=6,
            )

    # death effect
    def deathBurst(self, x, y):
        colors = [portalJumpColor, portalGravityColor, portalJetpackColor, moonDust]
        for color in colors:
            for _ in range(14):
                ang = random.uniform(0, 2 * math.pi)
                spd = random.uniform(2.0, 7.0)
                self.spawn(
                    x, y,
                    math.cos(ang) * spd, math.sin(ang) * spd,
                    random.uniform(30, 55), color,
                    radius=random.randint(3, 7), gravity=0.2,
                )

    # portal effect
    def portalSparks(self, x, y, color):
        for _ in range(6):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(1.0, 3.0)
            self.spawn(
                x, y,
                math.cos(ang) * spd, math.sin(ang) * spd,
                20, color, radius=4,
            )


class Camera:
    def __init__(self):
        self.x = 0.0
        self.trauma = 0.0

    def addShake(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt):
        self.trauma = max(0.0, self.trauma - 0.04 * dt)

    def shakeOffset(self):
        s = self.trauma * self.trauma * 18
        return random.uniform(-s, s), random.uniform(-s, s)
