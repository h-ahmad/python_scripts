#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec  1 16:26:40 2022

@author: hussain
"""

from Pyfhel import Pyfhel, PyCtxt
import numpy as np
import os
import torch 
import torch.nn as nn
import torch.optim as optim
from torchvision.models.resnet import resnet18
import pickle
import argparse
import torchvision
import torchvision.transforms as transforms
import time
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description = 'Main Script')
parser.add_argument('--data_path', type = str, default = './data', help = 'Main path to the dataset')
parser.add_argument('--data_file_name', type = str, default = 'cifar10_data.pkl', help = 'Dataset file if not online')
parser.add_argument('--dataset_name', type = str, default = 'mnist', help = 'mnist, cifar10')
parser.add_argument('--data_channels', type=int, default = 1, help = 'Number of channels as 1 or 3.')
parser.add_argument('--model_name', type = str, default = 'cnn2', help = 'lenet, cnn2, resnet18')
parser.add_argument('--epochs', type = int, default = 50, help = 'Number of epochs for each local model training')
parser.add_argument('--batch_size', type = int, default = 128, help = 'Batch size for each local data and model')
parser.add_argument('--number_of_clients', type = int, default = 16, help = 'Number of clients or particpants in the training process.')
parser.add_argument('--client_model_path', type = str, default = 'client_models', help = 'Folder to save client individual models by their number/index')
args = parser.parse_args() 

class CNN2Model(nn.Module):
    def __init__(self):
        super().__init__()
    
    def cnn2_model(self):
        if args.dataset_name == 'cifar10':
            lin_dim = 8
        if args.dataset_name == 'mnist':
            lin_dim = 7
        cnn2 = nn.Sequential(
            nn.Conv2d(in_channels=args.data_channels, out_channels=4, kernel_size=(5, 5), padding=1, stride=1, bias=False),
            nn.ReLU(True),
            nn.MaxPool2d(kernel_size=(2, 2), padding=1),
            nn.Conv2d(in_channels=4, out_channels=12, kernel_size=(5, 5), padding=1, stride=1, bias=False),
            nn.ReLU(True),
            nn.MaxPool2d(kernel_size=(2, 2), padding=1),
            nn.Flatten(),
            nn.Linear(in_features=(12) * (lin_dim * lin_dim), out_features=10, bias=False),
            # nn.ReLU(True),
            # nn.Linear(in_features=512, out_features=10, bias=False),
        )
        return cnn2
    
class LeNetModel(nn.Module):
    def __init__(self):
        super().__init__()
    
    def lenet_model(self):
        if args.dataset_name == 'cifar10': 
            lin_dim = 5
        if args.dataset_name == 'mnist':
            lin_dim = 4
        LeNet1 = nn.Sequential(
            nn.Conv2d(args.data_channels, 4, kernel_size=5),
            nn.Tanh(),
            nn.AvgPool2d(kernel_size=2),
            nn.Conv2d(4, 12, kernel_size=5),
            nn.Tanh(),
            nn.AvgPool2d(kernel_size=2),
            nn.Flatten(),
            nn.Linear( (12) * (lin_dim * lin_dim), 10),    # 192
        )
        return LeNet1

def load_data():
# =============================================================================
#     with open(os.path.join(args.data_path, args.data_file_name), 'rb') as file:
#             data_store = pickle.load(file)
#     xTrain, yTrain, xTest, yTest = data_store['X_train'], data_store['y_train'], data_store['X_test'], data_store['y_test']    
#     xTrain, yTrain, xTest, yTest = map(torch.tensor, (xTrain.astype(np.float32), yTrain.astype(np.int_), 
#                                                       xTest.astype(np.float32), yTest.astype(np.int_))) 
#     yTrain = yTrain.type(torch.LongTensor)
#     yTest = yTest.type(torch.LongTensor)
#     trainDs = torch.utils.data.TensorDataset(xTrain,yTrain)
#     testDs = torch.utils.data.TensorDataset(xTest,yTest)
#     trainLoader = torch.utils.data.DataLoader(trainDs,batch_size=args.batch_size)
#     testLoader = torch.utils.data.DataLoader(testDs,batch_size=args.batch_size)
# =============================================================================
    transform = transforms.ToTensor()
    if args.dataset_name == 'mnist':
        train_set = torchvision.datasets.MNIST(root = args.data_path,train=True,download=True,transform=transform)
        test_set = torchvision.datasets.MNIST(root = args.data_path,train=False,download=True,transform=transform)
    if args.dataset_name == 'cifar10':
        train_set = torchvision.datasets.CIFAR10(root = args.data_path,train=True,download=True,transform=transform)
        test_set = torchvision.datasets.CIFAR10(root = args.data_path,train=False,download=True,transform=transform)
    trainLoader = torch.utils.data.DataLoader(train_set,batch_size=args.batch_size,shuffle=True)
    testLoader = torch.utils.data.DataLoader(test_set,batch_size=args.batch_size,shuffle=True)
    return trainLoader, testLoader 

def train(train_loader, optimizer, model, loss_fn):
    training_loss = 0.0
    model.train()
    test = []
    for index, (data, target) in enumerate(train_loader):
        test.append(index)
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = loss_fn(output, target)
        loss.backward()
        optimizer.step()
        training_loss += loss.item()        
        # if index % 100 == 99:    # print every 100 mini-batches
        #     print(f'batch loss: {training_loss / 100:.3f}')
        #     training_loss = 0.0
    return model

def test(test_loader, loss_fn, model):
    correct = 0.00
    total = 0.00    
    model.eval()
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            _, predicted = torch.max(output.data, 1)
            total += target.size(0) # add batches count
            correct += (predicted == target).sum().item() # integer value of correct count            
    return (100 * correct // total)

def train_clients(num_client):
    train_loader, test_loader = load_data()    
    for epoch in range(1, args.epochs + 1):
        print('Client:', str(num_client+1), ' Epcoh:', epoch)
        client_model = train(train_loader, optimizer, model, loss_fn)    
    os.makedirs(args.client_model_path, exist_ok=True)
    saved_model_path = os.path.join(args.client_model_path, str(num_client+1)+'.pt')
    torch.save(client_model, saved_model_path) 

def gen_keys():
    HE = Pyfhel()
    # HE.contextGen(scheme='bfv', n=1024, t_bits=20, sec=128)
    HE.contextGen(scheme='bfv', n=4096, t_bits=60, sec=128)
    HE.keyGen()
    keys ={}
    keys['HE'] = HE
    keys['con'] = HE.to_bytes_context()
    keys['pk'] = HE.to_bytes_public_key()
    filename =  "public_key.pickle"
    with open(filename, 'wb') as handle:
        pickle.dump(keys, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
    keys['sk'] = HE.to_bytes_secret_key()
    filename =  "private_key.pickle"
    with open(filename, 'wb') as handle:
        pickle.dump(keys, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return HE

def get_secret_key():
    filename =  "private_key.pickle"
    with open(filename, 'rb') as handle:
            key = pickle.load(handle)
    HE = key['HE']
    HE.from_bytes_context(key['con'])
    HE.from_bytes_public_key(key['pk'])
    HE.from_bytes_secret_key(key['sk'])
    return HE

def encrypt_gradients(client_model, num_client):
    filename =  "public_key.pickle"
    with open(filename, 'rb') as handle:
        key = pickle.load(handle)
    HE = key['HE']
    HE.from_bytes_context(key['con'])
    HE.from_bytes_public_key(key['pk'])
    encrypted_weights={}
    layers_list = [module for module in client_model.modules() if not isinstance(module, nn.Sequential)]
    for i in range(len(layers_list)):            
        if hasattr(layers_list[i], 'weight') and type(layers_list[i]) != torch.nn.modules.batchnorm.BatchNorm2d:                
            print('processing: ', layers_list[i])
            weights = layers_list[i].weight            
            # if(type(layers_list[i]) == torch.nn.modules.linear.Linear): 
            weight = np.asarray(weights.detach().cpu())
            shape = weight.shape
            weight = weight.flatten()
            array= np.empty(len(weight),dtype=PyCtxt)
            for k in np.arange(len(weight)):
                array[k] = HE.encrypt(weight[k])  
            enc_array = array.reshape(shape)
            encrypted_weights['c_'+str(i)]=enc_array
            print('processed layer: ', layers_list[i])
    filename =  os.path.join(args.client_model_path, "client_" + str(num_client+1)+ ".pickle")
    dic = {}
    dic['key'] = HE
    dic['val'] = encrypted_weights
    with open(filename, 'wb') as handle:
        pickle.dump(dic, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
def aggregate_encrypted_gradients(num_of_clients):
    dct_weights ={}
    denom = float(1/num_of_clients)
    filename =  "public_key.pickle"
    with open(filename, 'rb') as handle:
        key = pickle.load(handle)
    HE = key['HE']
    HE.from_bytes_context(key['con'])
    HE.from_bytes_public_key(key['pk'])
    c_denom = HE.encrypt(denom)
    filename =  "public_key.pickle"
    with open(filename, 'rb') as handle:
        key = pickle.load(handle)
    HE = key['HE']
    HE.from_bytes_context(key['con'])
    HE.from_bytes_public_key(key['pk'])
    for i in range(num_of_clients):
        print('Aggregating client: ', (i+1))
        filename =  os.path.join(args.client_model_path, "client_" + str(i+1)+ ".pickle")
        with open(filename, 'rb') as handle:
            dct = pickle.load(handle)
        cweights=dct['val']
        enc_weights={}
        for key in cweights:
            arr = cweights[key]
            shape = arr.shape
            weight = arr.flatten()
            for l in np.arange(len(weight)):
                weight[l]._pyfhel = HE
            enc_array = weight.reshape(shape)
            enc_weights[key] = enc_array
        for key in enc_weights:
            if i == 0:
                arr = enc_weights[key]
                dct_weights[key] = np.zeros_like(arr,dtype=PyCtxt) # array/matrix of zeros            
            dct_weights[key] = enc_weights[key] + dct_weights[key]
    for key in dct_weights:
        dct_weights[key]= dct_weights[key]*c_denom
    dic = {}
    dic['key']=HE
    dic['val']=dct_weights
    filename =  os.path.join(args.client_model_path, "aggregated_gradients.pickle")
    with open(filename, 'wb') as handle:
        pickle.dump(dic, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return dct_weights, filename
        
def decrypt_gradients(filename):
    HE = get_secret_key()
    enc_weights={}
    dec_weights={}
    with open(filename, 'rb') as handle:
        dct = pickle.load(handle)
    cweights=dct['val']
    enc_weights = cweights
    for key in enc_weights:
        arr = enc_weights[key]
        shape = arr.shape
        weight = arr.flatten()
        for l in range(len(weight)):
            weight[l]= HE.decrypt(weight[l])
        dec_array = weight.reshape(shape)
        dec_weights[key] = dec_array    
    model = torch.load(os.path.join(args.client_model_path, 'global_model.pt'))
    layers_list = [module for module in model.modules() if not isinstance(module, nn.Sequential)]
    weight=[]
    for i in range(len(layers_list)):
        if hasattr(layers_list[i], 'weight') and type(layers_list[i]) != torch.nn.modules.batchnorm.BatchNorm2d:
            global_weights = model[i].weight
            global_shape = model[i].weight.shape
            new_weights = dec_weights['c_'+str(i)]
            global_weights_flat = global_weights.flatten().detach().cpu()
            new_weights_flat = new_weights.flatten()
            for j in range(len(global_weights_flat)):
                model[i].weight.flatten().detach().cpu()[j] = new_weights_flat[j][0]
                model[i].weight.reshape(global_shape)            
    torch.save(model, os.path.join(args.client_model_path, 'global_model.pt'))
    return model        

if __name__ == '__main__':
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if args.model_name == 'cnn2':
        model_creation = CNN2Model()
        model = model_creation.cnn2_model().to(device)
    if args.model_name == 'lenet':
        model_creation = LeNetModel()
        model = model_creation.lenet_model().to(device)
    if args.model_name == 'resnet18':
        model = resnet18(pretrained = True).to(device)    
    train_loader, test_loader = load_data()
    optimizer = optim.Adam(model.parameters())
    loss_fn = torch.nn.CrossEntropyLoss()

    os.makedirs(args.client_model_path, exist_ok = True)  
    torch.save(model, os.path.join(args.client_model_path, 'global_model.pt'))  
    print('<=================== Training Started! ==================>')
    
    # time calculation variables
    start_time = time.time()
    client_axis = []
    time_axis = []
    end_time = 0.0
    
    for num_client in range(args.number_of_clients):
        train_clients(num_client)
    
    HE=gen_keys()
    print('<=================== Encryption Started! ==================>')
    for num_client in range(args.number_of_clients):
        print('Encryption of client: ', num_client+1)
        client_model_path = os.path.join(args.client_model_path, str(num_client+1)+'.pt')
        client_model = torch.load(client_model_path)
        client_model.eval() 
        encrypt_gradients(client_model, num_client)   
        
        end_time += time.time() - start_time
        client_axis.append(num_client+1)
        time_axis.append(end_time)
        
    print('<===================Model Aggregation==================>')
    global_model_dict, saved_path = aggregate_encrypted_gradients(args.number_of_clients)
    print('<===================Decryption==================>')
    decrypt_gradients(saved_path)
    print('Decryption successfule!')
    print('<=================== Testing... ==================>')
    global_model = torch.load(os.path.join(args.client_model_path, 'global_model.pt'))
    accuracy = test(test_loader, loss_fn, global_model)
    print('Accuracy of global model: ', accuracy)
    print('Global model is saved at: ', args.client_model_path)
    
    
    plt.plot(client_axis, time_axis)
    plt.xlabel('Number of clients (N)')
    plt.ylabel('Time (s)')
    plt.title('CNN-2 complet training using FHE.')
    plt.savefig(args.model_name+'_training_encryption.png')
    plt.show()    
