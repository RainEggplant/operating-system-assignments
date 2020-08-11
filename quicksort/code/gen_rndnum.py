from argparse import ArgumentParser
from random import randint


def main():
    with open(args.output, 'w') as f:
        generator = (str(randint(0, (1 << 31) - 1)) + '\n' for n in range(args.number))
        f.writelines(generator)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.description = 'Generate a text file with specified number of random integers'
    parser.add_argument('-n', '--number', dest='number', type=int, default=1000000,
                        help='the number of random integers')
    parser.add_argument('-o', '--output', dest='output', type=str, default='random.txt',
                        help='output filename')
    args = parser.parse_args()

    main()
