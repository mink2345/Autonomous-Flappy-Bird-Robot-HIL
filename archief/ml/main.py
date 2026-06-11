import pygame
import neat
import os
import random
import pickle

pygame.init()

# ==============================================================================
# --- INSTELLINGEN & TURBO MODE ---
# ==============================================================================
TEKEN_SCHERM = False  # False = Maximale Snelheid (Headless)
WIN_WIDTH = 518
WIN_HEIGHT = 696
FPS = 0  # 0 is onbegrensd

CYAAN = (0, 200, 255)
GEEL = (255, 204, 0)
GROEN = (0, 200, 0)
WIT = (255, 255, 255)

if TEKEN_SCHERM:
    STAT_FONT = pygame.font.SysFont("comicsans", 30)


# ==============================================================================
# --- CLASSES ---
# ==============================================================================
class Vogel:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vel = 0
        self.tick_count = 0
        self.zwaartekracht = 1.5  # Standaard zwaartekracht

    def jump(self):
        self.vel = -9.5
        self.tick_count = 0

    def move(self):
        self.tick_count += 1

        # Realistische val-formule
        displacement = self.vel * self.tick_count + self.zwaartekracht * self.tick_count ** 2

        if displacement >= 16:
            displacement = 16
        if displacement < 0:
            displacement -= 2

        self.y = self.y + displacement

    def draw(self, win):
        pygame.draw.circle(win, GEEL, (int(self.x), int(self.y)), 15)

    def get_rect(self):
        return pygame.Rect(self.x - 15, self.y - 15, 30, 30)


class Buis:
    VEL = 5

    def __init__(self, x):
        self.x = x
        self.height = 0
        self.top = 0
        self.bottom = 0
        self.passed = False

        # DOMAIN RANDOMIZATION: Het gat is elke keer anders (tussen 125 en 155)
        self.gap = random.randrange(125, 155)
        self.set_height()

    def set_height(self):
        self.height = random.randrange(50, WIN_HEIGHT - self.gap - 100)
        self.top = self.height
        self.bottom = self.height + self.gap

    def move(self):
        self.x -= self.VEL

    def draw(self, win):
        pygame.draw.rect(win, GROEN, (self.x, 0, 50, self.top))
        pygame.draw.rect(win, GROEN, (self.x, self.bottom, 50, WIN_HEIGHT - self.bottom))

    def collide(self, vogel):
        vogel_rect = vogel.get_rect()
        top_rect = pygame.Rect(self.x, 0, 50, self.top)
        bottom_rect = pygame.Rect(self.x, self.bottom, 50, WIN_HEIGHT - self.bottom)

        if vogel_rect.colliderect(top_rect) or vogel_rect.colliderect(bottom_rect):
            return True
        return False


# ==============================================================================
# --- DE AI TRAINING LOOP ---
# ==============================================================================
def main(genomes, config):
    nets = []
    ge = []
    vogels = []

    for _, g in genomes:
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        vogels.append(Vogel(150, 300))
        g.fitness = 0
        ge.append(g)

    buizen = [Buis(500)]

    if TEKEN_SCHERM:
        win = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))

    clock = pygame.time.Clock()
    score = 0

    run = True
    while run and len(vogels) > 0:
        clock.tick(FPS)

        # Event pump is nodig om te voorkomen dat Pygame vastloopt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
                quit()

        pipe_ind = 0
        if len(vogels) > 0:
            if len(buizen) > 1 and vogels[0].x > buizen[0].x + 50:
                pipe_ind = 1

        for x, vogel in enumerate(vogels):
            vogel.move()
            ge[x].fitness += 0.1

            afstand_tot_plafond = abs(vogel.y - buizen[pipe_ind].height)
            afstand_tot_vloer = abs(vogel.y - buizen[pipe_ind].bottom)

            # DOMAIN RANDOMIZATION: Sensor ruis toevoegen (-2 tot +2 pixels)
            # Dit maakt het brein immuun voor kleine webcam-foutjes straks!
            ruis_y = vogel.y + random.uniform(-2, 2)
            ruis_plafond = afstand_tot_plafond + random.uniform(-2, 2)
            ruis_vloer = afstand_tot_vloer + random.uniform(-2, 2)

            output = nets[x].activate((ruis_y, ruis_plafond, ruis_vloer))

            if output[0] > 0.5:
                vogel.jump()

        rem = []
        add_pipe = False
        for buis in buizen:
            for x, vogel in enumerate(vogels):
                if buis.collide(vogel) or vogel.y < 0 or vogel.y > WIN_HEIGHT:
                    ge[x].fitness -= 1
                    vogels.pop(x)
                    nets.pop(x)
                    ge.pop(x)

                if not buis.passed and buis.x < vogel.x:
                    buis.passed = True
                    add_pipe = True

            buis.move()
            if buis.x + 50 < 0:
                rem.append(buis)

        if add_pipe:
            score += 1
            for g in ge:
                g.fitness += 5
            buizen.append(Buis(400))

            # HARDE STOP: 1000 punten is het bewijs van onsterfelijkheid
            if score > 1000:
                run = False
                break

        for r in rem:
            buizen.remove(r)

        if TEKEN_SCHERM:
            win.fill(CYAAN)
            for buis in buizen:
                buis.draw(win)
            for vogel in vogels:
                vogel.draw(win)

            text = STAT_FONT.render("Score: " + str(score), 1, WIT)
            win.blit(text, (WIN_WIDTH - 10 - text.get_width(), 10))
            text = STAT_FONT.render("Levend: " + str(len(vogels)), 1, WIT)
            win.blit(text, (10, 10))
            pygame.display.update()


# ==============================================================================
# --- NEAT SETUP ---
# ==============================================================================
def run_neat(config_path):
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                config_path)

    p = neat.Population(config)
    p.add_reporter(neat.StdOutReporter(True))
    p.add_reporter(neat.StatisticsReporter())

    # Checkpoint is nu elke 50 generaties
    p.add_reporter(neat.Checkpointer(100))

    print("--- START TURBO & CHAOS TRAINING ---")
    winner = p.run(main, 2000)

    print('\n*** TRAINING VOLTOOID! ***')
    with open("beste_brein.pkl", "wb") as f:
        pickle.dump(winner, f)
    print('Het ultieme robot-brein is opgeslagen als "beste_brein.pkl".')


if __name__ == '__main__':
    local_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(local_dir, 'config-feedforward.txt')
    run_neat(config_path)