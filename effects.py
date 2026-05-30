import math
import random
import pygame

moonDust = (200, 200, 215)
portalJumpColor = (120, 220, 120)
portalGravityColor = (180, 120, 240)
portalJetpackColor = (250, 180, 70)

modeColors = {
    "jump": (120, 220, 120),
    "gravity": (180, 120, 240),
    "jetpack": (250, 180, 70),
}

class ParticleSystem:
    def __init__(self):
        self.parts = []

    # update all particles and also remove all that thier lives have expired
    # all particles are eaffected by gravity
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
            #glow
            if p.get("glow"):
                glow_surf = pygame.Surface((radius * 6, radius * 6), pygame.SRCALPHA)
                glow_alpha = int(60 * t)
                r, g, b = p["color"][0], p["color"][1], p["color"][2]
                pygame.draw.circle(glow_surf, (r, g, b, glow_alpha),
                                   (radius * 3, radius * 3), radius * 3)
                surf.blit(glow_surf, (sx - radius * 3, sy - radius * 3))
            pygame.draw.circle(surf, p["color"], (sx, sy), radius)

    # initialize a new partical with the given attributes and adds it to the lsit
    def spawn(self, x, y, vx, vy, life, color, radius=5, gravity=0.0, glow=False):
        self.parts.append({
            "x": x, "y": y, "vx": vx, "vy": vy,
            "life": life, "maxLife": life,
            "color": color, "radius": radius, "gravity": gravity,
            "glow": glow,
        })
    # trail effect
    def trail(self, x, y, color=moonDust, mode=None):
        if mode and mode in modeColors:
            mc = modeColors[mode]
            # blend moon dust with mode color
            color = (
                (moonDust[0] + mc[0]) // 2,
                (moonDust[1] + mc[1]) // 2,
                (moonDust[2] + mc[2]) // 2,
            )
        self.spawn(
            x + random.uniform(-3, 3), y + random.uniform(-3, 3),
            random.uniform(-0.4, 0.4), random.uniform(-0.3, 0.3),
            18, color, radius=4, glow=True,
        )

    # landing effect
    def landDust(self, x, y):
        for _ in range(12):
            ang = random.uniform(math.pi, 2 * math.pi)
            spd = random.uniform(2.0, 4.5)
            self.spawn(
                x, y,
                math.cos(ang) * spd, math.sin(ang) * spd * 0.5,
                30, moonDust, radius=5, gravity=0.15, glow=False,
            )

    # jetpack main flame effect (enhanced)
    def jetpackFlame(self, x, y, dirY=1):
        for _ in range(4):
            color = random.choice([(255, 180, 60), (255, 120, 30), (255, 220, 80), (255, 255, 140), (200, 80, 20)])
            self.spawn(
                x + random.uniform(-6, 6), y,
                random.uniform(-0.6, 0.6),
                dirY * random.uniform(4.0, 7.5),
                18, color, radius=random.randint(5, 9), glow=True,
            )
        # inner hot core — brighter white/yellow
        self.spawn(
            x + random.uniform(-2, 2), y,
            random.uniform(-0.2, 0.2),
            dirY * random.uniform(3.0, 5.5),
            10, (255, 255, 200), radius=4, glow=True,
        )

    # side vent sparks — small jets from the sides of the pack
    def jetpackSideVents(self, x, y):
        for side in (-1, 1):
            if random.random() < 0.5:
                color = random.choice([(255, 160, 40), (255, 220, 100), (200, 120, 20)])
                self.spawn(
                    x + side * random.uniform(8, 14), y + random.uniform(-4, 4),
                    side * random.uniform(1.5, 3.5), random.uniform(-0.5, 0.5),
                    12, color, radius=random.randint(2, 4), glow=True,
                )

    # energy aura — soft orange halo around the player while thrusting
    def jetpackAura(self, x, y):
        if random.random() < 0.35:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(12, 22)
            color = (255, random.randint(120, 200), 20)
            self.spawn(
                x + math.cos(angle) * dist, y + math.sin(angle) * dist,
                math.cos(angle) * 0.3, math.sin(angle) * 0.3,
                14, color, radius=random.randint(2, 5), gravity=0.0, glow=True,
            )

    # ignition burst — shockwave of sparks on thrust-start
    def jetpackIgnition(self, x, y):
        for i in range(24):
            ang = (i / 24) * 2 * math.pi
            spd = random.uniform(3.0, 7.0)
            color = random.choice([(255, 200, 60), (255, 140, 30), (255, 255, 160), (255, 80, 20)])
            self.spawn(
                x + math.cos(ang) * 6, y + math.sin(ang) * 6,
                math.cos(ang) * spd, math.sin(ang) * spd * 0.7,
                random.uniform(18, 32), color,
                radius=random.randint(3, 6), gravity=0.05, glow=True,
            )

    # death effect
    def deathBurst(self, x, y):
        for _ in range(18):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2.5, 9.0)
            self.spawn(
                x, y,
                math.cos(ang) * spd, math.sin(ang) * spd,
                random.uniform(35, 65), (255, 0, 0),
                radius=random.randint(3, 8), gravity=0.2, glow=True,
            )

    # portal effect
    def portalSparks(self, x, y, color):
        for _ in range(16):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(1.5, 5.0)
            self.spawn(
                x + random.uniform(-8, 8), y + random.uniform(-8, 8),
                math.cos(ang) * spd, math.sin(ang) * spd,
                30, color, radius=5, glow=True,
            )

    #fireworks effect
    def winFireworks(self, x, y):
        colors = [
            (255, 220, 50), (100, 255, 100), (80, 180, 255),
            (255, 100, 180), (255, 255, 255), portalGravityColor,
        ]
        color = random.choice(colors)
        for _ in range(30):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(3.0, 10.0)
            self.spawn(
                x, y,
                math.cos(ang) * spd, math.sin(ang) * spd,
                random.uniform(40, 80), color,
                radius=random.randint(3, 7), gravity=0.1, glow=True,
            )


    #gravity flip effect
    def gravityFlipBurst(self, x, y, flippingUp):
        # inner tight ring
        for i in range(20):
            ang = (i / 20) * 2 * math.pi
            spd = random.uniform(3.0, 6.5)
            color = random.choice([
                (180, 120, 240), (220, 160, 255), (140, 80, 200), (255, 200, 255)
            ])
            self.spawn(
                x + math.cos(ang) * 8, y + math.sin(ang) * 8,
                math.cos(ang) * spd, math.sin(ang) * spd * 0.6,
                random.uniform(28, 45), color,
                radius=random.randint(3, 6), gravity=0.0, glow=True,
            )
        # directional streaks up or down based on flip direction
        dirY = -1 if flippingUp else 1
        for _ in range(10):
            color = random.choice([(255, 220, 255), (200, 150, 255), (240, 240, 255)])
            self.spawn(
                x + random.uniform(-12, 12), y,
                random.uniform(-1.5, 1.5),
                dirY * random.uniform(5.0, 10.0),
                random.uniform(22, 38), color,
                radius=random.randint(2, 5), gravity=0.0, glow=True,
            )
    #spike glow
    def spikeGlow(self, x, y):
        self.spawn(
            x + random.uniform(-4, 4), y + random.uniform(-4, 4),
            random.uniform(-0.1, 0.1), random.uniform(-0.2, 0.0),
            20, (255, 80, 60), radius=3, gravity=0.0, glow=True,
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

class ScreenFlash:
    def __init__(self):
        self.timer = 0.0
        self.maxTimer = 0.0
        self.color = (255, 255, 255)

    def trigger(self, color, duration=18.0):
        self.color = color
        self.timer = duration
        self.maxTimer = duration

    def update(self, dt):
        self.timer = max(0.0, self.timer - dt)

    def draw(self, surf):
        if self.timer <= 0:
            return
        t = self.timer / self.maxTimer
        alpha = int(160 * t)
        overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        r, g, b = self.color
        overlay.fill((r, g, b, alpha))
        surf.blit(overlay, (0, 0))

class PortalGlow:
    def __init__(self):
        self.timer = 0.0

    def update(self, dt):
        self.timer += dt

    def draw(self, surf, cx, cy, color, camX):
        # pulsing radius
        pulse = math.sin(self.timer * 0.12) * 0.3 + 1.0
        radius = int(30 * pulse)
        sx = int(cx - camX)
        sy = int(cy)
        glow_surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        r, g, b = color
        for layer, a in [(radius * 2, 25), (int(radius * 1.3), 40), (radius, 60)]:
            pygame.draw.circle(glow_surf, (r, g, b, a),
                               (radius * 2, radius * 2), layer)
        surf.blit(glow_surf, (sx - radius * 2, sy - radius * 2))

class StarField:
    def __init__(self, count=120):
        self.stars = []
        for _ in range(count):
            self.stars.append({
                "x": random.uniform(0, 1280),
                "y": random.uniform(0, 720),
                "r": random.randint(1, 2),
                "speed": random.uniform(0.05, 0.25),  # parallax factor
                "bright": random.randint(140, 255),
            })

    def draw(self, surf, camX):
        for s in self.stars:
            sx = int((s["x"] - camX * s["speed"]) % 1280)
            sy = int(s["y"])
            b = s["bright"]
            pygame.draw.circle(surf, (b, b, b), (sx, sy), s["r"])

class GravityFlipEffect:
    def __init__(self):
        self.rings = []
        self.flip_dir = 1

    def trigger(self, x, y, flippingUp):
        self.flip_dir = -1 if flippingUp else 1
        # spawn 3 rings with staggered delays
        for delay in (0, 6, 12):
            self.rings.append({
                "wx": x, "wy": y,
                "radius": 5.0,
                "max_radius": 120.0,
                "life": 35.0 + delay,
                "max_life": 35.0,
                "delay": float(delay),
            })

    def update(self, dt):
        for i in range(len(self.rings) - 1, -1, -1):
            r = self.rings[i]
            r["delay"] -= dt
            if r["delay"] > 0:
                continue
            r["life"] -= dt
            # grow ring outward
            r["radius"] += (r["max_radius"] / r["max_life"]) * dt * 1.8
            if r["life"] <= 0:
                self.rings.pop(i)

    def draw(self, surf, camX):
        for r in self.rings:
            if r["delay"] > 0:
                continue
            t = max(0.0, r["life"] / r["max_life"])
            alpha = int(200 * t)
            radius = max(1, int(r["radius"]))
            sx = int(r["wx"] - camX)
            sy = int(r["wy"])
            # draw ring as a circle outline on an alpha surface
            ring_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            # purple-white tones — clamp all channels to [0,255] to avoid ValueError
            col = (
                min(255, max(0, int(180 + 75 * (1 - t)))),
                min(255, max(0, int(120 * t))),
                min(255, max(0, int(240 * t + 15 * (1 - t)))),
                min(255, max(0, alpha)),
            )
            pygame.draw.circle(ring_surf, col,
                               (radius + 2, radius + 2), radius, max(1, int(3 * t + 1)))
            surf.blit(ring_surf, (sx - radius - 2, sy - radius - 2))
