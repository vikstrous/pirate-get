import os

def data_path(name):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', name)

def read_data(name):
    with open(data_path(name)) as f:
        return f.read()
