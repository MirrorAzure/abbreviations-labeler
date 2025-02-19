import torch

def torch_init():
    num_cores = torch.get_num_interop_threads()
    torch.set_num_threads(num_cores)

def get_device():
    device = torch.device('cpu') if not torch.cuda.is_available() else torch.device('cuda')
    return device

