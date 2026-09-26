import typing
import sys
import adsk.core
from .logging_utils import report_all_exceptions

_inside_callback = False

def register_event_handler(event: adsk.core.Event, callback: typing.Callable[[adsk.core.EventArgs], None]):
    """
    Registers the given callback to the given event. 
    The event arguments are passed to the callback as one argument.
    Exceptions thrown by the callback are logged.

    If the returned handler is freed by the GC, the callback is unregistered. It's therefore important
    to store the handler somewhere.
    """

    # We have to inherit the handler from the correct subclass. 
    # Check the typing annotation of `event.add(handler)` to see what type of handler it takes.
    event_handler_base_class_name = event.add.__annotations__['handler']

    # Find the class object for the handler subclass.
    module = sys.modules[event.__module__]
    handler_type = module.__dict__[event.add.__annotations__['handler']]

    # Create a handler class that invokes the callback.
    class Handler(handler_type):
        def notify(self, args):
            with report_all_exceptions():
                callback(args)
    
    # Create a handler from the class
    handler = Handler()

    # Finally register the handler to the event.
    event.add(handler)
    return handler
