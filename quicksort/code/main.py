from argparse import ArgumentParser
from quicksort_service import QuicksortService


def main():
    # read data
    data = []
    with open(args.input) as f:
        for line in f:
            data.append(int(line))

    # perform quicksort
    sorter = QuicksortService(data, args.n_threads)
    sorter.sort()

    # output result
    with open(args.output, 'w') as f:
        f.writelines((str(val) + '\n' for val in sorter.data))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.description = 'Perform quicksort on given data with given number of threads, then output the result'
    parser.add_argument('-i', '--input', dest='input', type=str, default='random.txt',
                        help='input filename')
    parser.add_argument('-o', '--output', dest='output', type=str, default='result.txt',
                        help='output filename')
    parser.add_argument('-n', '--n_threads', dest='n_threads', type=int, default=20,
                        help='the number of threads used for quicksort')
    args = parser.parse_args()

    main()
