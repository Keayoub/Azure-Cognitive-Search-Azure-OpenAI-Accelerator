import datetime
import numpy as np

# Datetimes
def datetime_from_hour_of_day(dt, h, m=0, s=0):
    r"""
    Returns the datetime obtained from the hour of day and another datetime

    Parameters:

    - dt: datetime, the datetime of reference
    - h: int, the hour of the day
    - m: int, the minute of the hour
    - s: int, the second of the minute
    """
    return datetime.datetime(dt.year, dt.month, dt.day, h, m, s)

def contains_hour_of_day(dt1, dt2, h, m=0, s=0):
    r"""
    Indicates if the interval induced by two datetimes contains an hour of the
    day

    Parameters:

    - dt1: datetime, the first datetime
    - dt2: datetime, the second datetime
    - h: int, the hour of the day
    - m: int, the minute of the hour
    - s: int, the second of the minute
    """
    if dt1 > dt2:
        return False
    else:
        dt = datetime_from_hour_of_day(dt2, h, m, s)
        return dt1 <= dt and dt <= dt2


house_properties = {
    "init_air_temp": 20,
    "init_mass_temp": 20,
    "target_temp": 20,
    "tolerance_temp": 2,
    "Ua": 2.18e02,  # House walls conductance (W/K). Multiplied by 3 to account for drafts (according to https://dothemath.ucsd.edu/2012/11/this-thermal-house/)
    "Cm": 3.45e06,  # House thermal mass (J/K) (area heat capacity:: 40700 J/K/m2 * area 100 m2)
    "Ca": 9.08e05,  # Air thermal mass in the house (J/K): 3 * (volumetric heat capacity: 1200 J/m3/K, default area 100 m2, default height 2.5 m)
    "Hm": 2.84e03,  # House mass surface conductance (W/K) (interioor surface heat tansfer coefficient: 8.14 W/K/m2; wall areas = Afloor + Aceiling + Aoutwalls + Ainwalls = A + A + (1+IWR)*h*R*sqrt(A/R) = 455m2 where R = width/depth of the house (default R: 1.5) and IWR is I/O wall surface ratio (default IWR: 1.5))
    "hvac_properties": {
        "id": "hvac_1",
        "COP": 2.5,
        "cooling_capacity": 5000, # W
        "latent_cooling_fraction": 0.35,
    },
    "heater_properties": {
        "id": "heater_1",
        "heating_capacity": 10000,  # W
    },
    "EV_properties": {
        "id": "EV_1",
        "battery_capacity": 40000, # Wh
        "max_autonomy": 200, # km
        "battery_level": 40000, # Wh
        "init_autonomy_objective": 200, # km
        "charging_power": 9000, # W
        "charging_efficiency": 0.9, # Ratio
    }
}

grid_properties = {
    "prices": {
        "peak_price": 5e-4, # $/Wh (between 6:00-8:00 and 16:00-20:00)
        "day_price": 5e-5   # $/Wh
    },
    "min_temp": -15,
    "max_temp": 30,
    "today": "variable",
    "tomorrow": None
}

sim_properties = {
    "start_time": "2020-01-01 00:00:00",
    "house_properties": house_properties,
    "grid_properties": grid_properties,
    "max_mean_temp": 25,    # Max mean temperature in Celsius
    "min_mean_temp": -15,   # Min mean temperature in Celsius
    "temp_daily_var": 10,   # Daily temperature variation in Celsius
}


class Simulator():
    def __init__(self, sim_properties):
        self.sim_properties = sim_properties
        self.time = self.init_time()
        self.house = self.init_house()
        self.grid = Grid(self.sim_properties["grid_properties"])
        self.update_ODtemperature()

    def init_time(self):
        time = datetime.datetime.strptime(self.sim_properties['start_time'], '%Y-%m-%d %H:%M:%S')
        return time

    def init_house(self):
        house = House(self.sim_properties["house_properties"])
        return house

    def step(self, action, time_step):
        """
        Take a time step for the house

        Input: action (dict), time_step (seconds)
        Return: Env current state (dict)
    
        """
        delta = datetime.timedelta(seconds=time_step)
        time_plus_12_hours = self.time + datetime.timedelta(hours=12)
        self.time += delta
        house_consumption = self.house.get_house_state()["house_consumption"]
        
        self.update_ODtemperature()

        self.house.step(self.OD_temp, delta, self.time, action)

        temp_in_12_hours = self.compute_ODtemperature(time_plus_12_hours)
        self.grid.step(temp_in_12_hours, house_consumption, delta, self.time)

        env_state = self.get_env_state()
        return env_state
    
    def get_env_state(self):
        house_state = self.house.get_house_state()
        grid_state = self.grid.get_grid_state()
        env_state = {
            'house_state': house_state,
            'grid_state': grid_state,
            'time': self.time,
            'OD_temp': self.OD_temp
        }

        return env_state
    
    def get_env_state_in_natural_language(self):
        state = self.get_env_state()
        on_off_dict = {True: "ON", False: "OFF"}

        text = "This is the current state of the environment: \n"
        text += "It is {}, {}, and the outdoors temperature is {:.2f} C. \n".format(state['time'].strftime("%B %d, %Y"), state['time'].strftime("%I:%M %p"), state['OD_temp'])
        text += "The indoors temperature in the house is {:.2f} C while the target is {:.2f} C.  The air conditioner is {}, the heater is {}. The consumption due to temperature control is {:.2f} kW. \n".format(state['house_state']['current_temp'], state['house_state']['target_temp'], on_off_dict[state['house_state']['hvac']["turned_on"]], on_off_dict[state['house_state']['heater']['turned_on']], state['house_state']['heater']['power_consumption']/1000 + state['house_state']['hvac']['power_consumption']/1000)
        if state['house_state']['EV']['plug_status'] == "plugged":
            text += "The electric vehicle is {} and the charger is {}. The vehicle's current autonomy is {:.2f} km. The autonomy objective is {:.2f} km. The electric vehicle charger current consumption is {:.2f} kW. \n".format(state['house_state']['EV']['plug_status'], state['house_state']['EV']['charging_status'], state['house_state']['EV']['current_autonomy'], state['house_state']['EV']['autonomy_objective'], state['house_state']['EV']['power_consumption']/1000)
        elif state['house_state']['EV']['plug_status'] == "unplugged":
            text += "The electric vehicle is {} and probably being used. \n".format(state['house_state']['EV']['plug_status'])
        text += "The total power consumption of the house is {:.2f} kW. \n".format(state['house_state']['house_consumption']/1000)
        
        ## Add here text for grid prices and energy consumption during the last hour and the last day
        today_policy = state['grid_state']['today']
        text += f"The pricing policy for today is {today_policy}. "
        tomorrow_policy = state['grid_state']['tomorrow']
        if state['grid_state']['tomorrow'] is None:
            text += "The pricing policy for tomorrow has not been published yet. "
        else:
            text += f'The pricing policy for tomorrow is {tomorrow_policy}. '
        price = state['grid_state']['price']
        text += f'The current energy price is {price * 1e5:.1f} cents per kWh.\n'
        total_expenses = state['grid_state']['total_expenses']
        text += f'The total expenses amount to {total_expenses:.2f}$. '
        day_expenses = state['grid_state']['day_expenses']
        text += f'The current day expenses amount to {day_expenses:.2f}$. '
        block_expenses = state['grid_state']['block_expenses']
        text += f'The current block expenses amount to {block_expenses:.2f}$.\n'

        return text

    def get_house_energy_properties_in_natural_language(self):
        house_properties = self.sim_properties["house_properties"]

        text = "These are the energy properties of the house: \n"
        text += "The air conditioner has a coefficient of performance of {:.2f} and a cooling capacity of {:.2f} kW. As a result, when it is on, it consumes {:.2f} kW. \n".format(house_properties["hvac_properties"]["COP"], house_properties["hvac_properties"]["cooling_capacity"]/1000, house_properties["hvac_properties"]["cooling_capacity"]/house_properties["hvac_properties"]["COP"]/1000)
        text += "The heater has a heating capacity of {:.2f} kW. As a result, when it is on, it consumes {:.2f} kW. \n".format(house_properties["heater_properties"]["heating_capacity"]/1000, house_properties["heater_properties"]["heating_capacity"]/1000)

        return text
    
    def get_EV_properties_in_natural_language(self):
        EV_properties = self.sim_properties["house_properties"]["EV_properties"]

        text = "These are the energy properties of the electric vehicle: \n"
        text += "The electric vehicle has a battery capacity of {:.2f} kWh, a maximum autonomy of {:.2f} km, and a charging power of {:.2f} kW. The charger's efficiency is {:.2f}. As a result, when it is charging, it consumes {:.2f} kW. \n".format(EV_properties["battery_capacity"]/1000, EV_properties["max_autonomy"], EV_properties["charging_power"]/1000, EV_properties["charging_efficiency"], EV_properties["charging_power"]/1000/EV_properties["charging_efficiency"])
        
        return text
    
    def describe_action_in_natural_language(self, action):
        text = "This is the description of the command that was sent: \n"
        if action['target_temp_command'] is None and action['EV_action'] is None:
            text += "No command was sent. "
        if action['target_temp_command'] is not None:
            text += "The target indoors temperature is set to {:.2f} C. ".format(action['target_temp_command'])
        if action['EV_action'] is not None:
            if action['EV_action']['plug_action'] is not None:
                if action['EV_action']['plug_action'] == "plug":
                    text += "The electric vehicle was plugged back after the trip. "
                elif action['EV_action']['plug_action'] == "unplug":
                    text += "The electric vehicle is unplugged to go for a trip. "
            if action['EV_action']['endtrip_autonomy'] is not None and action['EV_action']['plug_action'] == "plug":
                text += "The electric vehicle returned from its trip with {:.2f} km of autonomy left. ".format(action['EV_action']['endtrip_autonomy'])
            if action['EV_action']['autonomy_objective'] is not None:
                text += "The autonomy objective of the electric vehicle is set to {:.2f} km. ".format(action['EV_action']['autonomy_objective'])
        text += "\n"
        return text
    
    def update_ODtemperature(self):
        self.OD_temp = self.compute_ODtemperature(self.time)

    def compute_ODtemperature(self, time):    
        """
        Computes the outdoors temperature based on the time (sinusoidal function on the day of the year (coldest Jan 1st, hottest in July 1st), + sinusoidal function on the hour of the day (coldest at 12am, hottest at 12pm)  --> extremes = coldest on Jan 1st at night, hottest on July 1st at noon
        """
        day_of_year = time.timetuple().tm_yday  # returns 1 for January 1st, 365 or 366 for December 31st
        hour_of_day = time.hour

        max_mean = self.sim_properties['max_mean_temp']
        min_mean = self.sim_properties['min_mean_temp']
        temp_daily_var = self.sim_properties['temp_daily_var']
        
        mean_temp = -np.cos(day_of_year/365 * 2*np.pi) * (max_mean - min_mean)/2 + (max_mean + min_mean)/2

        OD_temp = mean_temp + np.cos((hour_of_day)/24 * 2*np.pi + np.pi) * temp_daily_var/2

        return OD_temp
        


######### House #########


class House():
    """
    Single house simulator.

    Attributes:
    house_properties: dictionary, containing the configuration properties of the House object
    init_air_temp: float, initial indoors air temperature of the house, in Celsius
    init_mass_temp: float, initial indoors mass temperature of the house, in Celsius
    current_temp: float, current indoors air temperature of the house, in Celsius
    current_mass_temp: float, current house mass temperature, in Celsius
    target_temp: float, target indoors air temperature of the house, in Celsius
    tolerance_temp: float, tolerance for the indoors air temperature of the house, in Celsius
    Ua: float, House conductance in Watts/Kelvin
    Ca: float, Air thermal mass, in Joules/Kelvin (or Watts/Kelvin.second)
    Hm: float, House mass surface conductance, in Watts/Kelvin
    Cm: float, House thermal mass, in Joules/Kelvin (or Watts/Kelvin.second)
    device_properties: dictionary, containing the properties of the houses' devices
    ac: ac object for the house
    heater: heater object for the house
    ac: ac object for the house
    disp_count: int, iterator for printing count

    Functions:
    step(self, od_temp, time_step): Take a time step for the house
    update_temperature(self, od_temp, time_step): Compute the new temperatures depending on the state of the house's HVACs
    """

    def __init__(self, house_properties):
        """
        Initialize the house

        Parameters:
        house_properties: dictionary, containing the configuration properties of the SingleHouse
        """

        self.house_properties = house_properties
        self.init_air_temp = house_properties["init_air_temp"]
        self.current_temp = self.init_air_temp
        self.init_mass_temp = house_properties["init_mass_temp"]
        self.current_mass_temp = self.init_mass_temp


        # Thermal constraints
        self.target_temp = house_properties["target_temp"]
        self.tolerance_temp = house_properties["tolerance_temp"]

        # Thermodynamic properties
        self.Ua = house_properties["Ua"]
        self.Ca = house_properties["Ca"]
        self.Hm = house_properties["Hm"]
        self.Cm = house_properties["Cm"]


        # Heating and cooling devices
        self.hvac_properties = house_properties["hvac_properties"]
        self.heater_properties = house_properties["heater_properties"]

        self.hvac = HVAC(self.hvac_properties)
        self.heater = Heater(self.heater_properties)


        # Electric vehicle
        self.EV = ElectricVehicle(house_properties["EV_properties"])

    def step(self, od_temp, time_step, date_time, action):
        """
        Take a time step for the house

        Return: -

        Parameters:
        self
        od_temp: float, current outdoors temperature in Celsius
        time_step: timedelta, time step duration
        date_time: datetime, current date and time
        target_temp_command: float to the new target temperature, None if not necessary to command
        """

        target_temp_command = action["target_temp_command"]

        self.update_temperature(od_temp, time_step, date_time)

        if target_temp_command:
            self.target_temp = target_temp_command

        self.hvac.step(self.target_temp, self.tolerance_temp, self.current_temp)
        self.heater.step(self.target_temp, self.tolerance_temp, self.current_temp)

        self.EV.step(time_step, action["EV_action"])

    def get_house_state(self):
        """
        Return the state of the house

        Return: dict
        """

        house_state = {
            "current_temp": self.current_temp,
            "target_temp": self.target_temp,
            "hvac": self.hvac.get_hvac_state(),
            "heater": self.heater.get_heater_state(),
            "EV": self.EV.get_EV_state(),
            "house_consumption": self.hvac.power_consumption() + self.heater.power_consumption() + self.EV.power_consumption(),
        }

        return house_state


    def update_temperature(self, od_temp, time_step, date_time):
        """
        Update the temperature of the house

        Return: -

        Parameters:
        self
        od_temp: float, current outdoors temperature in Celsius
        time_step: timedelta, time step duration
        date_time: datetime, current date and time


        ---
        Model taken from http://gridlab-d.shoutwiki.com/wiki/Residential_module_user's_guide
        """

        time_step_sec = time_step.seconds
        Hm, Ca, Ua, Cm = self.Hm, self.Ca, self.Ua, self.Cm

        # Convert Celsius temperatures in Kelvin
        od_temp_K = od_temp + 273
        current_temp_K = self.current_temp + 273
        current_mass_temp_K = self.current_mass_temp + 273

        # Heat from hvacs (negative if it is AC)
        Qa = self.hvac.get_Q() + self.heater.get_Q()

        # Heat from inside devices (oven, windows, etc)
        Qm = 0

        # Variables and time constants
        a = Cm * Ca / Hm
        b = Cm * (Ua + Hm) / Hm + Ca
        c = Ua
        d = Qm + Qa + Ua * od_temp_K
        g = Qm / Hm

        r1 = (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)
        r2 = (-b - np.sqrt(b**2 - 4 * a * c)) / (2 * a)

        dTA0dt = (
            Hm * current_mass_temp_K / Ca
            - (Ua + Hm) * current_temp_K / Ca
            + Ua * od_temp_K / Ca
            + Qa / Ca
        )

        A1 = (r2 * current_temp_K - dTA0dt - r2 * d / c) / (r2 - r1)
        A2 = current_temp_K - d / c - A1
        A3 = r1 * Ca / Hm + (Ua + Hm) / Hm
        A4 = r2 * Ca / Hm + (Ua + Hm) / Hm

        # Updating the temperature
        old_temp_K = current_temp_K
        new_current_temp_K = (
            A1 * np.exp(r1 * time_step_sec) + A2 * np.exp(r2 * time_step_sec) + d / c
        )
        new_current_mass_temp_K = (
            A1 * A3 * np.exp(r1 * time_step_sec)
            + A2 * A4 * np.exp(r2 * time_step_sec)
            + g
            + d / c
        )

        self.current_temp = new_current_temp_K - 273
        self.current_mass_temp = new_current_mass_temp_K - 273


######### Devices #########

class AbstractDevice(object):
    """
    Abstract class for devices
    """

    def __init__(self, device_properties):
        self.id = device_properties["id"]
        self.device_properties = device_properties

    def step(self, command):
        raise NotImplementedError("Abstract method not implemented")

    def power_consumption(self):
        raise NotImplementedError("Abstract method not implemented")




class HVAC(AbstractDevice):
    """
    Simulator of HVAC object (air conditioner)

    Attributes:

    id: string, unique identifier of the device.
    hvac_properties: dictionary, containing the configuration properties of the HVAC.
    COP: float, coefficient of performance (ratio between cooling capacity and electric power consumption)
    cooling_capacity: float, rate of "negative" heat transfer produced by the HVAC, in Watts
    latent_cooling_fraction: float between 0 and 1, fraction of sensible cooling (temperature) which is latent cooling (humidity)
    turned_on: bool, if the HVAC is currently ON (True) or OFF (False)
    time_step: a timedelta object, representing the time step for the simulation.


    Main functions:

    step(self, command): take a step in time for this TCL, given action of TCL agent
    get_Q(self): compute the rate of heat transfer produced by the HVAC
    power_consumption(self): compute the electric power consumption of the HVAC
    """

    def __init__(self, hvac_properties):
        """
        Initialize the HVAC

        Parameters:
        """

        super().__init__(hvac_properties)
        self.hvac_properties = hvac_properties
        self.COP = hvac_properties["COP"]
        self.cooling_capacity = hvac_properties["cooling_capacity"]
        self.latent_cooling_fraction = hvac_properties["latent_cooling_fraction"]
       
        self.turned_on = False
        self.max_consumption = self.cooling_capacity / self.COP

        if self.latent_cooling_fraction > 1 or self.latent_cooling_fraction < 0:
            raise ValueError(
                "HVAC id: {} - Latent cooling fraction must be between 0 and 1. Current value: {}.".format(
                    self.id, self.latent_cooling_fraction
                )
            )

        if self.cooling_capacity < 0:
            raise ValueError(
                "HVAC id: {} - Cooling capacity must be positive. Current value: {}.".format(
                    self.id, self.cooling_capacity
                )
            )
        if self.COP < 0:
            raise ValueError(
                "HVAC id: {} - Coefficient of performance (COP) must be positive. Current value: {}.".format(
                    self.id, self.COP
                )
            )

    def step(self, target_temp, tolerance_temp, current_temp):
        """
        Turn HVAC on if current temperature is above target temperature + tolerance temperature, turn off if current temperature is below target temperature

        Return: Nothing
        -

        Parameters:
        self
        command: bool, action of the TCL agent (True: ON, False: OFF)
        """
        if current_temp > target_temp + tolerance_temp:
            self.turned_on = True
        elif current_temp < target_temp:
            self.turned_on = False
        else:
            pass

    def get_Q(self):
        """
        Compute the rate of heat transfer produced by the HVAC

        Return:
        q_hvac: float, heat of transfer produced by the HVAC, in Watts

        Parameters:
        self
        """
        if self.turned_on:
            q_hvac = -1 * self.cooling_capacity / (1 + self.latent_cooling_fraction)
        else:
            q_hvac = 0

        return q_hvac

    def power_consumption(self):
        """
        Compute the electric power consumption of the HVAC

        Return:
        power_cons: float, electric power consumption of the HVAC, in Watts
        """
        if self.turned_on:
            power_cons = self.max_consumption
        else:
            power_cons = 0

        return power_cons

    def get_hvac_state(self):
        hvac_state = {
            "turned_on": self.turned_on,
            "power_consumption": self.power_consumption(),
        }
        return hvac_state

class Heater(AbstractDevice):
    """
    Simulator of Heater object (electric heater)

    Attributes:

    id: string, unique identifier of the device.
    heater_properties: dictionary, containing the configuration properties of the heater.
    heating_capacity: float, rate of heat transfer produced by the heater, in Watts
    turned_on: bool, if the heater is currently ON (True) or OFF (False)

    Main functions:

    step(self, command): take a step in time for this heater, given action of heater agent
    get_Q(self): compute the rate of heat transfer produced by the heater
    power_consumption(self): compute the electric power consumption of the heater
    """

    def __init__(self, heater_properties):
        """
        Initialize the heater

        Parameters:
            hvac_properties: dictionary, containing the configuration properties of the HVAC.
        """

        super().__init__(heater_properties)
        self.heater_properties = heater_properties
        self.heating_capacity = heater_properties["heating_capacity"]
       
        self.turned_on = False
        self.max_consumption = self.heating_capacity


        if self.heating_capacity < 0:
            raise ValueError(
                "HVAC id: {} - Cooling capacity must be positive. Current value: {}.".format(
                    self.id, self.heating_capacity
                )
            )

    def step(self, target_temp, tolerance_temp, current_temp):
        """
        Turn heater OFF if current temperature is higher than target temperature, turn ON if current temperature is below target temperature - tolerance temperature

        Return: Nothing
        -

        Parameters:
        self
        command: bool, action of the TCL agent (True: ON, False: OFF)
        """
        if current_temp > target_temp:
            self.turned_on = False
        elif current_temp < target_temp - tolerance_temp:
            self.turned_on = True
        else:
            pass

    def get_Q(self):
        """
        Compute the rate of heat transfer produced by the HVAC

        Return:
        q_hvac: float, heat of transfer produced by the HVAC, in Watts

        Parameters:
        self
        """
        if self.turned_on:
            q_hvac = self.heating_capacity 
        else:
            q_hvac = 0

        return q_hvac

    def power_consumption(self):
        """
        Compute the electric power consumption of the HVAC

        Return:
        power_cons: float, electric power consumption of the HVAC, in Watts
        """
        if self.turned_on:
            power_cons = self.max_consumption
        else:
            power_cons = 0

        return power_cons
    
    def get_heater_state(self):
        heater_state = {
            "turned_on": self.turned_on,
            "power_consumption": self.power_consumption(),
        }
        return heater_state


class ElectricVehicle(AbstractDevice):
    """
    Simulator of Electric Vehicle object (EV)
    
    Attributes:
        -- Car --   
        battery_capacity: float, battery capacity of the EV, in Wh
        max_autonomy: float, maximum autonomy of the EV, in km
        battery_level: float, current battery level of the EV, in Wh
        current_autonomy: float, current autonomy of the EV, in km
        autonomy_objective: float, autonomy objective of the EV, in km
        plug_status: string, status of the EV plug, "plugged" or "unplugged"
        -- Charging station --
        charging_power: float, power of the charging station, in W
        charging_efficiency: float, efficiency of the charging station, ratio
        charging_consumption: float,  consumption of the charging station, in W
        charging_status: string, status of the EV charging station, "idle" or "charging"

    Main functions:
        step(self, time_step, EV_action): take a step in time for this EV, given action of EV agent
        power_consumption(self): compute the electric power consumption of the EV
        get_EV_state(self): return the state of the EV

    """


    def __init__(self, device_properties):
        super().__init__(device_properties)
        self.device_properties = device_properties

        # Car
        self.battery_capacity = device_properties["battery_capacity"]   # Wh
        self.max_autonomy = device_properties["max_autonomy"]           # km
        self.battery_level = device_properties["battery_level"]         # Wh    
        self.current_autonomy = self.max_autonomy * self.battery_level / self.battery_capacity # km     # strong assumption: the autonomy is linear with the battery level
        self.autonomy_objective = device_properties["init_autonomy_objective"] # km

        # Charging station
        self.charging_power = device_properties["charging_power"]                   # W
        self.charging_efficiency = device_properties["charging_efficiency"]         # Ratio
        self.charging_consumption = self.charging_power/self.charging_efficiency    # W

        self.plug_status = "plugged" # "plugged", "unplugged"
        self.charging_status = "idle"   # "idle", "charging"


    def step(self, time_step, EV_action):
        """
        Take a time step for the EV. The EV can be plugged or unplugged, and can charge if it is plugged. 
        The autonomy objective can be set when plugged. This is how an agent can control the consumption of the EV charging process.
        """

        # Accepts a command to plug/unplug the EV, and/or to set the autonomy objective
        if EV_action is None:
            EV_action_plug = None
            EV_action_endtrip_autonomy = None
            EV_action_autonomy_obj = None
        else:
            EV_action_plug = EV_action["plug_action"]
            EV_action_endtrip_autonomy = EV_action["endtrip_autonomy"]
            EV_action_autonomy_obj = EV_action["autonomy_objective"]

        if EV_action_plug == "plug":
            if self.plug_status == "unplugged":
                assert EV_action_endtrip_autonomy is not None   # When the EV is plugged after being unplugged (return from a trip), the remaining autonomy must be told.
                self.battery_level = EV_action_endtrip_autonomy * self.battery_capacity / self.max_autonomy
                self.current_autonomy = EV_action_endtrip_autonomy
            self.plug_status = "plugged" 
            
        elif EV_action_plug == "unplug":
            self.plug_status = "unplugged"

        elif EV_action_plug is None:        # If no command is given, the EV keeps its current plug status and battery level
            pass

        if EV_action_autonomy_obj is not None:      # If such a command is given, the EV sets its autonomy objective
            self.autonomy_objective = EV_action_autonomy_obj


        # If the EV is plugged, it can charge
        ## Charging station decision
        if self.plug_status == "plugged":
            if self.current_autonomy < self.autonomy_objective:
                self.charging_status = "charging"
            elif self.current_autonomy >= self.autonomy_objective:
                self.charging_status = "idle"

        ## Battery level update
            if self.charging_status == "charging":
                self.battery_level += self.charging_power * time_step.seconds / 3600
                if self.battery_level > self.battery_capacity:
                    self.battery_level = self.battery_capacity
                self.current_autonomy = self.max_autonomy * self.battery_level / self.battery_capacity

            elif self.charging_status == "idle":
                pass

   
        # If the EV is unplugged, it cannot charge
        elif self.plug_status == "unplugged":
            self.battery_level = None       # When the EV is unplugged, the battery level is not known
            self.charging_status = "idle"   # The EV cannot charge if it is unplugged
            self.current_autonomy = None    # The autonomy is not known if the EV is unplugged
        
        return self.get_EV_state()  
    
    def power_consumption(self):
        """
        Return the power consumption of the EV
        """
        if self.charging_status == "charging":
            power_cons = self.charging_consumption
        else:
            power_cons = 0
        return power_cons
  
    def get_EV_state(self):
        EV_state = {
            "battery_level": self.battery_level,        
            "current_autonomy": self.current_autonomy,
            "plug_status": self.plug_status,
            "charging_status": self.charging_status,
            "autonomy_objective": self.autonomy_objective,
            "power_consumption": self.power_consumption(),
        }

        return EV_state



    



        

        




    

######### Grid #########

class Grid():
    """
    Grid simulator
    
    Provides a price signal to the house depending on the time of the day, and
    the current outdoor temperature
    """

    def __init__(self, grid_properties):
        """
        Initialize the grid

        Parameters:

        - grid_properties: dictionary, containing the configuration properties
          of the Grid
        """
        self.peak_price = grid_properties["prices"]["peak_price"]
        self.day_price = grid_properties["prices"]["day_price"]
        self.min_temp = grid_properties["min_temp"]
        self.max_temp = grid_properties["max_temp"]
        self.today = grid_properties["today"]
        self.tomorrow = grid_properties["tomorrow"]
        self.current_price = self.day_price
        self.total_expenses = 0.0
        self.day_expenses = 0.0
        self.block_expenses = 0.0

    def step(self, od_temp, power, delta, date_time):
        """
        Take a time step for the house

        Parameters:

        - od_temp: float, current outdoors temperature in Celsius
        - delta: timedelta, time step duration
        - date_time: datetime, current date and time
        """
        self.update_policies(od_temp, delta, date_time)
        self.update_current_price(delta, date_time)
        self.update_expenses(power, delta, date_time)

    def update_policies(self, od_temp, delta, date_time):
        """
        Update today and tomorrow policies

        Parameters:

        - od_temp: float, current outdoors temperature in Celsius
        - delta: timedelta, time step duration
        - date_time: datetime, current date and time
        """
        next_datetime = date_time + delta
        if contains_hour_of_day(date_time, next_datetime, 0):
            # At 0:00, we start a new day
            self.today = self.tomorrow
            self.tomorrow = None
        elif contains_hour_of_day(date_time, next_datetime, 19):
            # At 19:00, the next day policy is published
            is_extreme = lambda t: t < self.min_temp or t > self.max_temp
            self.tomorrow = "variable" if is_extreme(od_temp) else "fixed"

    def update_current_price(self, delta, date_time):
        """
        Update the current price

        Parameters:

        - delta: timedelta, time step duration
        - date_time: datetime, current date and time
        """
        next_datetime = date_time + delta
        if contains_hour_of_day(date_time, next_datetime, 6) or \
           contains_hour_of_day(date_time, next_datetime, 16):
            # At 6:00 and 16:00 we enter a peak block
            self.current_price = self.peak_price if self.today == "variable" \
                                                 else self.day_price
        elif contains_hour_of_day(date_time, next_datetime, 8) or \
             contains_hour_of_day(date_time, next_datetime, 20):
            # At 8:00 and 20:00 we exit a peak block
            self.current_price = self.day_price

    def update_expenses(self, power, delta, date_time):
        r"""
        Update the recorded expenses
        """
        next_datetime = date_time + delta
        energy = power * delta.seconds / 3600.0
        expenses = self.current_price * energy
        day_expenses = expenses
        block_expenses = expenses

        self.total_expenses += expenses
        if contains_hour_of_day(date_time, next_datetime, 0):
            delta = next_datetime - datetime_from_hour_of_day(next_datetime, 0)
            energy = power * delta.seconds / 3600.0
            day_expenses = self.current_price * energy
            self.day_expenses = 0
        self.day_expenses += day_expenses
        def block_hour(date_time, next_datetime):
            for h in range(0, 24, 2):
                if contains_hour_of_day(date_time, next_datetime, h):
                    return h
            return None
        h = block_hour(date_time, next_datetime)
        if h is not None:
            delta = next_datetime - datetime_from_hour_of_day(next_datetime, h)
            energy = power * delta.seconds / 3600.0
            block_expenses = self.current_price * energy
            self.block_expenses = 0.0
        self.block_expenses += block_expenses

    def get_grid_state(self):
        """
        Return the state of the grid

        Return: dict
        """
        return {
            "today": self.today,
            "tomorrow": self.tomorrow,
            "price": self.current_price,
            "total_expenses": self.total_expenses,
            "day_expenses": self.day_expenses,
            "block_expenses": self.block_expenses
        }

if __name__ == "__main__":


    test_type = "test_text"     # "test_EV", "test_HVAC", "test_text"

    if test_type == "test_EV":
        simulator = Simulator(sim_properties)

        env_state = simulator.get_env_state()

        print("Initial state")
        print(env_state["house_state"]["EV"])
        print("------------------")


        action = {
            'target_temp_command': None,
            'EV_action': {
                'plug_action': 'plug',
                'endtrip_autonomy': 20,
                'autonomy_objective': 200
            }
        }
        env_state = simulator.step(action, 60)

        print("After redundant action of plugging")
        print(env_state["house_state"]["EV"])
        print("------------------")


        action = {
            'target_temp_command': None,
            'EV_action': {
                'plug_action': 'unplug',
                'endtrip_autonomy': None,
                'autonomy_objective': None
            }
        }
        env_state = simulator.step(action, 60)

        print("After unplugging")
        print(env_state["house_state"]["EV"])
        print("------------------")


        action = {
            'target_temp_command': None,
            'EV_action': {
                'plug_action': None,
                'endtrip_autonomy': None,
                'autonomy_objective': None
            }
        }
        
        for i in range(60):
            simulator.step(action, 60)
            env_state = simulator.get_env_state()
        env_state = simulator.step(action, 60)

        print("After 1 hour of unplugged")
        print(env_state["house_state"]["EV"])
        print("------------------")
        
        action = {
            'target_temp_command': None,
            'EV_action': {
                'plug_action': 'plug',
                'endtrip_autonomy': 100,
                'autonomy_objective': 150
            }
        }
        env_state = simulator.step(action, 60)

        print("After plugging back and setting autonomy objective to 150 km")
        print(env_state["house_state"]["EV"])
        print("------------------")


        for i in range(60):
            simulator.step(action, 60)
        env_state = simulator.get_env_state()
        print("After 1 hour of charging")
        print(env_state["house_state"]["EV"])
        print("------------------")


        for i in range(600):
            simulator.step(action, 60)
        env_state = simulator.get_env_state()
        print("After 10 hours of charging")
        print(env_state["house_state"]["EV"])
        print("------------------")

        
        action = {
            'target_temp_command': None,
            'EV_action': {
                'plug_action': None,
                'endtrip_autonomy': None,
                'autonomy_objective': 200
            }
        }   

        env_state = simulator.step(action, 60)
        print("After setting autonomy objective to 200 km")
        print(env_state["house_state"]["EV"])
        print("------------------")

        for i in range(60):
            simulator.step(action, 60)
        env_state = simulator.get_env_state()
        print("After 1 hour of charging")
        print(env_state["house_state"]["EV"])
        print("------------------")


    elif test_type == "test_HVAC":

        sim_properties["start_time"] = "2020-01-01 6:00:00"
        simulator = Simulator(sim_properties)

        action = {
            'target_temp_command': None,
            'EV_action': None
        }

        for i in range(60*28):
            simulator.step(action, 60)
            env_state = simulator.get_env_state()
            if i % 2 == 0:
                print("Time: {}, Current temp: {:.2f} C, OD temp: {:.2f} C, House consumption: {:.2f} W, HVAC: {}, Heater: {}".format(env_state['time'], env_state['house_state']['current_temp'], env_state['OD_temp'], env_state['house_state']['house_consumption'], env_state['house_state']['hvac']["turned_on"], env_state['house_state']['heater']['turned_on'])) 




    elif test_type == "test_text":

        sim_properties["start_time"] = "2020-01-02 01:48:00"

        simulator = Simulator(sim_properties)


        action = {
            'target_temp_command': None,
            'EV_action': {
                'plug_action': 'unplug',
                'endtrip_autonomy': None,
                'autonomy_objective': None
            }
        }   
        simulator.step(action, 1)

#        action = {
#            'target_temp_command': None,
#            'EV_action': {
#                'plug_action': 'plug',
#                'endtrip_autonomy': 100,
#                'autonomy_objective': 100
#            }
#        }   

        simulator.step(action, 1)

        print("--- Static properties (this text can be accessed at any time by the agent) --- \n")
        print(simulator.get_house_energy_properties_in_natural_language())
        print(simulator.get_EV_properties_in_natural_language())

        print("--- Initial state (this text can be accessed at any time by the agent) --- \n")
        print(simulator.get_env_state_in_natural_language())

        action = {
            'target_temp_command': 23,
            'EV_action': None
        }   
        print("We send a command. We can ask for the description:")
        print(simulator.describe_action_in_natural_language(action))
        simulator.step(action, 1)

        print("The target temperature is changed, the heater turns on: \n")
        print(simulator.get_env_state_in_natural_language())


        for i in range(15):
            simulator.step(action, 60)

        print("--- We simulate 15 minutes more, to check if the heater works... --- \n")   

        env_state = simulator.get_env_state()
        print(simulator.get_env_state_in_natural_language())


        print("--- The electric car returns from a trip, nearly empty. The owner plugs it and sets the autonomy objective. --- \n")   

        action = {
            'target_temp_command': None,
            'EV_action': {
                'plug_action': 'plug',
                'endtrip_autonomy': 20,
                'autonomy_objective': 200
            }
        }   

        print(simulator.describe_action_in_natural_language(action))

        simulator.step(action, 1)

        print("-- The state is updated accordingly.")
        print(simulator.get_env_state_in_natural_language())

        print("--- We simulate 15 minutes more, to check if the charging works... --- \n")   

        for i in range(15):
            simulator.step(action, 60)
            
        print(simulator.get_env_state_in_natural_language())
