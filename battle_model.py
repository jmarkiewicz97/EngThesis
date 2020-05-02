# model.py
from mesa import Model
from mesa.time import RandomActivation
from mesa.space import ContinuousSpace
from mesa.datacollection import DataCollector
from math import floor
import random
import copy
import numpy as np

import warrior_agent

class BattleModel(Model):
    """A model with some number of agents."""
    def __init__(self, red_col,red_row,red_squad, blue_col,blue_row,blue_squad, width, height):
        self.running = True
        self.space = ContinuousSpace(width, height, False)
        self.schedule = RandomActivation(self)
        self.next_agent_id = 1

        separation_y = 1.5
        # Find center
        red_first_y = ((height/2 - (red_squad * red_row/2 * separation_y)) + separation_y/2) - ((red_squad-1) * separation_y*2)
        blue_first_y = ((height/2 - (blue_squad * blue_row/2 * separation_y)) + separation_y/2) - ((blue_squad-1) * separation_y*2)
        
        # Create agents
        self.spawner(15.0,red_first_y, 1.5,separation_y, red_col,red_row,red_squad, 'red')
        self.spawner(width - 15.0,blue_first_y, -1.5,separation_y, blue_col,blue_row,blue_squad, 'blue')
            
    def spawner(self, first_x, first_y, separation_x, separation_y, cols, rows, squad, type):
        for i in range(cols):
            for j in range(rows * squad):
                x = first_x + (separation_x * i)
                y = first_y + (separation_y * j)
                army = type + str(floor(j/rows))
                
                # Squad separator
                y = y + (4*separation_y) * (floor(j / rows))

                subtype = "warrior"

                if i == 0:
                    if j%5 == 1 or j%5 == 3:
                        subtype = "guard"

                if i == 1:
                    if j%5==2:
                        subtype = "general"

                if i == 2:
                    if j%5 == 1 or j%5 == 3:
                        subtype = "healer"
                    elif j%5 == 0 or j%5 == 4:
                        subtype = "marksman"
                    elif j%5 == 2:
                        subtype = "flagger"


                self.spawn(x,y,type,subtype,army)

        for agent in self.schedule.agent_buffer(False):
            if agent.subtype == "general":
                for soldier in self.schedule.agent_buffer(False):
                    if soldier.subtype != "general" and soldier.army == agent.army:
                        agent.soldiers.append(soldier)
            elif agent.subtype == "flagger":
                for soldier in self.schedule.agent_buffer(False):
                    if soldier.subtype != "flagger" and soldier.army == agent.army:
                        agent.soldiers.append(soldier)


        
        
    def spawn(self,x,y,type,subtype,army):
        if(type == 'red' and subtype == "general"):
            a = warrior_agent.RedGeneral(self.next_agent_id, army, self)
        elif(type == "red" and subtype == "warrior"):
            a = warrior_agent.RedCommonWarrior(self.next_agent_id, army, self)
        elif(type == "red" and subtype == "healer"):
            a = warrior_agent.RedHealer(self.next_agent_id, army, self)
        elif(type == "red" and subtype == "marksman"):
            a = warrior_agent.RedMarksman(self.next_agent_id, army, self)
        elif(type == "red" and subtype == "guard"):
            a = warrior_agent.RedGuard(self.next_agent_id, army, self)
        elif(type == "red" and subtype == "flagger"):
            a = warrior_agent.RedFlagger(self.next_agent_id, army, self)
        elif(type == "blue" and subtype == "general"):
            a = warrior_agent.BlueGeneral(self.next_agent_id, army, self)
        elif(type == "blue" and subtype == "warrior"):
            a = warrior_agent.BlueCommonWarrior(self.next_agent_id, army, self)
        elif(type == "blue" and subtype == "healer"):
            a = warrior_agent.BlueHealer(self.next_agent_id, army, self)
        elif(type == "blue" and subtype == "marksman"):
            a = warrior_agent.BlueMarksman(self.next_agent_id, army, self)
        elif(type == "blue" and subtype == "guard"):
            a = warrior_agent.BlueGuard(self.next_agent_id, army, self)
        elif(type == "blue" and subtype == "flagger"):
            a = warrior_agent.BlueFlagger(self.next_agent_id, army, self)

        pos = np.array((x, y))
        self.schedule.add(a)
        self.space.place_agent(a, pos)

        self.next_agent_id += 1

        #print("zespawnowane")

    def step(self):
        self.schedule.step()

        agents_and_allies_morale = []
        for agent in self.schedule.agent_buffer(False): #type: warrior_agent.WarriorAgent
            agents_and_allies_morale.append((agent, agent.get_average_morale_of_allies_in_flocking_radius()))

        for (agent, allies_morale) in agents_and_allies_morale: #type: (warrior_agent.WarriorAgent, float)
            agent.update_morale(agent.calculate_new_morale(allies_morale))

        print("Zywych agentow: " + str(len(self.schedule.agents)) + "\n")

        both = True
        blue = False
        red = False
        for agent in self.schedule.agents:
            if agent.type == "red":
                red = True
            elif agent.type == "blue":
                blue = True

        if red and blue:
            both = True
        else: both = False

        return both
