# Path to the kernel source tree you are using with virtme
KDIR := /home/ubuntu/FlightSize/linux  # Assumes your project is at ~/project/ and the kernel is at ~/linux

# If your project is somewhere else, use an absolute path:
# KDIR := /path/to/your/custom/linux

obj-m += tcp_monitor.o

all:
	make -C $(KDIR) M=$(PWD) modules

clean:
	make -C $(KDIR) M=$(PWD) clean