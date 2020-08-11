import argparse
from threading import Event, Thread, Semaphore, Lock

DEBUG = True  # 是否输出调试信息


class Bank:
    """表示银行服务的类"""
    def __init__(self):
        self.time = 0
        self.queue = []  # 顾客的等待队列及其锁
        self.mutex_queue = Lock()
        self.customers = []
        self.tellers = []
        self.total_served = 0  # 已完成服务的人数及其锁
        self.mutex_total = Lock()

    def start(self):
        """启动银行服务"""
        # 绑定顾客到本银行，启动每个顾客的线程
        for customer in self.customers:
            customer.bank = self
            customer.start()

        # 绑定柜员到本银行，启动每个柜员的线程
        for teller in self.tellers:
            teller.bank = self
            teller.start()

        # 离散时钟
        while self.total_served < len(self.customers):
            self.time += 1
            # 在一个时钟周期内，先运行所有顾客的线程
            for customer in self.customers:
                if not customer.done.is_set():  # 仅处理仍未完成服务的顾客
                    customer.wait_tick.release()

            for customer in self.customers:
                if not customer.done.is_set():
                    customer.wait_tock.acquire()

            # 再运行所有柜员的线程
            for teller in self.tellers:
                teller.wait_tick.release()

            for teller in self.tellers:
                teller.wait_tock.acquire()

        # 所有顾客已服务完毕（其线程已停止），此时停止所有柜员的线程
        for teller in self.tellers:
            teller.finish()

        # 输出结果
        for customer in self.customers:
            print("{} {} {} {} {}".format(customer.no, customer.t_in, customer.t_serve,
                                          customer.t_serve + customer.duration, customer.teller_no))


class Customer:
    """顾客类"""
    def __init__(self, no, t_in, duration):
        self.no = no  # 顾客编号
        self.t_in = t_in  # 顾客进入银行的时间
        self.duration = duration  # 需要服务的时长
        self.t_serve = None  # 接受服务的时间
        self.bank = None  # 所属的银行对象
        self.teller_no = None  # 提供服务的柜员号
        self.wait_tick = Semaphore(0)  # 用于与时钟同步的一对信号量
        self.wait_tock = Semaphore(0)
        self.done = Event()  # 用于结束线程的事件
        self._thread = Thread(target=self.tick)
        self._thread.setDaemon(True)

    def enqueue(self):
        """加入队列"""
        self.bank.mutex_queue.acquire()  # lock customer queue
        self.bank.queue.append(self)
        if DEBUG:
            print('Time {}: Customer {} enters into queue'.format(self.bank.time, self.no))
        self.bank.mutex_queue.release()  # unlock customer queue

    def tick(self):
        while not self.done.is_set():
            self.wait_tick.acquire()
            if self.bank.time == self.t_in:  # 在对应的时间取号
                self.enqueue()
            self.wait_tock.release()
        self.wait_tock.release()  # 进程被结束时也需要释放信号量

    def start(self):
        self._thread.start()

    def finish(self):
        self.done.set()


class Teller:
    """柜员类"""
    def __init__(self, no):
        self.no = no  # 柜员编号
        self.bank: Bank = None
        self.wait_tick = Semaphore(0)
        self.wait_tock = Semaphore(0)
        self._current_customer: Customer = None  # 当前服务的顾客
        self.done = Event()
        self._thread = Thread(target=self.tick)
        self._thread.setDaemon(True)

    def tick(self):
        while not self.done.is_set():
            self.wait_tick.acquire()
            if self._current_customer is not None:
                # 如果当前有服务的顾客，则判断是否已服务完毕
                if self.bank.time == self._current_customer.t_serve + self._current_customer.duration:
                    # 服务完毕，终止顾客线程，清除 _current_customer 以准备迎接下一顾客
                    self._current_customer.finish()
                    if DEBUG:
                        print('Time {}: Teller {} finishes serving Customer {}'.format(
                            self.bank.time, self.no, self._current_customer.no))
                    self._current_customer = None
                    self.bank.mutex_total.acquire()
                    self.bank.total_served += 1
                    self.bank.mutex_total.release()

            if self._current_customer is None:
                # 尝试叫号
                customer = None
                self.bank.mutex_queue.acquire()
                if len(self.bank.queue) > 0:
                    customer = self.bank.queue.pop(0)
                self.bank.mutex_queue.release()

                if customer is not None:
                    # 若成功叫号
                    if DEBUG:
                        print('Time {}: Teller {} starts serving Customer {}'.format(
                            self.bank.time, self.no, customer.no))
                    customer.t_serve = self.bank.time
                    customer.teller_no = self.no

                    # 如果用户所需的服务时长大于 1，则设为当前的用户。否则在本周期即完成了服务。
                    if customer.duration > 1:
                        self._current_customer = customer
                    else:
                        customer.finish()
                        if DEBUG:
                            print('Time {}: Teller {} finishes serving Customer {}'.format(
                                self.bank.time + 1, self.no, customer.no))
                        self.bank.mutex_total.acquire()
                        self.bank.total_served += 1
                        self.bank.mutex_total.release()

            self.wait_tock.release()
        self.wait_tock.release()

    def start(self):
        self._thread.start()

    def finish(self):
        self.done.set()


def main():
    parser = argparse.ArgumentParser(
        description='This solves the "Bank Teller Service" problem.')
    parser.add_argument('filename', type=str, help='Filename of test case')
    parser.add_argument('n_teller', type=int, help='Number of teller')
    args = parser.parse_args()

    bank = Bank()
    load_customers(args.filename, bank)
    load_tellers(args.n_teller, bank)
    bank.start()


def load_customers(filename, bank: Bank):
    """加载顾客到银行中"""
    with open(filename) as f:
        lines = f.readlines()
        for line in lines:
            props = line.split()
            customer = Customer(int(props[0]), int(props[1]), int(props[2]))
            bank.customers.append(customer)


def load_tellers(number, bank: Bank):
    """加载柜员到银行中"""
    for k in range(number):
        bank.tellers.append(Teller(k + 1))


if __name__ == '__main__':
    main()
