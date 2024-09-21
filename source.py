from dataclasses import dataclass

class Source:
    def __init__(self, name, text):
       self.name = name
       self.text = text
       self.line_beginnings = [0]
       self.lines = text.splitlines()
       for i, c in enumerate(text):
           if c == '\n':
               self.line_beginnings.append(i + 1)
           
    def get_line_and_column(self, index):
        line = 0
        while line + 1 < len(self.line_beginnings) and self.line_beginnings[line + 1] <= index:
           line += 1
        return line, index - self.line_beginnings[line]

    def split_lines(self, begin, end):
        begin_line, _ = self.get_line_and_column(begin)
        end_line, _ = self.get_line_and_column(end)

        if begin_line == end_line:
            return [Location(self, begin, end)]

        spans = []
        spans.append(Location(self, begin, self.line_beginnings[begin_line + 1] - 1))
        for line in range(begin_line + 1, end_line):
            spans.append(
                Location(self, self.line_beginnings[line], self.prefix_sums[line + 1] - 1))
        spans.append(Location(self, self.line_beginnings[end_line], end))
        return spans

@dataclass
class Location:
    source: Source
    begin: int
    end: int
    
    def begin_line(self):
        return self.begin_line_and_column()[0]

    def begin_column(self):
        return self.begin_line_and_column()[1]

    def begin_line_and_column(self):
        return self.source.get_line_and_column(self.begin)

    def wrap(left, right):
        return Location(left.source, left.begin, right.end)

    def split_lines(self):
        return self.source.split_lines(self.begin, self.end)

    def len(self):
        return self.end - self.begin