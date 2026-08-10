import random
from typing import Optional, Dict

# Small mock dataset
DATASET = {
    "science": {
        "class 9": [
            {
                "question": "What is the fundamental unit of life?",
                "answer": "The cell.",
                "difficulty": "easy"
            },
            {
                "question": "State Newton's first law of motion.",
                "answer": "An object remains in a state of rest or of uniform motion in a straight line unless compelled to change that state by an applied force.",
                "difficulty": "medium"
            },
            {
                "question": "What is sublimation?",
                "answer": "The transition of a substance directly from the solid to the gas state, without passing through the liquid state.",
                "difficulty": "medium"
            },
            {
                "question": "Name the tissue responsible for the transportation of water in plants.",
                "answer": "Xylem.",
                "difficulty": "easy"
            },
            {
                "question": "What is the chemical formula for water?",
                "answer": "H2O.",
                "difficulty": "easy"
            }
        ],
        "class 10": [
            {
                "question": "What is photosynthesis and why is it important for plants?",
                "answer": "Photosynthesis is the process by which green plants make their own food using sunlight, water, and carbon dioxide. It is important because it provides the food and energy for the plant to grow, and releases oxygen into the air.",
                "difficulty": "medium"
            },
            {
                "question": "What is a chemical reaction?",
                "answer": "A process in which one or more substances are converted to one or more different substances.",
                "difficulty": "medium"
            },
            {
                "question": "Name the acid present in our stomach.",
                "answer": "Hydrochloric acid (HCl).",
                "difficulty": "easy"
            },
            {
                "question": "What is the SI unit of electric current?",
                "answer": "Ampere.",
                "difficulty": "easy"
            },
            {
                "question": "What is an alloy?",
                "answer": "A homogeneous mixture of two or more metals, or a metal and a non-metal.",
                "difficulty": "medium"
            }
        ]
    },
    "maths": {
        "class 9": [
            {
                "question": "What is a rational number?",
                "answer": "A number that can be expressed in the form p/q, where p and q are integers and q is not equal to zero.",
                "difficulty": "easy"
            },
            {
                "question": "What is the formula for the area of a triangle?",
                "answer": "Half multiplied by base multiplied by height (1/2 * base * height).",
                "difficulty": "easy"
            },
            {
                "question": "What is a linear equation in two variables?",
                "answer": "An equation that can be put in the form ax + by + c = 0, where a, b and c are real numbers, and a and b are not both zero.",
                "difficulty": "medium"
            },
            {
                "question": "What is the sum of angles in a triangle?",
                "answer": "180 degrees.",
                "difficulty": "easy"
            },
            {
                "question": "What is the Pythagorean theorem?",
                "answer": "In a right-angled triangle, the square of the hypotenuse is equal to the sum of the squares of the other two sides.",
                "difficulty": "medium"
            }
        ],
        "class 10": [
            {
                "question": "What is an arithmetic progression?",
                "answer": "A sequence of numbers in which the difference between any two consecutive terms is constant.",
                "difficulty": "medium"
            },
            {
                "question": "What is the probability of a sure event?",
                "answer": "One.",
                "difficulty": "easy"
            },
            {
                "question": "What is the distance formula between two points?",
                "answer": "The square root of the sum of the squares of the differences of their x and y coordinates.",
                "difficulty": "medium"
            },
            {
                "question": "What is the trigonometric ratio for Sine (sin)?",
                "answer": "Perpendicular divided by Hypotenuse.",
                "difficulty": "medium"
            },
            {
                "question": "What is the formula for the volume of a cylinder?",
                "answer": "Pi multiplied by radius squared multiplied by height (πr²h).",
                "difficulty": "medium"
            }
        ]
    },
    "history": {
        "class 9": [
            {
                "question": "When did the French Revolution begin?",
                "answer": "1789.",
                "difficulty": "easy"
            },
            {
                "question": "Who was the ruler of France during the French Revolution?",
                "answer": "King Louis XVI.",
                "difficulty": "medium"
            },
            {
                "question": "What was the main cause of the Russian Revolution?",
                "answer": "Economic hardship, unequal distribution of land, and poor working conditions.",
                "difficulty": "medium"
            },
            {
                "question": "Who led the Bolsheviks in Russia?",
                "answer": "Vladimir Lenin.",
                "difficulty": "easy"
            },
            {
                "question": "What is Nazism?",
                "answer": "The political principles of the National Socialist German Workers' Party, led by Adolf Hitler.",
                "difficulty": "medium"
            }
        ],
        "class 10": [
            {
                "question": "When did the Non-Cooperation Movement begin in India?",
                "answer": "1920.",
                "difficulty": "easy"
            },
            {
                "question": "Who wrote 'Hind Swaraj'?",
                "answer": "Mahatma Gandhi.",
                "difficulty": "easy"
            },
            {
                "question": "What was the Rowlatt Act?",
                "answer": "An act that gave the British government enormous powers to repress political activities, and allowed detention of political prisoners without trial for two years.",
                "difficulty": "medium"
            },
            {
                "question": "What was the significance of the Dandi March?",
                "answer": "It marked the beginning of the Civil Disobedience Movement by breaking the salt law.",
                "difficulty": "medium"
            },
            {
                "question": "What was the main objective of the Simon Commission?",
                "answer": "To look into the functioning of the constitutional system in India and suggest changes.",
                "difficulty": "medium"
            }
        ]
    }
}

def get_random_question(subject: str, class_level: str, topic: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Fetches a random question from the dataset based on subject and class.
    
    Returns:
        dict: containing 'question', 'answer', and 'difficulty'.
        None if the dataset doesn't have the requested subject/class.
    """
    subject_lower = subject.lower().strip()
    class_level_lower = class_level.lower().strip()
    
    # Handle variations in class level input (e.g., '9', 'class 9', 'class9')
    if class_level_lower.isdigit():
        class_level_lower = f"class {class_level_lower}"
    elif "class" in class_level_lower and not " " in class_level_lower:
        class_level_lower = class_level_lower.replace("class", "class ")
        
    if subject_lower not in DATASET:
        return None
        
    class_data = DATASET[subject_lower]
    if class_level_lower not in class_data:
        return None
        
    questions = class_data[class_level_lower]
    if not questions:
        return None
        
    # Pick a random question
    selected = random.choice(questions)
    
    # Format into a natural language string response
    response = (
        f"Here is a {selected['difficulty']} {class_level_lower} {subject_lower} question. "
        f"{selected['question']} \n\n"
        f"(Expected Answer: {selected['answer']})"
    )
    
    return {
        "text": response,
        "difficulty": selected['difficulty']
    }
