# -*- coding: utf-8 -*-
"""05_02_Water_Rahma Absoh Dwiyanti.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1JtEpS9xVH8ZwyCHthvGzvtMtMTX6vdT8

# Assignment Ch. 5 - Transfer Learning [Case #2]
Startup Campus, Indonesia - `Artificial Intelligence Track`
* Dataset: MNIST Handwritten Digits (10 classes)
* Libraries: PyTorch, Torchvision, Scikit-learn
* Objective: Transfer Learning using CNN-based Pre-trained Models

`PREREQUISITE` All modules (with their suitable versions) are installed properly.
<br>`TASK` Complete the notebook cell's code marked with <b>#TODO</b> comment.
<br>`TARGET PORTFOLIO` Students are able to:
* implement transfer learning technique using various PyTorch pre-trained models, and
* examine the effect of freezing some parts of the layer.

<br>`WARNING` Do **NOT CHANGE** any codes within the User-defined Functions (UDFs) section.

### Case Study Description
A new robotic facility located in East Kalimantan, near the Titik Nol Ibu Kota Negara (IKN) Indonesia, asks you to create a Computer Vision model for their new droid (robot) products. The company requests you to **teach the robot how to read a sequence of numbers**. You suddenly realize that the first stage is to let the robot correctly identify each individual digit (0-9). However, since the prototype announcement date was hastened, your deadline is very tight: you only have **less than 1 week** to complete the job. As a professional AI developer, you keep calm and know that you can exploit the **Transfer Learning** method to solve this problem efficiently.

As a basic dataset in most of Computer Vision tasks, **Modified National Institute of Standards and Technology (MNIST) database** contains 10 handwritten digits. All of them are in the grayscale (1-channel). Torchvision, a sub-library of PyTorch, has dozens of pre-trained models that you can easily choose from. All of these models were originally trained on the ImageNet dataset [(ref1)](https://www.image-net.org/download.php), which contains millions of RGB (3-channel) images and 1,000 classes. For simplicity, let choose **Resnet18** [(ref2)](https://www.cv-foundation.org/openaccess/content_cvpr_2016/papers/He_Deep_Residual_Learning_CVPR_2016_paper.pdf), **DenseNet121** [(ref3)](https://openaccess.thecvf.com/content_cvpr_2017/papers/Huang_Densely_Connected_Convolutional_CVPR_2017_paper.pdf), and **Vision Transformer (ViT)** [(ref4)](https://arxiv.org/pdf/2010.11929.pdf) as baseline, state-of-the-art models to test the **image classification** performance. Your complete tasks are as follows.

1. Pick **DenseNet** as your first model to experiment with, then **change the number of neurons in the first and last layers** (since the ImageNet has 1,000 classes, while MNIST only has 10 classes; both are also come with different image size and channel).
2. Define **hyperparameters** and train the model (all **layers are trainable**).
3. Plot the model performance, for both **training** and **validation** results.
4. Now try to **freeze (layers are non-trainable) some parts** of layers: (1) "denseblock1", (2) "denseblock1" and "denseblock2". These will be two separate models.
5. **Retrain** each model, plot its performance, and examine the difference.
6. BONUS: Can you **replicate** all of the steps above with different models, i.e., **ResNet** and **ViT**?

### Import libraries
"""

import torch, torchvision, time
from numpy.random import seed
from tqdm.autonotebook import tqdm
from matplotlib import pyplot as plt
from copy import deepcopy
from warnings import filterwarnings as fw; fw("ignore")

torch.__version__ #== "2.0.1+cu117"

torchvision.__version__ #== "0.15.2+cu117"

#!pip install update torch torchvision -U

# define seeding
seed(0)
torch.manual_seed(0)
torch.cuda.manual_seed(0)
torch.cuda.manual_seed_all(0)
torch.backends.cudnn.deterministic = True

"""### User-defined Functions (UDFs)

- To print total model parameters
"""

def check_params(model, *args, **kwargs) -> dict:
    return {
        "total_trainable_params" : sum(p.numel() for p in model.parameters() if p.requires_grad),
        "total_nontrainable_params" : sum(p.numel() for p in model.parameters() if not p.requires_grad)
    }

"""- To get the pair of train and validation dataloaders"""

data_transform = torchvision.transforms.Compose([
    torchvision.transforms.Resize((224, 224)),
    torchvision.transforms.ToTensor(),
    torchvision.transforms.Normalize((torch.tensor(33.3184)/255,), (torch.tensor(78.5675)/255,))
])

train_dataset = torchvision.datasets.MNIST(root=".", train=True, transform=data_transform, download=True).train_data.float()

def get_dataloaders(train_batch_size : int, val_batch_size : int, max_rows : int = 1000, *args, **kwargs) -> tuple:
    data_transform = torchvision.transforms.Compose([
        torchvision.transforms.Resize((224, 224)),
        torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize((torch.tensor(33.3184)/255,), (torch.tensor(78.5675)/255,))
    ])

    train_dataset = torchvision.datasets.MNIST(root=".", train=True, transform=data_transform)
    train_idx = torch.randperm(len(train_dataset))[:int(max_rows*.75)]
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=train_batch_size, \
                                               sampler=torch.utils.data.SubsetRandomSampler(train_idx))

    val_dataset = torchvision.datasets.MNIST(root=".", train=False, transform=data_transform)
    val_idx = torch.randperm(len(val_dataset))[:int(max_rows*.25)]
    val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=val_batch_size, \
                                             sampler=torch.utils.data.SubsetRandomSampler(val_idx))

    return train_loader, val_loader

"""* To fit (training) the model"""

def fit(
    model : torchvision.models,
    epoch : int,
    train_loader : torch.utils.data.DataLoader,
    val_loader : torch.utils.data.DataLoader,
    *args, **kwargs
) -> dict:

    TRAIN_LOSS, TRAIN_ACC = [], []
    train_batches = len(train_loader)

    VAL_LOSS, VAL_ACC = [], []
    val_batches = len(val_loader)

    # loop for every epoch (training + evaluation)
    start_ts = time.time()
    for e in range(epoch):
        train_losses = 0
        train_accuracies = 0

        # progress bar
        progress = tqdm(enumerate(train_loader), desc="Loss: ", total=train_batches)

        # ----------------- TRAINING  --------------------
        # set model to training
        model.train()

        for i, data in progress:
            X, y = data[0].to(device), data[1].to(device)

            # training step for single batch
            model.zero_grad()

            # forward pass
            outputs = model(X)
            loss = loss_function(outputs, y)

            # backward pass
            loss.backward()
            optimizer.step()

            train_losses += loss.item()

            ps = torch.exp(outputs)
            top_p, top_class = ps.topk(1, dim=1)
            equals = top_class == y.view(*top_class.shape)
            train_accuracies += torch.mean(equals.type(torch.FloatTensor)).item()

            # updating progress bar
            progress.set_description("Loss: {:.4f}".format(train_losses/(i+1)))

        TRAIN_ACC.append(train_accuracies/train_batches)
        TRAIN_LOSS.append(train_losses/train_batches)

        # releasing unceseccary memory in GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # ----------------- VALIDATION  -----------------
        val_losses = 0
        val_accuracies = 0

        # set model to evaluating (testing)
        model.eval()
        with torch.no_grad():
            for i, data in enumerate(val_loader):
                X, y = data[0].to(device), data[1].to(device)
                outputs = model(X) # this gives the prediction from the network
                val_losses += loss_function(outputs, y).item()

                ps = torch.exp(outputs)
                top_p, top_class = ps.topk(1, dim=1)
                equals = top_class == y.view(*top_class.shape)
                val_accuracies += torch.mean(equals.type(torch.FloatTensor)).item()

        print("Epoch {}/{} >> Training loss: {:.3f}, Validation loss: {:.3f}, Validation accuracy: {:.3f}".format(
            e+1, epoch, train_losses/train_batches, val_losses/val_batches, val_accuracies/val_batches*100)
        )

        VAL_ACC.append(val_accuracies/val_batches)
        VAL_LOSS.append(val_losses/val_batches)

    tr_time = time.time()-start_ts
    print("Training time: {:.3f}s".format(tr_time))

    return {
        "model" : model.name,
        "train_acc" : TRAIN_ACC,
        "train_loss" : TRAIN_LOSS,
        "val_acc" : VAL_ACC,
        "val_loss" : VAL_LOSS,
        "exc_time" : tr_time
    }

"""* To visualize the model performance"""

def plot_performance(dict_ : dict, *args, **kwargs) -> None:
    my_figure = plt.figure(figsize=(12, 4))
    # NOTE: figsize=(width/horizontally, height/vertically)

    m = my_figure.add_subplot(121)
    plt.plot(dict_["train_loss"], label="Train Loss")
    plt.plot(dict_["val_loss"], label="Valid. Loss")
    plt.title("LOSS")
    plt.xlabel("Epoch")
    plt.ylabel("Score")
    plt.legend(loc="best")

    n = my_figure.add_subplot(122)
    plt.plot(dict_["train_acc"], label="Train Accuracy")
    plt.plot(dict_["val_acc"], label="Valid. Accuracy")
    plt.title("ACCURACY")
    plt.xlabel("Epoch")
    plt.ylabel("Score")
    plt.legend(loc="best")

    plt.tight_layout()
    plt.show()

"""### Define the model class"""

class VisionModel(torch.nn.Module):
    def __init__(self, model_selection : str, *args, **kwargs) -> None:
        super(VisionModel, self).__init__()
        self.model_selection = self.name = model_selection
        self.in_channels = 1

        def create_conv2d(this_layer, *args, **kwargs) -> torch.nn.modules.conv.Conv2d:
            return torch.nn.Conv2d(
                in_channels=self.in_channels, out_channels=this_layer.out_channels,
                kernel_size=this_layer.kernel_size, stride=this_layer.stride,
                padding=this_layer.padding, bias=this_layer.bias
            )

        if not self.model_selection.lower() in ["resnet", "densenet", "vit"]:
            raise ValueError("Please select the model: 'resnet', 'densenet', or 'vit'.")

        if self.model_selection == "resnet":
            self.model = torchvision.models.resnet18(pretrained=True)
            self.model.conv1 = create_conv2d(self.model.conv1) # change the input layer to take Grayscale image, instead of RGB
            self.model.fc = torch.nn.Linear(self.model.fc.in_features, 10) # change the output layer to output 10 classes

        elif self.model_selection == "densenet":
            self.model = torchvision.models.densenet121(pretrained=True)
            self.model.features.conv0 = create_conv2d(self.model.features.conv0)
            self.model.classifier = torch.nn.Linear(self.model.classifier.in_features, 10)

        elif self.model_selection == "vit":
            self.model = torchvision.models.vit_b_16(pretrained=True)
            self.model.conv_proj = create_conv2d(self.model.conv_proj)
            self.model.classifier = torch.nn.Linear(self.model.heads.head.in_features, 10)

        self.softmax = torch.nn.Softmax(dim=1)

    def forward(self, data, *args, **kwargs) -> torchvision.models:
        x = self.model(data)
        return self.softmax(x)

"""### Set device to CUDA"""

device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
device

"""### Define hyperparameters"""

EPOCH = 5
BATCH_SIZE = 6
LEARNING_RATE = 1e-5

"""### Define the model"""

model = VisionModel("densenet").to(device)
check_params(model)

model

"""### WILL BE USED LATER: Freeze some layers"""

model_freeze_block1 = deepcopy(model)
for name, param in model_freeze_block1.named_parameters():
    if param.requires_grad and "denseblock1" in name:
        param.requires_grad = False
check_params(model_freeze_block1)

model_freeze_block12 = deepcopy(model)
for name, param in model_freeze_block12.named_parameters():
    if param.requires_grad and any([x in name for x in ["denseblock1", "denseblock2"]]):
        param.requires_grad = False
check_params(model_freeze_block12)

"""### Get train and validation dataloaders

To speedup the training time, we will only use 1,000 (of 60,000) images from MNIST.
"""

train_loader, val_loader = get_dataloaders(BATCH_SIZE, BATCH_SIZE)
len(train_loader), len(val_loader)

"""### Set loss function and model optimizer"""

loss_function = torch.nn.CrossEntropyLoss()

trainable_model_params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.Adam(trainable_model_params, lr=LEARNING_RATE)

"""### Start the model training"""

results = fit(model=model, epoch=EPOCH, train_loader=train_loader, val_loader=val_loader)

results

"""### Plot the model performance"""

plot_performance(results)

"""### NEXT ROUND: Retrain the model with frozen layers"""

FROZEN_RESULTS = []
for idx, m in enumerate([model_freeze_block1, model_freeze_block12]):
    print("id: {}".format(idx))
    trainable_model_params = [p for p in m.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(trainable_model_params, lr=LEARNING_RATE)

    new_results = fit(model=m, epoch=EPOCH, train_loader=train_loader, val_loader=val_loader)
    FROZEN_RESULTS.append(new_results)

"""### Examine the difference in both accuracy and loss"""

plot_performance(FROZEN_RESULTS[0])

plot_performance(FROZEN_RESULTS[1])

# QUESTIONS
# TODO: With the same 5 epochs in training, why Transfer Learning with frozen layers are worse in the final accuracy?

# QUESTIONS
# TODO: Why the more layers are frozen, the lower the accuracy of the model in the early (the 1st) epoch?

"""### Examine the difference in the execution time"""

print("When all layers were TRAINABLE: {:.3f}s.".format(results["exc_time"]))
print("Only 'denseblock1' was FROZEN: {:.3f}s.".format(FROZEN_RESULTS[0]["exc_time"]))
print("Only 'denseblock1' and 'denseblock2' wwere FROZEN: {:.3f}s.".format(FROZEN_RESULTS[1]["exc_time"]))

# QUESTIONS
# TODO: Why the more layers are frozen, the faster the training-validation time?

"""### Scoring
Total `#TODO` = 12
<br>Checklist:

- [ ] Change the DenseNet input layer stack by calling create_conv2d()
- [ ] Change the DenseNet output layer with 10 classes
- [ ] Change the ViT input layer stack by calling create_conv2d()
- [ ] Change the ViT output layer with 10 classes
- [ ] Define the batch size
- [ ] Define the learning rate
- [ ] Define the loss function (for multi-classification)
- [ ] Pass the string "resnet" for ResNet18, "densenet" for DenseNet121, and "vit" for Vision Transformer
- [ ] Specify variables for your model, number of epochs, train data loader, and validation data loader
- [ ] QUESTION: With the same 5 epochs in training, why Transfer Learning with frozen layers are worse in the final accuracy?
- [ ] QUESTION: Why the more layers are frozen, the lower the accuracy of the model in the early (the 1st) epoch?
- [ ] QUESTION: Why the more layers are frozen, the faster the training-validation time?

### Additional readings
* ResNet: https://www.cv-foundation.org/openaccess/content_cvpr_2016/papers/He_Deep_Residual_Learning_CVPR_2016_paper.pdf
* DenseNet: https://openaccess.thecvf.com/content_cvpr_2017/papers/Huang_Densely_Connected_Convolutional_CVPR_2017_paper.pdf
* Vision Transformer (ViT): https://arxiv.org/pdf/2010.11929.pdf
* MNIST Classification w/ PyTorch (Beginner): https://www.kaggle.com/code/amsharma7/mnist-pytorch-for-beginners-detailed-desc

### Copyright © 2023 Startup Campus, Indonesia
* You may **NOT** use this file except there is written permission from PT. Kampus Merdeka Belajar (Startup Campus).
* Please address your questions to mentors.
"""