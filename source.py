from dataclasses import dataclass

class Source:
    def __init__(self, name, text):
       self.name = name
       self.text = text
       self.line_beginnings = [0]
       for i, c in enumerate(text):
           if c == '\n':
               self.line_beginnings.append(i + 1)
           
    def get_line_and_column(self, index):
        line = 0
        while line + 1 < len(self.line_beginnings) and self.line_beginnings[line + 1] <= index:
           line += 1
        return line + 1, index - self.line_beginnings[line] + 1

@dataclass
class Location:
    source: Source
    begin: int
    end: int
    
    def line_and_column(self):
        return self.source.get_line_and_column(self.begin)