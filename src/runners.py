from env_types import Variable, BlockType, BaseEnvironment, HexValue
from json import loads, dumps


def split_by_not_in_blocks_or_strings(text: str, sep: str = " "):
    """
    Split `text` by `sep` but ignore separators inside:
      - single or double quotes
      - blocks `( ... )` outside quotes
    Handles escaped quotes and separators.
    """
    result = []
    buf = []
    depth = 0
    in_quote = None
    escape = False

    for c in text:
        if escape:
            buf.append(c)
            escape = False
            continue

        if c == "\\":
            buf.append(c)
            escape = True
            continue

        # start or end quote
        if in_quote:
            buf.append(c)
            if c == in_quote:
                in_quote = None
            continue
        elif c in ("'", '"'):
            buf.append(c)
            in_quote = c
            continue

        # handle blocks only outside quotes
        if c == "(" and not in_quote:
            depth += 1
            buf.append(c)
            continue
        if c == ")" and not in_quote:
            depth -= 1
            buf.append(c)
            continue

        # split only if outside quotes and blocks
        if c == sep and depth == 0 and not in_quote:
            result.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)

    if buf:
        result.append("".join(buf).strip())

    return result


class BaseRunner:
    """Base Runner is used ONLY to create other Runner classes"""
    COMMANDS = {}

    def __init__(self, val="", args=None, env=BaseEnvironment()):
        """
        Initialize a Runner instance.

        Args:
            val (str, optional): The value to store in the runner. Defaults to an empty string.
            args (list, optional): A list of arguments for the runner. If None, defaults to an empty list.
            env (BaseEnvironment, optional): The environment context for the runner. Defaults to a new BaseEnvironment instance.
        """

        self._value = val
        if args is not None:
            self._args = args
        else:
            self._args = []
        self.env = env

    @staticmethod
    def floating(val):
        """
        Check if a value can be converted to a float.

        Args:
            val: The value to check for float conversion compatibility.

        Returns:
            bool: True if the value can be successfully converted to a float,
                False if a TypeError is raised during conversion.
        """
        try:
            float(val)
            return True
        except TypeError:
            return False

    @staticmethod
    def hexable(val):
        """
        Check if a value can be converted to a hexadecimal integer.

        Args:
            val: The value to check if it's a valid hexadecimal string.

        Returns:
            bool: True if val can be converted to a hexadecimal integer, False otherwise.
        """
        try:
            int(val, 16)
            return True
        except TypeError:
            return False

    def to_type(self, s: str):
        """
        Convert a string representation into its corresponding Python type or custom object.
        
        This method attempts to parse the input string and return the appropriate type:
        - Returns the input unchanged if it's not a string
        - Quoted strings (enclosed in double quotes) are returned without quotes
        - Numeric strings are converted to int
        - Float strings are converted to float
        - JSON-like strings (enclosed in {} or []) are parsed as JSON objects
        - Hexadecimal strings are converted to HexValue objects
        - Strings starting with "0x" followed by hex digits are converted to HexValue objects
        - Parenthesized strings are converted to BlockType objects
        - All other strings are treated as Variable objects
        
        Args:
            s (str): The string to convert to an appropriate type.
        
        Returns:
            Union[str, int, float, dict, list, HexValue, BlockType, Variable]: 
                The converted value in its appropriate type.
        """
        if not isinstance(s, str):
            return s
        if len(s) >= 2 and s.startswith("\"") and s[-1] == "\"":
            return s[1:-1]
        elif s.isdigit():
            return int(s)
        elif self.floating(s):
            return float(s)
        elif len(s) >= 2 and s[0] in {"{", "["} and s[-1] in {"}", "]"}:
            return loads(s)
        elif self.hexable(s):
            return HexValue(int(s, 16))
        elif s[:2] == "0x" and self.hexable(s[2:]):
            return HexValue(int(s[2:], 16))
        elif len(s) >= 2 and s.startswith("(") and s[-1] == ")":
            return BlockType(s)
        else:
            return Variable(s)

    def from_type(self, s: str):
        """
        Convert a value to a string representation based on its type.

        Args:
            s (str): The value to convert to string format.

        Returns:
            str: String representation of the input value. For primitive types (str, HexValue, 
                 float, int, BlockType), returns the string conversion. For complex types 
                 (dict, list), returns a JSON string with ensure_ascii=False.

        Raises:
            None explicitly raised, but may raise exceptions from str() or dumps() if conversion fails.
        """
        ts: type = type(s)
        if ts in {str, HexValue, float, int, BlockType}:
            return str(s)
        elif ts in {dict, list}:
            return dumps(s, ensure_ascii=False)

    @classmethod
    def register_as_command(cls, name):
        """
        Decorator that registers a function as a command for a specific language runner.
        
        This class method allows functions to be registered in the COMMANDS dictionary
        of a runner class, making them available as named commands for that runner.
        
        Args:
            cls: The class (runner) for which the command is being registered.
            name (str): The name of the command to register.
        
        Returns:
            function: A decorator function that registers the decorated function.
        
        Raises:
            TypeError: If the method is called on BaseRunner directly, as it cannot
                       be used as a specific language runner.
        
        Example:
            @MyRunner.register_as_command("run")
            def my_command():
                pass
        """
        if cls is BaseRunner:
            raise TypeError("BaseRunner can't be used as a specific language runner")
        def decorator(func):
            cls.COMMANDS[name] = func
            return func
        return decorator

    @classmethod
    def from_string(cls, s, env):
        """
        Create an instance from a string representation.

        Args:
            s: A string containing a callable name followed by space-separated arguments.
            env: The environment context in which to evaluate the arguments.

        Returns:
            An instance of the class with the parsed name, converted arguments, and given environment.

        Example:
            >>> obj = cls.from_string("function_name arg1 arg2", env)
        """
        sp = split_by_not_in_blocks_or_strings(s)
        all_args = [cls("", None, BaseEnvironment()).to_type(i) for i in sp[1:]]
        return cls(sp[0], all_args, env)

    def run(self, error=False):
        """
        Execute a command from the COMMANDS registry based on the stored value and arguments.

        Args:
            error (bool, optional): If True, re-raises any exception that occurs during command execution.
                                   If False, exceptions are silently caught. Defaults to False.

        Raises:
            Exception: Re-raised if error=True and an exception occurs during command execution.

        Notes:
            - The command is looked up in self.COMMANDS dictionary using self._value as the key.
            - Arguments are passed from self._args along with the current environment (self.env).
        """
        try:
            self.COMMANDS[self._value](*self._args, env=self.env)
        except Exception:
            if error:
                raise
