from flask_socketio import emit
class BaseEnvironment:
    """
    BaseEnvironment class for managing variables and output in a conversational environment.

    This class provides a foundation for storing state, emitting output, and maintaining
    a chat history. It tracks variables, the last computed value, and all outputs.

    Attributes:
        _vars (dict): Internal dictionary storing named variables.
        last: The last value that was output or retrieved.
        chat (list): List of all string outputs emitted during the session.
    """
    def __init__(self):
        self._vars = {}
        self.last = ""
        self.chat = []

    def output(self, x):
        """
        Output a value to the server and append it to the chat history.
        
        Attempts to emit the provided value as a string to the server. If a RuntimeError
        occurs during emission, it is silently caught and ignored. The string representation
        of the value is then appended to the chat history and stored as the last output.
        
        Args:
            x: The value to output. Will be converted to a string.
        """
        try:
            emit("server", str(x))
        except RuntimeError:
            pass
        self.chat.append(str(x))
        self.last = x

    def get(self, name):
        """
        Retrieve the value of a variable by name and update the last accessed variable.
        
        Args:
            name: The name of the variable to retrieve.
            
        Returns:
            The value of the variable corresponding to the given name.
            
        Raises:
            KeyError: If the variable name does not exist in the variables dictionary.
        """
        self.last = self._vars[name]

    def set(self, name, value):
        """
        Set a variable in the environment.

        Args:
            name (str): The name of the variable to set.
            value: The value to assign to the variable.
        """
        self._vars[name] = value


class CEnvironment(BaseEnvironment):
    def __init__(self):
        super().__init__()
        self.heap = [{"value": None, 'free': True} for _ in range(255)]
        self._first_free = 1

    def alloc(self, amount):
        if self.heap[self._first_free]['free'] is False:
            return None
        self.heap[self._first_free]['free'] = False
        self.heap[self._first_free]['value'] = [None for _ in range(amount)]
        addr = self._first_free
        self._first_free = 1
        while not self.heap[self._first_free]['free']:
            self._first_free += 1
        return str(hex(addr))[2:]

    def free(self, addr):
        addr = int(addr, 16)
        self.heap[addr]['free'] = True
        self.heap[addr]['value'] = None
        self._first_free = addr

    def heapget(self, addr, inneraddr):
        self.last = self.heap[int(addr, 16)]['value'][int(inneraddr, 16)]

    def heapset(self, addr, inneraddr, value):
        self.heap[int(addr, 16)]['value'][int(inneraddr, 16)] = value


class BaseEnvType:
    """
    Base class for environment types.

    This class serves as a foundation for creating typed environment variables.
    It wraps a value and provides conversion methods to standard Python types.

    Attributes:
        value: The underlying value of the environment type.

    Methods:
        __int__: Convert the value to an integer.
        __str__: Convert the value to a string representation.
    """
    def __init__(self, value):
        self.value = value

    def __int__(self):
        return int(self.value)

    def __str__(self):
        return str(self.value)


class Variable(BaseEnvType):
    """
    Represents a variable in the environment type system.
    A Variable is a basic environment type that can hold or reference values
    within the type system. It serves as a fundamental building block for
    constructing more complex type structures.
    """
    pass


class BlockType(BaseEnvType):
    """
    Represents a block in the environment type system.
    A BlockType is a basic environment type that can hold or reference values
    within the type system. It serves as a fundamental building block for
    constructing more complex type structures.
    """
    
    @property
    def converted(self):
        """
        Return the converted value by removing the first and last characters.

        Returns:
            str: The value with the first and last characters removed.
        """
        return self.value[1:-1]


class HexValue(BaseEnvType):
    """
    A class representing hexadecimal values.

    This class extends BaseEnvType to provide hexadecimal representation
    of numeric values.

    Properties:
        as_hex (str): Returns the hexadecimal string representation of the value.
            Example: hex(255) returns '0xff'
    """
    @property
    def as_hex(self):
        return hex(self.value)
