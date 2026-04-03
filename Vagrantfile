# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "fact-cad/FACT-master"  # base image
  config.vm.network "forwarded_port", guest: 5000, host: 5000  # listen port for FACT

  config.vm.provider "virtualbox" do |vb|
    vb.gui = false  # suppress the virtualbox gui popping up on machine start
    vb.cpus = 12  # assign 12 CPU cores to the VM (4 vCPU min)
    vb.memory = 16384 # assign 16GB RAM to the VM (8GB min)
  end
end