import pygame
import random
import auxiliary
from brain import Brain
from dna import BrainDNA, DNA
from math import cos, pi, sin, atan2, fmod
import logging
import numpy as np
import time

logger = logging.getLogger(__name__)


class CreatureIdGenerator:
    def __init__(self):
        self.creature_id_inc_counter = 0

    def get_next_id(self):
        self.creature_id_inc_counter += 1
        return self.creature_id_inc_counter


# create singleton creature id generator
creature_id_generator = CreatureIdGenerator()


class World:
    def __init__(self, width: int = 640, height: int = 480, background: tuple = (0, 0, 0),
                 creatures: list = [], edibles: list = [], food_spawn_interval: int = 1000,
                 creature_spawn_interval: int = 10000, random_spawning: bool = True, max_creatures: int = 100):
        pygame.init()
        self.size = self.width, self.height = width, height
        self.background = background
        self.screen = pygame.display.set_mode(self.size)
        self.clock = pygame.time.Clock()
        self.random_spawning = random_spawning
        self.max_creatures = max_creatures

        self.food_spawn_counter = 0
        self.food_spawn_interval = food_spawn_interval
        self.edibles = edibles

        self.creature_spawn_counter = 0
        self.creature_spawn_interval = creature_spawn_interval
        self.creatures = creatures

        self.creature_total = len(creatures)

    def __getstate__(self):
        state = self.__dict__.copy()
        # Remove the unpicklable entries.
        del state['screen']
        del state['clock']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.clock = pygame.time.Clock()

    def add_creature(self, creature):
        # sanity check so the computer doesn't crash with bad params
        if len(self.creatures) > self.max_creatures:
            return
        self.creatures.append(creature)  # comment back
        self.creature_total += 1

    def add_edible(self, food):
        self.edibles.append(food)

    def generate_random_creature(self):
        return BrainCreature(x=random.uniform(0, self.width), y=random.uniform(0, self.height), dna=DNA(),
                             brain_dna=BrainDNA(), name='Creature ' + str(creature_id_generator.get_next_id()))

    def remove_creature(self, creature):
        creature.log("died")
        self.creatures.remove(creature)
        # self.add_edible(Food(creature.x, creature.y, value=creature.size * 2, color=creature.color))

    def remove_edible(self, edible):
        self.edibles.remove(edible)

    def tick(self):
        dt = self.clock.tick(60)

        self.update_creatures(dt)
        self.update_edibles(dt)

        self.draw()
        pygame.display.flip()

    def draw(self):
        self.screen.fill(self.background)
        for creature in self.creatures:
            creature.draw(self.screen)
        for food in self.edibles:
            food.draw(self.screen)

        font = pygame.font.Font('freesansbold.ttf', 14)
        text = font.render(f"# of creatures: {len(self.creatures)}", True, (255, 255, 255), (0, 0, 0))
        text_rect = text.get_rect()
        text_rect.center = (100, 50)
        self.screen.blit(text, text_rect)

        current_text_bottom = 50 + text.get_size()[1]

        al_text = font.render(f"avg lifespan: {self.get_active_lifespan()}", True, (255, 255, 255), (0, 0, 0))
        al_text_rect = al_text.get_rect()
        al_text_rect.center = (100, current_text_bottom)
        self.screen.blit(al_text, al_text_rect)
        current_text_bottom += al_text.get_size()[1]

        # max_text = font.render(f"max lifespan: {self.get_max_lifespan()}", True, (255, 255, 255), (0, 0, 0))
        # max_text_rect = max_text.get_rect()
        # max_text_rect.center = (100, current_text_bottom)
        # self.screen.blit(max_text, max_text_rect)
        # current_text_bottom += max_text.get_size()[1]
        #
        # median_text = font.render(f"median lifespan: {self.get_median_lifespan()}", True, (255, 255, 255), (0, 0, 0))
        # median_text_rect = median_text.get_rect()
        # median_text_rect.center = (100, current_text_bottom)
        # self.screen.blit(median_text, median_text_rect)
        # current_text_bottom += median_text.get_size()[1]

    # selecting elite creatures and breeding them to add during creature spawn
    # n: number of elite creatures selected
    # k: number of children produced
    def elite_reproduction(self, n: int, k: int):
        m = min(n, self.creature_total)
        elite = sorted([(creature, creature.food_consumed) for creature in self.creatures],
                       key=lambda x: x[1], reverse=True)[:m]
        # sexual
        """
        elite_children = []
        for i in range(k):
            parents = random.sample(range(m), 2)
            elite_children.append(elite[parents[0]][0].sexual_multiply(elite[parents[1]][0]))
        """
        # asexual
        elite_children = [parent[0].asexual_multiply() for parent in elite]
        return elite_children

    def update_creatures(self, dt):
        if self.random_spawning:
            self.creature_spawn_counter += dt
            if self.creature_spawn_counter > self.creature_spawn_interval:
                elite_children = self.elite_reproduction(5, 5)
                for child in elite_children:
                    self.add_creature(child)
                self.creature_spawn_counter = 0

        for creature in self.creatures:
            creature.tick(self, dt)

            # random death:
            # if random.random() <= creature.death_rate * dt / 1000:
            #     self.remove_creature(creature)

            # elif creature.health > 0:
            if creature.health <= 0:
                self.remove_creature(creature)

    def update_edibles(self, dt):
        self.food_spawn_counter += dt
        if self.food_spawn_counter > self.food_spawn_interval:
            self.add_edible(Food(random.uniform(0, self.width), random.uniform(0, self.height)))
            self.food_spawn_counter = 0

    def get_active_lifespan(self):
        sum = 0
        count = 0
        for creature in self.creatures:
            sum += creature.get_lifespan()
            count += 1
        if count == 0:
            return 0
        return round(sum / count)

    def get_max_lifespan(self):
        max = 0
        for creature in self.creatures:
            if creature.get_lifespan() > max:
                max = creature.get_lifespan()
        return round(max)

    def get_median_lifespan(self):
        elems = []
        for creature in self.creatures:
            elems.append(round(creature.get_lifespan()))
        elems.sort()
        return elems[int(len(self.creatures) / 2)]


class Object:
    def __init__(self, x: float, y: float, direction: float = 0.0, name: str = 'object'):
        self.x = x
        self.y = y
        self.direction = direction
        self.name = name

    def log(self, info: str):
        # pass
        logger.debug(self.name + ": " + info)


class SquareObject(Object):
    def __init__(self, x: float, y: float, size: float, color: pygame.Color, direction: float = 0.0,
                 name: str = 'object'):
        super().__init__(x, y, direction, name=name)
        self.rect = pygame.Rect(x + size // 2, y + size // 2, size, size)
        self.color = color
        self.size = size

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.color, self.rect)


class Creature(SquareObject):
    # base_health = 300
    base_health = 2 * 10 ** 4
    multiply_delay = 4 * 10 ** 3
    # multiply_delay = 2 * (10 ** 4)
    death_rate = 0.01  # possibility of random death
    direction_change_delay = 500
    min_multiply_health = 1000

    def __init__(self, x: float, y: float, size: float, speed: float, color: pygame.Color,
                 direction: float = 0.0, vision_radius: int = 100, name: str = 'object_x',
                 multiply_chance=(0.25, 0.05), health: int = None):
        super().__init__(x, y, size, color, direction, name=name)

        self.log("creature created")
        self.speed = speed
        # self.health = self.base_health
        if health is None:
            health = self.base_health
        self.health = health
        self.log(f"health init: {self.health}")
        self.multiply_chance = multiply_chance

        self.multiply_cd = self.multiply_delay
        self.direction_change_cd = self.direction_change_delay

        # self.vision_radius = 100
        self.vision_radius = vision_radius
        self.log(f"vision radius: {self.vision_radius}")
        # self.vision_radius = 300
        self.detection_chance = 1000
        self.vision_rect = pygame.Rect(self.x + self.vision_radius, self.y + self.vision_radius,
                                       self.vision_radius * 2, self.vision_radius * 2)

        # auxiliary attributes
        self.dx = 0.0
        self.dy = 0.0
        self.x_acc = 0.0
        self.y_acc = 0.0

        self.lifespan_start = time.time()

        self.food_consumed = 0

    def __getstate__(self):
        state = self.__dict__.copy()
        # Remove the unpicklable entries.
        state['lifespan_start'] = time.time() - float(state['lifespan_start'])
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.lifespan_start = time.time() - self.lifespan_start

    def can_change_direction(self):
        return self.direction_change_cd <= 0

    def can_multiply(self) -> bool:
        return self.multiply_cd <= 0 and self.health > self.min_multiply_health

    """Get lifespan of creature in seconds"""

    def get_lifespan(self):
        return time.time() - self.lifespan_start

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        color = pygame.Color(255, 255, 255)

        pygame.draw.rect(surface, self.color, self.vision_rect, 1)

        a = pygame.math.Vector2(self.x, self.y)
        b = pygame.math.Vector2(self.x - self.size * cos(self.direction),
                                self.y - self.size * sin(self.direction))
        pygame.draw.line(surface, color, a, b)
        font = pygame.font.Font('freesansbold.ttf', 12)
        if self.can_multiply():
            text = font.render("fertile", True, (0, 255, 0), (0, 0, 0))
        else:
            text = font.render(str(self.multiply_cd // 1000), True, (255, 0, 0), (0, 0, 0))
        text_rect = text.get_rect()
        text_rect.center = (self.x, self.y)
        surface.blit(text, text_rect)

        # print health
        health_ratio = self.health / self.base_health
        if health_ratio > 1:
            health_ratio = 1
        if health_ratio < 0:
            health_ratio = 0
        r = int(255 - (255 * health_ratio))
        g = int(255 * health_ratio)
        b = 0
        health_text = font.render(f"h: {round(health_ratio * 100, 2)}%", True, (r, g, b), (0, 0, 0))
        health_text_rect = health_text.get_rect()
        health_text_rect.center = (self.x, self.y + 15)
        surface.blit(health_text, health_text_rect)

        food_text = font.render(f"f: {self.food_consumed}", True, (255, 255, 255), (0, 0, 0))
        food_text_rect = food_text.get_rect()
        food_text_rect.center = (self.x, self.y + 30)
        surface.blit(food_text, food_text_rect)

        # disposition output

        """
        dx_text = font.render(f"dx: {round(self.dx, 2)}", True, (255, 255, 255), (0, 0, 0))
        dx_text_rect = dx_text.get_rect()
        dx_text_rect.center = (self.x, self.y + 30)
        surface.blit(dx_text, dx_text_rect)

        dy_text = font.render(f"dy: {round(self.dy, 2)}", True, (255, 255, 255), (0, 0, 0))
        dy_text_rect = dx_text.get_rect()
        dy_text_rect.center = (self.x, self.y + 45)
        surface.blit(dy_text, dy_text_rect)
        """

        # position output
        """
        x_text = font.render(f"x: {round(self.x, 2)}", True, (255, 255, 255), (0, 0, 0))
        x_text_rect = x_text.get_rect()
        x_text_rect.center = (self.x, self.y + 60)
        surface.blit(x_text, x_text_rect)

        y_text = font.render(f"y: {round(self.y, 2)}", True, (255, 255, 255), (0, 0, 0))
        y_text_rect = y_text.get_rect()
        y_text_rect.center = (self.x, self.y + 75)
        surface.blit(y_text, y_text_rect)
        """

    def find_target(self, world: World, dt) -> SquareObject:
        min_food_dist = float('inf')  # just some number larger than the world
        closest_food = None
        for edible in world.edibles:
            if self.vision_rect.colliderect(edible.rect):
                dist = ((self.x - edible.x) ** 2 + (self.y - edible.y) ** 2) ** 0.5
                if dist < min_food_dist:
                    min_food_dist = dist
                    closest_food = edible
        if closest_food:
            return closest_food

        closest_creature = None
        min_creature_dist = float('inf')  # just some number larger than the world
        for creature in world.creatures:
            # if creature != self and self.rect.colliderect(creature.rect):
            if creature != self and self.vision_rect.colliderect(creature.rect):
                dist = ((self.x - creature.x) ** 2 + (self.y - creature.y) ** 2) ** 0.5
                if dist < min_creature_dist:
                    closest_creature = creature
                    min_creature_dist = dist
                # if random.random() < self.detection_chance * dt / 1000:
        #            return creature

        if closest_creature:
            return closest_creature

        return None

        # if min_food_dist < min_creature_dist:
        #     return closest_food
        # elif creature:
        #     return creature
        # else:
        #     return None

    # def find_target(self, world: World, dt) -> SquareObject:
    #     for edible in world.edibles:
    #         if self.vision_rect.colliderect(edible.rect):
    #             return edible
    #
    #     for creature in world.creatures:
    #         # if creature != self and self.rect.colliderect(creature.rect):
    #         if creature != self and self.vision_rect.colliderect(creature.rect):
    #             # if random.random() < self.detection_chance * dt / 1000:
    #             return creature
    #
    #     return None

    def multiply(self) -> 'Creature':
        self.multiply_cd = self.multiply_delay
        size = random.uniform(self.size * 0.9, self.size * 1.1)
        return Creature(self.x, self.y, size, speed=random.uniform(self.speed * 0.9, self.speed * 1.1),
                        color=self.color, direction=fmod(self.direction + pi, 2 * pi), name=self.name,
                        multiply_chance=self.multiply_chance)

    def sexual_multiply(self, partner):
        return self.multiply()

    def asexual_multiply(self):
        return self.multiply()

    def update_health(self, dt):
        # self.health -= (self.speed ** 1.1) * (self.size ** 1.1) * dt * 0.0005
        # self.health -= (self.speed ** 1.1) * (self.size ** 1.1) * dt * 0.000005
        # self.health -= ((self.size ** 3) * (self.speed ** 2) + self.vision_radius) * dt * 0.0000005  # primer-like
        self.health -= ((max(8.0, self.size / 2) ** 3) * (self.speed ** 2) + self.vision_radius) * dt * 0.00005
        # print(f"delta health: {(self.size ** 3) * (self.speed ** 2) * dt }")

    def update_direction_change_cd(self, dt):
        self.direction_change_cd = max(0, self.direction_change_cd - dt)

    def update_multiply_cd(self, dt):
        self.multiply_cd = max(0, self.multiply_cd - dt)

    def update_rect(self, rect: pygame.Rect):
        self.rect = rect
        self.x = rect.centerx
        self.y = rect.centery
        self.vision_rect.center = rect.center

    def creature_interaction(self, world: World, dt):
        if self.can_multiply():
            # creature interaction
            creatures_to_add = []
            for creature in world.creatures:
                if creature != self and creature.can_multiply() and self.rect.colliderect(creature.rect):

                    # sexual reproduction
                    # if random.random() < self.multiply_chance[0] * dt / 100:
                    if random.random() < 0.3:
                        child = self.sexual_multiply(creature)
                        creatures_to_add.append(child)
                        # world.add_creature(child)

                    # bigger creatures can it smaller creatures if their size is at least 20% the size of the smaller one
                    # ? add successful hunt probability?
                    # if (self.size ** 2) >= 1.4 * (creature.size ** 2):
                    #     self.health += 0.0001 * creature.health
                    #     world.remove_creature(creature)
            for creature in creatures_to_add:
                world.add_creature(creature)

            # asexual reproduction
            if random.random() < self.multiply_chance[1] * dt / 1000:
                world.add_creature(self.asexual_multiply())

    def get_velocity(self, dt):

        self.dx = self.speed / 50 * cos(self.direction) * dt
        self.dy = self.speed / 50 * sin(self.direction) * dt
        vel_x = self.dx + self.x_acc
        vel_y = self.dy + self.y_acc
        # self.log(f"velocity: x: {vel_x}, y: {vel_y}")

        self.x_acc = vel_x - int(vel_x)
        vel_x = int(vel_x)

        self.y_acc = vel_y - int(vel_y)
        vel_y = int(vel_y)

        return vel_x, vel_y

    def do_movement(self, world: World, dt: float):
        direction_changed = False
        if self.can_change_direction():
            target = self.find_target(world, dt)
            if target:
                self.log("found target %s" % target.name)
                if isinstance(target, Food) or (self.can_multiply() and target.can_multiply()):
                    self.direction = atan2(target.y - self.y, target.x - self.x)
                else:
                    self.direction = atan2(target.x - self.x, target.y - self.y)
                direction_changed = True

        vel_x, vel_y = self.get_velocity(dt)
        new_rect = self.rect.move(vel_x, vel_y)

        bounds = world.screen.get_rect()
        if not bounds.contains(new_rect):
            if self.can_change_direction():
                self.direction = fmod(self.direction + random.uniform(0, pi), (2 * pi))
                vel_x, vel_y = self.get_velocity(dt)
                new_rect = self.rect.move(vel_x, vel_y)
                direction_changed = True
            new_rect = new_rect.clamp(bounds)

        if direction_changed:
            self.direction_change_cd = self.direction_change_delay

        return new_rect

    def tick(self, world: World, dt: float):
        new_rect = self.do_movement(world, dt)

        for edible in world.edibles:
            if self.rect.colliderect(edible.rect):
                self.food_consumed += 1
                self.log(f"ate food with value: {edible.value}")
                self.health += edible.value
                world.remove_edible(edible)

        self.creature_interaction(world, dt)

        self.update_direction_change_cd(dt)
        self.update_multiply_cd(dt)
        self.update_health(dt)
        self.update_rect(new_rect)


class DnaCreature(Creature):
    min_size = 1.0
    max_size = 50.0
    min_speed = 1.0
    max_speed = 5.0
    min_a_multiply = 0
    max_a_multiply = 0.05
    min_s_multiply = 0
    max_s_multiply = 0.25

    min_vision_radius = 50.0
    max_vision_radius = 150.0

    def __init__(self, x: float, y: float, dna=DNA(), direction: float = 0.0, name: str = 'object', health: int = None):
        color = pygame.Color(int(dna.genes[0] * 255), int(dna.genes[1] * 255), int(dna.genes[2] * 255))
        speed = auxiliary.map(dna.genes[3], 0, 1, self.min_speed, self.max_speed)
        size = auxiliary.map(dna.genes[4], 0, 1, self.min_size, self.max_size)
        multiply_chance = (auxiliary.map(dna.genes[5], 0, 1, self.min_s_multiply, self.max_s_multiply),
                           auxiliary.map(dna.genes[5], 0, 1, self.max_a_multiply, self.min_a_multiply))
        vision_radius = auxiliary.map(dna.genes[6], 0, 1, size, self.max_vision_radius)
        super().__init__(x, y, size, speed, color, direction, vision_radius, name=name, multiply_chance=multiply_chance,
                         health=health)
        self.dna = dna

        # counter for food consumed

        self.log("creature created")
        self.log(f"health dna creature: {self.health}")

        # neural network parameters

    # reproduction comes with a cost

    def get_repro_dna(self, partner: 'DnaCreature' = None) -> DNA:
        if partner:
            dna = self.dna.crossover(partner.dna)
        else:
            dna = self.dna.copy()

        dna.mutation()
        return dna

    def asexual_multiply(self):
        child_health = self.health * 0.5
        self.health -= child_health
        self.multiply_cd = self.multiply_delay

        dna = self.get_repro_dna()

        self.log("produced child via asexual reproduction")
        return DnaCreature(self.x, self.y, dna=dna, direction=fmod(self.direction + pi, (2 * pi)), name="DnaCreature_" + str(creature_id_generator.get_next_id()),
                           health=child_health)

    def sexual_multiply(self, partner: 'DnaCreature') -> 'DnaCreature':
        self_donation = self.health * 0.25
        self.health -= self_donation
        partner_donation = partner.health * 0.25
        partner.health -= partner_donation
        self.multiply_cd = self.multiply_delay

        child_dna = self.get_repro_dna(partner)

        self.log("produced child with %s via sexual reproduction" % partner.name)

        return DnaCreature(self.x, self.y, dna=child_dna, direction=fmod((self.direction + pi), (2 * pi)),
                           name="DnaCreature_" + str(creature_id_generator.get_next_id()), health=self_donation + partner_donation)


class BrainCreature(DnaCreature):
    def __init__(self, x: float, y: float, dna: DNA = DNA(), brain_dna: DNA = BrainDNA(), direction: float = 0.0,
                 name: str = 'object', health: int = None):
        super().__init__(x, y, dna, direction, name, health=health)
        # objective function
        self.brain = Brain(brain_dna)

    def get_brain_repro_dna(self, partner: 'BrainCreature' = None) -> BrainDNA:
        if partner is None:
            dna = self.brain.dna.copy()
        else:
            dna = self.brain.dna.crossover(partner.brain.dna)

        dna.mutation()
        return dna

    def asexual_multiply(self):
        child_health = min(self.health * 0.5 + 1000, self.health)
        self.health -= child_health
        self.multiply_cd = self.multiply_delay
        # self.health -= 0.01 * self.health
        self.multiply_cd = self.multiply_delay

        dna = self.get_repro_dna()
        brain_dna = self.get_brain_repro_dna()

        return BrainCreature(self.x, self.y, dna=dna, brain_dna=brain_dna,
                             direction=fmod(self.direction + pi, (2 * pi)),
                             name="BrainCreature_" + str(creature_id_generator.get_next_id()), health=child_health)

    def sexual_multiply(self, partner: 'DnaCreature') -> 'DnaCreature':
        self_donation = min(self.health * 0.25 + 500, self.health)
        self.health -= self_donation
        partner_donation = min(self_donation, partner.health)
        partner.health -= partner_donation
        self.multiply_cd = self.multiply_delay

        dna = self.get_repro_dna(partner)
        brain_dna = self.get_brain_repro_dna(partner)

        return BrainCreature(self.x, self.y, dna=dna, brain_dna=brain_dna,
                             direction=fmod((self.direction + pi), (2 * pi)),
                             name="BrainCreature_" + str(creature_id_generator.get_next_id()), health=self_donation + partner_donation)

    def do_movement(self, world: World, dt: float):
        direction_changed = False
        if self.can_change_direction():
            target = self.find_target(world, dt)
            neuron_input = np.zeros(Brain.input_neurons)
            # neuron_input[3] = self.can_multiply()
            # neuron_input[6] = self.health
            # neuron_input[7] = self.multiply_cd / 1000
            if target:
                neuron_input[0] = self.vision_radius / auxiliary.stick_to_edge(target.x - self.x, -1, 1)
                neuron_input[1] = self.vision_radius / auxiliary.stick_to_edge(target.y - self.y, -1, 1)
                if isinstance(target, Food):
                    neuron_input[2] = 1
                    # neuron_input[5] = 10
                else:
                    neuron_input[2] = -1
                    # neuron_input[4] = target.can_multiply()
                    # if self.size > target.size:
                    #     neuron_input[5] = self.size / target.size
                    # else:
                    #     neuron_input[5] = -1 * target.size / self.size

            direction = self.brain.get_direction(neuron_input)
            direction_changed = self.direction == direction
            self.direction = direction
            # print('brain', neuron_input, direction)

        vel_x, vel_y = self.get_velocity(dt)
        new_rect = self.rect.move(vel_x, vel_y)

        bounds = world.screen.get_rect()
        if not bounds.contains(new_rect):
            if self.can_change_direction():
                self.direction = fmod((self.direction + random.uniform(0, pi)), (2 * pi))
                vel_x, vel_y = self.get_velocity(dt)
                new_rect = self.rect.move(vel_x, vel_y)
                direction_changed = True
            new_rect = new_rect.clamp(bounds)

        if direction_changed:
            self.direction_change_cd = self.direction_change_delay

        return new_rect


class Food(SquareObject):
    def __init__(self, x: float, y: float, value: float = 2000, size: float = 3.0,
                 color: pygame.Color = pygame.Color(125, 125, 125)):
        super().__init__(x, y, size, color, 0, name='food')
        self.value = value
