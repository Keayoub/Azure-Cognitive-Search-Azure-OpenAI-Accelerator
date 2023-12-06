import azure.functions as func
import logging
from grid_simulator import Simulator, sim_properties


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
grid_simulator = Simulator(sim_properties)


@app.route(route="plug_EV")
def plug_EV(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    action = {
        "target_temp_command": None,
        "EV_action": {
            "plug_action": "plug",
            "endtrip_autonomy": 20,
            "autonomy_objective": 200,
        },
    }
    grid_simulator.step(action, 60)
    current_state = grid_simulator.get_env_state_in_natural_language()
    return func.HttpResponse(
        f"This HTTP triggered function executed successfully. {current_state}",
        status_code=200,
    )


@app.route(route="unplug_EV")
def unplug_EV(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    action = {
        "target_temp_command": None,
        "EV_action": {
            "plug_action": "unplug",
            "endtrip_autonomy": None,
            "autonomy_objective": None,
        },
    }
    grid_simulator.step(action, 60)
    current_state = grid_simulator.get_env_state_in_natural_language()
    return func.HttpResponse(
        f"This HTTP triggered function executed successfully. {current_state}",
        status_code=200,
    )


@app.route(route="unplug_EV")
def unplug_EV(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    action = {
        "target_temp_command": None,
        "EV_action": {
            "plug_action": "unplug",
            "endtrip_autonomy": None,
            "autonomy_objective": None,
        },
    }
    grid_simulator.step(action, 60)
    current_state = grid_simulator.get_env_state_in_natural_language()
    return func.HttpResponse(
        f"This HTTP triggered function executed successfully. {current_state}",
        status_code=200,
    )
