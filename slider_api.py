"""
Define API for slider via http server
"""
from slider import Slider, MotorDriver
import uasyncio as asyncio


class Move:

    def __init__(self, slider: Slider):
        self.slider = slider
        self.loop = asyncio.get_event_loop()

    """ All action with dolly move
        required json payload with:
            # action: string [calibrate|move]
            # distance: int [mm]
            # direction: string [right|left]
            # time: int time [s] 
    """
    def post(self, api_request):

        if 'body' in api_request:
            if 'action' in api_request['body']:
                return self.__handle_action(api_request['body'])
            else:
                return {'status': 'error', 'message': 'missing_action'}
        else:
            return {'status': 'error', 'message': 'missing_payload'}

    """ Handle specified slider action by request
    """
    def __handle_action(self, request):

        # if self.slider.motor.is_locked():
        #     return {'status': 'error', 'msg': 'motor_locked'}

        if request['action'] == 'calibrate':
            return self.__calibrate()
        elif request['action'] == 'move':
            return self.__move(request)
        else:
            return {'status': 'error', 'msg': 'action_not_found'}

    """ Move dolly
    """
    def __move(self, request):
        direction = MotorDriver.LEFT if request['direction'] == 'left' else MotorDriver.RIGHT
        if 'distance' in request:
            self.slider.move_dolly(int(request['distance']), direction, int(request['time']))
        else:
            self.slider.move_dolly_edge(direction)

        return {'status': 'ok'}


class Stop:

    def __init__(self, slider: Slider):
        self.slider = slider

    """ Stop Motor
    """
    def post(self, api_request):
        self.slider.stop()
        return {'status': 'ok'}


class Status:

    def __init__(self, slider: Slider):
        self.slider = slider

    def get(self, api_request):
        return {
            'dolly_position': self.slider.dolly.get_position(),
            'slider_length': self.slider.length
        }
