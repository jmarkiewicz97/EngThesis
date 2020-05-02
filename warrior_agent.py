import mesa.agent
import functools
import numpy as np
import random

import simulation_parameters


class WarriorAgent(mesa.Agent):

    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, model)
        self.counter = 1
        self.army = army
        self.morale = simulation_parameters.BASIC_MORALE
        self.has_killed_recently = False
        self.damage_inflicted_recently = 0.0
        self.velocity = np.zeros(2)
        # recently = in the last turn
        self.damage_received_recently = 0.0
        self.ENEMY_SCANNING_RADIUS = simulation_parameters.VISION_RANGE  # promien widzenia przeciwnikow
        self.FLOCKING_RADIUS = simulation_parameters.FLOCKING_RADIUS  # promien widzenia swoich
        self.SEPARATION_DISTANCE = simulation_parameters.SEPARATION_DISTANCE  # jaki dystans chce zachowac od innych w oddziale
        self.COHERENCE_FACTOR = simulation_parameters.COHERENCE_FACTOR
        self.MATCH_FACTOR = simulation_parameters.MATCH_FACTOR
        self.SEPARATION_FACTOR = simulation_parameters.SEPARATION_FACTOR
        self.ENEMY_POSITION_FACTOR = simulation_parameters.ENEMY_POSITION_FACTOR
        self.guarder = self
        self.protected = False

    def step(self):
        """if self.subtype == "general" and self.counter == 1:
            self.f.write("Moja armia to: ")
            for soldier in self.soldiers:
                self.f.write(soldier.name + ", ")
            self.f.write("\n\n")"""  # wypisanie podkomendnych
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
        if enemies_in_attack_range:
            enemy = random.choice(enemies_in_attack_range)
            self.attack(enemy)
        else:
            self.move()

        self.counter += 1

    def die(self):
        self.type = 'dead'
        self.f.write("Zginąłem, to koniec")
        self.f.close()
        self.model.schedule.remove(self)

    def attack(self, enemy):
        if enemy.receive_damage(self.attack_damage, self.name):
            self.has_killed_recently = True
        if not enemy.protected:
            self.f.write("Haha! Zadałem wrogowi " + enemy.name + " " + str(self.attack_damage) + " punktów obrażeń.\n")
        else:
            self.f.write("Wróg " + enemy.name + " był broniony! Zadałem jego obrońcy " + enemy.guarder.name + " " + str(
                self.attack_damage) + " punktów obrażeń.\n")
        if self.has_killed_recently: self.f.write("Zabiłem go! Hurra!\n")
        self.damage_inflicted_recently = self.attack_damage

    # returns if the damage inflicted was a killing blow
    def receive_damage(self, damage, name):
        if self.protected:
            a = self.guarder.receive_ally_damage(damage, name)
            if a:
                return True
            else:
                return False
        else:
            self.hp -= damage
            self.f.write("Ała! Otrzymałem " + str(damage) + " punktów obrażeń od " + str(name) + ". Teraz mam " + str(
                self.hp) + " punktów zdrowia.\n")
            self.damage_received_recently += damage

            if self.hp <= 0:
                self.die()
                return True
            return False

    def receive_precise_damage(self, damage, name):
        self.hp -= damage
        self.f.write("Namierzył mnie " + str(name) + "! Zadał mi " + str(damage) + " punktów obrażeń. Teraz mam " + str(
            self.hp) + " punktów zdrowia.\n")
        self.damage_received_recently += damage
        self.morale -= 0.05

        if self.hp <= 0:
            self.die()
            return True
        return False

    # ostateczny wektor predkosci otrzymujemy normalizujac wektor predkosci z metody calculate_velocity_vector()
    # i mnozac go przez szybkosc
    # danego typu agenta (skalarna) parametryzowana w pliku konfiguracyjnym
    def move(self):
        velocity_vector = self.calculate_velocity_vector()
        normalised_velocity_vector = velocity_vector / np.linalg.norm(velocity_vector)
        self.velocity = normalised_velocity_vector * self.movement_speed
        end_point = self.pos + self.velocity
        self.model.space.move_agent(self, end_point)
        self.f.write("Idę na" + str(end_point) + "\n")

    def calculate_velocity_vector(self):
        visible_enemies = self.scan_for_enemies(self.ENEMY_SCANNING_RADIUS)
        visible_allies = self.scan_for_allies(self.FLOCKING_RADIUS)

        # wektor predkosci przed normalizacja - kombinacja liniowa wektorow z poszczegolnych regul o wspolczynnikach
        # rownych ich wagom (parametryzowanych w pliku konfiguracyjnym)
        velocity_vector = (self.coherence_vector(visible_allies) * self.COHERENCE_FACTOR +
                           self.match_vector(visible_allies) * self.MATCH_FACTOR +
                           self.separate_vector(visible_allies) * self.SEPARATION_FACTOR +
                           self.coherence_vector(visible_enemies) * self.ENEMY_POSITION_FACTOR)

        return velocity_vector

    def scan_for_allies(self, radius):
        warriors_in_flocking_radius = self.model.space.get_neighbors(self.pos, radius, False)
        allies_in_range = []
        for warrior in warriors_in_flocking_radius:
            if warrior.type == self.type:
                allies_in_range.append(warrior)
        return allies_in_range

    def scan_for_enemies(self, given_range):
        warriors_in_range = self.model.space.get_neighbors(self.pos, given_range, False)
        enemies_in_range = []
        for warrior in warriors_in_range:
            if warrior.type != self.type and warrior.type != 'dead':
                enemies_in_range.append(warrior)
        return enemies_in_range

    # zwraca wektor od agenta do srodka danej grupy agentow
    def coherence_vector(self, group_in_radius):
        vector = np.zeros(2)
        if group_in_radius:
            for warrior in group_in_radius:
                vector += self.model.space.get_heading(self.pos, warrior.pos)
            vector /= len(group_in_radius)
        return vector

    def match_vector(self, visible_allies):
        vector = np.zeros(2)
        if visible_allies:
            for ally in visible_allies:
                vector += ally.velocity
            vector /= len(visible_allies)
        return vector

    # wektor przeciwny do polozen agentow w przestrzeni "osobistej" tego agenta
    def separate_vector(self, visible_allies):
        vector = np.zeros(2)
        for ally in visible_allies:
            if self.model.space.get_distance(self.pos, ally.pos) < self.SEPARATION_DISTANCE:
                vector -= self.model.space.get_heading(self.pos, ally.pos)
        return vector

    def calculate_own_morale_modifier(self):
        morale_modifier = self.damage_received_morale_modifier() + self.kill_morale_modifier() + self.damage_inflicted_morale_modifier()
        return morale_modifier

    def kill_morale_modifier(self):
        return simulation_parameters.kill_morale_modifier(self.has_killed_recently)

    def damage_received_morale_modifier(self):
        return simulation_parameters.damage_received_morale_modifier(self.damage_received_recently, self.initial_hp)

    def damage_inflicted_morale_modifier(self):
        return simulation_parameters.damage_inflicted_morale_modifier(self.damage_inflicted_recently)

    def update_morale(self, new_morale):
        self.clear_recent_event_trackers()
        self.morale = new_morale
        if self.morale <= simulation_parameters.TO_FLEE_THRESHOLD:
            self.flee()
        self.adjust_attack_damage()

    def flee(self):
        self.f.write("Muszę się ratować!\n")
        self.die()

    def adjust_attack_damage(self):
        self.attack_damage = self.initial_attack_damage * self.morale / 100

    def clear_recent_event_trackers(self):
        self.damage_received_recently = 0.0
        self.damage_inflicted_recently = 0.0
        self.has_killed_recently = False

    def get_average_morale_of_allies_in_flocking_radius(self):
        morale = [ally.get_morale() for ally in self.scan_for_allies(self.FLOCKING_RADIUS)]
        if not morale:
            return 0
        return sum(morale) / len(morale)

    def calculate_new_morale(self, average_morale_of_allies) -> float:
        new_morale = (average_morale_of_allies * simulation_parameters.ALLIES_MORALE_WEIGHT) + \
                     (self.calculate_own_morale_modifier() + self.morale) * \
                     (1 - simulation_parameters.ALLIES_MORALE_WEIGHT)
        return new_morale

    def get_morale(self):
        return self.morale


class RedWarrior(WarriorAgent):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.type = 'red'
        self.attack_range = simulation_parameters.BASIC_ATTACK_RANGE
        self.movement_speed = simulation_parameters.RED_MOVEMENT_SPEED


class BlueWarrior(WarriorAgent):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.type = 'blue'
        self.attack_range = simulation_parameters.BASIC_ATTACK_RANGE
        self.movement_speed = simulation_parameters.BLUE_MOVEMENT_SPEED


class RedCommonWarrior(RedWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "warrior"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.hp = simulation_parameters.BASIC_HP
        self.initial_hp = self.hp
        self.attack_damage = simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage


class BlueCommonWarrior(BlueWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "warrior"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.hp = simulation_parameters.BASIC_HP
        self.initial_hp = self.hp
        self.attack_damage = simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage


class BlueGeneral(BlueWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "general"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.soldiers = []
        self.morale = simulation_parameters.BASIC_MORALE
        self.hp = 3 * simulation_parameters.BASIC_HP
        self.attack_range = 1.2 * simulation_parameters.BASIC_ATTACK_RANGE
        self.initial_hp = self.hp
        self.attack_damage = 2.5 * simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage
        self.movement_speed = 0.9 * simulation_parameters.BLUE_MOVEMENT_SPEED
        self.being_healed = False

    def step(self):
        self.being_healed = False
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        allies_in_healing_range = self.scan_for_allies(simulation_parameters.HEALING_RANGE)
        allies_in_flocking_range = self.scan_for_allies(self.FLOCKING_RADIUS)
        for ally in allies_in_healing_range:
            if ally.subtype == "healer":
                self.being_healed = True
                break

        if self.hp < 0.25 * self.initial_hp and self.being_healed == False:
            self.f.write("Jest źle, muszę poszukać medyka!\n")
            healer_visible = False
            for soldier in allies_in_flocking_range:
                if soldier.subtype == "healer":
                    healer_visible = True

            if healer_visible:
                self.f.write("Idę poszukać medyka!\n")
                self.move_medic()
            else:
                self.f.write("Taki los, medyka nie ma, walczę dalej!\n")
                enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
                if enemies_in_attack_range:
                    enemy = random.choice(enemies_in_attack_range)
                    self.attack(enemy)
                else:
                    self.move()

        else:
            enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
            if enemies_in_attack_range:
                enemy = random.choice(enemies_in_attack_range)
                self.attack(enemy)
            else:
                self.move()

        self.counter += 1

    def move_medic(self):
        allies = self.scan_for_allies(self.FLOCKING_RADIUS)
        healers = []
        for ally in allies:
            if ally.subtype == "healer":
                healers.append(ally)

        velocity_vector = self.separate_vector(allies) * self.SEPARATION_FACTOR + self.coherence_vector(
            allies) * self.COHERENCE_FACTOR + self.coherence_vector(healers) * simulation_parameters.WANT_HEALING
        normalised_velocity_vector = velocity_vector / np.linalg.norm(velocity_vector)
        self.velocity = normalised_velocity_vector * self.movement_speed
        end_point = self.pos + self.velocity
        self.model.space.move_agent(self, end_point)
        self.f.write("Idę na" + str(end_point) + "\n")

    def die(self):
        self.type = 'dead'
        self.f.write("Zginąłem, to koniec.\nObniżam morale swoich żołnierzy.")
        self.f.close()
        for soldier in self.soldiers:
            soldier.morale -= 10
            if soldier.type != "dead":
                soldier.f.write("Nasz generał powalon! Jak teraz mamy wygrać?\n")
        self.model.schedule.remove(self)


class RedGeneral(RedWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "general"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.soldiers = []
        self.morale = simulation_parameters.BASIC_MORALE
        self.hp = 3 * simulation_parameters.BASIC_HP
        self.attack_range = 1.2 * simulation_parameters.BASIC_ATTACK_RANGE
        self.initial_hp = self.hp
        self.attack_damage = 2.5 * simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage
        self.movement_speed = 0.9 * simulation_parameters.RED_MOVEMENT_SPEED
        self.being_healed = False

    def step(self):
        self.being_healed = False
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        allies_in_healing_range = self.scan_for_allies(simulation_parameters.HEALING_RANGE)
        allies_in_flocking_range = self.scan_for_allies(self.FLOCKING_RADIUS)
        for ally in allies_in_healing_range:
            if ally.subtype == "healer":
                self.being_healed = True
                break

        if self.hp < 0.25 * self.initial_hp and self.being_healed == False:
            self.f.write("Jest źle, muszę poszukać medyka!\n")
            healer_visible = False
            for soldier in allies_in_flocking_range:
                if soldier.subtype == "healer":
                    healer_visible = True

            if healer_visible:
                self.f.write("Idę poszukać medyka!\n")
                self.move_medic()
            else:
                self.f.write("Taki los, medyka nie ma, walczę dalej!\n")
                enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
                if enemies_in_attack_range:
                    enemy = random.choice(enemies_in_attack_range)
                    self.attack(enemy)
                else:
                    self.move()

        else:
            enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
            if enemies_in_attack_range:
                enemy = random.choice(enemies_in_attack_range)
                self.attack(enemy)
            else:
                self.move()

        self.counter += 1

    def move_medic(self):
        allies = self.scan_for_allies(self.FLOCKING_RADIUS)
        healers = []
        for ally in allies:
            if ally.subtype == "healer":
                healers.append(ally)

        velocity_vector = self.separate_vector(allies) * self.SEPARATION_FACTOR + self.coherence_vector(
            allies) * self.COHERENCE_FACTOR + self.coherence_vector(healers) * simulation_parameters.WANT_HEALING
        normalised_velocity_vector = velocity_vector / np.linalg.norm(velocity_vector)
        self.velocity = normalised_velocity_vector * self.movement_speed
        end_point = self.pos + self.velocity
        self.model.space.move_agent(self, end_point)
        self.f.write("Idę na" + str(end_point) + "\n")

    def die(self):
        self.type = 'dead'
        self.f.write("Zginąłem, to koniec.\nObniżam morale swoich żołnierzy.")
        self.f.close()
        for soldier in self.soldiers:
            soldier.morale -= 10
            if soldier.type != "dead":
                soldier.f.write("Nasz generał powalon! Jak teraz mamy wygrać?\n")
        self.model.schedule.remove(self)


class RedHealer(RedWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "healer"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.hp = 1.2 * simulation_parameters.BASIC_HP
        self.initial_hp = self.hp
        self.attack_damage = 0.3 * simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage
        self.morale = 10
        self.healing_range = simulation_parameters.HEALING_RANGE
        self.heal_damage = 2
        self.initial_heal_damage = self.heal_damage

    def calculate_velocity_vector(self):
        # visible_enemies = self.scan_for_enemies(self.ENEMY_SCANNING_RADIUS)
        visible_allies = self.scan_for_allies(self.FLOCKING_RADIUS)

        # wektor predkosci przed normalizacja - kombinacja liniowa wektorow z poszczegolnych regul o wspolczynnikach
        # rownych ich wagom (parametryzowanych w pliku konfiguracyjnym)
        velocity_vector = (self.coherence_vector(visible_allies) * self.COHERENCE_FACTOR +
                           self.match_vector(visible_allies) * self.MATCH_FACTOR +
                           self.separate_vector(visible_allies) * self.SEPARATION_FACTOR)

        return velocity_vector

    def heal(self, ally):
        if ally.hp + self.heal_damage < ally.initial_hp:
            ally.hp += self.heal_damage
            self.f.write("Leczę " + ally.name + " o " + str(self.heal_damage) + ". Teraz ma " + str(ally.hp) + "\n")
            ally.f.write(self.name + " uleczył mnie do " + str(ally.hp) + " punktów hp.\n")
        else:
            ally.hp = ally.initial_hp
            self.f.write("Leczę " + ally.name + " do pełna. Teraz ma " + str(ally.hp) + "\n")
            ally.f.write(self.name + " uleczył mnie do pełna, mam " + str(ally.hp) + " punktów życia.\n")

    def step(self):
        """if self.subtype == "general" and self.counter == 1:
            self.f.write("Moja armia to: ")
            for soldier in self.soldiers:
                self.f.write(soldier.name + ", ")
            self.f.write("\n\n")"""  # wypisanie podkomendnych
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        allies_in_healing_range = self.scan_for_allies(simulation_parameters.HEALING_RANGE)
        if allies_in_healing_range:
            for ally in allies_in_healing_range:
                if ally.hp < ally.initial_hp:
                    self.heal(ally)
            self.move()
        else:
            enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
            if enemies_in_attack_range:
                enemy = random.choice(enemies_in_attack_range)
                self.attack(enemy)
            else:
                self.move()

        self.counter += 1

    def adjust_heal_damage(self):
        self.heal_damage = self.initial_heal_damage * self.morale / 100

    def update_morale(self, new_morale):
        self.clear_recent_event_trackers()
        self.morale = new_morale
        if self.morale <= simulation_parameters.TO_FLEE_THRESHOLD:
            self.flee()
        self.adjust_attack_damage()
        self.adjust_heal_damage()


class BlueHealer(BlueWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "healer"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.morale = 10
        self.hp = 1.2 * simulation_parameters.BASIC_HP
        self.initial_hp = self.hp
        self.attack_damage = 0.3 * simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage
        self.healing_range = simulation_parameters.HEALING_RANGE
        self.heal_damage = 2
        self.initial_heal_damage = self.heal_damage

    def calculate_velocity_vector(self):
        # visible_enemies = self.scan_for_enemies(self.ENEMY_SCANNING_RADIUS)
        visible_allies = self.scan_for_allies(self.FLOCKING_RADIUS)

        # wektor predkosci przed normalizacja - kombinacja liniowa wektorow z poszczegolnych regul o wspolczynnikach
        # rownych ich wagom (parametryzowanych w pliku konfiguracyjnym)
        velocity_vector = (self.coherence_vector(visible_allies) * self.COHERENCE_FACTOR +
                           self.match_vector(visible_allies) * self.MATCH_FACTOR +
                           self.separate_vector(visible_allies) * self.SEPARATION_FACTOR)

        return velocity_vector

    def heal(self, ally):
        if ally.hp + self.heal_damage < ally.initial_hp:
            ally.hp += self.heal_damage
            self.f.write("Leczę " + ally.name + " o " + str(self.heal_damage) + ". Teraz ma " + str(ally.hp) + "\n")
            ally.f.write(self.name + " uleczył mnie do " + str(ally.hp) + " punktów hp.\n")
        else:
            ally.hp = ally.initial_hp
            self.f.write("Leczę " + ally.name + " do pełna. Teraz ma " + str(ally.hp) + "\n")
            ally.f.write(self.name + " uleczył mnie do pełna, mam " + str(ally.hp) + " punktów życia.\n")

    def step(self):
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        allies_in_healing_range = self.scan_for_allies(self.healing_range)
        if allies_in_healing_range:
            for ally in allies_in_healing_range:
                if ally.hp < ally.initial_hp:
                    self.heal(ally)
            self.move()
        else:
            enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
            if enemies_in_attack_range:
                enemy = random.choice(enemies_in_attack_range)
                self.attack(enemy)
            else:
                self.move()

        self.counter += 1

    def adjust_heal_damage(self):
        self.heal_damage = self.initial_heal_damage * self.morale / 100

    def update_morale(self, new_morale):
        self.clear_recent_event_trackers()
        self.morale = new_morale
        if self.morale <= simulation_parameters.TO_FLEE_THRESHOLD:
            self.flee()
        self.adjust_attack_damage()
        self.adjust_heal_damage()


class RedMarksman(RedWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "marksman"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.morale = 10
        self.hp = 0.6 * simulation_parameters.BASIC_HP
        self.initial_hp = self.hp
        self.attack_damage = 0.8 * simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage
        self.attack_range = 3 * simulation_parameters.BASIC_ATTACK_RANGE
        self.success_chance = simulation_parameters.SUCCESS_CHANCE
        self.movement_speed = 1.3 * simulation_parameters.RED_MOVEMENT_SPEED

    def step(self):
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
        attack_to_carry = True
        if enemies_in_attack_range:
            for enemy in enemies_in_attack_range:
                if enemy.subtype == "general":
                    self.precise_attack(enemy)
                    attack_to_carry = False
                    break
                elif enemy.subtype == "flagger":
                    self.precise_attack(enemy)
                    attack_to_carry = False
                    break
                elif enemy.subtype == "healer":
                    self.precise_attack(enemy)
                    attack_to_carry = False
                    break
                elif enemy.subtype == "marksman":
                    self.precise_attack(enemy)
                    attack_to_carry = False
                    break
            if attack_to_carry:
                enemy = random.choice(enemies_in_attack_range)
                self.attack(enemy)
        else:
            self.move()

        self.counter += 1

    def precise_attack(self, enemy):
        self.f.write("Celuję we wroga " + enemy.name + "...\n")
        shot = random.randrange(10)
        if shot < self.success_chance:
            self.morale += 0.05
            self.f.write("Tak, trafiłem go! Zadałem mu " + str(self.attack_damage) + " punktów obrażeń.\n")
            self.damage_inflicted_recently = self.attack_damage
            if enemy.receive_precise_damage(self.attack_damage, self.name):
                self.has_killed_recently = True
                self.f.write("W dodatku go zabiłem!\n")
        else:
            self.morale -= 0.1
            self.damage_inflicted_recently = 0
            self.f.write("O nie, chybiłem! Co za wstyd!\n")


class BlueMarksman(BlueWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "marksman"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.morale = 10
        self.hp = 0.6 * simulation_parameters.BASIC_HP
        self.initial_hp = self.hp
        self.attack_damage = 0.8 * simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage
        self.attack_range = 3 * simulation_parameters.BASIC_ATTACK_RANGE
        self.success_chance = simulation_parameters.SUCCESS_CHANCE
        self.movement_speed = 1.3 * simulation_parameters.BLUE_MOVEMENT_SPEED

    def step(self):
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
        attack_to_carry = True
        if enemies_in_attack_range:
            for enemy in enemies_in_attack_range:
                if enemy.subtype == "general":
                    self.precise_attack(enemy)
                    attack_to_carry = False
                    break
                elif enemy.subtype == "flagger":
                    self.precise_attack(enemy)
                    attack_to_carry = False
                    break
                elif enemy.subtype == "healer":
                    self.precise_attack(enemy)
                    attack_to_carry = False
                    break
                elif enemy.subtype == "marksman":
                    self.precise_attack(enemy)
                    attack_to_carry = False
                    break
            if attack_to_carry:
                enemy = random.choice(enemies_in_attack_range)
                self.attack(enemy)
        else:
            self.move()

        self.counter += 1

    def precise_attack(self, enemy):
        self.f.write("Celuję we wroga " + enemy.name + "...\n")
        shot = random.randrange(10)
        if shot < self.success_chance:
            self.morale += 0.05
            self.f.write("Tak, trafiłem go! Zadałem mu " + str(self.attack_damage) + " punktów obrażeń.\n")
            self.damage_inflicted_recently = self.attack_damage
            if enemy.receive_precise_damage(self.attack_damage, self.name):
                self.has_killed_recently = True
                self.f.write("W dodatku go zabiłem!\n")
        else:
            self.morale -= 0.1
            self.damage_inflicted_recently = 0
            self.f.write("O nie, chybiłem! Co za wstyd!\n")


class RedGuard(RedWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "guard"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.morale = 10
        self.hp = 6 * simulation_parameters.BASIC_HP
        self.attack_range = 0.4 * simulation_parameters.BASIC_ATTACK_RANGE
        self.initial_hp = self.hp
        self.attack_damage = 0.4 * simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage
        self.movement_speed = simulation_parameters.RED_MOVEMENT_SPEED
        self.guarded_ally = self
        self.guarding = False

    def step(self):
        self.guarded_ally.protected = False
        self.guarded_ally = self
        self.guarding = False
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        allies_to_guard = self.scan_for_allies(simulation_parameters.GUARDING_RANGE)
        enemies_close = self.scan_for_enemies(5 * simulation_parameters.BASIC_ATTACK_RANGE)
        for guard in allies_to_guard:
            if guard.subtype == "guard":
                allies_to_guard.remove(guard)

        if allies_to_guard and enemies_close:
            ally = random.choice(allies_to_guard)
            while ally.protected:
                allies_to_guard.remove(ally)
                if not allies_to_guard:
                    self.f.write("Nie ma kogo chronić\n")
                    enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
                    if enemies_in_attack_range:
                        enemy = random.choice(enemies_in_attack_range)
                        self.attack(enemy)
                        return
                    else:
                        self.move()
                        return
                ally = random.choice(allies_to_guard)
            self.protect(ally)
            self.move()
        else:
            enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
            if enemies_in_attack_range:
                enemy = random.choice(enemies_in_attack_range)
                self.attack(enemy)
            else:
                self.move()

        self.counter += 1

    def protect(self, ally):
        self.guarding = True
        self.f.write("W tym ruchu chronię sojusznika " + ally.name + ".\n")
        self.guarded_ally = ally
        ally.guarder = self
        ally.protected = True
        self.guarding = True

    def receive_ally_damage(self, damage, name):
        self.hp -= damage
        self.f.write(
            "Oj! Chroniąc " + self.guarded_ally.name + " otrzymałem " + str(
                damage) + " punktów obrażeń od " + name + ". Teraz mam " + str(
                self.hp) + " punktów zdrowia.\n")

        if self.hp <= 0:
            self.die()
            return True
        return False

    def die(self):
        self.type = 'dead'
        self.f.write("Zginąłem, to koniec")
        self.guarding = False
        self.guarded_ally.protected = False
        self.f.close()
        self.model.schedule.remove(self)


class BlueGuard(BlueWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "guard"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.morale = 10
        self.hp = 6 * simulation_parameters.BASIC_HP
        self.attack_range = 0.4 * simulation_parameters.BASIC_ATTACK_RANGE
        self.initial_hp = self.hp
        self.attack_damage = 0.4 * simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage
        self.movement_speed = simulation_parameters.BLUE_MOVEMENT_SPEED
        self.guarded_ally = self
        self.guarding = False

    def step(self):
        self.guarded_ally.protected = False
        self.guarded_ally = self
        self.guarding = False
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        allies_to_guard = self.scan_for_allies(simulation_parameters.GUARDING_RANGE)
        enemies_close = self.scan_for_enemies(5 * simulation_parameters.BASIC_ATTACK_RANGE)
        for guard in allies_to_guard:
            if guard.subtype == "guard":
                allies_to_guard.remove(guard)

        if allies_to_guard and enemies_close:
            ally = random.choice(allies_to_guard)
            while ally.protected:
                allies_to_guard.remove(ally)
                if not allies_to_guard:
                    self.f.write("Nie ma kogo chronić\n")
                    enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
                    if enemies_in_attack_range:
                        enemy = random.choice(enemies_in_attack_range)
                        self.attack(enemy)
                        return
                    else:
                        self.move()
                        return
                ally = random.choice(allies_to_guard)
            self.protect(ally)
            self.move()
        else:
            enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
            if enemies_in_attack_range:
                enemy = random.choice(enemies_in_attack_range)
                self.attack(enemy)
            else:
                self.move()

        self.counter += 1

    def protect(self, ally):
        self.guarding = True
        self.f.write("W tym ruchu chronię sojusznika " + ally.name + ".\n")
        self.guarded_ally = ally
        ally.guarder = self
        ally.protected = True
        self.guarding = True

    def receive_ally_damage(self, damage, name):
        self.hp -= damage
        self.f.write(
            "Oj! Chroniąc " + self.guarded_ally.name + " otrzymałem " + str(damage) + " punktów obrażeń od " + name + ". Teraz mam " + str(
                self.hp) + " punktów zdrowia.\n")

        if self.hp <= 0:
            self.die()
            return True
        return False

    def die(self):
        self.type = 'dead'
        self.f.write("Zginąłem, to koniec")
        self.guarding = False
        self.guarded_ally.protected = False
        self.f.close()
        self.model.schedule.remove(self)

class RedFlagger(RedWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "flagger"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.f.write("Moja armia: " + self.army + "\n\n")
        self.morale = 10
        self.soldiers = []
        self.hp = simulation_parameters.BASIC_HP
        self.attack_range = simulation_parameters.BASIC_ATTACK_RANGE
        self.initial_hp = self.hp
        self.attack_damage = 0.9 * simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage
        self.movement_speed = 1.1 * simulation_parameters.BLUE_MOVEMENT_SPEED

    def calculate_velocity_vector(self):
        # visible_enemies = self.scan_for_enemies(self.ENEMY_SCANNING_RADIUS)
        visible_allies = self.scan_for_allies(self.FLOCKING_RADIUS)

        # wektor predkosci przed normalizacja - kombinacja liniowa wektorow z poszczegolnych regul o wspolczynnikach
        # rownych ich wagom (parametryzowanych w pliku konfiguracyjnym)
        velocity_vector = (self.coherence_vector(visible_allies) * self.COHERENCE_FACTOR +
                           self.match_vector(visible_allies) * self.MATCH_FACTOR +
                           self.separate_vector(visible_allies) * self.SEPARATION_FACTOR)

        return velocity_vector

    def step(self):
        """if self.subtype == "flagger" and self.counter == 1:
                    self.f.write("Moja armia to: ")
                    for soldier in self.soldiers:
                        self.f.write(soldier.name + ", ")
                    self.f.write("\n\n")"""  # wypisanie podkomendnych
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        allies_in_courage_range = self.scan_for_allies(2 * simulation_parameters.HEALING_RANGE)
        allies_to_courage = []
        for soldier in allies_in_courage_range:
            if soldier.army == self.army:
                allies_to_courage.append(soldier)
        if allies_to_courage:
            self.courage(allies_to_courage)
        enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
        if enemies_in_attack_range:
            enemy = random.choice(enemies_in_attack_range)
            self.attack(enemy)
        else:
            self.move()

        self.counter += 1

    def courage(self, allies):
        self.f.write("Zwiększam morale wszystkich pobliskich sojuszników: ")
        for soldier in allies:
            soldier.morale += 0.5
            self.f.write(soldier.name + ", ")
            if soldier.type != "dead":
                soldier.f.write("Do boju! Moje morale są zwiększone przez chorążego " + self.name + "!\n")
        self.f.write(".\n")

    def die(self):
        self.type = 'dead'
        self.f.write("Zginąłem, to koniec.\nObniżam morale swoich żołnierzy.")
        self.f.close()
        for soldier in self.soldiers:
            soldier.morale -= 10
            if soldier.type != "dead":
                soldier.f.write("O nie! Chorąży nie żyje! Nasza flaga!\n")
        self.model.schedule.remove(self)

class BlueFlagger(BlueWarrior):
    def __init__(self, unique_id, army, model):
        super().__init__(unique_id, army, model)
        self.subtype = "flagger"
        self.name = self.type + self.subtype + str(self.unique_id)
        self.f = open("logi/" + self.name + ".txt", "w+")
        self.f.write("Powstałem, jestem " + self.name + "\n\n")
        self.f.write("Moja armia: " + self.army + "\n\n")
        self.morale = 10
        self.soldiers = []
        self.hp = simulation_parameters.BASIC_HP
        self.attack_range = simulation_parameters.BASIC_ATTACK_RANGE
        self.initial_hp = self.hp
        self.attack_damage = 0.9 * simulation_parameters.BASIC_DAMAGE
        self.initial_attack_damage = self.attack_damage
        self.movement_speed = 1.1 * simulation_parameters.BLUE_MOVEMENT_SPEED

    def calculate_velocity_vector(self):
        # visible_enemies = self.scan_for_enemies(self.ENEMY_SCANNING_RADIUS)
        visible_allies = self.scan_for_allies(self.FLOCKING_RADIUS)

        # wektor predkosci przed normalizacja - kombinacja liniowa wektorow z poszczegolnych regul o wspolczynnikach
        # rownych ich wagom (parametryzowanych w pliku konfiguracyjnym)
        velocity_vector = (self.coherence_vector(visible_allies) * self.COHERENCE_FACTOR +
                           self.match_vector(visible_allies) * self.MATCH_FACTOR +
                           self.separate_vector(visible_allies) * self.SEPARATION_FACTOR)

        return velocity_vector

    def step(self):
        """if self.subtype == "flagger" and self.counter == 1:
                    self.f.write("Moja armia to: ")
                    for soldier in self.soldiers:
                        self.f.write(soldier.name + ", ")
                    self.f.write("\n\n")"""  # wypisanie podkomendnych
        self.f.write("\nRuch " + str(self.counter) + ":\n")
        allies_in_courage_range = self.scan_for_allies(2 * simulation_parameters.HEALING_RANGE)
        allies_to_courage = []
        for soldier in allies_in_courage_range:
            if soldier.army == self.army:
                allies_to_courage.append(soldier)
        if allies_to_courage:
            self.courage(allies_to_courage)
        enemies_in_attack_range = self.scan_for_enemies(self.attack_range)
        if enemies_in_attack_range:
            enemy = random.choice(enemies_in_attack_range)
            self.attack(enemy)
        else:
            self.move()

        self.counter += 1

    def courage(self, allies):
        self.f.write("Zwiększam morale wszystkich pobliskich sojuszników: ")
        for soldier in allies:
            soldier.morale += 0.5
            self.f.write(soldier.name + ", ")
            if soldier.type != "dead":
                soldier.f.write("Do boju! Moje morale są zwiększone przez chorążego " + self.name + "!\n")
        self.f.write(".\n")

    def die(self):
        self.type = 'dead'
        self.f.write("Zginąłem, to koniec.\nObniżam morale swoich żołnierzy.")
        self.f.close()
        for soldier in self.soldiers:
            soldier.morale -= 10
            if soldier.type != "dead":
                soldier.f.write("O nie! Chorąży nie żyje! Nasza flaga!\n")
        self.model.schedule.remove(self)