import random
import string

def generate_random_corpus(filename: str, num_lines: int = 50, words_per_line: int = 15):
    """Generates a text file containing randomized alphanumeric strings and symbols."""
    
    # Define the character pool: lowercase, uppercase, digits, and common typing symbols
    char_pool = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    with open(filename, 'w', encoding='utf-8') as f:
        for _ in range(num_lines):
            line = []
            for _ in range(words_per_line):
                # Generate random "words" of lengths between 2 and 10 characters
                word_length = random.randint(2, 10)
                word = ''.join(random.choice(char_pool) for _ in range(word_length))
                line.append(word)
            
            f.write(" ".join(line) + "\n")
            
    print(f"Random corpus generated: {filename}")

if __name__ == "__main__":
    generate_random_corpus("random_training_data.txt", num_lines=100)