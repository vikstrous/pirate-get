import os

def data_path(name):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', name)

def open_data(name):
    return open(data_path(name))
