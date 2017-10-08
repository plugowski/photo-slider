"""
Define API for slider via http server
"""
from slider import Slider
import uasyncio as asyncio


class Move:

    def __init__(self, slider: Slider):
        self.slider = slider
        self.loop = asyncio.get_event_loop()

    def get(self, api_request):
        return {
            'dolly_position': self.slider.dolly.current_position,
            'slider_length': self.slider.length
        }

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
        if request['action'] == 'calibrate':
            return self.__calibrate()
        elif request['action'] == 'stop':
            return self.__stop()
        elif request['action'] == 'move':
            return self.__move(request)

    """ Slider calibration trigger
    """
    def __calibrate(self):
        self.loop.create_task(self.slider.calibrate())
        return {'status': 'ok'}

    """ Move dolly
    """
    def __move(self, request):
        direction = 1 if request['direction'] == 'left' else 0
        self.slider.move_dolly(request['distance'], direction, request['time'])
        return {'status': 'ok'}

    """ Stop motor!
    """
    def __stop(self):
        self.slider.stop()
        return {'status': 'ok'}
