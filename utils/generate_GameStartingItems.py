import sys

BASE_STRING = 'level{0} = GameStartingItem({0})'


for i in range(int(sys.argv[1])):
    print(BASE_STRING.format(i))
