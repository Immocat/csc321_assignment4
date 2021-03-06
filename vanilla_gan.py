# CSC 321, Assignment 4
#
# This is the main training file for the vanilla GAN part of the assignment.
#
# Usage:
# ======
#    To train with the default hyperparamters (saves results to checkpoints_vanilla/ and samples_vanilla/):
#       python vanilla_gan.py

import os
import pdb
import pickle
import argparse

import warnings
warnings.filterwarnings("ignore")

# Numpy & Scipy imports
import numpy as np
import scipy
import scipy.misc

# Torch imports
import torch
import torch.nn as nn
import torch.optim as optim

# Local imports
import utils
from data_loader import get_emoji_loader
from models import DCGenerator, DCDiscriminator
from models import WGANDiscriminator, WGANGenerator
from models import WGANGPDiscriminator, WGANGPGenerator
SEED = 11

# Set the random seed manually for reproducibility.
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(SEED)


def print_models(G, D):
    """Prints model information for the generators and discriminators.
    """
    print("                    G                  ")
    print("---------------------------------------")
    print(G)
    print("---------------------------------------")

    print("                    D                  ")
    print("---------------------------------------")
    print(D)
    print("---------------------------------------")


def create_model(opts):
    """Builds the generators and discriminators.
    """
    if opts.GAN_type == 'LSGAN':
        G = DCGenerator(noise_size=opts.noise_size, conv_dim=opts.conv_dim)
        D = DCDiscriminator(conv_dim=opts.conv_dim, batch_norm=not opts.disable_bn)
    elif opts.GAN_type == 'WGAN':
        G = WGANGenerator(noise_size=opts.noise_size, conv_dim=opts.conv_dim)
        D = WGANDiscriminator(conv_dim=opts.conv_dim, batch_norm=not opts.disable_bn)
    elif opts.GAN_type == 'WGANGP':
        G = WGANGPGenerator(noise_size=opts.noise_size, conv_dim=opts.conv_dim)
        D = WGANGPDiscriminator(conv_dim=opts.conv_dim)

    #print_models(G, D)

    #move to device
    G.to(opts.device) # in-place 
    D.to(opts.device) # in-place
    print_models(G, D)
    print('Models are at:'+str(opts.device))

    return G, D


def checkpoint(iteration, G, D, opts):
    """Saves the parameters of the generator G and discriminator D.
    """
    G_path = os.path.join(opts.checkpoint_dir, 'G.pkl')
    D_path = os.path.join(opts.checkpoint_dir, 'D.pkl')
    torch.save(G.state_dict(), G_path)
    torch.save(D.state_dict(), D_path)


def create_image_grid(array, ncols=None):
    """
    """
    num_images, channels, cell_h, cell_w = array.shape

    if not ncols:
        ncols = int(np.sqrt(num_images))
    nrows = int(np.math.floor(num_images / float(ncols)))
    result = np.zeros((cell_h*nrows, cell_w*ncols, channels), dtype=array.dtype)
    for i in range(0, nrows):
        for j in range(0, ncols):
            result[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w, :] = array[i*ncols+j].transpose(1, 2, 0)

    if channels == 1:
        result = result.squeeze()
    return result


def save_samples(G, fixed_noise, iteration, opts):
    generated_images = G(fixed_noise)
    generated_images = utils.to_data(generated_images)

    grid = create_image_grid(generated_images)

    # merged = merge_images(X, fake_Y, opts)
    path = os.path.join(opts.sample_dir, 'sample-{:06d}.png'.format(iteration))
    scipy.misc.imsave(path, grid)
    print('Saved {}'.format(path))


def sample_noise(dim):
    """
    Generate a PyTorch Variable of uniform random noise.

    Input:
    - batch_size: Integer giving the batch size of noise to generate.
    - dim: Integer giving the dimension of noise to generate.

    Output:
    - A PyTorch Variable of shape (batch_size, dim, 1, 1) containing uniform
      random noise in the range (-1, 1).
    """
    return utils.to_var(torch.rand(batch_size, dim) * 2 - 1).unsqueeze(2).unsqueeze(3)


def training_loop_LSGAN(train_dataloader, opts):
    """Runs the training loop.
        * Saves checkpoints every opts.checkpoint_every iterations
        * Saves generated samples every opts.sample_every iterations
    """

    # Create generators and discriminators
    G, D = create_model(opts)

    # Create optimizers for the generators and discriminators
    if opts.optimizer == 'Adam':
        d_optimizer = optim.Adam(D.parameters(), opts.lr, [opts.beta1, opts.beta2])
        g_optimizer = optim.Adam(G.parameters(), opts.lr, [opts.beta1, opts.beta2])
    elif opts.optimizer == 'RMSProp' or opts.GAN_type == 'WGAN':
        d_optimizer = optim.RMSprop(D.parameters(), opts.lr)
        g_optimizer = optim.RMSprop(G.parameters(), opts.lr)

    print(d_optimizer)
    print(g_optimizer)

    # Generate fixed noise for sampling from the generator
    fixed_noise = sample_noise(opts.noise_size)  # batch_size x noise_size x 1 x 1

    iteration = 1

    total_train_iters = opts.num_epochs * len(train_dataloader)

    device = opts.device
    noise_dim = opts.noise_size
    #batch_size = opts.batch_size

    for epoch in range(opts.num_epochs):

        for batch in train_dataloader:

            real_images, _ = batch
            #print(real_images.device)
            real_images = real_images.to(device)
            #print(real_images.device)
            
            #real_images, labels = utils.to_var(real_images), utils.to_var(labels).long().squeeze()
            #print(real_images.shape)
            
            ################################################
            ###         TRAIN THE DISCRIMINATOR         ####
            ################################################

            d_optimizer.zero_grad()

            # FILL THIS IN
            # 1. Compute the discriminator loss on real images
            D_real_loss = 0.5 * torch.sum((D(real_images) - 1)**2) / batch_size
            #D_real_loss = 0.5 * torch.sum((D(real_images) - 0.9)**2) / batch_size
            #print(D_real_loss)

            # 2. Sample noise
            noise = 2 * torch.rand(batch_size, noise_dim) - 1
            noise = noise.view(batch_size, noise_dim, 1, 1).to(device)
            #print(noise.shape)

            # 3. Generate fake images from the noise
            fake_images = G(noise)

            # 4. Compute the discriminator loss on the fake images
            D_fake_loss = 0.5 * torch.sum(D(fake_images)**2) / batch_size

            # 5. Compute the total discriminator loss
            D_total_loss = D_fake_loss + D_real_loss

            D_total_loss.backward()
            d_optimizer.step()

            ###########################################
            ###          TRAIN THE GENERATOR        ###
            ###########################################

            g_optimizer.zero_grad()

            # FILL THIS IN
            # 1. Sample noise
            noise = 2 * torch.rand(batch_size, noise_dim) - 1
            noise = noise.view(batch_size, noise_dim, 1, 1).to(device)

            # 2. Generate fake images from the noise
            fake_images = G(noise)

            # 3. Compute the generator loss
            G_loss = torch.sum((D(fake_images) -1)**2)/ batch_size
            #G_loss = torch.sum((D(fake_images) -0.9)**2)/ batch_size
            G_loss.backward()
            g_optimizer.step()


            # Print the log info
            if iteration % opts.log_step == 0:
                print('Iteration [{:4d}/{:4d}] | D_real_loss: {:6.4f} | D_fake_loss: {:6.4f} | G_loss: {:6.4f}'.format(
                       iteration, total_train_iters, D_real_loss.data[0], D_fake_loss.data[0], G_loss.data[0]))

            # Save the generated samples
            if iteration % opts.sample_every == 0:
                save_samples(G, fixed_noise, iteration, opts)

            # Save the model parameters
            if iteration % opts.checkpoint_every == 0:
                checkpoint(iteration, G, D, opts)

            iteration += 1

def training_loop_WGAN(train_dataloader, opts):
    """Runs the training loop.
        * Saves checkpoints every opts.checkpoint_every iterations
        * Saves generated samples every opts.sample_every iterations
    """

    # Create generators and discriminators
    G, D = create_model(opts)

    # Create optimizers for the generators and discriminators
    if opts.optimizer == 'Adam':
        d_optimizer = optim.Adam(D.parameters(), opts.lr, [opts.beta1, opts.beta2])
        g_optimizer = optim.Adam(G.parameters(), opts.lr, [opts.beta1, opts.beta2])
    elif opts.optimizer == 'RMSProp' or opts.GAN_type == 'WGAN':
        d_optimizer = optim.RMSprop(D.parameters(), opts.lr)
        g_optimizer = optim.RMSprop(G.parameters(), opts.lr)

    print(d_optimizer)
    print(g_optimizer)

    # Generate fixed noise for sampling from the generator
    fixed_noise = sample_noise(opts.noise_size)  # batch_size x noise_size x 1 x 1

    iteration = 1

    total_train_iters = opts.num_epochs * len(train_dataloader)

    device = opts.device
    noise_dim = opts.noise_size
    clip_value = 0.01

    for epoch in range(opts.num_epochs):

        for batch in train_dataloader:

            real_images, _ = batch
            #print(real_images.device)
            real_images = real_images.to(device)
            #print(real_images.device)
            
            #real_images, labels = utils.to_var(real_images), utils.to_var(labels).long().squeeze()
            #print(real_images.shape)
            
            ################################################
            ###         TRAIN THE DISCRIMINATOR         ####
            ################################################

            d_optimizer.zero_grad()

            # 2. Sample noise
            noise = 2 * torch.rand(batch_size, noise_dim) - 1
            noise = noise.view(batch_size, noise_dim, 1, 1).to(device)

            # 3. Generate fake images from the noise
            fake_images = G(noise).detach()

            # 5. Compute the total discriminator loss
            D_total_loss = torch.mean(D(fake_images)) - torch.mean(D(real_images))

            D_total_loss.backward()
            d_optimizer.step()

            # CLIP WEIGHTS!!!! of Dicriminator
            for p in D.parameters():
                p.data.clamp_(-clip_value, clip_value)

            ###########################################
            ###          TRAIN THE GENERATOR        ###
            ###########################################

            g_optimizer.zero_grad()

            # FILL THIS IN
            # 1. Sample noise
            noise = 2 * torch.rand(batch_size, noise_dim) - 1
            noise = noise.view(batch_size, noise_dim, 1, 1).to(device)

            # 2. Generate fake images from the noise
            fake_images = G(noise)

            # 3. Compute the generator loss
            G_loss = -torch.mean(D(fake_images))
            #G_loss = torch.sum((D(fake_images) -0.9)**2)/ batch_size
            G_loss.backward()
            g_optimizer.step()


            # Print the log info
            with torch.no_grad():
                if iteration % opts.log_step == 0:
                    print('Iteration [{:4d}/{:4d}] | D_total_loss: {:6.4f} | G_loss: {:6.4f}'.format(
                        iteration, total_train_iters, D_total_loss.data[0], G_loss.data[0]))

                # Save the generated samples
                if iteration % opts.sample_every == 0:
                    save_samples(G, fixed_noise, iteration, opts)

                # Save the model parameters
                if iteration % opts.checkpoint_every == 0:
                    checkpoint(iteration, G, D, opts)

                iteration += 1



def training_loop_WGANGP(train_dataloader, opts):
    """Runs the training loop.
        * Saves checkpoints every opts.checkpoint_every iterations
        * Saves generated samples every opts.sample_every iterations
    """

    # Create generators and discriminators
    G, D = create_model(opts)

    # Create optimizers for the generators and discriminators
    if opts.optimizer == 'Adam':
        d_optimizer = optim.Adam(D.parameters(), opts.lr, [opts.beta1, opts.beta2])
        g_optimizer = optim.Adam(G.parameters(), opts.lr, [opts.beta1, opts.beta2])
    elif opts.optimizer == 'RMSProp':
        d_optimizer = optim.RMSprop(D.parameters(), opts.lr)
        g_optimizer = optim.RMSprop(G.parameters(), opts.lr)

    print(d_optimizer)
    print(g_optimizer)

    # Generate fixed noise for sampling from the generator
    fixed_noise = sample_noise(opts.noise_size)  # batch_size x noise_size x 1 x 1

    iteration = 1

    total_train_iters = opts.num_epochs * len(train_dataloader)

    device = opts.device
    noise_dim = opts.noise_size
    lambda_GP = 10

    for epoch in range(opts.num_epochs):

        for batch in train_dataloader:

            real_images, _ = batch
            batch_size = real_images.shape[0]
            #print(real_images.device)
            real_images = real_images.to(device)
            #print(real_images.device)
            
            #real_images, labels = utils.to_var(real_images), utils.to_var(labels).long().squeeze()
            #print(real_images.shape)
            
            ################################################
            ###         TRAIN THE DISCRIMINATOR         ####
            ################################################

            d_optimizer.zero_grad()

            # 2. Sample noise
            noise = 2 * torch.rand(batch_size, noise_dim) - 1
            noise = noise.view(batch_size, noise_dim, 1, 1).to(device)

            # 3. Generate fake images from the noise
            fake_images = G(noise)
            D_fake_loss = torch.mean(D(fake_images))
            # 4. Calculate gradient penalty(GP)
            random_eps = torch.rand(1, device=device)
            #print(fake_images.shape)
            #print(real_images.shape)
            interpolates = (1 - random_eps) * fake_images + random_eps * real_images
            D_interpolates = D(interpolates)
            # 5. Compute the total discriminator loss
            fake = torch.ones(D_interpolates.size(), device=device)
            #print(fake_images.shape)
            #print(D_fake_loss.shape)
            gradients = torch.autograd.grad(
                outputs=D_interpolates, inputs=interpolates, grad_outputs=fake, create_graph=True, retain_graph=True, only_inputs=True)[0]
            #print(gradients[0].shape)
            D_total_loss = D_fake_loss - \
                torch.mean(D(real_images)) \
                + lambda_GP * \
                (gradients.norm(2) - 1)**2

            D_total_loss.backward()
            d_optimizer.step()


            ###########################################
            ###          TRAIN THE GENERATOR        ###
            ###########################################

            g_optimizer.zero_grad()

            # FILL THIS IN
            # 1. Sample noise
            noise = 2 * torch.rand(batch_size, noise_dim) - 1
            noise = noise.view(batch_size, noise_dim, 1, 1).to(device)

            # 2. Generate fake images from the noise
            fake_images = G(noise)

            # 3. Compute the generator loss
            G_loss = -torch.mean(D(fake_images))
            #G_loss = torch.sum((D(fake_images) -0.9)**2)/ batch_size
            G_loss.backward()
            g_optimizer.step()


            # Print the log info
            with torch.no_grad():
                if iteration % opts.log_step == 0:
                    print('Iteration [{:4d}/{:4d}] | D_total_loss: {:6.4f} | G_loss: {:6.4f}'.format(
                        iteration, total_train_iters, D_total_loss.data[0], G_loss.data[0]))

                # Save the generated samples
                if iteration % opts.sample_every == 0:
                    save_samples(G, fixed_noise, iteration, opts)

                # Save the model parameters
                if iteration % opts.checkpoint_every == 0:
                    checkpoint(iteration, G, D, opts)

                iteration += 1
def main(opts):
    """Loads the data, creates checkpoint and sample directories, and starts the training loop.
    """

    # Create a dataloader for the training images
    train_dataloader, _ = get_emoji_loader(opts.emoji, opts)

    # Create checkpoint and sample directories
    utils.create_dir(opts.checkpoint_dir)
    utils.create_dir(opts.sample_dir)

    if opts.GAN_type == 'LSGAN':
        training_loop_LSGAN(train_dataloader, opts)
    elif opts.GAN_type == 'WGAN':
        training_loop_WGAN(train_dataloader, opts)
    elif opts.GAN_type == 'WGANGP':
        training_loop_WGANGP(train_dataloader, opts)


def create_parser():
    """Creates a parser for command-line arguments.
    """
    parser = argparse.ArgumentParser()

    # Model hyper-parameters
    parser.add_argument('--image_size', type=int, default=32, help='The side length N to convert images to NxN.')
    parser.add_argument('--conv_dim', type=int, default=32)
    parser.add_argument('--noise_size', type=int, default=100)
    parser.add_argument('--disable_bn', action='store_true', help='Disable Batch Normalization(BN)')

    # Training hyper-parameters
    parser.add_argument('--num_epochs', type=int, default=40)
    parser.add_argument('--batch_size', type=int, default=16, help='The number of images in a batch.')
    parser.add_argument('--num_workers', type=int, default=0, help='The number of threads to use for the DataLoader.')
    parser.add_argument('--lr', type=float, default=0.0003, help='The learning rate (default 0.0003)')
    parser.add_argument('--beta1', type=float, default=0.5)
    parser.add_argument('--beta2', type=float, default=0.999)

    # Data sources
    parser.add_argument('--emoji', type=str, default='Apple', choices=['Apple', 'Facebook', 'Windows'], help='Choose the type of emojis to generate.')

    # Directories and checkpoint/sample iterations
    parser.add_argument('--checkpoint_dir', type=str, default='./checkpoints_vanilla')
    parser.add_argument('--sample_dir', type=str, default='./samples_vanilla')
    parser.add_argument('--log_step', type=int , default=10)
    parser.add_argument('--sample_every', type=int , default=200)
    parser.add_argument('--checkpoint_every', type=int , default=400)

    # GPU or CPU
    parser.add_argument('--disable-cuda', action='store_true', help='Disable CUDA')
    # GAN training object:
    parser.add_argument('--GAN_type', type=str, default='WGANGP', choices=['LSGAN','WGAN','WGANGP'], help='Choose the type of GAN')
    # optmizer
    parser.add_argument('--optimizer', type=str, default='Adam', choices=['Adam','RMSProp'], help='Choose the type of Optimizer')
    return parser


if __name__ == '__main__':

    parser = create_parser()
    opts = parser.parse_args()
    opts.device = None
    if not opts.disable_cuda and torch.cuda.is_available():
        opts.device = torch.device('cuda')
    else:
        opts.device = torch.device('cpu')

    batch_size = opts.batch_size

    print(opts)
    main(opts)
