import re
from datetime import datetime


# These functions are the agent's tools.
def add_numbers(a, b):
    return a + b


def subtract_numbers(a, b):
    return a - b


def multiply_numbers(a, b):
    return a * b


def divide_numbers(a, b):
    return a / b


def get_current_time():
    return datetime.now().strftime("%I:%M %p")


def get_current_date():
    return datetime.now().strftime("%B %d, %Y")


def run_agent(user_input):
    text = user_input.lower().strip()

    # Rule: show help if the user asks what the agent can do.
    if text == "help" or "what can you do" in text:
        return (
            "I can do calculations, tell you the time or date, "
            "and respond to greetings. Try '12 times 4' or 'what is the date?'"
        )

    # Rule: respond to greetings.
    if re.match(r"^(hi|hello|hey)\b", text):
        return "Hello! What would you like me to do?"

    # Rule: tell the user the current time.
    if "time" in text:
        return f"The current time is {get_current_time()}."

    # Rule: tell the user today's date.
    if "date" in text or "today" in text:
        return f"Today's date is {get_current_date()}."

    # Recognize examples like:
    # "17 plus 29", "17 + 29", "10 divided by 2"
    number = r"-?\d+(?:\.\d+)?"
    operator = (
        r"(?:multiplied by|divided by|plus|minus|times|"
        r"subtract|multiply|divide|add|\+|-|\*|/)"
    )

    match = re.search(
        rf"({number})\s*({operator})\s*({number})",
        text,
    )

    # Rule: choose the correct calculation function.
    if match:
        a = float(match.group(1))
        operation = match.group(2)
        b = float(match.group(3))

        operations = {
            "plus": add_numbers,
            "add": add_numbers,
            "+": add_numbers,

            "minus": subtract_numbers,
            "subtract": subtract_numbers,
            "-": subtract_numbers,

            "times": multiply_numbers,
            "multiply": multiply_numbers,
            "multiplied by": multiply_numbers,
            "*": multiply_numbers,

            "divide": divide_numbers,
            "divided by": divide_numbers,
            "/": divide_numbers,
        }

        # Avoid trying to divide by zero.
        if operation in {"divide", "divided by", "/"} and b == 0:
            return "You can't divide by zero."

        answer = operations[operation](a, b)
        return f"The answer is {answer:g}."

    # Fallback rule if nothing above matched.
    return (
        "I don't recognize that request yet. "
        "Type 'help' to see what I can do."
    )


print("Agent started. Type 'help' for options or 'quit' to stop.")

while True:
    request = input("\nYou: ")

    if request.lower().strip() in {"quit", "exit"}:
        print("Agent: Goodbye!")
        break

    print("Agent:", run_agent(request))