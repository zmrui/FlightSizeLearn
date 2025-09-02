#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/kobject.h>
#include <linux/sysfs.h>
#include <linux/fs.h>
#include <linux/string.h>
#include <linux/spinlock.h>
#include <linux/kprobes.h> // <-- For kprobes

// --- The shared data and its protection ---
static u32 ml_flight_size;
static DEFINE_SPINLOCK(fs_lock);

// --- The 'kobject' that will represent our directory in /sys ---
static struct kobject *ml_tcp_kobj;

// --- The 'store' function (writes from userspace) ---
static ssize_t flight_size_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count)
{
    u32 temp_fs;
    int ret = kstrtou32(buf, 10, &temp_fs);
    if (ret < 0) return ret;

    spin_lock_bh(&fs_lock);
    ml_flight_size = temp_fs;
    spin_unlock_bh(&fs_lock);

    pr_info("ml_flight_size updated to: %u\n", temp_fs);
    return count;
}

// --- The 'show' function (reads from userspace) ---
static ssize_t flight_size_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf)
{
    u32 temp_fs;
    spin_lock_bh(&fs_lock);
    temp_fs = ml_flight_size;
    spin_unlock_bh(&fs_lock);
    return sysfs_emit(buf, "%u\n", temp_fs);
}

static struct kobj_attribute flight_size_attribute = __ATTR(flight_size, 0600, flight_size_show, flight_size_store);

// =========================================================================
// == KERNEL-SIDE READER (CONSUMER)                                       ==
// =========================================================================

/**
 * ml_tcp_get_flight_size - Safely get the current ML-predicted flight size.
 *
 * This function is exported to be used by other kernel parts (e.g., kprobes).
 * It uses a spinlock to ensure it reads a stable value.
 */
u32 ml_tcp_get_flight_size(void)
{
    u32 temp_fs;
    spin_lock_bh(&fs_lock);
    temp_fs = ml_flight_size;
    spin_unlock_bh(&fs_lock);
    return temp_fs;
}
EXPORT_SYMBOL(ml_tcp_get_flight_size); // <-- Make function public

// --- Kprobe Implementation to READ the value ---
static struct kprobe kp;

// This is the function that will run when the probed function is called
static int handler_pre(struct kprobe *p, struct pt_regs *regs)
{
    // 1. READ the value from our exported function
    u32 current_fs = ml_tcp_get_flight_size();

    // 2. USE the value (for now, just print it)
    // NOTE: Don't print too often in real code! This is for demonstration.
    pr_info("KPROBE: Reading flight_size from tcp_sendmsg context: %u\n", current_fs);

    // Here you would add your logic to influence TCP,
    // e.g., by changing a value in a socket struct (`struct sock *sk`).

    return 0;
}

// =========================================================================

// --- Module Init and Exit ---
static int __init ml_tcp_init(void)
{
    int ret;
    pr_info("Loading ml_tcp_sysfs module\n");

    ml_tcp_kobj = kobject_create_and_add("ml_tcp", kernel_kobj);
    if (!ml_tcp_kobj) return -ENOMEM;

    ret = sysfs_create_file(ml_tcp_kobj, &flight_size_attribute.attr);
    if (ret) {
        kobject_put(ml_tcp_kobj);
        return ret;
    }
    pr_info("Sysfs file created: /sys/kernel/ml_tcp/flight_size\n");

    // --- Register the kprobe ---
    kp.symbol_name = "tcp_sendmsg"; // Function to probe
    kp.pre_handler = handler_pre;
    ret = register_kprobe(&kp);
    if (ret < 0) {
        pr_err("Failed to register kprobe: %d\n", ret);
        // Cleanup sysfs file on failure
        sysfs_remove_file(ml_tcp_kobj, &flight_size_attribute.attr);
        kobject_put(ml_tcp_kobj);
        return ret;
    }
    pr_info("Kprobe registered on %s\n", kp.symbol_name);

    return 0;
}

static void __exit ml_tcp_exit(void)
{
    unregister_kprobe(&kp);
    pr_info("Kprobe unregistered\n");

    sysfs_remove_file(ml_tcp_kobj, &flight_size_attribute.attr);
    kobject_put(ml_tcp_kobj);

    pr_info("ml_tcp_sysfs module unloaded\n");
}

module_init(ml_tcp_init);
module_exit(ml_tcp_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("Asynchronous flight size update via sysfs and reader via kprobe");