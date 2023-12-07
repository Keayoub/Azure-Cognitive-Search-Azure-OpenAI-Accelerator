import azure.functions as func
import logging
import json
from env import Simulator, sim_properties


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
grid_simulator = Simulator(sim_properties)


@app.route(route="plug_EV")
def plug_EV(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("plug_EV function processed a request.")

    action = {
        "target_temp_command": None,
        "EV_action": {
            "plug_action": "plug",
            "endtrip_autonomy": 20,
            "autonomy_objective": 200,
        },
    }
    grid_simulator.step(action, 1)
    current_state = grid_simulator.get_env_state_in_natural_language()
    return func.HttpResponse(
        f"{current_state}",
        status_code=200,
    )


@app.route(route="unplug_EV")
def unplug_EV(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("unplug_EV function processed a request.")

    action = {
        "target_temp_command": None,
        "EV_action": {
            "plug_action": "unplug",
            "endtrip_autonomy": None,
            "autonomy_objective": None,
        },
    }
    grid_simulator.step(action, 1)
    current_state = grid_simulator.get_env_state_in_natural_language()
    return func.HttpResponse(
        f"{current_state}",
        status_code=200,
    )


@app.route(route="change_hvac")
def change_hvac(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("change_hvac function processed a request.")

    temperature = req.params.get("temperature")
    if not temperature:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            temperature = req_body.get("temperature")
    logging.info(f"Temperature: {temperature}")
    if temperature:
        action = {"target_temp_command": int(temperature), "EV_action": None}
        grid_simulator.step(action, 1)
        current_state = grid_simulator.get_env_state_in_natural_language()
        return func.HttpResponse(
            f"Temperature changed to: {temperature}. {current_state}"
        )
    else:
        return func.HttpResponse(
            "This HTTP triggered function executed successfully. Pass a temperature in the query string or in the request body.",
            status_code=200,
        )


@app.route(route="run_for_time")
def run_for_time(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("run_for_time the simulator.")

    minute = req.params.get("minute")
    if not minute:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            minute = req_body.get("minute")
    if minute is not None:
        grid_simulator.run_for_time(int(minute))
        current_state = grid_simulator.get_env_state_in_natural_language()
        return func.HttpResponse(f"Simulator ran for {minute} minutes. {current_state}")
    else:
        return func.HttpResponse(
            "This HTTP triggered function executed successfully. Pass a temperature in the query string or in the request body.",
            status_code=200,
        )


@app.route(route="get_env_status")
def get_env_status(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("get_env_status function processed a request.")
    current_state = grid_simulator.get_env_state_in_natural_language()
    return func.HttpResponse(
        f"{current_state}",
        status_code=200,
    )


@app.route(route="execute_action")
def execute_action(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("execute_action function processed a request.")

    # read content from body
    action = req.get_json()
    logging.info(f"Request body: {action}")
    # logging.info(f"Action: {action["target_temp_command"]}")

    grid_simulator.step(action, 60)
    current_state = grid_simulator.get_env_state_in_natural_language()
    return func.HttpResponse(
        f"{current_state}",
        status_code=200,
    )
