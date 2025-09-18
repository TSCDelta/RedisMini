import ast
class SimpleString:
    def __init__(self, value: str):
        self.value = value


class Serializer:
    def serialize(self, value):
        if isinstance(value, SimpleString):
            result = f"+{value.value}\r\n"
            return result
        if isinstance(value, str):
            result = f"${len(value)}\r\n" + value + "\r\n"
            return result
        if isinstance(value, int):
            result = f":{value}\r\n"
            return result
        if isinstance(value, list):
            result = f"*{len(value)}" + "\r\n"
            for val in value:
                result += str(self.serialize(val))
            return result

if __name__ == "__main__":
    serializer = Serializer()
    value_type = input("Type (str/int/simple/list): ").strip()
    user_input = input("Enter a string to serialize: ")
    if value_type == "int":
        value = int(user_input)
    elif value_type == "str":
        value = user_input
    elif value_type == "simple":
        value = SimpleString(user_input)  
    elif value_type == "list":
        value = ast.literal_eval(user_input)
    else:
        raise ValueError("invalid type")

    
    try:
        
        result = serializer.serialize(value)
        print("Serialized RESP string:")
        print(repr(result))  
    except TypeError as e:
        print("Error:", e)