class RESPParser:

    def parse(self, input_string, start_pos = 0):
        if not input_string:
            raise ValueError("Input string cannot be empty.")   
        start_char = input_string[start_pos]
        if start_char == '+':
            result =  self.handle_simple_string(input_string, start_pos)
            return result
        elif start_char == ':':
            result = self.handle_int_string(input_string, start_pos)
            return result
        elif start_char == '$':
            result = self.handle_bulk_string(input_string, start_pos)
            return result
        elif start_char == '*':
            result = self.handle_array(input_string, start_pos)
            return result
        else:
            raise ValueError("Unknown RESP type.")
        
    def handle_simple_string(self, input_string, start_pos):
        end_pos = input_string.find("\r\n", start_pos)
        if end_pos == -1:
            raise ValueError("Missing delimiter")
        return input_string[start_pos + 1:end_pos]
    
    def handle_int_string(self, input_string, start_pos):
        end_pos = input_string.find("\r\n", start_pos)
        if end_pos == -1:
            raise ValueError("Missing delimiter")
        raw_data = input_string[start_pos + 1:end_pos]
        try:
            return int(raw_data)
        except ValueError:
            raise ValueError("Invalid integer value")
        
    def handle_bulk_string(self, input_string, start_pos):
        end_pos = input_string.find("\r\n", start_pos)
        if end_pos == -1:
            raise ValueError("Missing delimiter after $")
        bulk_amount = int(input_string[start_pos + 1:end_pos])
        if bulk_amount == -1:
            return None
        if bulk_amount == 0:
            return ""
        start_pos = end_pos + 2
        end_pos = input_string.find("\r\n", start_pos)
        if end_pos == -1:
            raise ValueError("Missing delimiter after bulk string content")
        content = input_string[start_pos:end_pos]
        if len(content) != bulk_amount:
            raise ValueError("Bulk string length mismatch")
        return content  
    
    def handle_array(self, input_string, start_pos):
        end_pos = input_string.find("\r\n", start_pos)
        if end_pos == -1:
            raise ValueError("Missing delimiter after array length")     
        arr_amount = int(input_string[start_pos + 1:end_pos])
        decrement = arr_amount
        array_arr = []
        current_pos = end_pos + 2  
        while decrement > 0:
            start_char = input_string[current_pos]
            if start_char == '+':
                variable = self.handle_simple_string(input_string, current_pos)
                end_pos = input_string.find("\r\n", current_pos)
            elif start_char == ':':
                variable = self.handle_int_string(input_string, current_pos)
                end_pos = input_string.find("\r\n", current_pos)
            elif start_char == '$':
                variable = self.handle_bulk_string(input_string, current_pos)
                length_pos = input_string.find("\r\n", current_pos)
                content_len = int(input_string[current_pos + 1:length_pos])
                end_pos = length_pos + 2 + content_len  
            elif start_char == '*':
                variable, end_pos = self.handle_array(input_string, current_pos)
            else:
                raise ValueError("Unsupported element type in array")
            array_arr.append(variable)
            current_pos = end_pos + 2
            decrement = decrement - 1
        return array_arr, current_pos -2

if __name__ == "__main__":
    parser = RESPParser()
    user_input = input("Enter a RESP command (e.g., +OK, :5, $5,): ")
    try:
        formatted_input = user_input.replace('\\r\\n', '\r\n')
        if (not formatted_input.endswith('\r\n') 
            and not formatted_input.startswith('$') 
            and not formatted_input.startswith('*')):
            formatted_input += '\r\n'
        if formatted_input[0] == "$":
            result = parser.handle_bulk_string(formatted_input, 0)
        elif formatted_input[0] == "*":
            result, _ = parser.handle_array(formatted_input, 0)
            print(result)
        else:
            result = parser.parse(formatted_input)
        print("Parsed result:", result)
    except ValueError as e:
        print("Error:", e)
    except NotImplementedError as e:
        print("Error:", e)