import os
import re
def main():
    pattern = re.compile(r"(^[\da-z](?=[ \n])|(?<= )[\da-z]+(?=[ \n])|(?<= )[\da-z]+$|^[\da-z]+$)|((\b\d+\b)\*(\b[\da-z]+\b))")
    with open("mem2") as mem_file:
        mem_file.readline()
        for line in mem_file.readlines():
            for cell in pattern.findall(line):
                if cell[0] != "":
                    print(f"{int(cell[0], 16):08b}", end=" ")
                elif cell[1] != "":
                    print(cell[1], end=" ") 
            print()
        
        mem_file.seek(0)

        target_index = 6
        char = '1'
        
        mem_file.readline()
        for line in mem_file.readlines():
            for cell in pattern.findall(line):
                if cell[0] != "":
                    if int(cell[0], 16) == 0:
                        new = "0"
                    else:
                        old = f"{int(cell[0], 16):08b}"
                        new = old[:-target_index] + char + old[-target_index:]
                        new = f"{int(new, 2):x}"
                    print(new, end=" ")
                elif cell[1] != "":
                    print(cell[1], end=" ") 
            print()


if __name__ == "__main__":
    main()