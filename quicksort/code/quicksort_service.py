from threading import Lock, Event
from concurrent.futures import ThreadPoolExecutor


class QuicksortService:
    def __init__(self, data, n_threads=20):
        self._data = data
        self._executor = ThreadPoolExecutor(max_workers=n_threads)
        self._n_thread = 0
        self._n_thread_lock = Lock()
        self._thread_done = Event()

    @property
    def data(self):
        return self._data

    def sort(self):
        self._thread_done.clear()
        if len(self._data) > 1000:
            with self._n_thread_lock:
                self._n_thread += 1
            self._executor.submit(self._quicksort, 0, len(self._data) - 1, True)

            while True:
                self._thread_done.wait()
                with self._n_thread_lock:
                    if self._n_thread == 0:
                        return
                    self._thread_done.clear()
        else:
            self._quicksort(0, len(self._data) - 1)

    def _quicksort(self, left, right, new_thread=False):
        if left >= right:
            return

        # choose median as pivot
        candidate_index = [left, (left + right) // 2, right]
        pivot_index = sorted(candidate_index, key=lambda val: self._data[val])[1]
        self._data[right], self._data[pivot_index] = self._data[pivot_index], self._data[right]

        i = left
        j = right - 1
        pivot = self._data[right]
        while True:
            # from L to R, find the first element greater than or equal to the pivot
            while self._data[i] < pivot:
                i += 1
            # from R to L, find the first element less than the pivot
            while i < j and self._data[j] >= pivot:
                j -= 1
            # if markers do not intersect, then swap the elements
            if i < j:
                self._data[i], self._data[j] = self._data[j], self._data[i]
            else:
                break

        # swap pivot with the element where marker stops
        self._data[right] = self._data[i]
        self._data[i] = pivot

        if i - left > 1000:
            with self._n_thread_lock:
                self._n_thread += 1
            self._executor.submit(self._quicksort, left, i - 1, True)
        else:
            self._quicksort(left, i - 1)

        if right - i > 1000:
            with self._n_thread_lock:
                self._n_thread += 1
            self._executor.submit(self._quicksort, i + 1, right, True)
        else:
            self._quicksort(i + 1, right)

        if new_thread:
            with self._n_thread_lock:
                self._n_thread -= 1
            self._thread_done.set()
