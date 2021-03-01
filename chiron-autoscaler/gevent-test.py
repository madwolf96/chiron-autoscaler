import os
from multiprocessing import Process


def get_os():
    print(os.getenv('PYTHONPATH'))
    print(os.getenv('RABBIT_USERNAME'))


if __name__ == '__main__':
    p_list = []
    for i in range(0, 5):
        p = Process(target=get_os, args=())
        p.start()
        p_list.append(i)

    for p in p_list:
        p.join()
