# import drawsvg as dw

# d = dw.Drawing(400, 400)

# print(d)
# print(type(d))

# print("-" * 80)

# print(d.as_svg())

# print("-" * 80)

# for attr in dir(d):
#     if not attr.startswith("_"):
#         print(attr)

import drawsvg as dw

master = dw.Drawing(420, 594)

child = dw.Drawing(200, 280, viewBox="0 0 800 800")
child.append(dw.Circle(400, 400, 300, fill='red'))

print(child.as_svg())

master.append(child)
print(master.as_svg())