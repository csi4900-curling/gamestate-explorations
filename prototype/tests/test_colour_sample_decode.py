from prototype.track_colours import read_sample


class Capture:
    def __init__(self, position, fail_grab=False, wrong_seek=False):
        self.position = position
        self.fail_grab = fail_grab
        self.wrong_seek = wrong_seek
        self.seeks = []

    def get(self, _):
        return self.position

    def set(self, _, target):
        self.seeks.append(target)
        self.position = target + int(self.wrong_seek)

    def grab(self):
        if self.fail_grab:
            return False
        self.position += 1
        return True

    def read(self):
        index = self.position
        self.position += 1
        return True, index


def test_adjacent_samples_decode_in_order_and_recover_by_exact_seek():
    capture = Capture(5)
    assert read_sample(capture, 8) == 8 and not capture.seeks
    capture.fail_grab = True
    assert read_sample(capture, 11) == 11 and capture.seeks == [11]
    assert read_sample(capture, 2) == 2 and capture.seeks == [11, 2]
    capture.wrong_seek = True
    assert read_sample(capture, 60) is None
