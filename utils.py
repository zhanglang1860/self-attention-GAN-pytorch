import cv2
import glob
import imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
import shutil
import torch
import torchvision.datasets as dset

from torchvision import transforms


def make_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)


def denorm(x):
    out = (x + 1) / 2
    return out.clamp_(0, 1)


def write_config_to_file(config, save_path):
    with open(os.path.join(save_path, 'config.txt'), 'w') as file:
        for arg in vars(config):
            file.write(str(arg) + ': ' + str(getattr(config, arg)) + '\n')


def copy_scripts(dst):
    for file in glob.glob('*.py'):
        shutil.copy(file, dst)


def make_transform(resize=True, imsize=128, centercrop=False, centercrop_size=128, totensor=True, tanh_scale=True, normalize=False):
        options = []
        if resize:
            options.append(transforms.Resize((imsize, imsize)))
        if centercrop:
            options.append(transforms.CenterCrop(centercrop_size))
        if totensor:
            options.append(transforms.ToTensor())
        if tanh_scale:
            f = lambda x: x*2 - 1
            options.append(transforms.Lambda(f))
        if normalize:
            options.append(transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)))
        transform = transforms.Compose(options)
        return transform


def make_dataloader(batch_size, dataset_type, data_path, shuffle=True, num_workers=4, drop_last=True,
                    resize=True, imsize=128, centercrop=False, centercrop_size=128, totensor=True, normalize=True):
    # Make transform
    transform = make_transform(resize=resize, imsize=imsize,
                               centercrop=centercrop, centercrop_size=centercrop_size,
                               totensor=totensor, normalize=normalize)
    # Make dataset
    if dataset_type in ['folder', 'imagenet', 'lfw']:
        # folder dataset
        assert os.path.exists(data_path), "data_path does not exist! Given: " + data_path
        dataset = dset.ImageFolder(root=data_path, transform=transform)
        num_of_classes = len(os.listdir(data_path))
    elif dataset_type == 'lsun':
        assert os.path.exists(data_path), "data_path does not exist! Given: " + data_path
        dataset = dset.LSUN(root=data_path, classes=['bedroom_train'], transform=transform)
        num_of_classes = 1
    elif dataset_type == 'cifar10':
        assert os.path.exists(data_path), "data_path does not exist! Given: " + data_path
        dataset = dset.CIFAR10(root=data_path, download=True, transform=transform)
        num_of_classes = 10
    elif dataset_type == 'fake':
        dataset = dset.FakeData(image_size=(3, centercrop_size, centercrop_size), transform=transforms.ToTensor())
        num_of_classes = 10
    assert dataset
    print("Data found! # of classes =", num_of_classes, ", # of images =", len(dataset))
    # Make dataloader from dataset
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers, drop_last=drop_last)
    return dataloader, num_of_classes


def make_gif(image, iteration_number, save_path, model_name, max_frames_per_gif=100):

    # Make gif
    gif_frames = []

    # Read old gif frames
    try:
        gif_frames_reader = imageio.get_reader(os.path.join(save_path, model_name + ".gif"))
        for frame in gif_frames_reader:
            gif_frames.append(frame[:, :, :3])
    except:
        pass

    # Append new frame
    im = cv2.putText(np.concatenate((np.zeros((32, image.shape[1], image.shape[2])), image), axis=0),
                     'iter %s' % str(iteration_number), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1, cv2.LINE_AA).astype('uint8')
    gif_frames.append(im)

    # If frames exceeds, save as different file
    if len(gif_frames) > max_frames_per_gif:
        print("Splitting the GIF...")
        gif_frames_00 = gif_frames[:max_frames_per_gif]
        num_of_gifs_already_saved = len(glob.glob(os.path.join(save_path, model_name + "_*.gif")))
        print("Saving", os.path.join(save_path, model_name + "_%05d.gif" % (num_of_gifs_already_saved)))
        imageio.mimsave(os.path.join(save_path, model_name + "_%05d.gif" % (num_of_gifs_already_saved)), gif_frames_00)
        gif_frames = gif_frames[max_frames_per_gif:]

    # Save gif
    # print("Saving", os.path.join(save_path, model_name + ".gif"))
    imageio.mimsave(os.path.join(save_path, model_name + ".gif"), gif_frames)


def make_plots(G_losses, D_losses, D_losses_real, D_losses_fake, D_xs, D_Gz_trainDs, D_Gz_trainGs, log_step, save_path, init_epoch=0):
    iters = np.arange(len(D_losses))*log_step + init_epoch
    fig = plt.figure(figsize=(20, 20))
    plt.subplot(311)
    plt.plot(iters, np.zeros(iters.shape), 'k--', alpha=0.5)
    plt.plot(iters, G_losses, color='C0', label='G')
    plt.legend()
    plt.title("Generator loss")
    plt.xlabel("Iterations")
    # fig.canvas.draw()
    # x_tick_labels = [item.get_text() for item in plt.gca().get_xticklabels()]
    # new_x_tick_labels = []
    # for x_tick_label in x_tick_labels:
    #     try:
    #         new_x_tick_labels.append(int(x_tick_label) + init_epoch)
    #     except:
    #         new_x_tick_labels.append(x_tick_label)
    # plt.gca().set_xticklabels(new_x_tick_labels)
    plt.subplot(312)
    plt.plot(iters, np.zeros(iters.shape), 'k--', alpha=0.5)
    plt.plot(iters, D_losses_real, color='C1', alpha=0.7, label='D_real')
    plt.plot(iters, D_losses_fake, color='C2', alpha=0.7, label='D_fake')
    plt.plot(iters, D_losses, color='C0', alpha=0.7, label='D')
    plt.legend()
    plt.title("Discriminator loss")
    plt.xlabel("Iterations")
    # fig.canvas.draw()
    # x_tick_labels = [item.get_text() for item in plt.gca().get_xticklabels()]
    # new_x_tick_labels = []
    # for x_tick_label in x_tick_labels:
    #     try:
    #         new_x_tick_labels.append(int(x_tick_label) + init_epoch)
    #     except:
    #         new_x_tick_labels.append(x_tick_label)
    # plt.gca().set_xticklabels(new_x_tick_labels)
    plt.subplot(313)
    plt.plot(iters, np.zeros(iters.shape), 'k--', alpha=0.5)
    plt.plot(iters, np.ones(iters.shape), 'k--', alpha=0.5)
    plt.plot(iters, D_xs, alpha=0.7, label='D(x)')
    plt.plot(iters, D_Gz_trainDs, alpha=0.7, label='D(G(z))_trainD')
    plt.plot(iters, D_Gz_trainGs, alpha=0.7, label='D(G(z))_trainG')
    plt.legend()
    plt.title("D(x), D(G(z))")
    plt.xlabel("Iterations")
    plt.savefig(os.path.join(save_path, "plots.png"))
    plt.clf()
    plt.close()


def save_ckpt(sagan_obj, final=False):
    if not final:
        torch.save({
                    'step': sagan_obj.step,
                    'G_state_dict': sagan_obj.G.state_dict(),
                    'G_optimizer_state_dict': sagan_obj.G_optimizer.state_dict(),
                    'D_state_dict': sagan_obj.D.state_dict(),
                    'D_optimizer_state_dict': sagan_obj.D_optimizer.state_dict(),
                    }, os.path.join(sagan_obj.model_weights_path, 'ckpt_{:07d}.pth'.format(sagan_obj.step)))
    else:
        # Save final
        torch.save({
                    'step': sagan_obj.step,
                    'G_state_dict': sagan_obj.G.state_dict(),
                    'G_optimizer_state_dict': sagan_obj.G_optimizer.state_dict(),
                    'D_state_dict': sagan_obj.D.state_dict(),
                    'D_optimizer_state_dict': sagan_obj.D_optimizer.state_dict(),
                    }, os.path.join(sagan_obj.model_weights_path, '{}_final_state_dict_ckpt_{}.pth'.format(sagan_obj.name, sagan_obj.step)))
        torch.save({
                    'step': sagan_obj.step,
                    'G': sagan_obj.G,
                    'G_optimizer': sagan_obj.G_optimizer,
                    'D': sagan_obj.D,
                    'D_optimizer': sagan_obj.D_optimizer,
                    }, os.path.join(sagan_obj.model_weights_path, '{}_final_model_ckpt_{}.pth'.format(sagan_obj.name, sagan_obj.step)))


def load_pretrained_model(sagan_obj):
    # Check for path
    assert os.path.exists(sagan_obj.pretrained_model), "Path of .pth pretrained_model doesn't exist! Given: " + sagan_obj.pretrained_model
    checkpoint = torch.load(sagan_obj.pretrained_model)
    # If we know it is a state_dict (instead of complete model)
    if sagan_obj.state_dict_or_model == 'state_dict':
        sagan_obj.start = checkpoint['step'] + 1
        sagan_obj.G.load_state_dict(checkpoint['G_state_dict'])
        sagan_obj.G_optimizer.load_state_dict(checkpoint['G_optimizer_state_dict'])
        sagan_obj.D.load_state_dict(checkpoint['D_state_dict'])
        sagan_obj.D_optimizer.load_state_dict(checkpoint['D_optimizer_state_dict'])
    # Else, if we know it is a complete model (and not just state_dict)
    elif sagan_obj.state_dict_or_model == 'model':
        sagan_obj.start = checkpoint['step'] + 1
        sagan_obj.G = torch.load(checkpoint['G']).to(sagan_obj.device)
        sagan_obj.G_optimizer = torch.load(checkpoint['G_optimizer'])
        sagan_obj.D = torch.load(checkpoint['D']).to(sagan_obj.device)
        sagan_obj.D_optimizer = torch.load(checkpoint['D_optimizer'])
    # Else try for complete model
    else:
        try:
            sagan_obj.start = checkpoint['step'] + 1
            sagan_obj.G.load_state_dict(checkpoint['G_state_dict'])
            sagan_obj.G_optimizer.load_state_dict(checkpoint['G_optimizer_state_dict'])
            sagan_obj.D.load_state_dict(checkpoint['D_state_dict'])
            sagan_obj.D_optimizer.load_state_dict(checkpoint['D_optimizer_state_dict'])
        except:
            sagan_obj.start = checkpoint['step'] + 1
            sagan_obj.G = torch.load(checkpoint['G']).to(sagan_obj.device)
            sagan_obj.G_optimizer = torch.load(checkpoint['G_optimizer'])
            sagan_obj.D = torch.load(checkpoint['D']).to(sagan_obj.device)
            sagan_obj.D_optimizer = torch.load(checkpoint['D_optimizer'])


def check_for_CUDA(sagan_obj):
    if not sagan_obj.disable_cuda and torch.cuda.is_available():
        print("CUDA is available!")
        sagan_obj.device = torch.device('cuda')
    else:
        print("Cuda is NOT available, running on CPU.")
        sagan_obj.device = torch.device('cpu')

    if torch.cuda.is_available() and sagan_obj.disable_cuda:
        print("WARNING: You have a CUDA device, so you should probably run without --disable_cuda")

